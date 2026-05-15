# Persillo — brand MASTER_CONTEXT

Accumulated, mutable state for the Persillo brand. Read by every flow at run-time
and updated after each round of feedback. Lives in git so learnings survive sessions.

Distinct from `brand.md`, which is the durable visual + motion DNA.

## Defaults

- `default_engine`: veo3
- `default_aspect`: 9:16
- `default_duration`: 8
- `max_cost_per_run_usd`: 2.50
- `max_cost_per_day_usd`: 25.00

## Preferred terms (Persillo dictionary)

- **Brændetid** — correct Danish spelling, not "brændtid"
- **Ren bivoks** / **100% bivoks** — never "bee wax" or English calques
- **Bomuldsvæge** — singular væge, plural væger
- **Bloklys** — large cylindrical / square candles
- **Stagelys** — slim candles for candleholders
- **Fyrfadslys** — tea-light candles

Product family proper names: Planken, Stammen, Stubben, Grenen, Roden, Koglen,
Grankoglen, Reden, Knoppen.

Colour variants: Gylden (warm honey-amber), Råhvid (cool ivory).

## Banned terms (AI-tells we have caught and refused)

- "Den dæmpede søster i kollektionen"
- "Bærer X's egen farve"
- "En rejse fra natur til ritual"
- "Hver detalje er omhyggeligt udvalgt"
- "Quiet luxury" as direct customer-facing copy (internal reference only)
- "Kuraterret", "betragtet", "considered" in customer-facing copy
- Anything claiming "håndlavet i Danmark" / "made in Denmark" — Persillo is
  Danish-designed, not Danish-manufactured. Production country TBD.

## Banned imagery (Persillo no-go list)

- People, hands, body parts
- White studio backgrounds, catalog-clean
- Plastic, chrome, glossy surfaces
- Honeycombs, honey drips, bees (source story told poetically via flora, never literally)
- Dramatic / flickering flames — only stable, quiet flame
- Generic "blurred background" without named props

## Run history learnings

(Append after each round. Date + flow + what worked / what didn't.)

### 2026-05-15 · editorial-cinematic · first Veo 3 smoke test

- Veo 3.1 + `personGeneration=allow_adult` works on Planken Gylden hero (1.6×25cm)
- 55s pipeline time, 1.0 MB mp4
- Verdict: technically works but the clip is "kedelig og dårlig video" — it
  faithfully re-renders the still photo with minimal drift. Missing: any actual
  *editorial concept* (mood, narrative, what we want the viewer to feel).
- Lesson: a render-pipeline is not a creative pipeline. Brief / storyboard /
  message layer must precede prompt-building, not be assumed from the image.
- Action: editorial flow will gain a `brief_builder` step before `prompt_builder`
  in a future commit. For now, brief is implicit and outputs reflect that.
