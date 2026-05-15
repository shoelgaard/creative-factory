#!/usr/bin/env python3
"""Seedance 2.0 image-to-video wrapper via fal.ai.

Submits an image + prompt to fal.ai's bytedance/seedance pro image-to-video
endpoint, polls until ready, then downloads the mp4.

Usage:
    FAL_API_KEY=... python3 scripts/seedance_gen.py \
        --image references/slot1_hero.jpg \
        --prompt "Editorial product film ..." \
        --out-dir output/2026-05-15_12-00/seedance2 \
        --duration 5 --aspect 9:16
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


DEFAULT_ENDPOINT = "fal-ai/bytedance/seedance/v1/pro/image-to-video"
API_BASE = "https://queue.fal.run"
ASPECT_CHOICES = ["9:16", "16:9", "1:1"]


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
) -> bytes:
    headers = {"Authorization": f"Key {api_key}"}
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


def _data_url(path: pathlib.Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "image/jpeg"
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def submit(
    *,
    endpoint: str,
    api_key: str,
    prompt: str,
    image_path: pathlib.Path,
    aspect: str,
    duration: int,
    timeout: int,
) -> str:
    payload = {
        "prompt": prompt,
        "image_url": _data_url(image_path),
        "aspect_ratio": aspect,
        "duration": duration,
        "resolution": "1080p",
    }
    url = f"{API_BASE}/{endpoint}"
    raw = _http(
        "POST",
        url,
        api_key=api_key,
        body=json.dumps(payload).encode("utf-8"),
        timeout=timeout,
    )
    data = json.loads(raw.decode("utf-8"))
    req_id = data.get("request_id") or data.get("requestId")
    if not req_id:
        raise RuntimeError(f"No request_id in fal.ai response: {data}")
    return req_id


def poll(
    *,
    endpoint: str,
    request_id: str,
    api_key: str,
    timeout: int,
    poll_interval: float,
    max_wait: float,
) -> dict:
    status_url = f"{API_BASE}/{endpoint}/requests/{request_id}/status"
    result_url = f"{API_BASE}/{endpoint}/requests/{request_id}"
    deadline = time.monotonic() + max_wait
    while True:
        raw = _http("GET", status_url, api_key=api_key, timeout=timeout)
        data = json.loads(raw.decode("utf-8"))
        status = data.get("status", "")
        if status in ("COMPLETED", "OK"):
            raw2 = _http("GET", result_url, api_key=api_key, timeout=timeout)
            return json.loads(raw2.decode("utf-8"))
        if status in ("FAILED", "ERROR", "CANCELLED"):
            raise RuntimeError(f"fal.ai job failed: {data}")
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"fal.ai request {request_id} did not finish within {max_wait}s"
            )
        time.sleep(poll_interval)


def _find_video_url(result: dict) -> Optional[str]:
    video = result.get("video")
    if isinstance(video, dict):
        return video.get("url")
    for key in ("video_url", "url"):
        v = result.get(key)
        if isinstance(v, str):
            return v
    return None


def download(url: str, dest: pathlib.Path, timeout: int) -> None:
    req = urllib.request.Request(url=url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
        dest.write_bytes(r.read())


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Seedance 2.0 image-to-video via fal.ai")
    p.add_argument("--image", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--endpoint", default=os.environ.get("FAL_ENDPOINT", DEFAULT_ENDPOINT))
    p.add_argument("--aspect", default="9:16", choices=ASPECT_CHOICES)
    p.add_argument("--duration", type=int, default=5)
    p.add_argument(
        "--api-key",
        default=os.environ.get("FAL_API_KEY", os.environ.get("FAL_KEY", "")),
    )
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--poll-interval", type=float, default=5.0)
    p.add_argument("--max-wait", type=float, default=600.0)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print(
            "Missing FAL_API_KEY (or FAL_KEY). Skipping seedance run.",
            file=sys.stderr,
        )
        return 2

    image_path = pathlib.Path(args.image)
    if not image_path.exists():
        print(f"Image not found: {image_path}", file=sys.stderr)
        return 2

    out_dir = pathlib.Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    print(
        f"[seedance2] endpoint={args.endpoint} aspect={args.aspect} "
        f"duration={args.duration}s"
    )
    started_at = time.monotonic()

    try:
        req_id = submit(
            endpoint=args.endpoint,
            api_key=args.api_key,
            prompt=args.prompt,
            image_path=image_path,
            aspect=args.aspect,
            duration=args.duration,
            timeout=args.timeout,
        )
        print(f"[seedance2] request_id: {req_id}")
        result = poll(
            endpoint=args.endpoint,
            request_id=req_id,
            api_key=args.api_key,
            timeout=args.timeout,
            poll_interval=args.poll_interval,
            max_wait=args.max_wait,
        )
    except Exception as exc:
        print(f"[seedance2] ERROR: {exc}", file=sys.stderr)
        return 1

    video_url = _find_video_url(result)
    if not video_url:
        print(
            f"[seedance2] no video url in result: {json.dumps(result)[:1000]}",
            file=sys.stderr,
        )
        return 1

    video_path = out_dir / f"seedance2_{ts}.mp4"
    try:
        download(video_url, video_path, timeout=args.timeout)
    except Exception as exc:
        print(f"[seedance2] download failed: {exc}", file=sys.stderr)
        return 1

    elapsed = time.monotonic() - started_at
    meta = {
        "engine": "seedance2",
        "endpoint": args.endpoint,
        "timestamp": ts,
        "image": str(image_path),
        "prompt": args.prompt,
        "aspect": args.aspect,
        "duration_seconds": args.duration,
        "elapsed_seconds": round(elapsed, 1),
        "request_id": req_id,
        "video": str(video_path),
        "source_url": video_url,
    }
    meta_path = out_dir / f"seedance2_{ts}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[seedance2] saved: {video_path} ({elapsed:.1f}s)")
    print(f"[seedance2] meta:  {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
