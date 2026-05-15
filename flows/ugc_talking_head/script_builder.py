"""Compose a Danish UGC dialogue from brand DNA + brief.

The script_builder is the *interpretive* layer of the flow. It reads the brand's
banned/preferred terms, the structured brief (hook + beats + cta), and emits a
single block of plain text that the actor will speak.

Design rules (from Persillo learnings):
- Sound like a normal Dane, not an AI trying to sound elegant
- The story is about the FEELING the product creates, not the product specs
- Short sentences, pauses, breath. Spoken Danish, not written Danish.
- Never make factual claims about manufacturing country (banned)
- Never use AI-tells from banned-terms list
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass
from typing import Optional

from shared.brand_loader import Brand


@dataclass
class UgcBrief:
    brand: str
    product: str
    persona: str = "auto"
    hook: Optional[str] = None
    beats: Optional[list[str]] = None
    cta: Optional[str] = None


@dataclass
class BuiltScript:
    text: str
    lines: list[str]
    word_count: int
    estimated_seconds: float


WORDS_PER_SECOND = 2.5  # comfortable Danish UGC pace


def _read_banned_terms(brand_slug: str, project_root: pathlib.Path) -> list[str]:
    """Extract bullet items from the '## Banned terms' section of MASTER_CONTEXT.md."""
    path = project_root / "brands" / brand_slug / "MASTER_CONTEXT.md"
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    m = re.search(r"##\s+Banned terms.*?\n(.*?)(?=\n##\s|\Z)", text, re.DOTALL)
    if not m:
        return []
    out: list[str] = []
    for line in m.group(1).splitlines():
        ml = re.match(r"\s*-\s*\"?([^\"]+)\"?", line)
        if ml:
            term = ml.group(1).strip().strip('"').strip()
            if term:
                out.append(term)
    return out


def _violations(script_text: str, banned: list[str]) -> list[str]:
    lower = script_text.lower()
    hits: list[str] = []
    for term in banned:
        if term and term.lower() in lower:
            hits.append(term)
    return hits


def build_script(
    brand: Brand,
    brief: UgcBrief,
    *,
    project_root: pathlib.Path,
) -> BuiltScript:
    lines: list[str] = []

    if brief.hook:
        lines.append(brief.hook.strip())
    if brief.beats:
        lines.extend(b.strip() for b in brief.beats if b.strip())
    if brief.cta:
        lines.append(brief.cta.strip())

    if not lines:
        # Hard fail. We never auto-generate copy — the user writes the words.
        raise ValueError(
            "Empty script: brief has no hook/beats/cta. "
            "Fill in briefs/<brand>/<file>.yaml or pass --hook/--beats/--cta. "
            "I do not auto-write copy."
        )

    text = " ".join(lines)
    word_count = sum(len(ln.split()) for ln in lines)
    est_s = round(word_count / WORDS_PER_SECOND, 1)

    banned = _read_banned_terms(brand.slug, project_root)
    hits = _violations(text, banned)
    if hits:
        # Hard fail before render — caller catches and asks user to rewrite.
        raise ValueError(
            f"Script violates banned-terms list for {brand.slug}: {hits}"
        )

    return BuiltScript(text=text, lines=lines, word_count=word_count, estimated_seconds=est_s)
