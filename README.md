# SPONTIS — What’s on. Right now.
Live: https://spontis-app.github.io/

Spontis er et inspirasjonskompass for Bergen: konserter, quiz, kino, workshops og spontant gøy – samlet på ett sted.

## Stack
Static site (GitHub Pages) · Vanilla JS/CSS · Data i `/data/events.sample.json`

## Scraper

- Kjør lokalt med `python -m scraper.run`. Output lander i `data/events.json` og følger et lite schema: `source`, `title`, `url`, valgfri `starts_at`/`ends_at` (ISO8601), `venue`, `city` (default Bergen), `tags`.
- Kilder som er aktivert som standard: Bergen Kino, Østre (via Ekko.no), USF Verftet, Bergen Kjøtt, Bergen Kunsthall/Landmark, BIT Teatergarasjen, Litteraturhuset, Kulturhuset i Bergen, Carte Blanche, Bergen Live, Nattjazz, Hordaland Kunstsenter, Aerial Bergen, Zip Collective, Festspillene i Bergen, Bergen Filharmoniske Orkester, Grieghallen og Den Nationale Scene (Resident Advisor dekker klubbkonsertene).
- Kennel Vinylbar henter “best effort” fra Instagram og er slått av som default.
- Feature-flagg (environment vars, «1» = på, «0» = av):
  - `SCRAPE_RA` — Resident Advisor
  - `SCRAPE_OSTRE` — Østre via Ekko
  - `ENABLE_USF` — USF Verftet
  - `ENABLE_BERGEN_KJOTT` — Bergen Kjøtt
  - `ENABLE_KUNSTHALL` — Bergen Kunsthall / Landmark
  - `ENABLE_BIT` — BIT Teatergarasjen
  - `ENABLE_LITTERATURHUSET` — Litteraturhuset i Bergen
  - `ENABLE_KULTURHUSET` — Kulturhuset i Bergen
  - `ENABLE_CARTE_BLANCHE` — Carte Blanche
  - `ENABLE_BERGEN_LIVE` — Bergen Live
  - `ENABLE_NATTJAZZ` — Nattjazz
  - `ENABLE_HKS` — Hordaland Kunstsenter
  - `ENABLE_AERIAL_BERGEN` — Aerial Bergen
  - `ENABLE_ZIP_COLLECTIVE` — Zip Collective
  - `ENABLE_FESTSPILLENE` — Festspillene i Bergen
  - `ENABLE_BERGEN_PHILHARMONIC` — Bergen Filharmoniske Orkester
  - `ENABLE_GRIEGHALLEN` — Grieghallen
  - `ENABLE_DNS` — Den Nationale Scene
  - `ENABLE_IG_KENNEL` — Kennel Vinylbar (default av; forvent 403 mulig)
  - `SCRAPE_RA` må være aktivert for RA, de andre fungerer uavhengig.
- Runneren deduper på (`title`, `starts_at`, `url`), logger antall per kilde og feiler ikke om én kilde skulle falle igjennom — du får alltid gyldig JSON (tom liste om det ikke finnes events).
- Offline test? Kjør `python -m scraper.run --offline --no-update-views` for å skrive sample-data lokalt uten nettverkskall.
- Genererte visninger (`today.json`, `tonight.json`, `heatmap.json`) ligger i `data/generated/` etter kjøring.
- Hurtigsjekk lokalt? Kjør `./scripts/checks.sh` for offline scraping, regenerering av visninger og (dersom tilgjengelig) pytest.

## 🤖 AI-arbeidsflyt

Spontis bruker et GPT‑5 Codex-oppsett der flere agenter samarbeider:

| Nivå | Verktøy | Bruksområde |
|------|---------|-------------|
| 💬 | ChatGPT (Web) | Planer, idéutvikling, spesifikasjoner |
| 🧠 | VS Code Codex | Lokal koding med rike prosjektdata |
| ⚙️ | Codex CLI | Automatisering, skript og CI-vennlige oppgaver |
| ☁️ | Codex Web | PR-forslag, code reviews og skyfeatures |

Alle økter loggføres i [`docs/codex_log.md`](docs/codex_log.md). Se `docs/spontis-roadmap.md` for detaljer og rutiner (automatisk post-commit-logg, VS Code-snippets m.m.).
