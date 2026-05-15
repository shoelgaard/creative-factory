"""Estimate the cost of an engine call.

Strategy:
1. Read logs/<engine>.jsonl for matching (model, params) — return median actual
   cost if any line has cost_actual_usd, else median estimate.
2. Fall back to engines/<engine>/pricing.md table (simple "per-second" parse).
3. Final fallback: hardcoded conservative number with a warning.
"""

from __future__ import annotations

import pathlib
import re
import statistics
from typing import Optional

from .run_log import read_all


# Conservative last-resort floor in USD per second of video
LAST_RESORT_USD_PER_SEC = 0.10


def _from_history(
    logs_root: pathlib.Path, engine: str, model: str, duration_s: int
) -> Optional[float]:
    rows = [
        r
        for r in read_all(logs_root, engine=engine)
        if r.get("model") == model and r.get("status") == "ok"
    ]
    if not rows:
        return None

    actuals = [r["cost_actual_usd"] for r in rows if r.get("cost_actual_usd") is not None]
    if actuals:
        per_sec = statistics.median(
            a / max(r.get("params", {}).get("duration", duration_s), 1)
            for a, r in zip(actuals, rows)
            if r.get("cost_actual_usd") is not None
        )
        return round(per_sec * duration_s, 4)

    estimates = [r["cost_estimate_usd"] for r in rows if r.get("cost_estimate_usd") is not None]
    if estimates:
        per_sec = statistics.median(
            e / max(r.get("params", {}).get("duration", duration_s), 1)
            for e, r in zip(estimates, rows)
            if r.get("cost_estimate_usd") is not None
        )
        return round(per_sec * duration_s, 4)

    return None


_PRICE_LINE = re.compile(r"\|\s*([\w.\-/:]+).*?\$?([\d.]+)\s*\|", re.IGNORECASE)


def _from_pricing_md(
    engines_root: pathlib.Path, engine: str, model: str, duration_s: int
) -> Optional[float]:
    path = engines_root / engine / "pricing.md"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = _PRICE_LINE.search(line)
        if not m:
            continue
        name, price = m.group(1), m.group(2)
        if name and (model.startswith(name) or name in model):
            try:
                per_sec = float(price)
            except ValueError:
                continue
            return round(per_sec * duration_s, 4)
    return None


def estimate(
    *,
    project_root: pathlib.Path,
    engine: str,
    model: str,
    duration_s: int,
) -> tuple[float, str]:
    """Return (estimate_usd, source) for one engine call."""
    logs_root = project_root / "logs"
    engines_root = project_root / "engines"

    hist = _from_history(logs_root, engine, model, duration_s)
    if hist is not None:
        return hist, f"historic median from logs/{engine}.jsonl"

    pricing = _from_pricing_md(engines_root, engine, model, duration_s)
    if pricing is not None:
        return pricing, f"rate table in engines/{engine}/pricing.md"

    return (
        round(LAST_RESORT_USD_PER_SEC * duration_s, 4),
        f"LAST RESORT floor ${LAST_RESORT_USD_PER_SEC}/s — add pricing.md or run history",
    )
