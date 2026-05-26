#!/usr/bin/env python3
"""Gemini image generation wrapper (Nano Banana).

Synchronous: POST → response with inline base64 image(s). No long-running ops.
Supports multiple reference images via inlineData parts.

Usage (direct):
    GEMINI_API_KEY=... python3 engines/gemini-image/client.py \
        --prompt "Editorial product still life ..." \
        --out output/test/banana_a01.png \
        --aspect 4:5 --size 2K \
        --ref references/product.jpg --ref references/template.png
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import mimetypes
import os
import pathlib
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Optional


DEFAULT_MODEL = "gemini-3.1-flash-image-preview"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ASPECT_CHOICES = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
SIZE_CHOICES = ["512px", "1K", "2K", "4K"]
MIME_TO_EXT = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _infer_mime(path: pathlib.Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime and mime.startswith("image/"):
        return mime
    suf = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(suf, "image/jpeg")


def _ref_part(path: pathlib.Path) -> dict:
    return {
        "inline_data": {
            "mime_type": _infer_mime(path),
            "data": base64.b64encode(path.read_bytes()).decode("ascii"),
        }
    }


def generate(
    *,
    prompt: str,
    refs: list[pathlib.Path],
    api_key: str,
    model: str = DEFAULT_MODEL,
    aspect: str = "4:5",
    size: str = "2K",
    mime: str = "image/png",
    timeout: int = 360,
    max_attempts: int = 3,
    retry_delay: float = 5.0,
) -> tuple[bytes, str]:
    """Returns (image_bytes, image_mime). Retries on transient 5xx errors."""
    parts: list[dict] = [{"text": prompt}]
    for r in refs:
        parts.append(_ref_part(r))

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {"aspectRatio": aspect, "imageSize": size},
        },
    }
    body = json.dumps(payload).encode("utf-8")
    url = API_URL.format(model=model)

    attempt = 1
    delay = retry_delay
    while True:
        req = urllib.request.Request(
            url=url,
            data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
                data = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            transient = exc.code in (429, 500, 502, 503, 504)
            if transient and attempt < max_attempts:
                print(
                    f"[gemini-image] transient HTTP {exc.code} (attempt {attempt}/{max_attempts}). "
                    f"Retrying in {delay:.1f}s.",
                    file=sys.stderr,
                )
                time.sleep(delay)
                attempt += 1
                delay = min(60.0, delay * 2)
                continue
            raise RuntimeError(f"Gemini HTTP {exc.code}: {raw}") from exc
        except urllib.error.URLError as exc:
            if attempt < max_attempts:
                time.sleep(delay)
                attempt += 1
                delay = min(60.0, delay * 2)
                continue
            raise RuntimeError(f"Gemini network error: {exc}") from exc

    # Walk parts for inline image data
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if not inline:
                continue
            b64 = inline.get("data")
            if not b64:
                continue
            mime_out = inline.get("mimeType") or inline.get("mime_type") or "image/png"
            return base64.b64decode(b64), mime_out
    raise RuntimeError(f"No image in Gemini response: {json.dumps(data)[:1000]}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Gemini image generation (Nano Banana).")
    p.add_argument("--prompt", required=True)
    p.add_argument("--out", required=True, help="Output file path (.png).")
    p.add_argument("--model", default=os.environ.get("GEMINI_IMAGE_MODEL", DEFAULT_MODEL))
    p.add_argument("--aspect", default="4:5", choices=ASPECT_CHOICES)
    p.add_argument("--size", default="2K", choices=SIZE_CHOICES)
    p.add_argument("--ref", action="append", default=[], help="Reference image path. Repeatable.")
    p.add_argument("--api-key", default=os.environ.get("GEMINI_API_KEY", ""))
    p.add_argument("--timeout", type=int, default=360)
    p.add_argument("--max-attempts", type=int, default=3)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print("Missing GEMINI_API_KEY", file=sys.stderr)
        return 2

    refs = [pathlib.Path(r).expanduser().resolve() for r in args.ref]
    for r in refs:
        if not r.exists():
            print(f"Ref not found: {r}", file=sys.stderr)
            return 2

    out = pathlib.Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    try:
        img, mime = generate(
            prompt=args.prompt,
            refs=refs,
            api_key=args.api_key,
            model=args.model,
            aspect=args.aspect,
            size=args.size,
            timeout=args.timeout,
            max_attempts=args.max_attempts,
        )
    except Exception as exc:
        print(f"[gemini-image] ERROR: {exc}", file=sys.stderr)
        return 1

    out.write_bytes(img)
    print(f"[gemini-image] saved: {out} ({time.monotonic() - started:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
