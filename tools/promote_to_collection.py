#!/usr/bin/env python3
"""Promote a subset of candidates into a named collection (flat structure).

Target: brands/<brand>/<collection>/<round>/<files>
        — flat, same layout as candidates/

Collections:
  promoted — visually approved, ready for ad-test
  winners  — ad-tested winners (after Meta data confirms performance)

Usage:
    python3 tools/promote_to_collection.py \
        --source-dir brands/persillo/candidates/round-3 \
        --brand persillo --collection promoted --round round-3 \
        --ids R3-001,R3-007,R3-012
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-dir", required=True, help="A candidates dir (e.g. brands/persillo/candidates/round-3/)")
    p.add_argument("--brand", required=True)
    p.add_argument("--collection", default="promoted", choices=["promoted", "winners"])
    p.add_argument("--round", required=True, help="Round label, e.g. 'round-3' — used as target subfolder")
    p.add_argument("--ids", required=True, help="CSV of concept IDs to promote.")
    args = p.parse_args()

    src = pathlib.Path(args.source_dir).expanduser().resolve()
    if not src.exists():
        print(f"Not found: {src}", file=sys.stderr)
        return 2

    ids = {s.strip() for s in args.ids.split(",") if s.strip()}

    project_root = pathlib.Path(__file__).resolve().parents[1]
    dest = project_root / "brands" / args.brand / args.collection / args.round
    dest.mkdir(parents=True, exist_ok=True)

    copied = 0
    missing: list[str] = []
    for cid in sorted(ids):
        img = None
        for ext in (".jpg", ".png"):
            cand = src / f"{cid}{ext}"
            if cand.exists():
                img = cand
                break
        if not img:
            missing.append(cid)
            continue
        shutil.copy2(img, dest / img.name)
        brief = src / f"{cid}.brief.json"
        if brief.exists():
            shutil.copy2(brief, dest / brief.name)
        copied += 1

    print(f"[promote] {copied} → brands/{args.brand}/{args.collection}/{args.round}/")
    if missing:
        print(f"[promote] missing: {', '.join(missing)}", file=sys.stderr)

    indexer = project_root / "tools" / "build_candidates_index.py"
    if indexer.exists():
        subprocess.run([sys.executable, str(indexer), "--dir", str(dest)], check=False)
    return 0 if copied else 1


if __name__ == "__main__":
    raise SystemExit(main())
