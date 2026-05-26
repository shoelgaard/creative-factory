# Persillo — active statics

Ads currently running on Meta, organised by ISO week.

```
active/
└── uge <NN> - <YYYY>/
    └── <files>.jpg
```

Convention: ISO week number + 4-digit year (e.g. `uge 22 - 2026`). Hver uge får
sin egen mappe. Du flytter en static-ad fra `promoted/statics/` til den uges
mappe når den faktisk er uploadet til Meta og kører.

Når ugen er slut, mappen bliver historisk — flyt videre til neste ugemappe
("uge 23 - 2026"), og lad den forrige stå som arkiv over hvad der kørte.

Når en ad bliver bekræftet vinder fra Meta-data (CTR, CPM, etc.), kopier den
til `brands/persillo/winners/statics/` — det er der vores bevarede vindere
ligger til reference og genbrug.
