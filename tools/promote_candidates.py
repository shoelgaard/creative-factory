#!/usr/bin/env python3
"""Copy a statics run's outputs into per-product candidate folders.

Reads each <id>.brief.json in a statics run folder, figures out the variant,
and copies <id>.{jpg,png} into:
    brands/<brand>/references/products/<product>/<variant>/candidates/<ts>/

Also writes an INDEX.md per candidates folder listing each candidate with its
headline / primary / description copy.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys


VARIANT_FOLDER = {
    "gylden": "Gylden",
    "raahvid": "Råhvid",
    "råhvid": "Råhvid",
    "mixed": "Mixed",
    "gylden + råhvid": "Mixed",
    "gylden+råhvid": "Mixed",
}


def _normalise(variant: str) -> str:
    key = variant.strip().lower()
    return VARIANT_FOLDER.get(key, "Mixed")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True, help="Statics run dir containing <id>.jpg + <id>.brief.json")
    p.add_argument("--brand", required=True)
    p.add_argument("--product", required=True, help="Product family folder name (e.g. Grenen)")
    p.add_argument("--ts", default=None, help="Timestamp folder name (default: derived from run-dir's grandparent)")
    args = p.parse_args()

    run_dir = pathlib.Path(args.run_dir).expanduser().resolve()
    if not run_dir.exists():
        print(f"Not found: {run_dir}", file=sys.stderr)
        return 2

    ts = args.ts or run_dir.parents[2].name  # output/<ts>/statics/<brand>/run/
    project_root = pathlib.Path(__file__).resolve().parents[1]
    product_root = project_root / "brands" / args.brand / "references" / "products" / args.product

    briefs = sorted(run_dir.glob("*.brief.json"))
    by_variant: dict[str, list[tuple[pathlib.Path, dict]]] = {}

    for bf in briefs:
        meta = json.loads(bf.read_text(encoding="utf-8"))
        cid = meta["id"]
        variant = _normalise(meta.get("variant", ""))
        # Find image (jpg preferred, png fallback)
        img = None
        for ext in (".jpg", ".png"):
            cand = run_dir / f"{cid}{ext}"
            if cand.exists():
                img = cand
                break
        if not img:
            print(f"[promote] {cid}: no image, skipping", file=sys.stderr)
            continue
        by_variant.setdefault(variant, []).append((img, meta))

    total_copied = 0
    touched_dirs: set[pathlib.Path] = set()

    for variant, items in by_variant.items():
        dest_dir = product_root / variant / "candidates" / ts
        dest_dir.mkdir(parents=True, exist_ok=True)
        touched_dirs.add(dest_dir)

        for img, meta in sorted(items, key=lambda x: x[1]["id"]):
            shutil.copy2(img, dest_dir / img.name)
            # Also copy the brief so INDEX rebuild is self-contained
            brief_src = run_dir / f"{meta['id']}.brief.json"
            if brief_src.exists():
                shutil.copy2(brief_src, dest_dir / brief_src.name)
            total_copied += 1

        print(f"[promote] {variant}: {len(items)} new candidates → {dest_dir.relative_to(project_root)}")

    # Rebuild INDEX.md from ALL briefs in each touched dir
    for dest_dir in touched_dirs:
        variant = dest_dir.parents[1].name
        briefs_present = sorted(dest_dir.glob("*.brief.json"))
        lines = [
            f"# {args.product} / {variant} — candidates ({ts})",
            "",
            "Copy from concepts file. Mark winners with `★` (in your editor or by hand). "
            "When promoted, they move to `brands/<brand>/winners/statics/`.",
            "",
            f"_{len(briefs_present)} candidates total._",
            "",
        ]
        for bf in briefs_present:
            m = json.loads(bf.read_text(encoding="utf-8"))
            cid = m["id"]
            # Prefer jpg, else png
            img_name = None
            for ext in (".jpg", ".png"):
                if (dest_dir / f"{cid}{ext}").exists():
                    img_name = f"{cid}{ext}"
                    break
            if not img_name:
                continue
            lines.extend([
                f"## {cid}",
                f"![{cid}]({img_name})",
                "",
                f"**Headline:** {m.get('headline','')}",
                f"**Primary:** {m.get('primary','')}",
                f"**Description:** {m.get('description','')}",
                f"**Template ref:** `{m.get('template_ref','')}`",
                f"**Copy mode:** {m.get('copy_mode','external')}",
                "",
                "---",
                "",
            ])
        (dest_dir / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"\n[promote] done. {total_copied} files copied across {len(by_variant)} variants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
