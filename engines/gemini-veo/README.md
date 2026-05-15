# gemini-veo engine

Thin wrapper around Google's Veo 3 long-running video generation endpoint.

## What it does well

- Native audio (ambient room-tone, faint motion, no music) generated alongside the video
- Stable handling of editorial product subjects (cinematic still-lifes)
- High coherence between reference image and output motion

## What it does badly

- Talking heads — the 3.1 preview models tolerate spoken text but the output
  looks visibly AI-generated. Use Arcads / HeyGen for that.
- Fast cuts / multi-shot — single continuous clip only.
- 4K — output tops at ~720p effective.

## Auth & setup

Set `GEMINI_API_KEY` in `.env`. The wrapper also auto-loads the existing
Persillo `.env` at `~/Library/CloudStorage/OneDrive-ADClient/AI agents HQ/Persillo/Produkter/.env`.

## Direct usage (without a flow)

```bash
python3 engines/gemini-veo/client.py \
  --image references/slot1_hero.jpg \
  --prompt "Editorial product film ..." \
  --out-dir output/test/veo3 \
  --duration 8 --aspect 9:16
```

But normally a flow invokes this; you should not call it directly outside of
debugging.
