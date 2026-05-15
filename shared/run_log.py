"""Append-only run log for engine calls.

One JSONL file per engine in `logs/<engine>.jsonl`. Schema is documented in
logs/README.md. This module is the single point of write — engines and flows
should call `append_run()` and never touch the files directly.
"""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import threading
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


_LOCK = threading.Lock()


@dataclass
class RunEntry:
    ts: str
    engine: str
    flow: str
    brand: str
    run_id: str
    model: str
    params: dict[str, Any]
    status: str
    elapsed_s: float
    cost_estimate_usd: Optional[float] = None
    cost_actual_usd: Optional[float] = None
    asset_id: Optional[str] = None
    video_path: Optional[str] = None
    error: Optional[str] = None


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_run(logs_root: pathlib.Path, entry: RunEntry) -> None:
    """Append one entry to logs/<engine>.jsonl. Thread-safe."""
    logs_root.mkdir(parents=True, exist_ok=True)
    path = logs_root / f"{entry.engine}.jsonl"
    line = json.dumps(asdict(entry), ensure_ascii=False) + "\n"
    with _LOCK:
        with path.open("a", encoding="utf-8") as f:
            f.write(line)


def read_all(logs_root: pathlib.Path, engine: Optional[str] = None) -> list[dict]:
    """Read all entries from one or every engine ledger."""
    entries: list[dict] = []
    if not logs_root.exists():
        return entries
    files = (
        [logs_root / f"{engine}.jsonl"] if engine else sorted(logs_root.glob("*.jsonl"))
    )
    for path in files:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries
