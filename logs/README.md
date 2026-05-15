# Engine call ledgers

One JSONL file per engine. Append-only. Committed to git — this is the cost
source of truth and survives sessions.

Each line is one API call (successful or failed). Schema:

```json
{
  "ts": "2026-05-15T11:48:13Z",           // ISO-8601 UTC
  "engine": "gemini-veo",                  // matches engines/<name>
  "flow": "editorial-cinematic",           // matches flows/<name>'s display name
  "brand": "persillo",                     // brand slug
  "run_id": "2026-05-15_11-47-55",         // matches output/<ts> folder name
  "model": "veo-3.1-generate-preview",     // engine-specific model id
  "params": {                              // engine-specific call parameters
    "aspect": "9:16",
    "duration": 8,
    "personGeneration": "allow_adult"
  },
  "status": "ok" | "failed" | "transient_error_retried",
  "elapsed_s": 55.0,                       // total wall-clock for this call
  "cost_estimate_usd": 0.60,               // from cost_estimator
  "cost_actual_usd": null,                 // filled if engine reports actual cost
  "asset_id": "operations/satcjbm7ryv8",   // provider's identifier for the asset
  "video_path": "output/2026-05-15_11-47-55/editorial-cinematic/persillo/run/veo3/veo3_20260515-114756.mp4",
  "error": null                            // free-text error message if failed
}
```

## Why JSONL, why committed

- **Append-only** — never edit a past line, only append new ones. History is truth.
- **Grep-able** — `grep '"model": "veo-3.1' logs/gemini-veo.jsonl | jq '.elapsed_s'` is the cost analyst.
- **Per-engine file** — each provider has its own pricing rules; one file per engine keeps schemas simple.
- **Committed** — if we lose this, we lose months of historical cost data. The mp4 outputs are gitignored (regenerable), but the *record* of every call we ever made is institutional memory.

## Reading the ledgers

```bash
cf cost report                    # summary across all engines, all time
cf cost report --since 2026-05-01 # since a date
cf cost report --flow editorial-cinematic --brand persillo
cf cost report --engine gemini-veo
```

Or directly with `jq`:

```bash
jq -s 'map(.cost_estimate_usd) | add' logs/gemini-veo.jsonl  # total estimated cost
```
