"""Build the Nano Banana prompt from brand + product + concept.

Three layers:
  1. Brand DNA — verbatim brand body (visual grammar, no-gos)
  2. Product hint — physical facts (dimensions, material, colour)
  3. Concept — visual brief + (optional) embedded copy text

Multi-ref strategy: product image always passed. Template image passed when
use_template_ref=True (explicitly framed as "compositional reference, do not
clone").
"""

from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass

from shared.brand_loader import Brand

from .concept_parser import Concept


@dataclass
class BuiltPrompt:
    text: str
    refs: list[pathlib.Path]
    aspect: str


_PROMPT_TEMPLATE = """\
You are generating a single static ad creative for {brand_name}, a Danish
premium beeswax-candle brand. Editorial photography realism. Quiet, lavmælt,
Kinfolk/Frama/Aesop visual language.

PRODUCT (subject of the ad, see reference image #1):
{product_block}

VISUAL BRIEF FOR THIS AD:
{visual_brief}

{template_block}

BRAND VISUAL GRAMMAR (must follow):
- Editorial still-life, lavmælt nordisk lys, magasin-kvalitet
- Materials: travertine, raw oak, linen, matte off-white ceramic, brushed brass
- Backdrop: warm muted-grey limewashed plaster, subtle brush-mottling — NEVER pure white catalog background
- Light: soft directional Nordic daylight from the left, ~4000K, gentle long shadows
- Mood: quiet luxury, intimate, slow

STRICT NO-GO LIST (do not include):
- No people, no hands, no body parts
- No glossy plastic surfaces, no chrome
- No honeycombs, honey drips, bees (source story told via dried Nordic flora, never literally)
- No flickering/blown flames — only stable, quiet flame if lit
- No "blurred background" — use specific named props (linen books, ceramic cup, dried lavender)
- No "håndlavet i Danmark" / "made in Denmark" claims anywhere

PRODUCT PROPORTIONS (critical — Gemini drifts toward generic):
{proportions_block}

{copy_block}

OUTPUT: a single still image, aspect ratio {aspect}, editorial photography
realism, high-resolution detail, natural color rendering. The product must be
the focal subject and faithfully resemble reference image #1.
""".strip()


_PRODUCT_FACTS = {
    "grenen": {
        "name": "Grenen",
        "block": (
            "Persillo Grenen — a slim beeswax taper candle. "
            "Diameter 2.2 cm, height 25 cm. Pencil-thin proportions (~11:1 height:diameter). "
            "Sold in packs of 4. 14-hour burn time per candle. 100% pure beeswax, cotton wick."
        ),
        "proportions": (
            "Grenen is EXTREMELY THIN AND TALL: 2.2 cm wide × 25 cm tall. Think of a "
            "chopstick or long pencil. Cylindrical. NEVER render it as a chunky pillar candle."
        ),
        "variants": {
            "gylden": "warm honey-amber colour (natural beeswax, the deeper gold variant)",
            "raahvid": "cool ivory colour (the lighter, cooler natural beeswax variant)",
            "mixed": "both warm honey-amber (Gylden) and cool ivory (Råhvid) variants present in the same composition",
        },
    },
}


def _product_block(product_slug: str, variant: str) -> tuple[str, str]:
    facts = _PRODUCT_FACTS.get(product_slug.lower())
    if not facts:
        return f"product slug '{product_slug}' (see reference image)", ""
    variant_key = variant.lower().replace(" ", "").replace("+", "").replace("å", "aa")
    if "gylden" in variant_key and "raahvid" in variant_key:
        variant_key = "mixed"
    elif "mixed" in variant_key:
        variant_key = "mixed"
    elif "raahvid" in variant_key or "ra" in variant_key:
        variant_key = "raahvid"
    else:
        variant_key = "gylden"

    variant_desc = facts["variants"].get(variant_key, facts["variants"]["gylden"])
    block = (
        f"{facts['block']} This composition uses the **{variant.strip()}** variant: {variant_desc}."
    )
    return block, facts["proportions"]


def _template_block(template_path: pathlib.Path | None, use_ref: bool) -> str:
    if not template_path or not template_path.exists():
        return ""
    if use_ref:
        return (
            f"COMPOSITIONAL REFERENCE (see reference image #2): the second image is a "
            f"competing brand's ad shown ONLY as a structural reference — for composition "
            f"balance, typography placement weight, and lighting mood. DO NOT clone its "
            f"materials, colours, brand marks, or product. Build the ad from scratch with "
            f"Persillo's product and Persillo's brand grammar."
        )
    return (
        f"(A competing brand's ad inspired the compositional structure for this concept, but "
        f"is not provided as a direct reference. Build from the visual brief above.)"
    )


def _copy_block(concept: Concept) -> str:
    if concept.copy_mode == "embedded":
        embed = concept.embed_text or concept.headline
        return (
            f"TYPOGRAPHY: render the following text inside the image as part of the visual "
            f"composition. Use a sober editorial sans-serif (think Aesop, Frama, Le Labo "
            f"typography). Place it according to the visual brief. Text content (RENDER "
            f"EXACTLY, do not paraphrase or translate): \"{embed}\""
        )
    return (
        "TYPOGRAPHY: do NOT include any text, logo, headline, or typography in the image. "
        "Copy will be added on the Meta ad-manager layer."
    )


def _find_product_image(
    project_root: pathlib.Path, brand_slug: str, product_slug: str, variant: str
) -> pathlib.Path:
    """Find the hero product image for the given variant.

    Variants in folders: 'Gylden' and 'Råhvid'. Filename: 'slot1_hero.jpg'.
    """
    base = project_root / "brands" / brand_slug / "references" / "products"
    # Folder name is the family name capitalised in Sylvester's existing structure
    family_capitalised = product_slug.capitalize()
    fam_dir = base / family_capitalised
    if not fam_dir.exists():
        # try lowercase
        fam_dir = base / product_slug.lower()
    if not fam_dir.exists():
        raise FileNotFoundError(f"No product folder at {base}/{family_capitalised} or {product_slug}")

    v = variant.strip().lower().replace("+", " ").replace("å", "aa")
    if "gylden" in v and ("raahvid" in v or "mixed" in v):
        chosen = "Gylden"  # default to Gylden for mixed; flow will need both refs eventually
    elif "raahvid" in v or "ra" in v:
        chosen = "Råhvid"
    else:
        chosen = "Gylden"

    candidate = fam_dir / chosen / "slot1_hero.jpg"
    if candidate.exists():
        return candidate
    # fallback to any jpg in variant folder
    for p in (fam_dir / chosen).glob("*.jpg"):
        return p
    raise FileNotFoundError(f"No product image found under {fam_dir / chosen}")


def _find_template_image(project_root: pathlib.Path, brand_slug: str, template_ref: str) -> pathlib.Path | None:
    """Match concept template slug against actual filenames.

    Concept slugs use hyphens (e.g. 'diptyque-large-candles-wooden-tier').
    Filenames use __ separators (e.g. 'diptyque__0139d__large-candles-wooden-tier__crop.png').
    We require all hyphen-tokens from the slug to appear in the filename, in order.
    """
    tdir = project_root / "brands" / brand_slug / "references" / "templates"
    if not tdir.exists():
        return None

    tokens = [t.lower() for t in template_ref.split("-") if t]

    def _matches(filename: str) -> bool:
        fl = filename.lower()
        cursor = 0
        for tok in tokens:
            idx = fl.find(tok, cursor)
            if idx < 0:
                return False
            cursor = idx + len(tok)
        return True

    # Prefer cropped, then full
    crops = sorted(tdir.glob("*__crop.png"))
    for p in crops:
        if _matches(p.name):
            return p
    fulls = sorted([p for p in tdir.glob("*.png") if "__crop" not in p.name])
    for p in fulls:
        if _matches(p.name):
            return p
    return None


def build_for_concept(
    *,
    brand: Brand,
    product_slug: str,
    concept: Concept,
    project_root: pathlib.Path,
    use_template_ref: bool = True,
    aspect: str = "4:5",
) -> BuiltPrompt:
    product_block, proportions = _product_block(product_slug, concept.variant)
    product_img = _find_product_image(project_root, brand.slug, product_slug, concept.variant)
    template_img = _find_template_image(project_root, brand.slug, concept.template_ref)

    refs = [product_img]
    if use_template_ref and template_img:
        refs.append(template_img)

    prompt = _PROMPT_TEMPLATE.format(
        brand_name=brand.name,
        product_block=product_block,
        visual_brief=concept.visual,
        template_block=_template_block(template_img, use_template_ref),
        proportions_block=proportions,
        copy_block=_copy_block(concept),
        aspect=aspect,
    )

    return BuiltPrompt(text=prompt, refs=refs, aspect=aspect)
