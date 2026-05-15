# MASTER_CONTEXT — Creative Factory session state

Persistent state mellem sessioner. Opdateres efter hver round.

## Active brand

**persillo** (default)

## Engine status

| Engine | Status | Last verified | Notes |
|---|---|---|---|
| veo3 | ✅ working (first clip 2026-05-15 11:48) | 2026-05-15 | Model: `veo-3.1-generate-preview`, `personGeneration=allow_adult`. Submit + 55s polling + download virker. Retry på code 14/8 (transient) tilføjet. |
| seedance2 | scaffolded, untested | — | needs FAL_API_KEY |

## Cost-budget (per clip, estimated)

| Engine | Est. cost | Notes |
|---|---|---|
| veo3 (8s, 720p) | $0.40-$0.75 | Gemini API pricing; varies by model variant |
| seedance2 (5s, 1080p) | ~$0.50 | fal.ai pay-as-you-go |

## Veo 3 learnings (2026-05-15)

1. **Model-ID:** `veo-3.0-generate-preview` returnerer 404. Brug `veo-3.1-generate-preview` (eller `veo-3.0-generate-001`).
2. **personGeneration:** `dont_allow` afvises af alle aktuelle Veo-modeller. `allow_all` afvises af 3.1. **`allow_adult` virker overalt** — vi støtter os til negativ-prompt for at suppress mennesker.
3. **Transient errors:** Operation-fejl code 14 "high demand" rammer regelmæssigt. Vi resubmitter op til 3 gange med backoff (30s → 60s → 120s).
4. **Tilgængelige modeller (per `ListModels` 2026-05-15):**
   - veo-2.0-generate-001
   - veo-3.0-generate-001
   - veo-3.0-fast-generate-001 (billigere)
   - veo-3.1-generate-preview ← default
   - veo-3.1-fast-generate-preview
   - veo-3.1-lite-generate-preview

## OneDrive case-collision (RESOLVED 2026-05-15 11:50)

OneDrive konsoliderede selv: kun `Creative Factory/` overlever lokalt (verificeret med `find -maxdepth 2 -iname creative*`). Den lowercase-stub er væk. Kanonisk navn fremad: **`Creative Factory`** (med mellemrum, capitalized).

## Runs

| Timestamp | Brand | Engine | Image | Result | Note |
|---|---|---|---|---|---|
| 2026-05-15 11:41 | persillo | veo3 | planken_gylden_hero.jpg | FAIL (400) | `personGeneration=dont_allow` ikke supporteret |
| 2026-05-15 11:42 | persillo | veo3 | planken_gylden_hero.jpg | FAIL (op code 14) | Submit OK; "high demand" |
| 2026-05-15 11:46 | persillo | veo3 | planken_gylden_hero.jpg | FAIL (404) | `veo-3.0-generate-preview` ikke fundet — bad model ID |
| 2026-05-15 11:47 | persillo | veo3 | planken_gylden_hero.jpg | FAIL (400) | `allow_all` ikke supporteret af 3.1 |
| 2026-05-15 11:48 | persillo | veo3 | planken_gylden_hero.jpg | ✅ OK (55s, 1.0 MB mp4) | Veo 3.1 + allow_adult. Output: `output/2026-05-15_11-47-55/veo3/veo3_20260515-114756.mp4`. Manuel kvalitets-judge pending. |
