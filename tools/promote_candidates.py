#!/usr/bin/env python3
"""Copy a statics run's outputs into the flat brand candidates folder.

Target: brands/<brand>/candidates/<round>/
All images and briefs land in one flat folder, regardless of variant. INDEX.md
groups them by variant for browsing.
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
    p.add_argument("--run-dir", required=True, help="Statics run dir containing <id>.jpg + <id>.brief.json")
    p.add_argument("--brand", required=True)
    p.add_argument("--round", required=True, help="Round label, e.g. 'round-3' (creates brands/<brand>/candidates/<round>/)")
    args = p.parse_args()

    run_dir = pathlib.Path(args.run_dir).expanduser().resolve()
    if not run_dir.exists():
        print(f"Not found: {run_dir}", file=sys.stderr)
        return 2

    project_root = pathlib.Path(__file__).resolve().parents[1]
    dest_dir = project_root / "brands" / args.brand / "candidates" / args.round
    dest_dir.mkdir(parents=True, exist_ok=True)

    briefs = sorted(run_dir.glob("*.brief.json"))
    copied = 0
    for bf in briefs:
        meta = json.loads(bf.read_text(encoding="utf-8"))
        cid = meta["id"]
        img = None
        for ext in (".jpg", ".png"):
            cand = run_dir / f"{cid}{ext}"
            if cand.exists():
                img = cand
                break
        if not img:
            print(f"[promote] {cid}: no image, skipping", file=sys.stderr)
            continue
        shutil.copy2(img, dest_dir / img.name)
        shutil.copy2(bf, dest_dir / bf.name)
        copied += 1

    print(f"[promote] {copied} files → brands/{args.brand}/candidates/{args.round}/")

    # Rebuild INDEX
    indexer = project_root / "tools" / "build_candidates_index.py"
    if indexer.exists():
        subprocess.run([sys.executable, str(indexer), "--dir", str(dest_dir)], check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
