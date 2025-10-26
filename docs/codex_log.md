# Codex Session Log

Et delt loggarkiv for AI-assisterte arbeidsøkter i Spontis-prosjektet.

## Struktur
- **Dato:** ISO-format (`YYYY-MM-DD`)
- **Agent:** Hvilken instans (ChatGPT / VS Code Codex / Codex CLI / Codex Web)
- **Prompt:** Kort oppsummering av oppgaven
- **Resultat:** Hva ble endret, hvor, og evt. tester/commit
- **Neste steg:** Oppgaver eller ideer som bør følges opp

---

*(Første reelle logginnslag kommer her.)*

## 2025-10-25 — Codex CLI (økt 6)
- **Agent:** Codex CLI
- **Prompt:** «Vi fortsetter med spontis … se etter bugs i scraping … mange baller i luften.»
- **Resultat:** Forbedret feedbalansen (kildetak i `js/feed.js`), renset skriptere som tok med navigasjon (`scraper/sources/zip_collective.py`, `scraper/sources/festspillene.py`), opprettet discovery-kandidater (Isotop, KMD, KODE) og planla sprint 25.–31. okt.
- **Neste steg:** Verifiser ny scraping-run og logg kildefordeling, fyll `docs/discovery/candidates.json` videre (ByVenn/VisitBergen), og start instrumentering for CTA/åpningstider.
