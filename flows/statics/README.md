# Statics flow

Bulk-renders static ad creatives from a concepts markdown file.
Engine: gemini-image (Nano Banana Pro). Default aspect: 4:5 for Meta feed.

## Concept file format

H3 header per concept, with these fields:

```
### [ ] A1 · diptyque-large-candles-wooden-tier · Gylden
**Visual:** ...
**Headline:** ...
**Primary:** ...
**Description:** ...
**CopyMode:** embedded | external          (optional, default external)
**EmbedText:** "..."                       (optional, when CopyMode=embedded)
```

- The checkbox `[ ]` becomes `[x]` when user marks a concept for explicit selection.
- Concept ID (A1) is unique per file.
- Template ref must match a file in `brands/<slug>/references/templates/`.
- Variant: `Gylden | Råhvid | Mixed | Gylden + Råhvid`.

## Run

```bash
# Render every concept in the file
cf statics gen --brand persillo --concepts brands/persillo/concepts/grenen-round-1.md

# Render only specific concept IDs
cf statics gen --brand persillo --concepts brands/persillo/concepts/grenen-round-1.md --only A1,B2,C3

# Render only concepts marked with [x]
cf statics gen --brand persillo --concepts brands/persillo/concepts/grenen-round-1.md --only-checked

# Disable passing the template as a direct engine ref (template stays as text-only inspiration)
cf statics gen --brand persillo --concepts ... --no-template-ref
```

## Output

```
output/<ts>/statics/<brand>/run/
├── manifest.json
├── A1.png
├── A1.prompt.txt        — full prompt sent to gemini-image
├── A1.brief.json        — concept fields + ref paths
├── B2.png
├── ...
```

## Cost

Default model is gemini-3.1-flash-image-preview ("Nano Banana Pro") at ~$0.039
per 2K image. 30 concepts ≈ $1.17. Cost gate fires before any call goes out.

## Engine behaviour notes

- Multi-ref: when `--use-template-ref` (default), product image + template image
  both go to engine. Prompt explicitly frames template as "compositional reference,
  do not clone".
- Embedded copy: Danish characters (æøå) sometimes misrender. Prefer external
  copy (overlay in Meta ad manager) when headline contains those characters.
