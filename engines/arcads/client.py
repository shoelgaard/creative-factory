#!/usr/bin/env python3
"""Arcads external-API client.

Currently exposes the actor pipeline:
  list_situations / list_voices  → discovery
  create_script + generate_script + poll_script_videos → render

Auth: prefers `ARCADS_BASIC_AUTH` (pre-encoded 'Basic <base64>' from the dashboard).
Falls back to `ARCADS_API_KEY` (used as Basic username with empty password).
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import pathlib
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional


BASE_URL = "https://external-api.arcads.ai"


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _auth_header() -> str:
    val = os.environ.get("ARCADS_BASIC_AUTH")
    if val:
        return val if val.lower().startswith("basic ") else f"Basic {val}"
    key = os.environ.get("ARCADS_API_KEY")
    if key:
        encoded = base64.b64encode(f"{key}:".encode("utf-8")).decode("ascii")
        return f"Basic {encoded}"
    raise RuntimeError(
        "Arcads auth missing. Set ARCADS_BASIC_AUTH ('Basic <base64>' from the dashboard) "
        "or ARCADS_API_KEY in your .env."
    )


def _http(
    method: str,
    path: str,
    *,
    body: Optional[dict] = None,
    query: Optional[dict] = None,
    timeout: int = 60,
) -> Any:
    url = f"{BASE_URL}{path}"
    if query:
        cleaned = {k: v for k, v in query.items() if v is not None}
        if cleaned:
            url = f"{url}?{urllib.parse.urlencode(cleaned)}"
    headers = {"Authorization": _auth_header(), "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
            raw = r.read()
            if not raw:
                return None
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Arcads HTTP {exc.code} on {method} {path}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Arcads network error on {method} {path}: {exc}") from exc


# ---- Discovery ----

def list_voices(*, gender: Optional[str] = None, language: Optional[str] = None, page_size: int = 50) -> list[dict]:
    resp = _http(
        "GET",
        "/v1/voices",
        query={"gender": gender, "language": language, "pageSize": page_size},
    )
    if isinstance(resp, dict):
        return resp.get("items", resp.get("data", []))
    return resp or []


def list_situations(
    *,
    actor_gender: Optional[str] = None,
    actor_age: Optional[str] = None,
    talking_actor_enabled: Optional[bool] = True,
    page_size: int = 50,
) -> list[dict]:
    resp = _http(
        "GET",
        "/v1/situations",
        query={
            "actorGender": actor_gender,
            "actorAge": actor_age,
            "talkingActorEnabled": str(talking_actor_enabled).lower() if talking_actor_enabled is not None else None,
            "pageSize": page_size,
        },
    )
    if isinstance(resp, dict):
        return resp.get("items", resp.get("data", []))
    return resp or []


def list_products() -> list[dict]:
    resp = _http("GET", "/v1/products")
    if isinstance(resp, dict):
        return resp.get("items", resp.get("data", []))
    return resp or []


# ---- Project / folder ----

def create_folder(*, product_id: str, name: str) -> dict:
    return _http("POST", "/v1/folders", body={"productId": product_id, "name": name})


def create_project(*, product_id: str, folder_id: str, name: str) -> dict:
    return _http(
        "POST", "/v1/projects", body={"productId": product_id, "folderId": folder_id, "name": name}
    )


# ---- Actor-pipeline (scripts) ----

def create_script(
    *,
    name: str,
    text: str,
    project_id: str,
    videos: list[dict],
) -> dict:
    """videos: [{"situationId": "...", "voiceId": "..."} , ...]"""
    return _http(
        "POST",
        "/v1/scripts",
        body={"name": name, "text": text, "projectId": project_id, "videos": videos},
    )


def generate_script(script_id: str) -> bool:
    """Returns True if generation kicked off. Raises on 422 (blocked / no credits)."""
    res = _http("POST", f"/v1/scripts/{script_id}/generate")
    return bool(res) if res is not None else True


def list_script_videos(script_id: str) -> list[dict]:
    resp = _http("GET", f"/v1/scripts/{script_id}/videos")
    if isinstance(resp, dict):
        return resp.get("items", resp.get("data", []))
    return resp or []


def poll_script_videos(
    script_id: str,
    *,
    poll_interval: float = 8.0,
    max_wait: float = 900.0,
) -> list[dict]:
    """Block until all videos have a terminal videoStatus or timeout."""
    deadline = time.monotonic() + max_wait
    last: list[dict] = []
    while True:
        videos = list_script_videos(script_id)
        last = videos
        statuses = [_video_status(v) for v in videos]
        if videos and all(s in {"generated", "uploaded", "failed"} for s in statuses):
            return videos
        if time.monotonic() > deadline:
            raise RuntimeError(f"Arcads script {script_id} did not finish within {max_wait}s")
        time.sleep(poll_interval)


def _video_status(v: dict) -> str:
    """Normalise a VideoDto's status to a single string."""
    vs = v.get("videoStatus")
    if isinstance(vs, dict):
        return (
            vs.get("status")
            or vs.get("state")
            or vs.get("value")
            or "pending"
        )
    if isinstance(vs, str):
        return vs
    return "pending"


# ---- Download ----

def download(url: str, dest: pathlib.Path, *, timeout: int = 180) -> None:
    req = urllib.request.Request(url=url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
        dest.write_bytes(r.read())


# ---- CLI for direct connectivity test ----

def _cli() -> int:
    p = argparse.ArgumentParser(description="Arcads engine smoke-test")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("products")
    sub.add_parser("voices-da", help="List voices filtered to language=da")
    sit = sub.add_parser("situations", help="List talking-actor situations")
    sit.add_argument("--gender", default="female")
    sit.add_argument("--age", default="adult")
    args = p.parse_args()

    if args.cmd == "products":
        print(json.dumps(list_products(), indent=2, ensure_ascii=False))
    elif args.cmd == "voices-da":
        print(json.dumps(list_voices(language="da"), indent=2, ensure_ascii=False))
    elif args.cmd == "situations":
        print(
            json.dumps(
                list_situations(actor_gender=args.gender, actor_age=args.age),
                indent=2,
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
