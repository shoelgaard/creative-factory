# UGC talking-head flow

A pre-cast Arcads actor delivers a brand-voiced script directly to camera.
Single clip, no product on camera (the product is what she *talks about*).

## When to use

- You want a credible "real person recommends this" video for Meta / TikTok / IG
- You have a clear hook + one or two beats + an implicit CTA
- The audience reads scripted UGC as authentic-enough — not influencer-polished, not corporate-clean

## When not to use

- You want product on camera → use editorial-cinematic flow for now;
  product-showcase via Arcads' v2 endpoint lands later
- You want voice-of-the-founder / talking-CEO → use B2B avatar flow when it lands (HeyGen)
- You want pure ambient / no person → use editorial-cinematic

## Run it

```bash
# Simplest case — interactive, all fields prompted
cf ugc gen --brand persillo --product "Stubben Gylden"

# With inline brief
cf ugc gen --brand persillo --product "Stubben Gylden" \
  --hook "Det her lys ved hvornår dagen slutter" \
  --beats "Jeg tænder den når børnene er i seng og jeg får en time for mig selv" \
          "Den dufter ikke som de andre — bare ren bivoks, varm og rolig" \
  --cta "Den hedder Stubben i gylden, fra Persillo"

# From a YAML brief file
cf ugc gen --brand persillo --brief-file briefs/persillo/stubben-gylden-v1.yaml
```

## Output

```
output/<ts>/ugc-talking-head/<brand>/run/
├── brief.json
├── script.txt              ← the full dialogue rendered to the actor
├── meta.json
└── arcads_<ts>.mp4
```

## Gates that fire

1. **Dialogue gate** — full script shown numbered with word-count vs. target duration
2. **Credit gate** — cost estimate before render

Both must be explicitly approved (`y`). `--yes` bypasses but use sparingly.

## Engine: arcads

Calls `POST /v1/scripts` (create) → `POST /v1/scripts/{id}/generate` →
poll `GET /v1/scripts/{id}/videos` → download.

Aspect / duration / camera are determined by the *situation* (preset scene)
chosen for the persona. We do not pass aspect/duration in this flow.
