#!/usr/bin/env python3
"""Build INDEX.md for a flat candidates folder.

Visual-first: just thumbnail + ID + variant. No copy fields — user adds copy
separately on the Meta layer.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dir", required=True)
    args = p.parse_args()

    d = pathlib.Path(args.dir).expanduser().resolve()
    if not d.exists():
        print(f"Not found: {d}", file=sys.stderr)
        return 2

    briefs = sorted(d.glob("*.brief.json"))
    if not briefs:
        print("No briefs found.")
        return 1

    # Group by variant for easy scanning
    by_variant: dict[str, list[dict]] = {"Gylden": [], "Råhvid": [], "Mixed": []}
    for bf in briefs:
        m = json.loads(bf.read_text(encoding="utf-8"))
        v = (m.get("variant") or "").strip().lower()
        if "raahvid" in v or v.startswith("rå"):
            by_variant["Råhvid"].append(m)
        elif "mixed" in v or ("gylden" in v and ("raahvid" in v or "rå" in v)):
            by_variant["Mixed"].append(m)
        else:
            by_variant["Gylden"].append(m)

    lines = [f"# {d.name} — candidates", "",
             f"_{len(briefs)} images. Browse, then tell me which IDs to promote._", ""]

    for variant in ["Gylden", "Råhvid", "Mixed"]:
        metas = by_variant[variant]
        if not metas:
            continue
        lines.append(f"## {variant} ({len(metas)})")
        lines.append("")
        for m in sorted(metas, key=lambda x: x["id"]):
            cid = m["id"]
            img = None
            for ext in (".jpg", ".png"):
                if (d / f"{cid}{ext}").exists():
                    img = f"{cid}{ext}"
                    break
            if not img:
                continue
            tpl = m.get("template_ref", "")
            lines.append(f"### {cid}")
            lines.append(f"![{cid}]({img})")
            lines.append(f"*Template ref: `{tpl}`*")
            lines.append("")
        lines.append("")

    (d / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    counts = ", ".join(f"{v}: {len(by_variant[v])}" for v in ["Gylden", "Råhvid", "Mixed"] if by_variant[v])
    print(f"[index] {len(briefs)} → {d.relative_to(d.parents[2])}  ({counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
