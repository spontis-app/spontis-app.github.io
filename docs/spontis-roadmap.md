# Spontis Overview & Roadmap

## Nå-situasjon
- **Produkt:** Statisk front-end på GitHub Pages (`index.html`, `css`, `js/app.js`) som viser en kuratert feed for Bergen med tids- og temafilter.
- **Data:** Python-scraper (`scraper/`) som henter fra 20+ kilder og leverer `data/events.json`. Sample-data (`data/events.sample.json`) finnes for lokal testing.
- **UX:** Heroen er nå lokalisert til norsk med tydelig CTA (“Se dagens høydepunkter”), mobilvennlige filterchips og detaljmodal for hvert event.
- **Dokumentasjon:** Idebank for smartfiltre og personalisering (`docs/feature-proposal-smart-filters.md`) + nye notater om vektorbasert “hukommelse” og brukerdrevet kuratering (`docs/scraper-vector-memory.md`).

## Viktigste fokusområder (før lansering)
1. **Datakvalitet/ferskhet**
   - Kjør scraper jevnlig, verifiser felter (tid, venue, tags) og vurder enkel QA-rapport (antall events/kilde, oppdateringstid).
   - Etablér fallback om scraping feiler (cache av sist kjørte feed + tydelig statusbanner).
   - Overvåk DNS-/nettfeil og flagg kilder som faller ut (reflekteres i `meta.json`).
2. **Førsteintrykk & verdi**
   - Fullfør lokalisering “over folden” (CTA, filterchips, microcopy) og vurder norsk variant av sidebar-info.
   - ✅ “Sist oppdatert”, kilde-/eventteller og “Rett rundt hjørnet” er live.
3. **Discovery-loop**
   - Definer “dagens topp 3”/helgeformat for sosiale medier og automatiser genereringen.
   - Bestem call-to-action (nyhetsbrev, delingskort, “jeg skal”-knapp) som skal testes først.
4. **Smartfiltre MVP**
   - ✅ Første chip-sett: Gratis, Familie, Live & DJ, Sen kveld.
   - Skisser lokal lagring av preferanser (fra feature-proposal) og legg roadmap for personalisering stegvis.
   - ✅ Første smartfilter-sett live: Gratis, Familie, Live & DJ, Sen kveld.

## Veivalg videre
- **Dataintelligens:** Implementer vektorbasert indeks for tagging/dedupe og OCR-flyt for plakater (fra `scraper-vector-memory.md`). Start med notebook-prototype.
- **Kildeoppdagelse & kuratering:** Pilot “foreslå arrangement”-skjema + moderatorrolle, samtidig som vi logger interaksjoner for å avgjøre hvilke kategorier som skal prioriteres i scraping. Automatiser kandidatfangst via ByVenn, VisitBergen og Proff/Brønnøysund (NACE-filter), og hold oversikt i `docs/discovery/candidates.json`.
- **Sosial funksjon:** Utforsk “møt folk før arrangementet” med opt-in grupper/chat og baseline moderering.
- **Distribusjon:** Sett opp analyser (Plausible eller lignende) for filterbruk, CTA-klikk, share cards. Bruk data for å styre sosiale loops og eventuelle push-kanaler.

## Foreslått 4-ukers sprintplan
### Uke 1
- Stabiliser eksisterende scraping (DNS fallback, logging i meta).
- Legg til tre prioriterte kilder (Kvarteret ICS, Hulen/TicketCo, Bergen Live).
- Hent venues fra ByVenn + VisitBergen og produser første `docs/discovery/candidates.json`.

### Uke 2
- Integrer Proff/Brønnøysund (NACE-koder) og “savner du et sted?”-skjema i UI.
- Bygg rapport CLI som viser hull pr. kategori/venue og foreslå prioritering.
- Start lagring av smartfilter-preferanser i LocalStorage.

### Uke 3
- Prototype vektor-notebook: embeddings, dedupe, “ligner på”.
- Test “foreslå arrangement”-skjema (kan være Google Form i første runde) + manuell QA.
- Koble kandidatregisteret mot roadmap/issue tracker (status, ansvarlig, est. lansering).
- Legg inn instrumentering for filterklikk og CTA i Plausible.

### Uke 4
- Evaluer data fra notebook + brukerinndata og bestem neste automatisering.
- Pilot “jeg skal”/sosial funksjon på utvalgte events (kan være enkel lenke til midlertidig chat).
- Gjennomgå KPI-er (trafikk, delinger, nyhetsbrev-påmeldinger) og planlegg neste iterasjon.

## Risikoer å følge med på
- **Kompleks scraping:** Instagram/kilder med anti-bot kan kreve manuell oppfølging. Ha fallback og modereringsrutine.
- **Moderering/bybruk:** Åpne bidrag og sosial funksjon maserer behov for klare retningslinjer og rapporteringskanal.
- **Ressurser:** Automatiserte loops og vektorlag krever oppfølging; prioriter hva som bygges in-house vs. manuelt i første omgang.

## Målinger som bør på plass
- Tidsstempel for siste vellykkede scraping + antall events per kilde.
- Interaksjonsrate på filterchips, CTA, share (via Plausible).
- Sosiale metrics per format (hvilke “dagens høydepunkter”-poster gir trafikk/klikk).
- Antall brukerbidrag (foreslåtte events, chat-join) og godkjenningsrate.

## Neste umiddelbare steg
1. Kjør `scripts/dev/run_stack.sh` (scraper + auto-scraper + targeted pytest) og verifiser at meta-alert/hero-chip rapporterer riktig status før publisering.
2. Publiser admin-snapshot (`docs/status/sources.html`) enten som GitHub Pages underside eller CI-artifact slik at feilede kilder er synlige i sanntid.
3. Drive discovery-pipelinen videre: fyll `docs/discovery/candidates.json` med ByVenn/VisitBergen-funn og bruk rapporten til å planlegge nye kilder.
4. Start notebook-prototype for embeddings slik at ideene i notatet kan valideres tidlig.

## AI-arbeidsflyt og loggføring
- **Codex-logg:** Alle AI-økter deles i `docs/codex_log.md` med formatet dato/agent/prompt/resultat/neste steg.
- **Automatisk post-commit:** Kjør `./scripts/setup-hooks.sh` for å lenke `scripts/git-hooks/post-commit` inn i `.git/hooks/post-commit`. Commits som starter med `codex:` skriver automatisk en blokk til loggen.
- **Manuell logging:** VS Code-snippet og task kan brukes for hurtig innfylling. Snippet ligger i `.vscode/codex.code-snippets`, tasken i `.vscode/tasks.json`, og begge kaller `scripts/dev/append_codex_log.py`.
- **Agent-rollene:** ChatGPT (planer), VS Code Codex (lokal kontekst), Codex CLI (script/CI) og Codex Web (PR/review) – se README-seksjonen “AI-arbeidsflyt” for oversikt.
- **Kildeoppdagelse:** Automatiske jobber (ByVenn, VisitBergen, Proff) skriver til `docs/discovery/` og varsler roadmapen når nye kandidater skal prioriteres.
- **UI-redesign backlog:** Dokumentert i `docs/design/ui-redesign.md` – ta opp igjen når auto-scraper og feedbalanse er stabile.
*** End Patch
