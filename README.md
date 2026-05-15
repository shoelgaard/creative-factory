# Creative Factory

One CLI, one brief → finished ad clips. MVP-scope: Persillo only, Veo 3 + Seedance 2.0
(image-to-video), 8-second 9:16 clips, side-by-side comparison.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the four-layer design (interfaces ·
flows · engines · brands).

## Quick start

```bash
bash interfaces/cli/setup.sh
# Add GEMINI_API_KEY to .env (FAL_API_KEY is optional)

python3 interfaces/cli/cf.py editorial gen \
  --image references/slot1_hero.jpg \
  --brand persillo
```

Output lands in `output/<ts>/editorial-cinematic/<brand>/run/`.

## CLI

```bash
cf <flow> <command> [options]

cf editorial gen --image <path> --brand <slug>
                 [--engine veo3|seedance2|both]
                 [--prompt "..."] [--aspect 9:16] [--duration 8]
cf list
```

- `--brand` is **required** on every `gen`. No default brand.
- `--engine both` runs Veo 3 and Seedance 2.0 in parallel for side-by-side comparison.
- Without `FAL_API_KEY`, seedance is skipped automatically.

## Layout

```
flows/<name>/              # one per video-type
engines/<name>/            # one per external service (Gemini-Veo, fal, etc.)
brands/<slug>/             # one per brand (Persillo is the only active brand)
shared/                    # brand_loader, cost_estimator, gates, output convention
interfaces/cli/cf.py       # CLI router
interfaces/skills/<flow>/  # Claude Code skills (/editorial, /ugc, ...)
logs/<engine>.jsonl        # cost ledger per engine (institutional memory)
output/<ts>/<flow>/<brand>/run/   # gitignored, finished artefacts
references/                # gitignored, product images
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
