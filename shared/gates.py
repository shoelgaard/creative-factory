"""Mandatory confirmation gates.

Borrowed pattern from krusemediallc/arcads-claude-code: never let an expensive
call go through without an explicit human `yes`. Each gate is a separate
question — credit and dialogue do not collapse into one approval.

Gates auto-skip in non-interactive mode (stdin not a TTY) ONLY if the caller
explicitly passes `assume_yes=True`. Otherwise they fail closed.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Iterable


@dataclass
class CreditEstimate:
    engine: str
    model: str
    duration_s: int
    estimate_usd: float
    source: str


def _ask(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        print(f"{prompt}  [assume_yes=True → auto-OK]")
        return True
    if not sys.stdin.isatty():
        print(f"{prompt}  [no TTY, no assume_yes → FAIL CLOSED]", file=sys.stderr)
        return False
    try:
        ans = input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in ("y", "yes", "ja", "j")


def credit_gate(
    estimates: Iterable[CreditEstimate],
    *,
    max_per_run_usd: float | None = None,
    assume_yes: bool = False,
) -> bool:
    """Show cost breakdown, return True if approved."""
    estimates = list(estimates)
    total = sum(e.estimate_usd for e in estimates)

    print("\n=== Credit gate ===")
    for e in estimates:
        print(
            f"  {e.engine:14s}  {e.model:36s}  {e.duration_s}s  "
            f"${e.estimate_usd:>6.2f}   ({e.source})"
        )
    print(f"  {'TOTAL':14s}  {'':36s}  {'':4s}  ${total:>6.2f}")

    if max_per_run_usd is not None and total > max_per_run_usd:
        print(
            f"\n[gate] ABORT: total ${total:.2f} exceeds max_per_run_usd "
            f"${max_per_run_usd:.2f} configured for this brand.",
            file=sys.stderr,
        )
        return False

    return _ask("Proceed with these calls? [y/N]: ", assume_yes)


def dialogue_gate(script_lines: list[str], target_duration_s: int, *, assume_yes: bool = False) -> bool:
    """Show numbered dialogue, word-count vs target duration, require explicit yes."""
    if not script_lines:
        return True

    print("\n=== Dialogue gate ===")
    total_words = 0
    for i, line in enumerate(script_lines, start=1):
        words = len(line.split())
        total_words += words
        print(f"  {i:2d}. ({words:>2d}w) {line}")
    # ~2.5 words/sec is comfortable speaking pace for UGC
    estimated_speak_s = total_words / 2.5
    fit = "✓" if estimated_speak_s <= target_duration_s + 1.0 else "✗ TOO LONG"
    print(
        f"  total: {total_words} words ≈ {estimated_speak_s:.1f}s spoken "
        f"vs target {target_duration_s}s  {fit}"
    )
    return _ask("Approve this dialogue? [y/N]: ", assume_yes)


def still_to_video_gate(still_path: str, *, assume_yes: bool = False) -> bool:
    """Generated a still as start frame. Show its path, require explicit yes before video render."""
    print("\n=== Still → video gate ===")
    print(f"  Generated still: {still_path}")
    print("  Open the file and confirm it is brand-on BEFORE paying for video render.")
    return _ask("Continue to video render with this still? [y/N]: ", assume_yes)
