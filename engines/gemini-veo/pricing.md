# gemini-veo pricing (estimate fallback)

Google does not return cost in API responses. These are estimates published by
Google's pricing page and confirmed against community benchmarks. Replace with
historical data from `logs/gemini-veo.jsonl` as soon as we have a few runs.

| Model | $ per 1s video | Notes |
|---|---:|---|
| veo-3.1-generate-preview | ~$0.075 | 8s clip ≈ $0.60 |
| veo-3.0-generate-001 | ~$0.075 | Same as 3.1 preview |
| veo-3.0-fast-generate-001 | ~$0.040 | About half the cost, slightly lower quality |
| veo-3.1-fast-generate-preview | ~$0.040 | Same tier as 3.0-fast |
| veo-3.1-lite-generate-preview | ~$0.020 | Cheapest, useful for iteration |

Audio is included in the per-second rate. No additional charge for native audio.
