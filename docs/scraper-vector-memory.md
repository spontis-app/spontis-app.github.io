# Scraper Note: Vector Database Memory

Idee: Suppler dagens regelbaserte scraping med et vektorlag som kan lære og utvikle seg over tid.

- **Semantisk indeks:** Lag embeddings av tittel, beskrivelse, venue og tags for hvert event og legg dem i et vektorbasert lager (f.eks. LanceDB, Weaviate, Pinecone). Dette gir rikere matching enn dagens regex-baserte tagging.
- **Dynamisk læring:** Når nye kilder eller formater dukker opp, sammenlign mot eksisterende vektorer. Lav likhet ⇒ flagg som potensiell ny kategori/kilde, høy likhet ⇒ dedupe eller gjenbruk eksisterende metadata.
- **Redaktør-feedback:** Lagre justeringer (avviste/aksepterte events, redigerte tags) som treningssignaler. Oppdater embeddings-periodisk slik at modellen inkorporerer lokal domain-knowledge uten kodeendringer.
- **Hybrid pipeline:** Behold deterministiske steg (schema, tid/venue-cleanup), men bruk vektorlaget for fuzzy tagging, “lignende arrangementer”, og prioritering i feeden.

Neste steg kan være å prototypere en notebook som:
1. Eksporter sample-eventdata til embeddings.
2. Kjører enkel nearest-neighbour-søk for dedupe og “ligner på”-forslag.
3. Logger hvilke felt som mangler og lar oss teste manuell feedback-loop.

## Tilleggsidé: “Møt folk før arrangementet”

- **Formål:** La brukere finne andre som skal på samme event, avtale felles oppmøte eller bare bryte isen digitalt. Særlig nyttig for folk som vil dra alene.
- **Tilnærming:** Når eventdataen berikes med stabile ID-er, kan vi tilby en frivillig “jeg skal”-knapp som åpner for chat/gruppe (f.eks. via tidsbegrenset link til Signal/Discord). Vektor-konteksten kan brukes til å foreslå relevante icebreaker-spørsmål eller matche med folk med overlappende preferanser.
- **Moderering & sikkerhet:** Krever en lettvekts identitetsmekanisme (epost + engangskode) og klare retningslinjer. Logging/flagging av uønsket oppførsel bør planlegges før lansering.
- **Pilot:** Start med håndplukkede events/arrangører som er komfortable med sosial funksjon, og mål interessen via påmeldingsrate og kvalitative tilbakemeldinger før bred utrulling.

## Tilleggsidé: Brukerne som kuratorer/admin

- **Visjon:** La aktive brukere registrere og moderere arrangementer, slik at SPONTIS kan skalere raskere enn crawleren klarer alene.
- **Flyt:** “Foreslå arrangement”-knapp i UI ⇒ skjema med strukturert input (tittel, tid, venue, lenke, tags). Forslag går via lettvekts reviewing (rotasjon blant superbrukere) før publisering.
- **Roller og tillit:** Start med inviterte “local editors” (arrangører, kulturfrivillige). Bygg reputasjonssystem over tid – godkjente bidrag øker tillit, mens feilkilder flagges.
- **Verktøy:** Kombiner formdata med vektorindeksen for å fange duplikater og foreslå tags automatisk. Logging + revisjonshistorikk trengs for å rulle tilbake troll/misbruk.
- **Automatisering:** Når kvaliteten holder jevnt nivå, kan godkjente kuratorer få “auto-publish” for egne venues – bærekraftig pipeline med minimal kjerne-moderering.

## Tilleggsidé: Fra plakat til feed

- **Visjon:** Fang opp analoge plakater/flyers ved at brukere tar et bilde, og la SPONTIS konvertere det til strukturert arrangement automatisk.
- **Teknikk:** Bruk mobilopplasting → kjør OCR (f.eks. Tesseract, Google Vision) + multimodale embeddings. Vektorbasen kan kartlegge tekstblokker mot eksisterende events, foreslå labels og sjekke om arrangementet er nytt.
- **Kvalitetssikring:** Automatiske feltforslag (tid, venue) valideres av innsender eller en moderator før publisering. Bilder kan også brukes som cover i feeden.
- **Læring:** Hvert godkjente bilde bygger en treningsbank av “plakat → struktur”-par, som senere kan drive finjustering av modellen.

## Tilleggsidé: Brukerinteresse styrer scraping

- **Hypotese:** Ved å logge hvilke events/temaer brukere følger, kan vi prioritere nye kilder der interessen er høy.
- **Flyt:** Når mange brukere flagger interesse for f.eks. “friluftsliv”, lager vi en scraping-oppgave backlog for relevante venues/platformer. Vektorinnsikt + interaksjonsdata gir en “utforskning”-score per kategori.
- **Eksperiment:** Bygg en “hvilke events savner du?”-survey i UI, logg svar, og la en automatisk crawler-generator foreslå nye URL-er fra tipset. Testrunder kan bekrefte hvilke kategorier som bør automatiseres først.
