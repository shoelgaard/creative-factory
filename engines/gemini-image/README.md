# gemini-image engine

Wrapper around Gemini's image-generation endpoint ("Nano Banana"). Synchronous
single-call API — no long-running operation polling.

## What it does well

- Editorial product photography at 2K with strong material fidelity
- Multi-reference: product image + template + mood-board, all in one call
- Aspect-ratio respected accurately (4:5 for Meta feed)

## What it does badly

- Hands (sometimes 6 fingers, weird joints) — Persillo flow avoids them anyway
- Embedded typography: text in image often misrenders Danish characters (æøå).
  For headlines with Danish glyphs, prefer external copy (overlay in Meta ad
  manager) over embedded.
- Very long prompts: tends to ignore later constraints. Keep prompt under ~600 words.

## Auth

`GEMINI_API_KEY` in `.env` (or the inherited Persillo `.env`).

## Direct usage

```bash
python3 engines/gemini-image/client.py \
  --prompt "Editorial product still life ..." \
  --out output/test/banana.png \
  --aspect 4:5 --size 2K \
  --ref brands/persillo/references/products/Grenen/Gylden/slot1_hero.jpg \
  --ref brands/persillo/references/templates/diptyque__0139d__large-candles-wooden-tier__crop.png
```
