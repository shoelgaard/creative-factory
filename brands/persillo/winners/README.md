# Persillo winners

Outputs you've judged as good enough to ship or reuse. Promote files here from
the `output/` folder when a render passes your bar.

```
winners/
├── statics/   — winning static ads (jpg/png)
├── ugc/       — winning UGC clips (mp4)
└── editorial/ — winning editorial cinematic clips (mp4)
```

## Why this exists

Two reasons:

1. **Library to reuse.** Templates of your own that worked, so future runs
   can be primed with "make me variations on this winner".
2. **Compound learning.** Each winner's brief.json is kept alongside the
   asset so we can grep what made it work and update brand.md / MASTER_CONTEXT.md.

## Convention

When promoting a file from `output/<ts>/<flow>/<brand>/run/`:

- Copy (don't move — keep originals in output/) the mp4/jpg + its meta.json
- Drop them in `winners/<flow>/<ts>__<short-description>/`
- The short description is yours — e.g. `2026-05-15__stubben-aften-hook-v1`

Later we'll add `cf winner promote <output-path>` to automate this.
