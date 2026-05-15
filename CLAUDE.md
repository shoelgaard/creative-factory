# Creative Factory — Claude Code context

Læses i hver ny session. Holder dig i samme rille som forrige session.

## Hvad det her er

CLI-pipeline: produkt-billede + brand → 8s cinematic ads. Persillo først, derefter
flere brands. Python, stdlib + certifi. Skill-pack-mønster lånt fra
arcads-claude-code (mappestruktur, MASTER_CONTEXT, brand.md per brand).

## MVP-kommandoen

```bash
python3 scripts/cf.py gen --image <path> --brand persillo --engine [veo3|seedance2|both]
```

- `both` kører begge engines i parallel og lægger output side-om-side
- Output: `output/<ts>/<engine>/*.mp4` + meta.json + brief.json
- Brief.json indeholder de eksakte prompts og parametre, så outputs er reproducerbare

## Beslutninger (immutable)

1. **Python**, ikke Bun. Matcher eksisterende Persillo-pipeline.
2. **Veo 3 + Seedance 2.0** i MVP. Begge image-to-video. Begge med parallel side-by-side
   eksekvering så bruger kan judge kvalitet direkte.
3. **Ingen Arcads/Higgsfield/Remotion** i MVP — det er rå engine-clips.
4. **stdlib + certifi** — ingen tunge SDK-deps. Mirror gemini_image_gen.py-pattern.
5. **Engines er subprocesses**, ikke libraries. Holder fejl-blast-radius lille,
   gør det trivielt at swap'e en engine ud.

## Pattern-references

- `Persillo/Produkter/_System/Scripts/gemini_image_gen.py` — argparse-stil,
  urllib-pattern, retry-logik, output-naming.
- `~/.claude/projects/.../Persillo/memory/brand_thesis.md` — fuld brand-thesis.
- `~/.claude/projects/.../Persillo/memory/image_generation_learnings.md` — alle
  lærdomme fra image-pipeline. Gælder også for video (særligt proportions-fix).
- `~/.claude/projects/.../Persillo/memory/winning_prompts.md` — vinder-prompts
  per slot. Frø til video-prompt-builder.

## Test-asset

`/Users/sylvesterhoelgaard/Library/CloudStorage/OneDrive-ADClient/AI agents HQ/Persillo/Produkter/Bivokslys/Planken/Gylden/Produktbilleder/02_Final/slot1_hero.jpg`

Smoke-test default. 1:1 men cf håndterer aspect-konvertering på engine-siden
(begge engines accepterer 9:16 og crop'er fra det højere af to akser).

## Brand-tilføjelse

Ny brand = ny mappe `brands/<slug>/brand.md` med samme frontmatter (`name`,
`tagline`, `positioning`) og samme sektioner. `prompt_builder.py` reads body
verbatim; nye brands kræver kun ny brand.md.

## Quality gate (gælder også her)

- **Evidens.** Vis tjek (file-read, curl-output) ikke verbale forsikringer.
- **Mekanisk først.** Brug grep/python-import-test til at validere før du
  hævder det virker.
- **Root cause.** Hvis Veo fejler, find ud af hvorfor — workaround først efter
  årsag er forstået.
- **Ærlig rapportering.** Hvad er testet, hvad er ikke, hvad er usikkert.

## Bruger-preferences

Dansk. Direkte. Parallel når muligt. Beslut selv på tekniske valg. Spørg kun ved
reelle business-beslutninger (penge, prioritering, brand, retning).

## Næste lag (når MVP er valideret)

1. URL-input (`--url`) — scrape hero + product info
2. Copy-gen ved siden af video (primary text, headline, hooks)
3. Multi-shot komposition via Remotion (3-4 klip per ad)
4. Andre brands (AD Client HQ, Ace eSport, Pokemon)
5. UGC-spor (Arcads + ElevenLabs voice clone)
6. Higgsfield motion-presets for viral ad-look
