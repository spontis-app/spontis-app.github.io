# Spontis – Sprint 2025-10-25 → 2025-10-31

## Overordnet fokus
- Holde feeden variert gjennom nye kildevalg og bedre per-kilde kontroll i frontend.
- Forsterke distribusjonen: “Dagens høydepunkter” som daglig format + CTA mot nyhetsbrev.
- Fortsette discovery-pipelinen slik at vi kan fylle hull i “gratis”, “familie” og “sen kveld”.

## Sprintmål
1. **Balansert feed på forsiden:** Instrumentere og validere kilde-diversitet for både “Nå” og hovedfeed.
2. **Kildeutvidelse uke 43:** Aktivere minst to nye venues (Kvarteret ICS, Hulen/TicketCo) og dokumentere resten i discovery-backloggen.
3. **Distribusjon og CTA:** Klargjøre format for “dagens høydepunkter” og levere første CTA-utkast mot nyhetsbrev.

## Hovedleveranser
| Leveranse | Beskrivelse | Eierskap | Deadline |
| --- | --- | --- | --- |
| Feedbalanse-observabilitet | Logg/tall for kildefordeling etter `createBalancedFeed` + rapport i `docs/status/feed_diversity.md` | Codex | 28.10 |
| Nye kilder aktivert | Kvarteret ICS + Hulen/TicketCo i produksjon, meta oppdatert | Oscar | 30.10 |
| Discovery-backlog | Oppdatert `docs/discovery/candidates.json` m/ ByVenn & VisitBergen top 10 | Codex | 27.10 |
| “Dagens høydepunkter” format | Mal + første levering (3 events, distribusjonsløp) | Oscar | 25.10 |
| CTA-eksperiment | UI-komponent + tracker for “Få helgens anbefalinger” | Codex → Oscar review | 31.10 |

## Kjerneoppgaver
- **Frontend / data**
  - Instrumenter `js/feed.js` slik at kildeandel eksponeres til `meta` og logges.
  - `meta.json` eksponerer nå `source_distribution`, `top_source_share` og `diversity_index`; bruk tallene i daglige rapporter.
  - Legg til min/max-konfig i `meta.json` slik at justering kan gjøres uten deploy.
  - Verifiser feeden manuelt daglig; dokumenter topp 5 kilder i `docs/codex_log.md`.
- **Scraping / kilder**
  - Full run hver morgen; noter feil i `docs/status/sources.html`.
  - Hulen/TicketCo: avklar API eller fallback; skap tasks om større arbeid gjenstår.
  - Oppdater `scraper/source_registry.py` og `.env.example` for nye flagg.
- **Discovery**
  - Kjør ByVenn/VisitBergen skript (semi-manuelt om nødvendig) og populér `docs/discovery/candidates.json`.
  - Prioriter kandidater etter kategori (gratis, familie, sen kveld) og lag kort anbefaling.
- **Distribusjon**
  - Mal for “dagens høydepunkter”: Slack-post + IG-story (tekstutkast).
  - CTA: design knapp + modalkopi, planlegg Mailchimp-liste og privacy-tekst.
  - Sett opp Plausible-eventer for CTA og filterklikk (kan være TODO hvis krever konto).

## Milepæler & ritualer
- **Daglig kl 09:30:** Scrape-run + verifiser `meta.json`. Logg i `docs/codex_log.md`.
- **Daglig kl 12:00:** Publiser “dagens høydepunkter” (3 events) + sjekk feedbalansen.
- **Onsdag 29.10 standup:** Review kildeprogresjon + CTA-status (15 min async notat).
- **Fredag 31.10 demo:** Vise før/etter av feedbalanse og CTA.

## Målinger denne sprinten
- Maks andel fra én kilde ≤ 30 % i både “Nå” og hovedfeed (målt pr. dag).
- Antall aktive kilder ≥ 22 etter nye aktiveringer.
- Minst 1 CTA-klikkdag (oppfølging via midlertidig event logging).
- “Dagens høydepunkter”-post publiseres 4 av 5 dager.

## Risikoer & avklaringer
- TicketCo API kan kreve ekstra autentisering; ha fallback-plan (manuell CSV).
- CTA trenger Mailchimp-settinger og privacy-tekst; avklar med Oscar før lansering.
- Instrumentering krever at frontend logger til et nytt endepunkt eller midlertidig JSON; må ikke bryte Pages-build.

## Backlog (kan skyves)
- Instrumentering i Plausible ferdigstilles (krever konto-tilgang).
- Notebook for embeddings/vektor dedupe startes opp.
- “Jeg skal”-feature tas opp igjen når CTA eksperiment er live.
