# arcads pricing (estimate fallback)

Arcads uses a credit system. The external API does not publish a per-second
rate for the actor pipeline (`/v1/scripts`). The values below are best-effort
placeholders and will be replaced by historical median from `logs/arcads.jsonl`
as soon as we have a few runs.

| Endpoint / pipeline | $ per 1s video | Notes |
|---|---:|---|
| /v1/scripts (actor pipeline) | ~$0.30 | placeholder — verify after first run |
| /v2/videos/generate seedance-2.0 | ~$0.10 | matches direct fal.ai rate |
| /v2/videos/generate veo31 | ~$0.075 | matches direct Gemini Veo rate |

**Important:** these are EUR/USD-converted credit cost estimates. Arcads bills
in credits at the account's purchased rate. Log `creditsCharged` from the asset
response and convert via the account's credit→USD rate.
