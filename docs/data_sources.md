# Data sources and terms of use

Four public sources, downloaded by `code/01_get_data.py` on 2026-11-13 (times in UTC from `data/processed/sources.json`). Terms were looked up on 2026-11-14 from the development container; each statement names where it was read. The author should re-read the licence texts before submission: nothing here is legal advice.

## 1. SFOE electricity production plants

- Publisher: Swiss Federal Office of Energy (SFOE).
- URL used: `https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/csv/2056/ch.bfe.elektrizitaetsproduktionsanlagen.zip`
- Version: file last modified 2026-11-12 16:25 GMT, downloaded 2026-11-13 16:25; 19,480,133 bytes. sha256 in `sources.json`.
- Second file (register-lag check only): `.../elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen_2056.csv.zip`, last modified 2026-09-16 21:49 GMT, 19,195,387 bytes.
- Kept: photovoltaic plants (sub-category 2) of canton FR: plant id, EGID, start of operation, initial and total power, plant category. No address, postcode or coordinates.
- Terms: the STAC collection record gives the licence link `https://opendata.swiss/en/terms-of-use/#terms_by` ("Terms of use"), field `license: proprietary`, provider SFOE as producer and licensor (https://data.geo.admin.ch/api/stac/v0.9/collections/ch.bfe.elektrizitaetsproduktionsanlagen). The geocat.ch metadata record (https://www.geocat.ch/geonetwork/srv/api/records/e5a00bdb-5022-4856-ad4a-d1afe7bf38b0/formatters/xml) states: "Opendata BY: Open use. Must provide the source." (German: "Freie Nutzung. Quellenangabe ist Pflicht."). The opendata.swiss terms page itself returned 403 from this environment: not read, owner to check https://opendata.swiss/en/terms-of-use.
- Suggested citation: Swiss Federal Office of Energy (SFOE), "Electricity production plants" (Elektrizitaetsproduktionsanlagen), file of 2026-11-12, accessed 2026-11-13, https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/csv/2056/ch.bfe.elektrizitaetsproduktionsanlagen.zip

## 2. FSO federal register of buildings and dwellings (GWR), public level

- Publisher: Federal Statistical Office (FSO).
- URL used: `https://public.madd.bfs.admin.ch/fr.zip` (canton FR extract).
- Version: last modified 2026-11-13 05:02 GMT, downloaded 2026-11-13 16:25; 42,718,433 bytes. The register is a daily snapshot.
- Kept: all columns of the building table `gebaeude_batiment_edificio.csv` for FR buildings (`buildings_fr.parquet`), including category, status, construction year and period, dwellings, floors, footprint, coordinates and heating fields. The code list `kodes_codes_codici.csv` was used to read the codes (not committed).
- Terms: the archive contains `license.pdf` (dated 2024-08-19 in the zip listing). Its French text reads: "Utilisation libre. Obligation d'indiquer la source." with "Vous pouvez utiliser ce jeu de données à des fins non commerciales", "... à des fins commerciales", and "L'indication de la source (Office fédéral de la statistique; Registre fédéral des bâtiments et des logements) est obligatoire." It cites art. 16 of the ordinance on the federal register of buildings and dwellings (RS 431.841): the FSO publishes the data of authorisation level A on the internet. Read from `fr.zip` itself; the FSO web pages could not be used to confirm it (the pages reached are script-rendered or returned 404).
- Suggested citation: Federal Statistical Office (Bundesamt fuer Statistik); Federal Register of Buildings and Dwellings (GWR), public data, canton Fribourg, file of 2026-11-13, accessed 2026-11-13, https://public.madd.bfs.admin.ch/fr.zip

## 3. SFOE roof solar suitability (sonnendach.ch)

- Publisher: Swiss Federal Office of Energy (SFOE).
- URL used: `https://data.geo.admin.ch/ch.bfe.solarenergie-eignung-daecher/solarenergie-eignung-daecher/solarenergie-eignung-daecher_2056.gpkg.zip`
- Version: file last modified 2023-04-19 13:47 GMT (2023 release; the STAC collection itself was updated 2025-01-18), downloaded 2026-11-13 16:23; 1,510,073,383 bytes.
- Kept: attributes of the roof surfaces of FR buildings in table `SOLKAT_CH_DACH` (id, EGID, area, class, tilt, orientation, irradiation, electricity yield, dates), no geometry (`roofs_fr.parquet`, 418,606 rows). The 1.5 GB download is not committed (`data/raw/` is git-ignored).
- Terms: the STAC collection record gives the same licence link as source 1, `https://opendata.swiss/en/terms-of-use/#terms_by`, `license: proprietary` (https://data.geo.admin.ch/api/stac/v0.9/collections/ch.bfe.solarenergie-eignung-daecher). The geocat.ch metadata record (https://www.geocat.ch/geonetwork/srv/api/records/b614de5c-2f12-4355-b2c9-7aef2c363ad6/formatters/xml) states: "Opendata BY: Open use. Must provide the source." The opendata.swiss page returned 403: not read, owner to check.
- The general terms for the federal spatial data infrastructure (https://www.geo.admin.ch/en/general-terms-of-use-fsdi) say acquisition and use of data is "free of charge, subject to the provisions on fair use" and that the source must be cited "in accordance with the terms of use of the corresponding dataset".
- Suggested citation: Swiss Federal Office of Energy (SFOE), "Suitability of roofs for the use of solar energy" (Sonnendach), release of 2023-04-19, accessed 2026-11-13, https://data.geo.admin.ch/ch.bfe.solarenergie-eignung-daecher/solarenergie-eignung-daecher/solarenergie-eignung-daecher_2056.gpkg.zip

## 4. ElCom electricity tariffs, via LINDAS

- Publisher: Federal Electricity Commission (ElCom); served by the Linked Data Service LINDAS of the Swiss Federal Archives.
- URL used: SPARQL endpoint `https://lindas.admin.ch/query` (POST, `Accept: text/csv`), graph `https://lindas.admin.ch/elcom/electricityprice`, cube `https://energy.ld.admin.ch/elcom/electricityprice` ("Electricity tariff per provider and municipality in Switzerland"). The query text is in `code/01_get_data.py` and its hash in `sources.json`.
- Version: answer saved 2026-11-13 19:52 (1,880,100 bytes); category H4, standard product, years 2020 to 2025. The cube metadata shows a modification date of 2026-11-14.
- Kept: total, energy, grid usage, charge and aid fee per operator, municipality and year, reduced to canton FR municipalities (`tariffs_fr.parquet`).
- Terms: the cube's metadata (`curl -H "Accept: text/turtle" https://energy.ld.admin.ch/elcom/electricityprice`) gives `dcterms:license` and `dcterms:rights` as `https://ld.admin.ch/vocabulary/TermsOfUse/Open-Use`; that term is named "Open use" with identifier `NonCommercialAllowed-CommercialAllowed-ReferenceNotRequired` (read from https://ld.admin.ch/vocabulary/TermsOfUse/Open-Use). The opendata.swiss catalogue entries (https://opendata.swiss, https://ckan.opendata.swiss) returned 403: not read; the LINDAS "Terms and conditions" page was not opened. Owner to check both.
- Suggested citation: Federal Electricity Commission (ElCom), "Electricity tariff per provider and municipality in Switzerland", LINDAS cube electricityprice, accessed 2026-11-13, https://energy.ld.admin.ch/elcom/electricityprice
