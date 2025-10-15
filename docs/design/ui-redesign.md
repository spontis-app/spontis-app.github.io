# UI Redesign Concept — “Nå i Bergen”

*Status:* Backlog (etter auto-scraper + feed-balansesprinten)

## Referanse
- Minimalistisk mørk modul med hero-tittel “Nå i Bergen”, fokus på tidspunkt (kl. 18–23) og hurtigfiltre (“I kveld”, “I morgen”, “Helgen”).
- Kortene bruker store bilder, tydelige titler, undertekst med tid + kategori + kilde.
- Designskissen (lagret i Notion / referansebildet delt 15.10) bør brukes som stemningsbrett når vi tar fatt på redesignet.

## Når vi tar den
1. Etter at auto-scraper og feed-balansesystemet er stabilt (est. uke 3–4).
2. Sammenfallende med dashboard-/statsarbeid slik at UI kan bruke ferske balanse-mål.
3. Vurder å migrere `js/app.js`-rendering til modulstruktur (f.eks. `js/feed.js`, `js/layout.js`) før vi gjør store UI-endringer.

## TODO når sprinten startes
- Lage oppdatert komponentbibliotek (kort, filterchips, hero-seksjon).
- Implementere mørk/lys-tema (prefers-color-scheme).
- Sammenstille bildeassets (landskap/portrett) og reintroduksjon av auto-genererte cover der originalen mangler.
