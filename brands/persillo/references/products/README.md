# Persillo products

One folder per product variant. Flows read from here so you don't repeat
product info on every run.

## Folder convention

```
products/
└── <slug>/
    ├── product.md       — name, dimensions, claims, links (the canonical card)
    ├── hero.jpg         — primary product photo for static-ad generation
    ├── variants/        — optional extra angles
    └── refs/            — optional reference photos (lifestyle, packaging, etc.)
```

`<slug>` is short, lowercase, hyphenated. Examples: `stubben-gylden`, `planken-raahvid`.

## product.md template

```markdown
---
name: Stubben Gylden
slug: stubben-gylden
family: Stubben
colour: Gylden
dimensions_cm: 6 × 10
burn_time_hours: 35
material: 100% ren bivoks
wick: bomuldsvæge
price_dkk: 149
url: https://persillo.dk/products/stubben-gylden
---

# Stubben Gylden

(Short factual block — bullet what is true. No marketing language.)
- Solid cylinder, 6 cm diameter, 10 cm height
- Honey-amber colour from the natural beeswax
- ~35 hours burn time
- Made from 100% pure beeswax (production country not Denmark)

## Product photos

- hero.jpg — primary listing photo
- variants/*.jpg — additional angles
```

Flows that need a product call something like:
`brand_loader.load_product("persillo", "stubben-gylden")` and get the
frontmatter + image paths back.
