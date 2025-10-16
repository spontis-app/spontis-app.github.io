# Standup Brief — Neste Økt (oktober 2025)

**Dato/agent:** 2025-10-16 · Codex CLI  
**Status:** Auto-scraper, meta-diagnostikk og admin-snapshot oppdatert. TicketCo/Festspillene/kino dekket av nye tester. 24+ live events etter ny scraping.

## Hva er klart
- Hero-chip viser `aktive/total` kilder + ⚠ ved feil.
- `scripts/dev/run_stack.sh` kjører scraper-run, auto-scraper og tester i ett.
- Adminside `docs/status/sources.html` kan genereres via `python -m scripts.discovery.report_admin`.
- Discovery-rapport (`scripts/discovery/report.py`) flagger `failing`/`inactive` og summerer kandidater.

## Neste fokus
1. **Publiser admin-snapshot:** Legg `docs/status/sources.html` på GitHub Pages/CI-artifact slik at feilede kilder kan overvåkes uten lokal kjøring.
2. **Discovery pipeline:** Oppdater `docs/discovery/candidates.json` med nye funn og planlegg prioriterte kilder (Kvarteret, Hulen, Bergen Live).
3. **Kino-modal finpuss:** Når aggregert kort vises, list de tre første filmene i modal for klarhet.
4. **Data QA:** Bekreft kjeding (`python -m scraper.run && python auto_scraper.py && pytest ...`) før deploy; noter avvik i `source_stats`.

## Praktisk sjekkliste
- python -m scraper.run && python auto_scraper.py && pytest tests/sources/test_scrapers.py -k 'festspillene or kino'
- python -m scripts.discovery.report_admin → åpne `docs/status/sources.html`
- Oppdater `docs/codex_log.md` etter økta.

## Spørsmål / beslutninger
- Hvor publiseres admin-snapshot (Pages vs CI artifact)?
- Hvilken rekkefølge på nye kilder etter hopper (TicketCo vs ICS)?

## Risiko
- Sandbox mangler DNS → sørg for å kjøre scraperne lokalt.
- Meta-alerten viser sample-data hvis `--offline`-kjøring ikke overskrives; kjør live scraping før commit/push.
