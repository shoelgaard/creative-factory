# Veo 3 prompt template

The `prompt_builder.py` fuses three layers in this order:

1. **Brand body** (from `brands/<slug>/brand.md`) — visual grammar, no-gos,
   motion grammar, style anchors. Same per brand, same per run.
2. **Product hint** — derived from the filename (`planken_gylden_hero.jpg` →
   "Persillo Planken Gylden beeswax taper candle, 1.6×25 cm, pencil-thin,
   warm honey-amber"). The image itself does the heavy lifting; the hint just
   keeps the language anchored.
3. **User steer** — optional `--prompt "..."` flag, blended in as
   "Additional steer: ...".

Output target: 8-second cinematic image-to-video, 9:16, native ambient audio,
~5-10% camera drift over the duration, stable quiet flame, no people.

If a generation comes back wrong (too dramatic motion, wrong proportions,
plastic-feeling materials), don't tweak the user-steer — update brand.md so the
fix compounds across all future runs.
