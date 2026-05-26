"""Parse the concept markdown file into structured Concept objects.

The format expected is the one used in `concepts/persillo/grenen-round-1.md`:

    ### [ ] A1 · diptyque-large-candles-wooden-tier · Gylden
    **Visual:** ...
    **Headline:** ...
    **Primary:** ...
    **Description:** ...

Optional fields:
    **CopyMode:** embedded | external          (default: external)
    **EmbedText:** "...text to render in-image..."  (used when CopyMode=embedded)
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Concept:
    id: str
    template_ref: str          # short slug, matches a file in templates/
    variant: str               # Gylden | Råhvid | Mixed | Gylden + Råhvid
    visual: str
    headline: str
    primary: str
    description: str
    copy_mode: str = "external"        # external | embedded
    embed_text: Optional[str] = None
    checkbox_marked: bool = False      # True if `[x]` instead of `[ ]`
    raw_section: str = ""


_HEADER_RE = re.compile(
    r"^###\s+\[\s*([xX ]?)\s*\]\s+(\S+)\s*·\s*([^·]+?)\s*·\s*(.+?)\s*$",
    re.MULTILINE,
)
_FIELD_RE = re.compile(r"\*\*(\w+):\*\*\s+(.+?)(?=\n\*\*\w+:\*\*|\n###|\Z)", re.DOTALL)


def parse_concepts(path: pathlib.Path) -> list[Concept]:
    text = path.read_text(encoding="utf-8")
    concepts: list[Concept] = []

    headers = list(_HEADER_RE.finditer(text))
    for i, m in enumerate(headers):
        section_start = m.start()
        section_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        section = text[section_start:section_end]

        checkbox = m.group(1).strip().lower() == "x"
        cid = m.group(2).strip()
        template_ref = m.group(3).strip()
        variant = m.group(4).strip()

        fields: dict[str, str] = {}
        for fm in _FIELD_RE.finditer(section):
            fields[fm.group(1).strip().lower()] = fm.group(2).strip().rstrip()

        concepts.append(
            Concept(
                id=cid,
                template_ref=template_ref,
                variant=variant,
                visual=fields.get("visual", ""),
                headline=fields.get("headline", ""),
                primary=fields.get("primary", ""),
                description=fields.get("description", ""),
                copy_mode=fields.get("copymode", "external").lower(),
                embed_text=fields.get("embedtext"),
                checkbox_marked=checkbox,
                raw_section=section,
            )
        )
    return concepts


def filter_concepts(
    concepts: list[Concept],
    *,
    only_ids: Optional[list[str]] = None,
    only_checked: bool = False,
) -> list[Concept]:
    if only_ids:
        ids = {c.upper() for c in only_ids}
        return [c for c in concepts if c.id.upper() in ids]
    if only_checked:
        return [c for c in concepts if c.checkbox_marked]
    return concepts
