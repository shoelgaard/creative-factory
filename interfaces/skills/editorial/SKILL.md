---
name: editorial
description: Editorial cinematic product film flow. Use when the user asks for a quiet single-clip cinematic ad from a product photo (no people, no talking, no fast cuts) — typical case is a Persillo Planken / Stammen / Stubben hero rendered as an 8-second drift. Triggers on "lav en editorial", "editorial cinematic", "cinematic ad", "Veo / Seedance side by side", or pointing at a product image and asking for a cinematic clip.
---

# Editorial cinematic skill

When the user wants an editorial product clip (no spoken UGC, no avatar):

1. **Verify brand.** Check `brands/<slug>/brand.md` exists. `--brand` is required.
   If the brand doesn't exist, stop and ask which brand to use — never invent one.
2. **Verify image.** Check the reference image path. Default Persillo test asset
   is `references/planken_gylden_hero.jpg` (also at the Persillo OneDrive 02_Final folder).
3. **Read the per-brand `MASTER_CONTEXT.md`.** It contains banned terms, banned
   imagery, and accumulated learnings. The flow already injects it into prompts,
   but verifying it lets you catch contradictions in the user's brief.
4. **Run:**
   ```bash
   python3 interfaces/cli/cf.py editorial gen \
     --image <path> --brand <slug> \
     [--engine veo3|seedance2|both] \
     [--prompt "extra steering"] \
     [--duration 8] [--aspect 9:16]
   ```
5. **Report back** the run folder. Open `brief.json` if the user wants the
   exact prompts. Open the mp4 with `open <path>` (macOS).
6. **After judgment**, if the clip is not brand-on, update
   `brands/<slug>/brand.md` (durable DNA) and/or `brands/<slug>/MASTER_CONTEXT.md`
   (mutable accumulated knowledge) **before** rerunning. Compound improvement
   is the entire point — don't just tweak the user's prompt.

## Hard rules

- `--brand` is REQUIRED. If the user doesn't say which brand, ask. Never default.
- Don't run `--engine both` for a brand-new prompt that hasn't been tuned. Run
  `veo3` first, judge, tune brand.md if needed, then comparison-run.
- Outputs live in `output/<ts>/editorial-cinematic/<brand>/run/` — never reuse
  an existing run folder.
- This flow does NOT do spoken UGC. If the user wants a person talking, route
  them to `/ugc` instead.
