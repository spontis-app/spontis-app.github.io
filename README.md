# SPONTIS — What’s on. Right now.
Live: https://spontis-app.github.io/

Spontis er et inspirasjonskompass for Bergen: konserter, quiz, kino, workshops og spontant gøy – samlet på ett sted.

## Stack
Static site (GitHub Pages) · Vanilla JS/CSS · Data i `/data/events.sample.json`

Frontend kjører helt uten rammeverk og er optimalisert for mobil/dark-mode først. Filterne er delt i tidsfokus vs. «vibe» og
viser tydelig kilde-attribusjon per kort og i sidepanelet.

## Scraper

- Kjør lokalt med `python -m scraper.run` (bruk `--help` for flere flagg). Output lander i `data/events.json` og følger et
  validert schema: `source`, `title`, `url`, valgfri `starts_at`/`ends_at` (ISO 8601), `venue`, `city` (default Bergen), `tags`,
  `when`, `where` og `sources`.
- Alle event-data normaliseres til `Europe/Oslo`, får menneskevennlig `when`/`where`, schema-valideres og events som er mer
  enn noen timer gamle filtreres bort.
- Kilder som er aktivert som standard: Bergen Kino, Østre (via Ekko.no), USF Verftet, Bergen Kjøtt, Bergen Kunsthall/Landmark og Resident Advisor Bergen.
- Kennel Vinylbar henter “best effort” fra Instagram og er slått av som default.
- Feature-flagg (environment vars, «1» = på, «0» = av):
  - `SCRAPE_RA` — Resident Advisor
  - `SCRAPE_OSTRE` — Østre via Ekko
  - `ENABLE_USF` — USF Verftet
  - `ENABLE_BERGEN_KJOTT` — Bergen Kjøtt
  - `ENABLE_KUNSTHALL` — Bergen Kunsthall / Landmark
  - `ENABLE_IG_KENNEL` — Kennel Vinylbar (default av; forvent 403 mulig)
  - `SCRAPE_RA` må være aktivert for RA, de andre fungerer uavhengig.
- Runneren deduper på (`title`, `starts_at`, `url`), logger strukturert per kilde og feiler ikke om én kilde skulle falle igjennom —
  du får alltid gyldig JSON (tom liste om det ikke finnes events).
- Etter scraping bør du kjøre `python scripts/build_views.py` for å generere `today.json`, `tonight.json` og `heatmap.json`.
