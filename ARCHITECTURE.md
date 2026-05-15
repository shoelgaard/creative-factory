# Creative Factory — Architecture

**Version:** 0.1 (proposed) · **Status:** awaiting review · **Branch:** `feat/architecture`

This document is the contract for how Creative Factory is structured. Every
implementation decision must reference it. When it conflicts with the code,
the document wins until both are updated together.

---

## 1. Mission

One production platform that lets one person produce brand-safe ads at scale
across multiple video styles, multiple brands, and multiple delivery channels —
without rebuilding the system every time we want a new kind of video.

The platform is not a pipeline. It is a **set of independent tools** plugged
into a thin shared spine.

---

## 2. The four layers

```
┌─────────────────────────────────────────────────────────────────┐
│  INTERFACES   how a human triggers work                          │
│               /ugc · /editorial · /statics  (Claude Code skills) │
│               cf <flow> gen ...             (terminal CLI)       │
│               (later) webapp, Telegram, mobile                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FLOWS        one per video-type — the recipe                    │
│               ugc-talking-head · editorial-cinematic · statics   │
│               (later) cartoon · product-animation · b2b-avatar   │
└─────────────────────────────────────────────────────────────────┘
                              │ uses ↓
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ENGINES      thin wrappers around external services             │
│               arcads · fal · gemini-veo · gemini-image           │
│               (later) heygen · elevenlabs · runway · luma        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  BRANDS       one per brand — the parameter                      │
│               persillo (only active brand)                       │
│               brand.md · MASTER_CONTEXT.md · references/         │
└─────────────────────────────────────────────────────────────────┘

         shared/   ←  brand-loader, cost-estimator, gates, output-convention
         logs/     ←  one JSONL ledger per engine (cost source of truth)
```

**Hard rules:**
1. A flow can use many engines. An engine can be used by many flows. n:n, never 1:1.
2. A brand is **input** to a flow. Never hardcoded inside a flow.
3. A new flow / engine / brand must be addable without touching any other flow / engine / brand.
4. `shared/` only contains what *every* flow uses. If only two flows share something, it lives in one of them or as an explicit library import.

---

## 3. Repo layout

```
creative-factory/
├── ARCHITECTURE.md                       ← this file
├── CLAUDE.md                             ← per-session instructions
├── MASTER_CONTEXT.md                     ← cross-session platform state
├── README.md
├── HANDOFF.md                            ← legacy, kept for history
├── .env.example
├── .gitignore
│
├── interfaces/
│   ├── cli/
│   │   └── cf                            ← entry-point: routes to flows
│   └── skills/
│       ├── ugc/SKILL.md                  ← /ugc → cf ugc gen
│       ├── editorial/SKILL.md            ← /editorial → cf editorial gen
│       └── statics/SKILL.md              ← /statics → cf statics gen
│
├── flows/
│   ├── editorial-cinematic/              ← migrated from current scripts/
│   │   ├── flow.yaml                     ← name, version, engines used, schema ref
│   │   ├── brief.schema.yaml             ← input schema
│   │   ├── README.md                     ← what the flow does, when to use
│   │   ├── prompt_builder.py             ← brand.md + brief → engine prompts
│   │   ├── render.py                     ← orchestrates engine calls
│   │   └── tests/
│   │
│   ├── ugc-talking-head/                 ← new
│   │   ├── flow.yaml
│   │   ├── brief.schema.yaml
│   │   ├── README.md
│   │   ├── script_builder.py             ← brand + brief → spoken dialogue
│   │   ├── render.py                     ← calls arcads-engine
│   │   └── tests/
│   │
│   └── statics/                          ← later
│       └── ...
│
├── engines/
│   ├── arcads/
│   │   ├── engine.yaml                   ← name, version, capabilities, models
│   │   ├── client.py                     ← /v2/videos/generate, /v2/images, /v1/b-roll
│   │   ├── pricing.md                    ← rate table (estimate fallback)
│   │   └── README.md
│   │
│   ├── fal/
│   │   ├── engine.yaml                   ← endpoints: bytedance/seedance, kling, luma
│   │   ├── client.py
│   │   └── README.md
│   │
│   ├── gemini-veo/
│   │   ├── engine.yaml                   ← models: veo-3.1, veo-3.0, veo-3.0-fast
│   │   ├── client.py                     ← migrated from scripts/veo3_gen.py
│   │   └── README.md
│   │
│   └── gemini-image/
│       ├── engine.yaml
│       └── client.py                     ← Nano Banana, when statics flow lands
│
├── brands/
│   └── persillo/
│       ├── brand.md                      ← visual + motion DNA (existing)
│       ├── MASTER_CONTEXT.md             ← per-brand state (learnings, banned terms, defaults)
│       └── references/
│           ├── products/                 ← gitignored, lives in OneDrive
│           └── personas/                 ← gitignored, 10-angle character sheets when used
│
├── shared/
│   ├── brand_loader.py                   ← single way to read brands/<slug>/
│   ├── cost_estimator.py                 ← greps logs/<engine>.jsonl for historic rates
│   ├── gates.py                          ← dialogue gate, credit gate, still→video gate
│   ├── output.py                         ← output/<ts>/<flow>/<brand>/<run>/
│   ├── run_log.py                        ← appends to logs/<engine>.jsonl + MASTER_CONTEXT
│   └── http.py                           ← shared SSL/retry helpers (stdlib + certifi)
│
├── logs/                                 ← committed; cost history is institutional memory
│   ├── README.md                         ← JSONL schema, one event per API call
│   ├── arcads.jsonl
│   ├── fal.jsonl
│   ├── gemini-veo.jsonl
│   └── gemini-image.jsonl
│
├── output/                               ← gitignored
│   └── <ts>/<flow>/<brand>/<run>/
│       ├── *.mp4
│       ├── meta.json                     ← prompt, model, cost, engine, version
│       └── brief.json                    ← original brief that produced this run
│
└── references/                           ← gitignored, project-wide samples
```

---

## 4. Anatomy of each layer

### 4.1 A flow

A flow is a self-contained recipe. It owns:

- `flow.yaml` — version (semver), description, engines it depends on, the brief-schema path
- `brief.schema.yaml` — what input the flow accepts (validated before render)
- `prompt_builder.py` *or* `script_builder.py` — turns `brand.md + MASTER_CONTEXT + brief` into engine-ready prompts/scripts
- `render.py` — orchestrates engine calls, runs gates, writes output + log entries
- `README.md` — when to use this flow, when not to, examples
- `tests/` — at least one smoke test against a stub engine

A flow may **not** import another flow. If two flows need the same logic, that logic moves to `shared/`.

A flow may **not** mutate brand state. It reads `brand.md` and `MASTER_CONTEXT.md`; it writes only to `output/` and `logs/`.

### 4.2 An engine

An engine is a thin wrapper around one external service. It owns:

- `engine.yaml` — version, base URL, auth strategy, supported models, supported parameters per model, hard limits (max duration, aspect ratios, image-count)
- `client.py` — `submit()`, `poll()`, `download()`. Stdlib + certifi only. No SDK dependencies.
- `pricing.md` — fallback rate table when `logs/<engine>.jsonl` has no history
- `README.md` — what this engine does well, what it does badly, gotchas

An engine **never** reads `brand.md`. Brand is a flow concern, not an engine concern.

An engine **always** appends to `logs/<engine>.jsonl` after every call (successful or failed). That ledger is the cost source of truth.

### 4.3 A brand

A brand is configuration. It owns:

- `brand.md` — durable: visual DNA, motion grammar, no-go list, factual constraints (e.g. "Persillo is not handmade in Denmark")
- `MASTER_CONTEXT.md` — accumulated: preferred terms, banned terms, learnings from prior runs, default product hints, default channel/audience
- `references/products/` — product photos (gitignored, lives in OneDrive)
- `references/personas/` — character sheets when a brand wants a consistent AI-persona across UGC (skipped for now — using Arcads' pre-cast avatars first)

A brand is loaded by `shared/brand_loader.py` and passed to flows as a typed object.

### 4.4 An interface

An interface is how a human triggers a flow. There are three planned interfaces, in order of when we build them:

- **Claude Code skill** (now): `/ugc`, `/editorial`, `/statics`. Each `SKILL.md` is a thin shell that calls `cf <flow> gen` after gathering inputs via conversation.
- **CLI** (now): `cf <flow> gen --brand <slug> [--image X] [--brief brief.yaml] [...]`. The skill calls this. Humans can call it directly.
- **Webapp / mobile** (later, if needed): `interfaces/web/` or `interfaces/bot/`. Calls the same flows. We build it only when CLI + skill stop being enough.

An interface **never** contains business logic. It only collects inputs and forwards to a flow.

---

## 5. CLI convention

```
cf <flow> <command> [options]
```

Commands every flow must support:

- `cf <flow> gen --brand <slug> [...]` — produce output
- `cf <flow> describe` — print flow.yaml + brief schema
- `cf <flow> estimate --brand <slug> [...]` — return projected cost before running

Platform-level commands:

- `cf list` — list installed flows, engines, brands
- `cf cost report [--flow X] [--brand Y] [--since DATE]` — read `logs/*.jsonl`, return totals
- `cf doctor` — verify env, keys, engine reachability

---

## 6. Cost architecture

Three layers of cost protection:

### 6.1 JSONL ledger per engine

Every API call by every engine writes one line to `logs/<engine>.jsonl`:

```json
{
  "ts": "2026-05-15T11:48:13Z",
  "engine": "gemini-veo",
  "flow": "editorial-cinematic",
  "brand": "persillo",
  "run_id": "2026-05-15_11-47-55",
  "model": "veo-3.1-generate-preview",
  "params": {"aspect": "9:16", "duration": 8, "personGeneration": "allow_adult"},
  "status": "ok",
  "elapsed_s": 55.0,
  "cost_estimate_usd": 0.60,
  "cost_actual_usd": null,
  "asset_id": "operations/satcjbm7ryv8",
  "video_path": "output/2026-05-15_11-47-55/editorial-cinematic/persillo/veo3/..."
}
```

`cost_actual_usd` is filled when the provider reports it (Arcads does, Gemini doesn't yet). Otherwise we live on estimates.

### 6.2 Estimator

`shared/cost_estimator.py` greps `logs/<engine>.jsonl` for matching `model + params` and returns historical median cost. Falls back to `engines/<name>/pricing.md` when no history exists.

### 6.3 Mandatory gates (borrowed from Arcads skill-pack)

Before any expensive call, the flow must pass three gates:

1. **Dialogue gate** (UGC, B2B-head, any flow with spoken text) — print numbered script, count words against target duration, require explicit `yes`. Separate from credit gate.
2. **Credit gate** (every flow) — print cost breakdown with source citation (`from logs/arcads.jsonl 2026-05-12`), require explicit `yes`.
3. **Still→video gate** (any flow that turns a still into video) — generate still first, show it, require explicit `yes` before paying for video render.

Gates are implemented in `shared/gates.py` and called by every flow's `render.py`. No flow may bypass them.

Soft limits configurable per brand in `brands/<slug>/MASTER_CONTEXT.md`:
- `max_cost_per_run_usd` — flow refuses to render if estimate exceeds
- `max_cost_per_day_usd` — flow refuses if today's `logs/*.jsonl` total + new estimate exceeds

---

## 7. Output convention

```
output/
└── 2026-05-15_11-47-55/                  ← timestamp = run id
    └── editorial-cinematic/              ← flow name
        └── persillo/                     ← brand slug
            └── run/                      ← one folder per run
                ├── brief.json            ← what was asked
                ├── meta.json             ← what was produced (per asset)
                ├── *.mp4                 ← the videos
                └── *.jpg                 ← stills used as start frames, if any
```

Output is gitignored. Cost history (`logs/`) is committed. The artifact lives in OneDrive (sync = backup); the *record* of how it was made lives in git.

---

## 8. Git workflow

- `main` is always shippable. The most recent UGC ad we'd be comfortable showing the team came from `main`.
- New flow / engine / brand / refactor → feature branch `feat/<name>`.
- One logical change per commit. Commit messages explain *why*, not *what*.
- Each flow has its own version in `flow.yaml`. Bump on every functional change. Outputs record which flow version produced them.
- Each engine has its own version in `engine.yaml`. Bump when external API changes force a wrapper change.
- `MASTER_CONTEXT.md` (per-brand) is committed — accumulated learnings are institutional memory.
- `.env` never committed. Verified by `.gitignore` and `cf doctor`.

GitHub repo: `shoelgaard/creative-factory` (private). HTTPS auth via macOS keychain.

---

## 9. How to add a new ___

### A new flow

1. `git checkout -b feat/flow-<name>`
2. `mkdir flows/<name> && cd flows/<name>`
3. Create `flow.yaml`, `brief.schema.yaml`, `README.md`, `render.py`, `prompt_builder.py` (or script_builder), `tests/`
4. Import only `shared/*` and `engines/<name>` — never another flow
5. Add `interfaces/skills/<name>/SKILL.md` with the `/`-trigger phrase
6. Add CLI entry in `interfaces/cli/cf` routing table
7. Write at least one smoke test
8. PR / merge to `main`

### A new engine

1. `git checkout -b feat/engine-<name>`
2. `mkdir engines/<name> && cd engines/<name>`
3. Create `engine.yaml`, `client.py`, `pricing.md`, `README.md`
4. Implement `submit() / poll() / download()` returning a uniform asset descriptor
5. Add `logs/<name>.jsonl` and update `logs/README.md` schema if the engine has unusual fields
6. No flow changes in this PR — engine first, integration second
7. PR / merge to `main`

### A new brand

1. `mkdir brands/<slug>`
2. Write `brand.md` with the same frontmatter as `persillo/brand.md` (name, tagline, positioning)
3. Copy `MASTER_CONTEXT.md` template, fill defaults
4. Add `brands/<slug>/references/products/.gitkeep`, drop product photos in OneDrive
5. No code changes anywhere else — brands are pure config

### A new interface

1. `mkdir interfaces/<name>`
2. The interface calls existing flows. It does not contain business logic.
3. Document the trigger pattern (URL, keystroke, slash-command, Telegram command) in the interface's own README

---

## 10. Migration plan (current state → this architecture)

Current state:

```
scripts/cf.py               → moves to interfaces/cli/cf
scripts/veo3_gen.py         → moves to engines/gemini-veo/client.py
scripts/seedance_gen.py     → moves to engines/fal/client.py
scripts/lib/brand_loader.py → moves to shared/brand_loader.py
scripts/lib/prompt_builder.py → moves to flows/editorial-cinematic/prompt_builder.py
brands/persillo/brand.md    → stays
skills/creative-factory/    → splits into interfaces/skills/editorial/ (UGC stub deleted, rebuilt in own PR)
output/2026-05-15_11-47-55/ → restructured to output/2026-05-15_11-47-55/editorial-cinematic/persillo/run/
```

Two commits on `feat/restructure`:

1. **Restructure** (mechanical): move files, update imports, no behaviour change. Run `cf editorial gen --image references/planken_gylden_hero.jpg --brand persillo` after; same output as before.
2. **Add logging + gates**: introduce `logs/gemini-veo.jsonl`, `shared/gates.py`, `cost_estimator`. The existing Veo flow now produces a log entry and runs through the credit gate.

Then `feat/ugc` adds the UGC flow against `engines/arcads` (new engine, new flow).

---

## 11. Non-goals (deliberately not in scope yet)

- **Multi-shot composition** (Remotion, ffmpeg stitching) — flows produce single clips for now
- **Eval-loop** (vision-LLM scorer) — manual judge until cost / volume justifies automating it
- **Server-side rendering** (Mac Mini, cloud worker) — local CLI is enough until interface 2 (webapp) lands
- **Multi-account / team** — single-user platform until proven valuable, then we revisit
- **Auto-publish to ad platforms** (Meta, TikTok, YouTube ad uploads) — we deliver mp4 + meta.json, human uploads

---

## 12. Open questions (your call)

1. **`MASTER_CONTEXT.md` placement.** Currently there's one in repo root. Should it stay as a *platform-level* state file (cross-brand learnings, infrastructure decisions) and have a separate one per brand at `brands/<slug>/MASTER_CONTEXT.md` (brand-specific accumulated learnings)? Proposed: yes. Both files exist, distinct purposes.

2. **Output location.** Currently `output/` lives in OneDrive. That's fine for finished videos. But should run-metadata (`meta.json`, `brief.json`) also be committed to git in `runs/<ts>/` so we have an institutional record of every ad we ever produced — even if the mp4 itself stays out of git? Proposed: yes, commit metadata, ignore binaries.

3. **Versioning scheme.** Proposed: flows and engines use semver in their `.yaml`. The platform itself uses date-based tags (`v2026-05-15`) cut whenever main is in a known-good state.

4. **Default brand selection.** When `cf editorial gen` is called without `--brand`, should it default to `persillo` (since that's currently the only brand)? Proposed: yes, configurable in platform-level `MASTER_CONTEXT.md`.

---

## 13. Sign-off

When you've read this and are OK with the structure (or pushed back and we've revised it), I'll:

1. Merge `feat/architecture` to `main`
2. Open `feat/restructure` and do the migration (commit 1: mechanical move; commit 2: add logging + gates)
3. Verify the existing Veo clip can still be reproduced by `cf editorial gen --image references/planken_gylden_hero.jpg --brand persillo`
4. Open `feat/ugc` and build the UGC flow on top of the Arcads engine, with Persillo Stubben Gylden as the first test case

No code changes happen until you sign off on this document.
