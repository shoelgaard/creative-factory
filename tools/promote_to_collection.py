#!/usr/bin/env python3
"""Promote candidate statics into a named collection.

A "collection" sits between candidates (raw renders) and winners (ad-tested).
'promoted' is the typical collection — visually approved, queued for ad testing.

Target structure:
    brands/<brand>/<collection>/<flow>/<round>/<variant>/<id>.jpg

Each promoted image carries its brief.json alongside. A QUEUE.md per round
notes any 'needs iteration' notes for follow-up renders.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys


VARIANT_FOLDER = {
    "gylden": "Gylden",
    "raahvid": "Råhvid",
    "råhvid": "Råhvid",
    "mixed": "Mixed",
    "gylden + råhvid": "Mixed",
}


def _norm_variant(v: str) -> str:
    return VARIANT_FOLDER.get(v.strip().lower(), "Mixed")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True, help="The candidates folder (or original run dir).")
    p.add_argument("--brand", required=True)
    p.add_argument("--product", required=True, help="e.g. Grenen")
    p.add_argument("--collection", default="promoted", help="promoted | winners")
    p.add_argument("--flow", default="statics")
    p.add_argument("--round", required=True, help="round label, e.g. grenen-round-1")
    p.add_argument("--ids", required=True, help="CSV of concept IDs to promote (A1,B2,D5,...).")
    p.add_argument(
        "--iteration-notes",
        default="",
        help="Optional notes per ID, format 'A1: needs xyz | D5: fix flat tops'.",
    )
    args = p.parse_args()

    run_dir = pathlib.Path(args.run_dir).expanduser().resolve()
    if not run_dir.exists():
        print(f"Not found: {run_dir}", file=sys.stderr)
        return 2

    ids = {s.strip().upper() for s in args.ids.split(",") if s.strip()}
    iter_notes: dict[str, str] = {}
    if args.iteration_notes:
        for part in args.iteration_notes.split("|"):
            if ":" in part:
                k, _, v = part.partition(":")
                iter_notes[k.strip().upper()] = v.strip()

    project_root = pathlib.Path(__file__).resolve().parents[1]
    base = project_root / "brands" / args.brand / args.collection / args.flow / args.round

    by_variant: dict[str, list[dict]] = {}

    for bf in sorted(run_dir.glob("*.brief.json")):
        meta = json.loads(bf.read_text(encoding="utf-8"))
        cid = meta["id"]
        if cid.upper() not in ids:
            continue
        variant = _norm_variant(meta.get("variant", ""))
        img = None
        for ext in (".jpg", ".png"):
            cand = run_dir / f"{cid}{ext}"
            if cand.exists():
                img = cand
                break
        if not img:
            print(f"[promote] {cid}: image missing in {run_dir}", file=sys.stderr)
            continue

        dest_dir = base / variant
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(img, dest_dir / img.name)
        shutil.copy2(bf, dest_dir / bf.name)

        meta["_iteration_note"] = iter_notes.get(cid.upper())
        by_variant.setdefault(variant, []).append(meta)

    # Write QUEUE.md per round (lists iteration follow-ups)
    queue_entries = []
    for variant, metas in by_variant.items():
        for m in sorted(metas, key=lambda x: x["id"]):
            if m.get("_iteration_note"):
                queue_entries.append((variant, m["id"], m["_iteration_note"], m))

    if queue_entries:
        lines = [f"# {args.round} — iteration queue", ""]
        for variant, cid, note, m in queue_entries:
            lines.extend([
                f"## {variant} · {cid}",
                f"- Original headline: {m.get('headline','')}",
                f"- Iteration: {note}",
                "",
            ])
        (base / "QUEUE.md").write_text("\n".join(lines), encoding="utf-8")

    # Write README per round listing what's in here
    readme = [
        f"# {args.product} {args.round} — {args.collection}",
        "",
        f"Visually approved candidates from the round-1 batch. Not yet ad-tested.",
        "When ad-tested winners emerge, copy them into `winners/{args.flow}/`.",
        "",
    ]
    for variant in sorted(by_variant):
        metas = by_variant[variant]
        readme.append(f"## {variant} ({len(metas)})")
        for m in sorted(metas, key=lambda x: x["id"]):
            iter_tag = " ⚠️ needs iteration" if m.get("_iteration_note") else ""
            readme.append(f"- **{m['id']}**{iter_tag} — {m.get('headline','')}")
        readme.append("")
    (base / "README.md").write_text("\n".join(readme), encoding="utf-8")

    total = sum(len(v) for v in by_variant.values())
    print(f"[promote] {total} files into brands/{args.brand}/{args.collection}/{args.flow}/{args.round}/")
    for variant in sorted(by_variant):
        ids_in = ", ".join(m["id"] for m in sorted(by_variant[variant], key=lambda x: x["id"]))
        print(f"  {variant} ({len(by_variant[variant])}): {ids_in}")
    if queue_entries:
        print(f"\n[promote] {len(queue_entries)} need iteration — see QUEUE.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
