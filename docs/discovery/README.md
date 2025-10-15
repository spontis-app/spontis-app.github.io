# Discovery Candidates

Dette kataloget brukes til automatiske og manuelle lister over potensielle nye kilder/venues.

- `candidates.json` (kommer) inneholder objekter med feltene `name`, `category`, `source` (byvenn/visitbergen/proff/manual), `status` (`new`, `review`, `active`), `confidence` (0-1), og eventuelle notater.
- Skript i `scripts/discovery/` skal opprette/oppdatere filene.
- Oppdater roadmapen når kandidater går fra `review` til `active`.
