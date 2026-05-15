# Editorial cinematic flow

Single-clip product film from one reference image. Quiet drift, stable flame,
native ambient audio. Intended for Persillo and similar editorial brands.

## When to use

- You have a finished product photo and want an 8-second cinematic loop for
  PDP, Meta feed, or YouTube pre-roll
- The brand is editorial / quiet-luxury (Kinfolk / Frama / Aesop reference)
- You explicitly do **not** want spoken UGC, talking-head, or fast-cut motion

## When not to use

- You want a person talking → use the `ugc-talking-head` flow
- You want still images → use the `statics` flow (when it lands)
- You need multi-shot composition → not built yet; this flow renders one clip

## Run it

```bash
cf editorial gen --image references/<file> --brand persillo
cf editorial gen --image references/<file> --brand persillo --engine both
cf editorial gen --image references/<file> --brand persillo --engine seedance2
```

`--brand` is required. `--engine both` runs Veo 3 and Seedance 2.0 in parallel
and saves both outputs in the same run folder for side-by-side comparison.

## Output

```
output/<ts>/editorial-cinematic/<brand>/run/
├── brief.json
├── veo3/
│   ├── veo3_<ts>.mp4
│   └── veo3_<ts>.meta.json
└── seedance2/                    # only if --engine includes seedance2
    ├── seedance2_<ts>.mp4
    └── seedance2_<ts>.meta.json
```

## Engines

- **gemini-veo** (default) — Veo 3.1 via Gemini API. 8s, native audio, ~$0.40-0.75/clip.
- **fal** (optional) — Seedance 2.0 via fal.ai. 5s default, 1080p, ~$0.50/clip. Requires `FAL_API_KEY`.
