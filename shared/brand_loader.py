"""Load brand.md files and parse YAML-frontmatter + markdown body."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass


@dataclass
class Brand:
    slug: str
    name: str
    tagline: str
    positioning: str
    body: str
    path: pathlib.Path

    @property
    def system_block(self) -> str:
        """The chunk of brand.md fed verbatim to the prompt-builder."""
        return self.body.strip()


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end == -1:
        return {}, raw
    header = raw[3:end].strip()
    body = raw[end + 4 :].lstrip("\n")
    meta: dict[str, str] = {}
    for line in header.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    return meta, body


def load_brand(slug: str, brands_root: pathlib.Path) -> Brand:
    path = brands_root / slug / "brand.md"
    if not path.exists():
        raise FileNotFoundError(
            f"Brand '{slug}' not found at {path}. Add brands/{slug}/brand.md first."
        )
    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(raw)
    return Brand(
        slug=slug,
        name=meta.get("name", slug.title()),
        tagline=meta.get("tagline", ""),
        positioning=meta.get("positioning", ""),
        body=body,
        path=path,
    )
