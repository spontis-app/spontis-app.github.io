# Discovery Candidates

Dette kataloget brukes til automatiske og manuelle lister over potensielle nye kilder/venues.

- `candidates.json` inneholder objekter med feltene `name`, `category`, `source` (byvenn/visitbergen/proff/manual), `status` (`new`, `review`, `active`), `confidence` (0-1), og eventuelle notater.
- Skript i `scripts/discovery/` skal opprette/oppdatere filene.
- Oppdater roadmapen når kandidater går fra `review` til `active`.
- Oversikt? Kjør `python scripts/discovery/report.py` (legg til `--json` for maskinvennlig output) for å få en rask status over feeden, feilede kilder (`failing`) og kandidatlisten.
