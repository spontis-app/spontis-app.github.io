# Sprint Brief — Discovery & Source Expansion

**Tidsrom:** uke 42–45 (midten av oktober 2025)  
**Mål:** Øke kildedekningen for SPONTIS og automatisere forslag til nye arrangører, samtidig som vi holder førstepresentasjonen sterk og dataen fersk.

## Fokusområder

1. **Stabilisere scraping**
   - Logg og varsle DNS-/nettfeil i `meta.json`.
   - Legg til robuste fallbacks for Bergen Kino, Hulen, DNS m.fl.

2. **Nye kilder (fase 1)**
   - Integrere Kvarteret (ICS), Hulen (TicketCo) og Bergen Live.
   - Opprette feature-flagg + testscripts i `scraper/source_registry.py`.

3. **Automatisk kildeoppdagelse**
   - Bruk ByVenn og VisitBergen API/feeds for å hente venues → diff mot eksisterende kilder.
   - Lag kandidatregister `docs/discovery/candidates.json` med felter: `name`, `category`, `source`, `status`.

4. **Analyser & rapportering**
   - CLI-rapport (`python -m scripts.discovery.report`) som viser hull og anbefalte nye venues.
   - Plausible event logging for smartfilterbruk etter lansering.

5. **Forbered fase 2**
   - Planlegg Proff/Brønnøysund integrasjon (NACE-koder) og “savner du et sted?”-feedback i UI.
   - Noter data som trengs for embeddings-notebook (tags, venue, beskrivelse).

## Milepæler

| Uke | Milepæl | Leveranse |
|-----|---------|-----------|
| 42 | Scraper stabil | meta logger feilkilder, nye kilder aktivert |
| 43 | Discovery pipeline | Kandidatliste fra ByVenn/VisitBergen + CLI-rapport |
| 44 | Preferanselagring kickoff | API for smartfilter-localstorage + brukerfeedback-form |
| 45 | Review & next wave | Rapporterte resultater, plan for Proff/Brønnøysund og videre kilder |

## Avhengigheter

- Tilgang/API-nøkler for ByVenn, VisitBergen (bekreft format).
- TicketCo organiser-IDer for Hulen/Bergen Live (hentes manuelt først).
- Ressurstid for å validere nye kilder før produksjonssetting.

## Suksesskriterier

- Antall aktive kilder ≥ 10 innen sprintslutt.
- Mindst 5 nye kandidater i `candidates.json` med metadata.
- “Rett rundt hjørnet” viser reelle events daglig og inkluderer minst 3 unike venues.
