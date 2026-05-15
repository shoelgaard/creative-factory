---
name: creative-factory
description: Generate brand-aware product video ads from a single reference image using Veo 3 and/or Seedance 2.0. Use when the user wants to produce a Persillo (or other registered brand) cinematic ad-clip from an existing product photo, compare engines side-by-side, or iterate on motion/style with a steering prompt.
---

# Creative Factory skill

When the user asks for a product video, a brand-styled ad clip, or wants to
compare Veo 3 vs Seedance 2.0 on the same brief:

1. Verify the brand has a `brands/<slug>/brand.md`. If not, ask the user which
   existing brand to base it on, or stop and propose creating a new brand-DNA file.
2. Verify the reference image exists at the path given. Default test asset is
   the Persillo Planken Gylden hero (`slot1_hero.jpg`).
3. Run:
   ```bash
   python3 scripts/cf.py gen --image <path> --brand <slug> --engine <veo3|seedance2|both> [--prompt "..."] [--duration 8] [--aspect 9:16]
   ```
4. Report back the run-dir path. Open `brief.json` if the user wants to see the
   exact prompts that were used (the builder fuses brand.md + user steer +
   product hint into engine-specific prompts).
5. After each round of generation, ask the user to judge. If the result is not
   brand-on, update `brands/<slug>/brand.md` (motion grammar, no-go list, or
   style anchors) and `MASTER_CONTEXT.md` with the learning **before** rerunning.

## Constraints

- Persillo: no people, no hands, no white catalog backgrounds, no honeycombs,
  no dramatic motion. Stable quiet flame, slow drift, native ambient audio.
- Always run engines as subprocesses (parallel when `--engine both`).
- Never overwrite an existing `output/<ts>` folder — each run gets its own.
- Costs are non-trivial. Confirm with the user before launching `both` for a
  brand-new prompt that hasn't been tuned yet.
