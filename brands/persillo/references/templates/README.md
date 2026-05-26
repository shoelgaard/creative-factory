# Persillo templates

Static-ad templates you download manually from competitors / inspiration.
The statics-flow uses these as visual references when generating new ads
with your product + USP.

## Folder convention

```
templates/
├── <brand>__<days>d__<short-desc>.png       — full screenshot from Meta Ad Library
└── <brand>__<days>d__<short-desc>__crop.png — auto-generated, just the ad creative
```

- `<brand>` lowercase, no spaces (aesop, frama, byredo, lelabo, audo, otherland, diptyque, trudon, tekla, broste, ...)
- `<days>` zero-padded to 4 digits (e.g. `0379d`) — days the ad has been running per Ad Library timestamp. Longest-running ads = best performers.
- `<short-desc>` hyphenated lowercase, describes the visual (`bal-dafrique-red-velvet`, `chair-01-wooden-staggered`).

`ls` sorts oldest-active ads to bottom because of zero-padding — top of the list is the worst performers, bottom is the proven winners.

## Auto-crop

After dropping new screenshots in this folder, run:

```bash
python3 tools/crop_meta_ad.py brands/persillo/references/templates/
```

This generates `<name>__crop.png` next to each `<name>.png`, with the Meta UI
(Active badge, library ID, ad copy, Shop Now button, thumbnails) removed.
Statics-flow only ingests `__crop.png` versions.

## template.md (optional, but useful for bulk runs)

```markdown
---
source: https://www.facebook.com/ads/library/?id=...
brand: Aesop
captured: 2026-05-15
---

# Aesop hand balm typography

What works:
- Single product on linen, small typography in upper-left corner
- Off-white background, soft directional light
- Headline is 4 words max — very large, very thin

Best for: hero-style ads where the product image is the entire visual.
Pair with USPs that are short and quotable.
```

Legal: you collect these manually for inspiration. The platform does not
scrape ad libraries automatically.
