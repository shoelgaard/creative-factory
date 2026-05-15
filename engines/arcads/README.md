# arcads engine

Thin wrapper around the [Arcads external API](https://external-api.arcads.ai/docs).

Currently exposes the **actor pipeline** (`/v1/scripts`) — pre-cast real actors
delivering a script. Aspect, duration, and camera framing are determined by the
chosen "situation" (preset scene+camera+emotion combo), not by request parameters.

The v2 unified video endpoint (`/v2/videos/generate`) is not wrapped here yet;
when we need it we'll add it alongside, sharing the same auth and HTTP helpers.

## What it does well

- Pre-cast real-human actors → high UGC credibility
- Multi-scene scripts (multiple `videos[]` entries render independently)
- Account-side project / folder organisation

## What it does badly / can't do

- No product reference image input on the actor pipeline. Talking-head only —
  the candle is not in the shot. For product-on-camera use a different flow
  (Seedance via fal, or Arcads' own v2 product-showcase).
- Language is a property of the chosen *voice*, not the actor. Danish
  availability must be verified at runtime (probe `GET /v1/voices?language=da`).
- Per-second cost not published — log `creditsCharged` from first call.

## Auth

Two options, in order of preference:

1. `ARCADS_BASIC_AUTH` — pre-encoded `Basic <base64>` header copied directly
   from the Arcads dashboard at `app.arcads.ai/settings/api`.
2. `ARCADS_API_KEY` — used as Basic auth username with empty password.
   Some accounts get 403 in this mode; prefer option 1.

Wrap the value in single quotes in `.env` (special chars `{`, `[`, `*` break
shell parsing):

```
ARCADS_BASIC_AUTH='Basic abcdef0123...'
```

## Smoke test

```bash
python3 engines/arcads/client.py products       # list your products
python3 engines/arcads/client.py voices-da      # confirm Danish voices exist
python3 engines/arcads/client.py situations --gender female --age adult
```

If `voices-da` returns an empty list, Danish is not available on your account.
Drop Sylvester a line — we'll need to fall back to English or check whether
Arcads supports DA via a different language code.
