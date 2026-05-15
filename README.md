# Creative Factory

One CLI, one brief → finished ad clips. MVP-scope: Persillo only, Veo 3 + Seedance 2.0
(image-to-video), 8-second 9:16 clips, side-by-side comparison.

## Quick start

```bash
bash scripts/setup.sh
# Add GEMINI_API_KEY to .env (FAL_API_KEY is optional; Veo-only runs without it)

python3 scripts/cf.py gen \
  --image references/slot1_hero.jpg \
  --brand persillo \
  --engine veo3
```

Output lands in `output/<timestamp>/<engine>/`.

## CLI

```bash
cf gen --image <path> --brand <slug> --engine [veo3|seedance2|both]
       [--prompt "extra steering"] [--aspect 9:16] [--duration 8]
```

- `--engine both` runs Veo 3 and Seedance 2.0 **in parallel** and saves their
  outputs side-by-side for direct comparison.
- Without `FAL_API_KEY`, seedance is skipped automatically.

## Layout

```
brands/<slug>/brand.md     # visual DNA, do's/don'ts, motion grammar
scripts/cf.py              # CLI router
scripts/veo3_gen.py        # Veo 3 image-to-video via Gemini API
scripts/seedance_gen.py    # Seedance 2.0 image-to-video via fal.ai
scripts/lib/               # brand_loader, prompt_builder
output/<ts>/               # generated clips + brief.json + meta.json
references/                # product images (gitignored)
```

## Status

- ✅ Scaffolding, brand.md, prompt-builder, both engine wrappers, parallel CLI
- ✅ First Veo 3 clip generated (Planken Gylden hero, 8s 9:16, 55s pipeline time, 1.0 MB)
  → `output/2026-05-15_11-47-55/veo3/veo3_20260515-114756.mp4` — needs manual quality judge
- ⏳ FAL_API_KEY (for seedance side-by-side) — not blocking
- ⏳ Push to GitHub (`creative-factory` repo) once quality-bar is confirmed

## Verified model + flags (2026-05-15)

- Veo model: `veo-3.1-generate-preview` (3.0-preview returns 404 — use 3.1, or 3.0-generate-001)
- `personGeneration`: must be `allow_adult` for 3.1 (`dont_allow`/`allow_all` rejected)
- Transient errors: op-codes 8 + 14 retried up to 3× with 30/60/120s backoff
