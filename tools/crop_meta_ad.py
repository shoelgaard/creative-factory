#!/usr/bin/env python3
"""Crop Meta Ad Library screenshots down to just the ad creative.

Strategy: convert to grayscale, compute per-row variance. The ad creative is
the longest contiguous run of high-variance rows. Chrome (white background +
text) has low variance per row.

Usage:
    python3 tools/crop_meta_ad.py path/to/screenshot.png
    python3 tools/crop_meta_ad.py "brands/persillo/references/templates/"   # all .png in a dir

Output: <stem>__crop.png next to the original. Originals untouched.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from PIL import Image


def _row_variance(gray: Image.Image) -> list[float]:
    px = list(gray.getdata())
    w, h = gray.size
    out = [0.0] * h
    for y in range(h):
        row = px[y * w : (y + 1) * w]
        m = sum(row) / w
        out[y] = sum((p - m) ** 2 for p in row) / w
    return out


def _col_variance(gray: Image.Image) -> list[float]:
    px = list(gray.getdata())
    w, h = gray.size
    out = [0.0] * w
    for x in range(w):
        col = [px[y * w + x] for y in range(h)]
        m = sum(col) / h
        out[x] = sum((p - m) ** 2 for p in col) / h
    return out


def _longest_high_variance_span(values: list[float], threshold: float) -> tuple[int, int]:
    best_start = best_end = 0
    cur_start = None
    for i, v in enumerate(values):
        if v >= threshold:
            if cur_start is None:
                cur_start = i
        else:
            if cur_start is not None:
                if i - cur_start > best_end - best_start:
                    best_start, best_end = cur_start, i
                cur_start = None
    if cur_start is not None and len(values) - cur_start > best_end - best_start:
        best_start, best_end = cur_start, len(values)
    return best_start, best_end


def _row_mean(gray: Image.Image) -> list[float]:
    px = list(gray.getdata())
    w, h = gray.size
    out = [0.0] * h
    for y in range(h):
        row = px[y * w : (y + 1) * w]
        out[y] = sum(row) / w
    return out


def _col_mean(gray: Image.Image) -> list[float]:
    px = list(gray.getdata())
    w, h = gray.size
    out = [0.0] * w
    for x in range(w):
        col = [px[y * w + x] for y in range(h)]
        out[x] = sum(col) / h
    return out


def _longest_non_chrome_span(means: list[float], chrome_thr: float) -> tuple[int, int]:
    """Find the longest contiguous run of rows/cols whose mean brightness is
    below chrome_thr (i.e. NOT chrome / not nearly-white).
    """
    best_start = best_end = 0
    cur_start = None
    for i, m in enumerate(means):
        if m < chrome_thr:
            if cur_start is None:
                cur_start = i
        else:
            if cur_start is not None:
                if i - cur_start > best_end - best_start:
                    best_start, best_end = cur_start, i
                cur_start = None
    if cur_start is not None and len(means) - cur_start > best_end - best_start:
        best_start, best_end = cur_start, len(means)
    return best_start, best_end


def crop_one(path: pathlib.Path, *, chrome_thr: float = 235.0) -> pathlib.Path | None:
    """Crop by finding the largest contiguous non-chrome block.

    Meta Ad Library chrome is always near-white (#FFF or #F0F0F0). A row whose
    mean brightness >= chrome_thr is treated as chrome. The longest contiguous
    block of below-threshold rows = the ad creative.
    """
    img = Image.open(path).convert("RGB")
    gray = img.convert("L").resize((min(img.width, 400), min(img.height, 800)))
    sx = img.width / gray.width
    sy = img.height / gray.height

    row_mean = _row_mean(gray)
    col_mean = _col_mean(gray)

    y0, y1 = _longest_non_chrome_span(row_mean, chrome_thr)
    x0, x1 = _longest_non_chrome_span(col_mean, chrome_thr)

    # If the column scan fails (mostly-light creative), use full width
    if (x1 - x0) < gray.width * 0.3:
        x0, x1 = 0, gray.width

    box = (
        max(0, int(x0 * sx) - 2),
        max(0, int(y0 * sy) - 2),
        min(img.width, int(x1 * sx) + 2),
        min(img.height, int(y1 * sy) + 2),
    )
    w = box[2] - box[0]
    h = box[3] - box[1]

    # Fallback: if box is still suspect (creative is very light, e.g. white-on-white),
    # use a fixed-region crop of the middle 60% vertically, 90% horizontally.
    if w < img.width * 0.3 or h < img.height * 0.25:
        print(
            f"[crop] {path.name} → fallback fixed-region (heuristic gave w={w} h={h}).",
            file=sys.stderr,
        )
        fy0 = int(img.height * 0.22)
        fy1 = int(img.height * 0.80)
        fx0 = int(img.width * 0.05)
        fx1 = int(img.width * 0.95)
        box = (fx0, fy0, fx1, fy1)

    cropped = img.crop(box)
    out = path.with_name(path.stem + "__crop.png")
    cropped.save(out, format="PNG", optimize=True)
    print(f"[crop] {path.name} → {out.name} (box={box}, size={cropped.size})")
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Crop Meta Ad Library screenshots to the ad creative.")
    p.add_argument("targets", nargs="+", help="File(s) or directory(ies) containing PNG screenshots.")
    p.add_argument(
        "--chrome-thr",
        type=float,
        default=235.0,
        help="Brightness above which a row/column is treated as Meta chrome (white background). 0-255.",
    )
    p.add_argument(
        "--skip-already-cropped",
        action="store_true",
        default=True,
        help="Skip files whose name already ends in __crop.png",
    )
    args = p.parse_args()

    paths: list[pathlib.Path] = []
    for t in args.targets:
        tp = pathlib.Path(t).expanduser().resolve()
        if tp.is_dir():
            paths.extend(sorted(tp.glob("*.png")))
        elif tp.is_file():
            paths.append(tp)
        else:
            print(f"[crop] not found: {tp}", file=sys.stderr)

    paths = [p for p in paths if not p.stem.endswith("__crop")] if args.skip_already_cropped else paths
    if not paths:
        print("[crop] no inputs", file=sys.stderr)
        return 2

    fails = 0
    for path in paths:
        try:
            res = crop_one(path, chrome_thr=args.chrome_thr)
            if res is None:
                fails += 1
        except Exception as exc:
            fails += 1
            print(f"[crop] FAILED {path.name}: {exc}", file=sys.stderr)
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
