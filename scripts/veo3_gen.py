#!/usr/bin/env python3
"""Veo 3 image-to-video wrapper.

Calls the Gemini API's Veo 3 long-running endpoint with a reference image and
a prompt, polls until the operation completes, then downloads the resulting
mp4 next to a meta.json descriptor.

Usage:
    GEMINI_API_KEY=... python3 scripts/veo3_gen.py \
        --image references/slot1_hero.jpg \
        --prompt "Editorial product film ..." \
        --out-dir output/2026-05-15_12-00/veo3 \
        --duration 8 --aspect 9:16
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
import urllib.parse
import urllib.request
from typing import Optional


DEFAULT_MODEL = "veo-3.1-generate-preview"
TRANSIENT_OP_CODES = {8, 14}  # RESOURCE_EXHAUSTED, UNAVAILABLE
API_BASE = "https://generativelanguage.googleapis.com/v1beta"
ASPECT_CHOICES = ["9:16", "16:9", "1:1"]
DURATION_CHOICES = [4, 6, 8]


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _http(
    method: str,
    url: str,
    *,
    api_key: str,
    body: Optional[bytes] = None,
    timeout: int = 180,
    accept_binary: bool = False,
) -> bytes:
    headers = {"x-goog-api-key": api_key}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} on {method} {url}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error on {method} {url}: {exc}") from exc


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


def start_operation(
    *,
    model: str,
    api_key: str,
    prompt: str,
    image_path: pathlib.Path,
    aspect: str,
    duration: int,
    timeout: int,
) -> str:
    img_bytes = image_path.read_bytes()
    payload = {
        "instances": [
            {
                "prompt": prompt,
                "image": {
                    "bytesBase64Encoded": base64.b64encode(img_bytes).decode("ascii"),
                    "mimeType": _infer_mime(image_path),
                },
            }
        ],
        "parameters": {
            "aspectRatio": aspect,
            "durationSeconds": duration,
            "personGeneration": "allow_adult",
            "sampleCount": 1,
        },
    }
    url = f"{API_BASE}/models/{model}:predictLongRunning"
    raw = _http(
        "POST",
        url,
        api_key=api_key,
        body=json.dumps(payload).encode("utf-8"),
        timeout=timeout,
    )
    data = json.loads(raw.decode("utf-8"))
    name = data.get("name")
    if not name:
        raise RuntimeError(f"No operation name in response: {data}")
    return name


def poll_operation(
    *,
    name: str,
    api_key: str,
    timeout: int,
    poll_interval: float,
    max_wait: float,
) -> dict:
    url = f"{API_BASE}/{name}"
    deadline = time.monotonic() + max_wait
    while True:
        raw = _http("GET", url, api_key=api_key, timeout=timeout)
        data = json.loads(raw.decode("utf-8"))
        if data.get("done"):
            return data
        if time.monotonic() > deadline:
            raise RuntimeError(f"Operation {name} did not finish within {max_wait}s")
        time.sleep(poll_interval)


def _find_video_uri(op_response: dict) -> Optional[str]:
    """Walk the operation response and return the first video URI we can find."""
    resp = op_response.get("response", {})
    # Veo response shapes vary slightly across previews; try several paths.
    paths = [
        ("generateVideoResponse", "generatedSamples"),
        ("generatedSamples",),
        ("predictions",),
    ]
    for path in paths:
        node = resp
        for key in path:
            if isinstance(node, dict):
                node = node.get(key)
            else:
                node = None
                break
        if isinstance(node, list) and node:
            for item in node:
                if not isinstance(item, dict):
                    continue
                video = item.get("video") or item
                if isinstance(video, dict):
                    uri = video.get("uri") or video.get("videoUri")
                    if uri:
                        return uri
                    b64 = video.get("bytesBase64Encoded") or video.get("data")
                    if b64:
                        return f"data:base64,{b64}"
    return None


def download_video(uri: str, *, api_key: str, dest: pathlib.Path, timeout: int) -> None:
    if uri.startswith("data:base64,"):
        dest.write_bytes(base64.b64decode(uri.split(",", 1)[1]))
        return
    # Append API key for Gemini file URIs that require it
    sep = "&" if "?" in uri else "?"
    url = uri if "key=" in uri else f"{uri}{sep}key={urllib.parse.quote(api_key)}"
    raw = _http("GET", url, api_key=api_key, timeout=timeout, accept_binary=True)
    dest.write_bytes(raw)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Veo 3 image-to-video generator.")
    p.add_argument("--image", required=True, help="Reference product image.")
    p.add_argument("--prompt", required=True, help="Video prompt.")
    p.add_argument("--out-dir", required=True, help="Output directory.")
    p.add_argument(
        "--model",
        default=os.environ.get("VEO_MODEL", DEFAULT_MODEL),
        help=f"Veo model id. Default: {DEFAULT_MODEL}",
    )
    p.add_argument("--aspect", default="9:16", choices=ASPECT_CHOICES)
    p.add_argument("--duration", type=int, default=8, choices=DURATION_CHOICES)
    p.add_argument(
        "--api-key", default=os.environ.get("GEMINI_API_KEY", ""),
    )
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--poll-interval", type=float, default=10.0)
    p.add_argument("--max-wait", type=float, default=600.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print("Missing GEMINI_API_KEY", file=sys.stderr)
        return 2

    image_path = pathlib.Path(args.image)
    if not image_path.exists():
        print(f"Image not found: {image_path}", file=sys.stderr)
        return 2

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(
        f"[veo3] model={args.model} aspect={args.aspect} duration={args.duration}s"
    )
    started_at = time.monotonic()

    op = None
    op_name = None
    op_attempt = 1
    op_max_attempts = 3
    op_retry_delay = 30.0
    while op_attempt <= op_max_attempts:
        try:
            op_name = start_operation(
                model=args.model,
                api_key=args.api_key,
                prompt=args.prompt,
                image_path=image_path,
                aspect=args.aspect,
                duration=args.duration,
                timeout=args.timeout,
            )
            print(f"[veo3] operation: {op_name} (attempt {op_attempt}/{op_max_attempts})")
            op = poll_operation(
                name=op_name,
                api_key=args.api_key,
                timeout=args.timeout,
                poll_interval=args.poll_interval,
                max_wait=args.max_wait,
            )
        except Exception as exc:
            print(f"[veo3] ERROR: {exc}", file=sys.stderr)
            return 1
        err = op.get("error") if isinstance(op, dict) else None
        if not err:
            break
        code = err.get("code")
        message = err.get("message", "")
        if code in TRANSIENT_OP_CODES and op_attempt < op_max_attempts:
            print(
                f"[veo3] transient op error (code={code}): {message}. "
                f"Retrying in {op_retry_delay:.0f}s.",
                file=sys.stderr,
            )
            time.sleep(op_retry_delay)
            op_attempt += 1
            op_retry_delay = min(120.0, op_retry_delay * 2)
            continue
        print(f"[veo3] operation error (code={code}): {message}", file=sys.stderr)
        return 1

    if op is None or "error" in op:
        print(
            f"[veo3] gave up after {op_max_attempts} attempts: "
            f"{op and op.get('error')}",
            file=sys.stderr,
        )
        return 1

    uri = _find_video_uri(op)
    if not uri:
        print(
            f"[veo3] no video uri in response: {json.dumps(op)[:1000]}",
            file=sys.stderr,
        )
        return 1

    video_path = out_dir / f"veo3_{ts}.mp4"
    try:
        download_video(uri, api_key=args.api_key, dest=video_path, timeout=args.timeout)
    except Exception as exc:
        print(f"[veo3] download failed: {exc}", file=sys.stderr)
        return 1

    elapsed = time.monotonic() - started_at
    meta = {
        "engine": "veo3",
        "model": args.model,
        "timestamp": ts,
        "image": str(image_path),
        "prompt": args.prompt,
        "aspect": args.aspect,
        "duration_seconds": args.duration,
        "elapsed_seconds": round(elapsed, 1),
        "operation": op_name,
        "video": str(video_path),
    }
    meta_path = out_dir / f"veo3_{ts}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[veo3] saved: {video_path} ({elapsed:.1f}s)")
    print(f"[veo3] meta:  {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
