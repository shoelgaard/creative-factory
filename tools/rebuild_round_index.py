#!/usr/bin/env python3
"""Rebuild README.md + QUEUE.md for a promoted/winners round folder.

Walks <round>/<variant>/*.brief.json and regenerates the two top-level files
based on everything currently present.

Usage:
    python3 tools/rebuild_round_index.py --round-dir brands/persillo/promoted/statics/grenen-round-1
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--round-dir", required=True)
    p.add_argument(
        "--iteration-notes",
        default="",
        help="CSV-ish overrides: 'A1: needs xyz | D5: ...'. Persisted into QUEUE.md.",
    )
    args = p.parse_args()

    rd = pathlib.Path(args.round_dir).expanduser().resolve()
    if not rd.exists():
        print(f"Not found: {rd}", file=sys.stderr)
        return 2

    iter_notes: dict[str, str] = {}
    if args.iteration_notes:
        for part in args.iteration_notes.split("|"):
            if ":" in part:
                k, _, v = part.partition(":")
                iter_notes[k.strip().upper()] = v.strip()

    by_variant: dict[str, list[dict]] = {}
    for variant_dir in sorted(rd.iterdir()):
        if not variant_dir.is_dir():
            continue
        for bf in sorted(variant_dir.glob("*.brief.json")):
            meta = json.loads(bf.read_text(encoding="utf-8"))
            meta["_variant_dir"] = variant_dir.name
            by_variant.setdefault(variant_dir.name, []).append(meta)

    total = sum(len(v) for v in by_variant.values())
    if total == 0:
        print("No briefs found.")
        return 1

    # README
    readme = [
        f"# {rd.name} — promoted",
        "",
        f"_{total} visually approved candidates across {len(by_variant)} variants. Not yet ad-tested._",
        "",
        "When ad-tested winners emerge, copy them into `brands/<brand>/winners/statics/`.",
        "",
    ]
    queue_lines: list[str] = []

    for variant in sorted(by_variant):
        metas = by_variant[variant]
        readme.append(f"## {variant} ({len(metas)})")
        for m in sorted(metas, key=lambda x: x["id"]):
            note = iter_notes.get(m["id"].upper())
            tag = " ⚠️ needs iteration" if note else ""
            readme.append(f"- **{m['id']}**{tag} — {m.get('headline','')}")
            if note:
                queue_lines.extend([
                    f"## {variant} · {m['id']}",
                    f"- Original headline: {m.get('headline','')}",
                    f"- Iteration: {note}",
                    "",
                ])
        readme.append("")

    (rd / "README.md").write_text("\n".join(readme), encoding="utf-8")

    if queue_lines:
        queue = [f"# {rd.name} — iteration queue", ""] + queue_lines
        (rd / "QUEUE.md").write_text("\n".join(queue), encoding="utf-8")
    elif (rd / "QUEUE.md").exists():
        (rd / "QUEUE.md").unlink()

    print(f"[rebuild] {total} promoted across {len(by_variant)} variants.")
    if queue_lines:
        print(f"[rebuild] {len(queue_lines) // 4} need iteration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
