# Persillo USPs

Selling points stored so you don't retype them on every run. Two scopes:

```
usps/
├── brand.md            — Persillo-wide USPs (true for every product)
└── <product-slug>.md   — product-specific USPs
```

## Format

One USP per bullet. Short, factual, in your own voice. No marketing fluff.
First few words = the angle, rest = the substance.

```markdown
# Stubben Gylden USPs

- Lang brændetid — ~35 timers stille flamme på ét lys
- Ren bivoks — ingen parafin, ingen tilsætning, ingen duft
- Stille flamme — drypper ikke, oser ikke, blafrer ikke
- Naturlig farve — den varme honning kommer fra voksen selv
- Holdbar — kan brænde gennem mange aftener uden at miste form
```

Flows reading USPs:
- `usps/brand.md` is always loaded
- `usps/<product-slug>.md` is loaded when --product matches
- Statics-flow picks N USPs (by index or random) to generate N ad-variants
