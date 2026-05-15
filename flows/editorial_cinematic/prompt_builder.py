"""Build engine-specific video-prompts from brand.md + user input.

Two engines, two flavors:
  - veo3:      8s native-audio cinematic, accepts narrative description
  - seedance2: image-to-video on fal.ai, accepts a concise motion/style prompt

Both flavors derive from the same source (brand body + user steer + product hints)
to keep outputs comparable side-by-side.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass

from shared.brand_loader import Brand


@dataclass
class BuiltPrompt:
    veo3: str
    seedance2: str
    shared_brief: str


_VEO3_TEMPLATE = """\
Editorial product film for {brand_name} — {tagline}.

Subject (from reference image): {product_hint}

Movement: very subtle. Slow push-in or near-static parallax over the full duration.
The flame, if lit, burns stable and quiet — never dramatic. One natural element
(steam, a botanical sway, a shifting sliver of light) may move almost imperceptibly.
No whip-pans, no zooms, no rotation around the product, no reveal-shots.

Light: soft directional Nordic daylight from the left, around 4000K, casting
gentle long shadows with soft falloff. Like morning light through a tall
north-facing window — quiet, slow, intimate.

Setting & materials: warm muted-grey limewashed plaster wall with subtle
brush-mottling. Surface from travertine, raw oak, or matte sand-coloured ceramic.
Natural Nordic flora as needed (dried lavender, wheat, poppy, chamomile, yarrow,
elder) — placed casually, never arranged for the camera.

Audio (native): subtle room-tone, faint wick-crackle if lit, otherwise the quality
of stillness itself. No music, no voiceover, no sound-design hits.

Style anchors: Kinfolk magazine spread, Frama product story, Aesop botanical
apothecary aesthetic. 85mm portrait framing, editorial photography realism,
natural color rendering, high-resolution detail.

Strict constraints: no people, no hands, no body parts. No white catalog
background. No glossy or plastic surfaces. No honeycombs or honey drips
(the source story is told poetically via flora, never literally).

{user_steer}
""".strip()


_SEEDANCE_TEMPLATE = """\
Editorial cinematic product film, {brand_name} aesthetic.
Subject: {product_hint}.
Slow push-in, near-static parallax. Stable quiet flame if lit. No camera rotation.
Soft Nordic daylight from the left, warm muted-grey limewashed wall, travertine
or raw oak surface. Kinfolk / Frama / Aesop visual reference. 85mm portrait,
editorial realism, natural color. No people, no hands. {user_steer}
""".strip()


def _product_hint(image_path: pathlib.Path) -> str:
    """Make a best-effort textual hint from the image filename.

    Veo and Seedance both see the actual image. This hint is just a textual
    nudge so the prompt knows what KIND of product it is referring to.
    """
    stem = image_path.stem.lower()
    if "planken" in stem and "gylden" in stem:
        return (
            "a single Persillo Planken Gylden beeswax taper candle (1.6 cm wide, "
            "25 cm tall, square cross-section, pencil-thin, warm honey-amber colour)"
        )
    if "planken" in stem and ("raahvid" in stem or "raw" in stem):
        return (
            "a single Persillo Planken Råhvid beeswax taper candle (1.6 cm wide, "
            "25 cm tall, square cross-section, pencil-thin, cool ivory colour)"
        )
    if "stammen" in stem:
        return "a Persillo Stammen pillar candle (6 cm wide, 20 cm tall, cylindrical)"
    if "stubben" in stem:
        return "a Persillo Stubben pillar candle (6 cm wide, 10 cm tall, cylindrical)"
    return "the product shown in the reference image, faithfully rendered in scale"


def build_prompt(
    brand: Brand,
    image_path: pathlib.Path,
    user_steer: str | None = None,
) -> BuiltPrompt:
    hint = _product_hint(image_path)
    steer = (user_steer or "").strip()
    veo3 = _VEO3_TEMPLATE.format(
        brand_name=brand.name,
        tagline=brand.tagline or "",
        product_hint=hint,
        user_steer=f"Additional steer: {steer}" if steer else "",
    ).strip()
    seedance = _SEEDANCE_TEMPLATE.format(
        brand_name=brand.name,
        product_hint=hint,
        user_steer=steer,
    ).strip()
    shared = (
        f"Brand: {brand.name}\nProduct hint: {hint}\nUser steer: {steer or '(none)'}"
    )
    return BuiltPrompt(veo3=veo3, seedance2=seedance, shared_brief=shared)
