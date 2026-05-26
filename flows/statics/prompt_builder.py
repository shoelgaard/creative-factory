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
TASK: faithful PRODUCT SWAP into an existing static ad template.

REFERENCE IMAGE #1 (product): Persillo Grenen tapers — see for variant colour,
material texture, proportions. This product must appear in the final image.

REFERENCE IMAGE #2 (template, if present): a competing brand's static ad. This
is the EXACT scene we are recreating. Reproduce it faithfully:
- same room / surface / backdrop / wall
- same props (books, fabrics, plants, sand, water, tiles, sofa, shelves, etc.)
- same lighting direction and lighting mood
- same color palette — if the template is dark moody Aesop black, KEEP that
  black. If it's Byredo red velvet, KEEP that red. If it's Otherland holiday
  pine on a wooden table, KEEP that pine and wooden table.
- same camera angle, framing, depth
- same typography PLACEMENT zones (but with blank or removed competing-brand text)

THE ONE THING TO CHANGE:
Whatever product appears in the template (perfume bottle, jar candle, lotion
tube, soap, etc.) becomes Persillo Grenen {variant_short} tapers. Match the
same number of products / placement / orientation as the template wherever
possible.

PRODUCT — {variant_short}:
{variant_desc}

PRODUCT PHYSICAL FORM (must hold even when the template style is very different):
{proportions_block}

OPTIONAL composition hint from concept brief:
{visual_brief}

NO-GO regardless of template:
- No people, no hands, no body parts (if template had a person, replace with the
  candle in the same position)
- No honeycomb / bees / honey
- No competing brand's logo, name, or readable label — those zones go blank
- No "håndlavet i Danmark" / "made in Denmark" anywhere
- No flickering flame (if lit, the flame is stable and quiet)
- DO NOT default to travertine + limewashed warm-grey + dried lavender if the
  template doesn't have those. The template's surfaces and props win.

{copy_block}

OUTPUT: a single still image, aspect ratio {aspect}, photographic realism
faithful to the TEMPLATE's visual style. The product is Persillo Grenen
({variant_short}).
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
            "GRENEN PHYSICAL FORM — render this exactly, deviation = unusable:\n"
            "- A STRAIGHT CYLINDER: 2.2 cm diameter at the base, 2.2 cm diameter at the top. "
            "  The candle has the SAME diameter from bottom to top. Like a chopstick, like a pencil.\n"
            "- The candle is NEVER tapered. It does NOT get narrower toward the top. "
            "  It does NOT have a conical, dome, dipped-pencil, or seashell (konkylie) shape at the top.\n"
            "- The TOP is FLAT — a cleanly cut horizontal disc. NOT rounded, NOT domed, NOT pointed.\n"
            "- A SINGLE white cotton wick exits the centre of the flat top. ONE wick, at the TOP ONLY.\n"
            "  Never a wick at the bottom. Never wicks at both ends.\n"
            "- Height ~25 cm — at least 11x as tall as it is wide. Truly slender.\n"
            "- When showing a pack: EXACTLY 4 candles. Never 3. Never 5. Never 6. FOUR."
        ),
        "variants": {
            "gylden": (
                "the **Gylden** variant — warm honey-amber colour, the deeper golden natural "
                "beeswax. Slightly glossy translucent surface where light passes through. "
                "Colour reads as warm amber-gold, like dark honey."
            ),
            "raahvid": (
                "the **Råhvid** variant — cool ivory colour, the lighter cooler natural beeswax. "
                "Soft matte surface. Colour reads as warm off-white / cream-ivory, NEVER pure white, "
                "NEVER yellow, NEVER honey. Think the cream colour of unbleached linen or natural "
                "wool. The candle is the same cylindrical shape as Gylden (flat top, single wick, "
                "straight sides, 2.2 × 25 cm) — only the colour differs."
            ),
            "mixed": (
                "BOTH variants present in the same composition: the warm honey-amber Gylden tapers "
                "AND the cool cream-ivory Råhvid tapers. Both have identical cylindrical form "
                "(flat top, single wick, straight sides). Show them side by side or interleaved "
                "so the colour contrast is clearly visible."
            ),
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


def _find_product_images(
    project_root: pathlib.Path, brand_slug: str, product_slug: str, variant: str
) -> list[pathlib.Path]:
    """Return product hero refs for the variant. For Mixed: both Gylden + Råhvid heroes.

    Each variant folder is 'Gylden' or 'Råhvid'. Hero file: 'slot1_hero.jpg'.
    For Mixed we also include slot4_material.jpg if present (shows wax texture clearly).
    """
    base = project_root / "brands" / brand_slug / "references" / "products"
    family_capitalised = product_slug.capitalize()
    fam_dir = base / family_capitalised
    if not fam_dir.exists():
        fam_dir = base / product_slug.lower()
    if not fam_dir.exists():
        raise FileNotFoundError(f"No product folder at {base}/{family_capitalised} or {product_slug}")

    v = variant.strip().lower().replace("+", " ").replace("å", "aa")
    is_mixed = ("gylden" in v and ("raahvid" in v or "ra " in v or v.startswith("ra"))) or "mixed" in v
    is_raahvid = (not is_mixed) and ("raahvid" in v or v.startswith("ra"))
    chosen_variants = ["Gylden", "Råhvid"] if is_mixed else (["Råhvid"] if is_raahvid else ["Gylden"])

    refs: list[pathlib.Path] = []
    for chosen in chosen_variants:
        hero = fam_dir / chosen / "slot1_hero.jpg"
        if hero.exists():
            refs.append(hero)
            continue
        for p in (fam_dir / chosen).glob("*.jpg"):
            refs.append(p)
            break
    if not refs:
        raise FileNotFoundError(f"No product images found under {fam_dir}")
    return refs


# Backwards-compatible single-ref accessor
def _find_product_image(
    project_root: pathlib.Path, brand_slug: str, product_slug: str, variant: str
) -> pathlib.Path:
    return _find_product_images(project_root, brand_slug, product_slug, variant)[0]


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


_PACK_KEYWORDS = (
    "pack", "pakke", "package", "boxed", "unbox", "gift",
    "stack", "stacked", "stak", "abundance", "refill",
)


def _find_pack_refs(
    project_root: pathlib.Path, brand_slug: str, product_slug: str, variant: str
) -> list[pathlib.Path]:
    """Return the abundance/pack reference for the variant.

    Only uses slot8_abundance.jpg — it's the editorial pack shot with Persillo's
    natural prop styling. Skips vol_*.jpg (those are clean catalog shots used by
    the website's quantity selector, not editorial reference material).
    """
    base = project_root / "brands" / brand_slug / "references" / "products"
    family = product_slug.capitalize()
    fam_dir = base / family
    if not fam_dir.exists():
        return []
    v = variant.strip().lower()
    if "raahvid" in v.replace("å", "aa") or v.startswith("rå"):
        variant_dir = fam_dir / "Råhvid"
    else:
        variant_dir = fam_dir / "Gylden"
    abundance = variant_dir / "slot8_abundance.jpg"
    return [abundance] if abundance.exists() else []


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
    product_imgs = _find_product_images(project_root, brand.slug, product_slug, concept.variant)
    template_img = _find_template_image(project_root, brand.slug, concept.template_ref)

    refs = list(product_imgs)  # 1 ref for Gylden/Råhvid, 2 refs for Mixed

    # If the visual brief talks about the pack/box/gift, add pack refs
    brief_lower = (concept.visual + " " + concept.headline + " " + concept.primary).lower()
    if any(k in brief_lower for k in _PACK_KEYWORDS):
        pack_refs = _find_pack_refs(project_root, brand.slug, product_slug, concept.variant)
        # Avoid duplicates if pack ref happens to equal a product ref
        for pr in pack_refs:
            if pr not in refs:
                refs.append(pr)

    if use_template_ref and template_img:
        refs.append(template_img)

    # Normalise variant for the template
    v_lower = concept.variant.strip().lower().replace("å", "aa")
    if ("gylden" in v_lower and "raahvid" in v_lower) or "mixed" in v_lower:
        variant_short = "Gylden + Råhvid"
    elif "raahvid" in v_lower or v_lower.startswith("ra"):
        variant_short = "Råhvid"
    else:
        variant_short = "Gylden"

    facts = _PRODUCT_FACTS.get(product_slug.lower(), {})
    variants = facts.get("variants", {})
    variant_key = "mixed" if "Gylden + Råhvid" in variant_short else ("raahvid" if variant_short == "Råhvid" else "gylden")
    variant_desc = variants.get(variant_key, product_block)

    prompt = _PROMPT_TEMPLATE.format(
        variant_short=variant_short,
        variant_desc=variant_desc,
        visual_brief=concept.visual or "(none — follow the template faithfully)",
        proportions_block=proportions,
        copy_block=_copy_block(concept),
        aspect=aspect,
    )

    return BuiltPrompt(text=prompt, refs=refs, aspect=aspect)
