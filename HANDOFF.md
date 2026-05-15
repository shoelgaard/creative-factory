# Creative Factory — Session Handoff

**Status (2026-05-15):** MVP live. Veo 3.1 leverer 8s 9:16 clips fra produkt-billede + Persillo brand-DNA. Første clip på Planken Gylden hero ligger i `output/2026-05-15_11-47-55/veo3/`. Manuel kvalitets-judge mangler.

Næste skridt:
1. Sylvester ser klippet og siger om det rammer "Persillo-værdigt"
2. Itererér på `brands/persillo/brand.md` hvis bar'en ikke holder
3. Tilføj `FAL_API_KEY` til `.env` for at aktivere Seedance 2.0 + køre `--engine both` til sammenligning
4. Beslut OneDrive-navngivning (se MASTER_CONTEXT.md "OneDrive case-collision")
5. GitHub-repo: hvilken konto/org? Skal lokal `creative-factory/` slettes når `Creative Factory/` pushes?

## Hvad er det her

Creative Factory: én CLI-pipeline der tager produkt-billede ELLER URL → leverer færdige ads (video + statics + copy) for flere brands. Persillo først, derefter AD Client HQ, Ace eSport, Pokemon. Bygges som Claude Code skill-pack i Python.

## Beslutninger truffet i tidligere session

1. **Python**, ikke Bun/TypeScript — matcher eksisterende `gemini_image_gen.py` pattern i Persillo/_System/Scripts/
2. **Skill-pack-mønster** lånt fra https://github.com/krusemediallc/arcads-claude-code (mappestruktur, MASTER_CONTEXT.md, references/)
3. **Engines i MVP:** Veo 3 (direkte via Gemini API, bruger eksisterende `GEMINI_API_KEY`) + Seedance 2.0 (via fal.ai). Begge køres parallelt så bruger kan sammenligne outputs side-om-side på samme brief.
4. **IKKE Arcads i MVP** — det er en marketing-platform med UGC-fokus, overkill for Persillo editorial. Tilføjes senere som sister-skill når UGC bliver aktivt for andre brands.
5. **IKKE Higgsfield i MVP** — tilføjes senere som motion-preset-lag når viral ad-look bliver aktivt.
6. **IKKE Remotion/komposition i MVP** — vi outputter rå engine-clips. Multi-shot edit tilføjes når enkelt-clips er beviset gode.
7. **Kode i GitHub** (privat repo `creative-factory`). Brand-kits + prompts versioneres. Outputs/refs i lokal OneDrive.

## MVP-scope (uge 1)

Én CLI-kommando:
```bash
cf gen --image <path> --brand persillo --engine [veo3|seedance2|both]
```
- Input: produkt-billede + brand
- Output: 1-2 × 8s mp4 i `output/<dato>/`
- Engine `both` = parallel kør begge, gemmer side-om-side til sammenligning

## Mappestruktur der skal bygges

```
creative-factory/
├── CLAUDE.md                   # projekt-specifik, læses af nye sessioner
├── README.md
├── .env.example                # GEMINI_API_KEY, FAL_API_KEY
├── .gitignore                  # .env, output/, references/, __pycache__
├── MASTER_CONTEXT.md           # session-state (default brand, costs, learnings)
├── brands/
│   └── persillo/
│       └── brand.md            # visual DNA, do's/don'ts, prompt-fragmenter
├── skills/
│   └── creative-factory/       # Claude Code skill definition
│       ├── SKILL.md
│       └── prompts/            # per-engine prompt templates
├── scripts/
│   ├── setup.sh                # init: install deps, prompt for keys
│   ├── veo3_gen.py             # Veo 3 wrapper (mirror gemini_image_gen.py)
│   ├── seedance_gen.py         # Seedance 2.0 wrapper via fal.ai
│   ├── cf.py                   # top-level CLI router
│   └── lib/
│       ├── prompt_builder.py
│       └── brand_loader.py
├── references/                 # gitignored, produkt-billeder
└── output/                     # gitignored, generated videos
```

## Test-asset klar

Persillo Planken Gylden hero-billede:
`/Users/sylvesterhoelgaard/Library/CloudStorage/OneDrive-ADClient/AI agents HQ/Persillo/Produkter/Bivokslys/Planken/Gylden/Produktbilleder/02_Final/slot1_hero.jpg`

Brug det til første smoke-test.

## Pattern-reference

Den eksisterende Gemini-image-pipeline i Persillo:
`/Users/sylvesterhoelgaard/Library/CloudStorage/OneDrive-ADClient/AI agents HQ/Persillo/Produkter/_System/Scripts/gemini_image_gen.py`

Kopier:
- urllib (ingen SDK-deps)
- argparse CLI pattern
- retry-logik
- Output-naming (timestamp + index)
- `.env` pattern med `GEMINI_API_KEY`

## Persillo brand-DNA (destilleret)

Læs også fuld kontekst i:
- `/Users/sylvesterhoelgaard/.claude/projects/-Users-sylvesterhoelgaard-Library-CloudStorage-OneDrive-ADClient-AI-agents-HQ-Persillo/memory/brand_thesis.md`
- `/Users/sylvesterhoelgaard/.claude/projects/-Users-sylvesterhoelgaard-Library-CloudStorage-OneDrive-ADClient-AI-agents-HQ-Persillo/memory/pdp_standard_sequence.md`
- `/Users/sylvesterhoelgaard/.claude/projects/-Users-sylvesterhoelgaard-Library-CloudStorage-OneDrive-ADClient-AI-agents-HQ-Persillo/memory/image_generation_learnings.md`

Kondensat til prompt-builder:
- Editorial Kinfolk/RUM-look, ikke West Elm/Amazon
- Naturlig base (travertin, rå eg, limewashed)
- Warm muted-grey limewashed bagvæg
- Blødt sidelys fra venstre, blød skygge
- Ingen mennesker/hænder
- Slank produkt-proportion (Persillo-kerter er 1.6×25cm — Gemini fed dem altid for tykke)
- Stabil rolig flamme, ikke dramatisk
- Hygge = rigtige genstande (bøger, keramik, lin, messing), aldrig "blurred background"

## Brugerens preferences (fra global CLAUDE.md)

- Dansk
- Direkte, kort, ingen over-forklaring
- Parallel-execution når muligt
- Beslut selv på tekniske valg, spørg kun om reelle business-beslutninger
- Quality gate: evidens-baseret verifikation, mekanisk først, root-cause ikke symptom
- "Compound improvement" — hvert feedback-round opdaterer SOP/prompts/memory

## Næste skridt i ny session

1. Læs denne fil
2. Læs `/Users/sylvesterhoelgaard/.claude/plans/lazy-wondering-parasol.md` for fuld plan
3. Vent på bruger-input om:
   - GitHub-username + om repo skal være på personlig eller org-konto
   - fal.ai API-key (eller bekræftelse på at vi starter Veo-only)
4. Når input er der: scaffold mappestruktur → skriv veo3_gen.py + cf.py → første test på Planken-hero → commit → push til GitHub

## Tools/dependencies forventet

- Python 3.14 (installeret ✓)
- urllib (stdlib) til Veo 3 + fal.ai
- argparse (stdlib)
- python-dotenv (installeres af setup.sh) til at læse .env

## Det vi IKKE skal bygge nu

- Web-app / Telegram-bot (Fase 3, senere)
- Mac Mini always-on engine (Fase 3, senere)
- Multi-brand context switching (Fase 2, efter Persillo POC)
- Remotion/komposition (Fase 2)
- HeyGen avatar af bruger (Fase 4, B2B-spor)
- Arcads/Higgsfield (Fase 5, UGC-spor andre brands)

Hold MVP-scope stramt: 1 brand, 1-2 engines, 1 CLI-kommando, manuel kvalitets-judge.
