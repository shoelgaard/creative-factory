# fal engine

Thin wrapper around the fal.ai queue API.

Currently exposes Seedance 2.0 image-to-video. More fal.ai models can be added
without changing this engine's interface — just add a new model entry to
`engine.yaml` and route the `--model` flag through.

## What it does well

- Seedance 2.0 motion is exceptionally realistic for product close-ups
- 1080p default output
- Predictable queue API with `request_id` polling

## What it does badly

- No audio — silent output
- Slower than Veo for short clips (5s render can take 2-6 min)

## Auth & setup

`FAL_API_KEY` (or legacy `FAL_KEY`) in `.env`.

## Direct usage

```bash
python3 engines/fal/client.py \
  --image references/slot1_hero.jpg \
  --prompt "Editorial cinematic product film ..." \
  --out-dir output/test/seedance \
  --duration 5 --aspect 9:16
```
