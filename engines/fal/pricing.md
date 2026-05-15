# fal pricing (estimate fallback)

fal.ai is pay-per-second. These numbers are from the fal.ai pricing page.
Replace with historical data from `logs/fal.jsonl` once we have runs.

| Model | $ per 1s video | Notes |
|---|---:|---|
| fal-ai/bytedance/seedance/v1/pro/image-to-video | ~$0.10 | 5s clip ≈ $0.50 at 1080p |

fal.ai may add platform fees on top. The exact billed cost is returned by the
queue API and should be logged to `logs/fal.jsonl` as `cost_actual_usd`.
