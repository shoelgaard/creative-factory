---
name: Persillo
tagline: Editorial bivokslys-brand i nordisk lavmælt stil
positioning: Frama møder Kinfolk møder Aesop — det danske premium-bivokslys for Audo/Frama/&Tradition-køberen
---

# Persillo — brand DNA for video-prompt-bygning

Denne fil er kilden til ALT visuelt sprog i Persillo-ads. Læses af `prompt_builder.py` og blandes ind i hver engine-prompt.

## Historien i én linje

**Fra dansk natur, ved hånd, ind i dit mest intime øjeblik.**

## Visuel grammatik (must-haves)

- **Genre:** editorial stilleben, lavmælt nordisk lys, magasin-kvalitet
- **Base-materialer:** travertin, rå eg, lin (utvunget), keramik (mat, off-white/sand), børstet messing
- **Bagvæg:** warm muted-grey limewashed plaster, subtil pensel-mottling — ALDRIG ren hvid eller katalog-clean
- **Lys:** naturligt sidelys fra venstre, blødt og varmt (~4000K), bløde skygger med form
- **Stemning:** quiet luxury, stille, intim, langsom — som morgenlys gennem et nordvendt vindue
- **Dansk flora:** lavendel, hvede, valmue, kornblomst, kamille, røllike, hyld, hyben, tidsel, lyng (tørret eller frisk)
- **Komposition:** plads til luft, asymmetri foretrukken, ikke center-symmetri (undtaget hero)

## Forbudt (no-go)

- **Ingen mennesker, hænder eller kropsdele.** Aldrig.
- **Ingen hvide studio-bagvægge**, kataloglook eller e-comm clean
- **Ingen plastik, krom, glansoverflader** eller "stylet til Instagram"-pyntegenstande
- **Ingen bier, honningtavler, honningdråber** (kilde-historien leveres POETISK via flora, ikke literalt)
- **Ingen blæsende/flakkende flamme** — stabil, rolig, stille
- **Ingen "blurred background"** alene — kræver konkrete, navngivne props (bøger, keramik, lin, messing)
- **Ingen West Elm / Amazon / katalog-styling**
- **Ingen film-grain, painterly, watercolor** — vi er realistisk editorial-fotografi, ikke kunstnerisk fortolkning

## Produkt-proportioner (KRITISK for Gemini/Veo)

Gemini gør ALTID Persillo-kerter for tykke/korte. Overkorriger altid i prompten.

| Produkt | Mål | Beskrivelse |
|---|---|---|
| Planken | 1,6 × 1,6 × 25 cm (firkantet) | Pencil-thin, 15.6:1 ratio — "tyndere end du tror" |
| Stammen | 6 × 20 cm (cylinder) | Solid pillar |
| Stubben | 6 × 10 cm (cylinder) | Kort pillar |
| Grenen | 2,2 × 25 cm (cylinder) | Slank stagelys |
| Roden | 2,2 × 30 cm (snoet) | Snoet stagelys |
| Koglen | 6 × 15 cm (kegle) | |
| Grankoglen | 7 × 30 cm (kegle) | |
| Reden | 7,5 × 9 cm (lys i glas) | |

Skriv eksakte dimensioner i parentes efter produktbeskrivelsen i hver prompt. Tilføj sammenligninger: "barely wider than a pencil", "chopstick-thin", "razor-thin".

## Flamme

Stabil, rolig, ca. 2-3× bredden af kerten. Aldrig dramatisk eller flakkende. Den skal ånde, ikke performe.

## Bevægelses-grammatik (video-specifik — Veo/Seedance)

Persillo-ads er IKKE action-clips. De er *kontemplative tableau-er* — som magasinopslag der lige har lært at trække vejret.

**Tilladt bevægelse (i prioriteret rækkefølge):**
1. Flammen flakker stille og naturligt (subtle wick burn)
2. Kameraet drift'er meget langsomt — slow push-in eller subtle parallax (~5-10% over 8s)
3. Lyset skifter mærkbart — solstråle bevæger sig en smule, eller skygger blødgøres
4. Et enkelt natur-element bevæger sig næsten umærkeligt (røg, en hvedestilks svaj, et lindens blad)

**Forbudt bevægelse:**
- Hurtige whip-pans, zooms, cuts
- Roterende kamera rundt om produkt
- Snap-zooms eller dramatiske framing-shifts
- Slow-motion vand/splash-effekter
- Letterbox-pillow-fall (forfine partikler der lander overdrevent cinematisk)
- "Reveal"-bevægelser (produkt åbenbarer sig fra skjul)

**Lyd (Veo native audio):**
- Subtil ambient room-tone — vinduestone, fjern naturlig stilhed
- Måske en svag brænd-knitren fra vægen (hvis tændt)
- INGEN musik, INGEN voiceover, INGEN sound-design pop
- Stilhedens egen kvalitet er pointen

## Style-anchors (referencer Veo/Seedance forstår)

Brug i én sætning per prompt, ikke som sektion:
> Kinfolk magazine spread, Frama product story, Aesop botanical apothecary aesthetic. 85mm portrait, editorial photography realism, natural color rendering.

## Prompt-skrivnings-principper (lærdom fra image-pipeline)

1. **Positiv framing, aldrig negativ.** "Smooth intact matte surface" ikke "no drips". Modellen rendrer det den ser, også negationer.
2. **Narrativt flow, ikke list-sektioner.** Skriv som magasin-billedtekst, ikke spec-sheet.
3. **Realisme-ord:** "editorial photography realism", "high-resolution detail", "natural color rendering".
4. **Specifikt lys, ikke generisk:** "soft directional Nordic daylight from the left, ~4000K, casting gentle long shadows" ikke "warm light".
5. **Konkrete props med navn** — ikke "books and ceramics" men "a stack of three linen-bound poetry books, a matte sand-coloured ceramic cup, a small dried lavender sprig".

## Copy-voice (hvis vi engang tilføjer captions)

Ærlige, konkrete, mundrette danske sætninger. Beskriv hvad lyset GØR, ikke hvad det "repræsenterer". Undgå AI-tells: "kuraterret", "betragtet", "considered", "den dæmpede søster", "en rejse fra natur til ritual".

## Hårde fakta — må aldrig fejl-citeres

- Persillo-lysene er **IKKE håndlavet i Danmark**. Produktionsland TBD. Skriv aldrig "dansk håndværk", "håndlavet i Danmark", "made in Denmark" i copy eller alt-tekst.
- Dansk æstetik ≠ dansk fabrikation. Hold det adskilt.
