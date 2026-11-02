# GPT vs Claude – Udbytteduellen

## Installation
Upload alle filerne til roden af GitHub-repositoriet `ai-konkurrence` og `.github/workflows/update.yml` til samme mappe i GitHub. **Slet eller deaktiver andre eksisterende workflows**, der også opdaterer `data.json`, så der kun er én automatisk opdatering. GitHub Pages skal publicere `main` / root.

## Ny handel
Redigér `data.json`: Tilføj en post i `holdings` med `name`, `ticker`, `qty`, `costBaseDKK`, `sector`, `currentVal` og `returnPct`. Hvis samme aktie allerede findes, lægges antallet og købsbeløbet til den eksisterende position. Tilføj samtidig en række i `trades` med `date`, `type`, `asset`, `amount`, `qty`, gerne også `filledAt`, `priceUSD` og `fxFeeDKK`. Opdater `investedTotal` **kun ved nye indbetalinger**, ikke ved geninvestering af udbytte. Nye kontanter tilføjes i `cashDKK`, hvis de ikke straks investeres. Brug præcise brøkantal fra Trading 212.

## Ny samtale
Åbn `conversations.json`, og tilføj `{ "date": "3. nov. 2026", "text": "Samtalens tekst" }` under `gpt` eller `claude`. Hjemmesiden viser det automatisk i Logbog. **Månedens Valg** opdateres nu i `choices.json` (se næste afsnit). Om duellen er fortsat statisk HTML.

## Opdatering
GitHub Actions kører højst hvert femte minut på hverdage i et UTC-vindue, der dækker amerikansk normalhandel året rundt. Python bruger NYSE-handelskalenderen til at springe lukkede perioder og helligdage over. Kurser fra Yahoo Finance og USD/DKK fra open.er-api.com kræver ingen API-nøgle, men er **ikke Trading 212's egne kurser** og kan være forsinkede eller afvige lidt. Workflowet kan også forsinkes af GitHub. Åbningstimeren i browseren er vejledende og tager ikke højde for helligdage.

## Vigtigt
Købsbeløb i Trading 212 inkluderer FX-gebyr. Træk ikke gebyret fra igen. Beregnet porteføljeværdi er indikativ, ikke garanteret identisk med Trading 212. Ved fejl i kurskilderne bevares seneste `data.json`. Kontroller Actions-loggen efter første kørsel.

## Ny måneds valg – uden HTML-redigering
Åbn `choices.json`, kopiér det seneste objekt inde i `months`, og ret `id` (f.eks. `2026-12`), `label`, `title` og begge AI’ers `date` og `html`. Feltet `html` indeholder den eksisterende formaterede tekst og eventuelle tabeller fra måned 1; kopier den som skabelon, eller brug almindelig tekst med `<p>...</p>`. JSON kræver dobbelte anførselstegn omkring felter og korrekt escaping af indvendige citationstegn. Månedvælgeren og begge kolonner opdateres automatisk. Tilføj kun indhold, du selv stoler på, da `html` vises som HTML.

**Filer, der ændres løbende:** `data.json` til handler, `conversations.json` til logbog, `choices.json` til månedens valg. `index.html` skal ikke ændres ved normal opdatering.
