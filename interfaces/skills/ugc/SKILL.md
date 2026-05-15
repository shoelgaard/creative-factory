---
name: ugc
description: UGC talking-head flow via Arcads pre-cast actors. Use when the user wants a credible-looking person delivering a brand-voiced script to camera, UGC-style, in Danish (or other languages once verified). Triggers on "lav en UGC", "talking head", "Arcads", "kvinde der fortæller om", "AI-influencer for [brand]", or pointing at a product and asking for a "real person" recommend it. NOT for editorial cinematic (use /editorial) or product-on-camera ambient (also /editorial).
---

# UGC talking-head skill

When the user wants a pre-cast actor delivering a script for a brand:

1. **Verify brand.** Check `brands/<slug>/brand.md` exists. `--brand` is required.
   If the brand doesn't exist, stop and ask which brand — never invent.
2. **Read the per-brand `MASTER_CONTEXT.md`** for banned terms, defaults, persona.
3. **Brief structure.** A complete brief needs `product`, `hook`, `beats[]`, `cta`.
   - If the user provides a YAML brief path: use `--brief-file`.
   - If the user gives inline detail: use `--hook` / `--beats` / `--cta` flags.
   - If the user gives only the product: ask for hook + beats + cta in conversation
     before running. Do NOT render a brief that lacks a hook.
4. **Run:**
   ```bash
   python3 interfaces/cli/cf.py ugc gen \
     --brand <slug> --product "<name>" \
     [--persona female-adult|female-young-adult|male-adult|auto] \
     [--hook "..." --beats "..." "..." --cta "..."]
     [--brief-file briefs/<brand>/<file>.yaml]
   ```
5. **Two gates fire**:
   - **Dialogue gate** — numbered script with word-count vs. target duration. User must confirm.
   - **Credit gate** — cost estimate from `logs/arcads.jsonl` history (or pricing.md fallback).
6. **Report back** the run folder. Open `script.txt` if the user wants to read
   what was sent. Open the mp4 with `open <path>` (macOS).
7. **After judgment**, update `brands/<slug>/MASTER_CONTEXT.md` with banned-term
   additions if the script slipped through with bad phrasing.

## Hard rules

- `--brand` is REQUIRED. No defaults.
- The script_builder enforces the banned-terms list — render fails with
  `ValueError` if a banned phrase made it in. That is correct behaviour.
- Persillo specifically: never claim "håndlavet i Danmark" / "made in Denmark".
  The brand is Danish-designed, not Danish-manufactured.
- Don't render the same brief twice on the same day without changing something
  meaningful. Multiple variations = multiple briefs with distinct hooks.
- This flow produces a talking-head against Arcads' preset scene. The product
  is **not** on camera. If the user wants product on camera, route them to
  `/editorial` instead or wait for the product-showcase flow.
