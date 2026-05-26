#!/usr/bin/env python3
"""Generate the round-3 concepts file: every template × Gylden + Råhvid.

Composition rotates across templates so the engine sees more variation:
single / group-of-4 / close-up / flat-lay / in-room.
"""

from __future__ import annotations

import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
TPL_DIR = PROJECT_ROOT / "brands" / "persillo" / "references" / "templates"
OUT_FILE = PROJECT_ROOT / "brands" / "persillo" / "concepts" / "grenen-round-3.md"

# Templates we skip entirely (off-brand for Persillo)
SKIP = {
    "trudon__0032d__carmen-on-bed-female",     # female on bed, breaks no-people rule
}

# Templates where the "pack/box" composition fits best
PACK_TEMPLATES = {
    "byredo__0078d__discovery-set-nomade-boxed",
    "byredo__0040d__bal-dafrique-red-velvet",
    "diptyque__0131d__most-loved-scents-stacked",
    "diptyque__0139d__hand-soap-stack-lavender",
    "frama__0014d__10off-shelf-interior",
    "le-labo__0026d__hand-crafted-candles-wooden-box",
    "lelabo__0026d__hand-crafted-candles-wooden-box",
    "lelabo__0026d__discovery-sets-tiled-corner",
    "lelabo__0026d__spritz-refill-repeat-hand-pouring",
    "lelabo__0026d__wash-pomade-repeat",
    "otherland__0016d__cardamom-milk-soft-typography",
    "otherland__0379d__fallen-fir-refill-holiday-table",
    "trudon__0035d__carmen-black-bottle-new-collection",
}

# Composition cues rotated through the list, one per template-variant pair
COMPOSITIONS = [
    "Show ONE single Grenen taper in a simple matte ceramic holder, centred and unlit, soft Nordic side light from the left.",
    "Show EXACTLY FOUR Grenen tapers as a tight group in identical simple matte ceramic holders, evenly spaced, soft side light, all candles same height with flat tops.",
    "Tight close-up of ONE Grenen taper — the flat top, the single wick, the wax texture clearly visible. Dark moody backdrop or soft warm gradient.",
    "Top-down flat-lay of 3 Grenen tapers lying loosely on a travertine slab, slight asymmetry, soft morning light.",
    "An interior scene — a side table or dining table — with 2-3 Grenen tapers lit in simple matte ceramic holders. Quiet domestic mood, warm side light.",
    "ONE Grenen taper LIT in a simple matte ceramic holder, single stable quiet flame. Dark or muted backdrop so the warm flame is the focal point.",
    "EXACTLY FOUR Grenen tapers in a horizontal row on a long travertine slab, evenly spaced, identical holders, soft Nordic side light from the left.",
]

COMPOSITIONS_PACK = [
    "An open Persillo package on a travertine surface, showing the 4 Grenen tapers nestled inside in tissue paper. Soft side light, no extra props beyond the package and tapers.",
    "Two Persillo packages stacked on a warm-grey limewashed surface, beside one taper standing upright next to the stack. Quiet editorial mood.",
    "A Persillo package half-opened on a linen tørklæde as if being unwrapped — 4 Grenen tapers visible inside. Morning daylight.",
    "Three Persillo packages stacked vertically against a warm-grey limewashed wall, dried lavendel sprig beside them on travertine. Soft side light.",
]


VARIANTS = ["Gylden", "Råhvid"]


def slugify_template(filename_stem: str) -> str:
    """Convert filename stem 'aesop__0036d__solaris-hand-serum-on-fan' to the slug used in concepts.

    We keep the brand + descriptive part, drop the days-counter so concepts read cleanly.
    """
    parts = filename_stem.split("__")
    if len(parts) >= 3:
        brand_part = parts[0]
        # find first __ that ISN'T a days counter
        descriptive = "-".join(p for p in parts[1:] if not (p.endswith("d") and p[:-1].isdigit()))
        return f"{brand_part}-{descriptive}"
    return filename_stem.replace("__", "-")


def gather_templates() -> list[str]:
    seen = set()
    out = []
    for f in sorted(TPL_DIR.glob("*__crop.png")):
        stem = f.stem.replace("__crop", "")
        if stem in SKIP:
            continue
        if stem in seen:
            continue
        seen.add(stem)
        out.append(stem)
    return out


def main() -> int:
    templates = gather_templates()
    lines = [
        "# Grenen — Statics Round 3 (max template variation, no embedded copy)",
        "",
        "**Format:** 4:5 (1080 × 1350) · **Brand:** persillo · **Product:** Grenen · **Engine:** gemini-image",
        "",
        "Round 3 design intent (per user feedback after round 2):",
        "- ALL 49 templates traversed (round 1+2 used only 33)",
        "- Every template × Gylden + Råhvid — balanced variant exposure for Andromeda",
        "- NO embedded copy on images — Persillo copy added on the Meta ad-manager layer",
        "- Composition rotated across the set (single / group-of-4 / close-up / flat-lay / in-room / lit / pack)",
        "- Form-constraints enforced by prompt_builder (cylinder, flat top, 1 wick, exactly 4 per pack)",
        "- Pack-themed templates automatically receive package reference images",
        "",
        "---",
        "",
    ]

    counter = 0
    comp_cycle = 0
    pack_cycle = 0
    for tpl in templates:
        tpl_slug = slugify_template(tpl)
        is_pack = tpl in PACK_TEMPLATES
        for variant in VARIANTS:
            counter += 1
            if is_pack:
                composition = COMPOSITIONS_PACK[pack_cycle % len(COMPOSITIONS_PACK)]
                pack_cycle += 1
            else:
                composition = COMPOSITIONS[comp_cycle % len(COMPOSITIONS)]
                comp_cycle += 1
            cid = f"R3-{counter:03d}"
            visual = (
                f"Take the compositional structure, lighting mood and typography balance from the "
                f"referenced ad as inspiration. Render Persillo Grenen tapers in the {variant} variant "
                f"following the Persillo brand grammar (editorial still life, warm-grey limewashed wall "
                f"or travertine surface, soft Nordic side light, no people, no chrome, no glossy plastic). "
                f"{composition}"
            )
            lines.extend([
                f"### [ ] {cid} · {tpl_slug} · {variant}",
                f"**Visual:** {visual}",
                "",
            ])

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"[gen] wrote {counter} concepts → {OUT_FILE.relative_to(PROJECT_ROOT)}")
    print(f"[gen] templates: {len(templates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
