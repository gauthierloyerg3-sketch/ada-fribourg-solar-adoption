# Decisions

Newest entries go on top.

| Date | Decision | Why |
|---|---|---|
| 2026-11-13 | Verified: next-year tariffs are in the ElCom cube before the year starts (2027 is present on 2026-11-13), so the T+1 price is known at T. The model feature will be the deviation from the canton median of the year, not the level. | The level moves from a median of 21.2 Rp/kWh (2022) to 32.4 (2024); a model fitted on the 2022 level would extrapolate on the test. |
| 2026-11-13 | Tariffs are fetched for all Swiss municipalities (H4, standard, 2020 to 2025) and filtered afterwards to the `ggdenr` of buildings_fr; municipalities with two operators get the mean of each price and `n_operators`. | Simpler and more reliable than a canton filter in SPARQL; matches the task. Unit (Rp/kWh) is inferred, not stated in the answer. |
| 2026-11-13 | Stage 01 takes source names (`plants`, `buildings`, `roofs`, `plants_2026_09`); default runs all four. A partial run updates only its own entries in `sources.json`. | Registers change daily; a single-source run must not move the other extracts. |
| 2026-11-13 | Register-lag table counts first installations on population buildings (first PV date per building, in each file separately); a building first dated in one file and not the other counts only where it appears. | Same definition as the labels, so the table speaks to the label undercount. |
| 2026-11-13 | No more phase gates: sessions go from task to task and stop only before a major decision. The main session runs on the top model tier to check all subagent work. | Gauthier's instruction after Phase 3. |
| 2026-11-13 | Bootstrap intervals resample whole municipalities, not single buildings. | Neighbours' outcomes are correlated; this is the more conservative choice. Approved with TASKS.md. |
| 2026-11-13 | Baseline 2 uses the 250 m neighbour radius, fixed before any result. | So that the radius is not picked on the test. Approved with TASKS.md. |
| 2026-11-13 | The tariff known at cut-off T is the price of year T+1 (2022 for train, 2024 for test). | ElCom publishes next-year tariffs in late summer (to be verified in T02). Approved with TASKS.md. |
| 2026-11-13 | AI sessions merge their own PRs into main once CI is green (code PRs also need reviewer PASS). Phase gates and scope or method choices still wait for Gauthier. | Gauthier's instruction after PR 1: removes a manual step. He reviews after the fact. |
| 2026-11-13 | Baseline 1 stays as declared (rank by total roof yield on class 3+ surfaces), although it scores below random. No search for a better-looking variant. | It was fixed before seeing results. The inverted-U shape (adoption about 5% in the lowest and the two highest yield deciles, about 9% in between) is a result to report, and it means the LASSO needs a non-linear yield term. |
| 2026-11-13 | Notebooks are committed with outputs cleared during development; one executed version is committed before submission. | Clean diffs while developing; CI proves they run top to bottom, and the executed copy shows the results to the marker. |
| 2026-11-13 | `pv_fr.parquet` carries no address, postcode or coordinates. | They are not needed: plants are linked to buildings by EGID. |
| 2026-11-13 | `data/processed/sources.json` records URL, size, SHA-256, HTTP Last-Modified and download time of each raw file. | The registers change daily; this fixes which version produced the extracts. |
| 2026-11-13 | Roof columns kept in `roofs_fr.parquet`: objectid, df_uid, egid, flaeche, klasse, neigung, ausrichtung, mstrahlung, gstrahlung, stromertrag, datum_erstellung, datum_aenderung. Names are the file's, lower-cased; `GWR_EGID` becomes `egid`. | The real file has upper-case names (`GWR_EGID`, `FLAECHE`, `KLASSE`, `GSTRAHLUNG`, `STROMERTRAG`); the geometry is not needed. Summer/winter yield, heat and boiler columns are left out to keep the file small. |
| 2026-11-13 | Roofs are kept for every building of the register (not only the population). | Stage 01 does not know the population yet; the file is 18 MB. |
| 2026-11-13 | Plants with a missing start date or EGID are ignored by `first_pv_date` (210 plants lack an EGID, none lack a date). | They cannot be dated or linked to a building. |
| 2026-11-13 | Buildings with roof records but no surface of class 3 or better get `suitable_area_m2` = 0 and `yield_kwh` = 0; buildings with no roof record get missing values. | The pool drops both, but the two cases are reported separately. |
| 2026-11-13 | The roof file is the 2023 release (surfaces built in October 2022). Buildings built after that have no roof record and fall out of the pool. | It is the only release available; new builds are excluded anyway, but some older buildings may also lack a record. |
| 2026-11-13 | `capture_at_k` was added during setup. | CI needs one real test, and every later stage uses this metric. |
| 2026-11-13 | requirements.txt uses lower bounds for now; pin exact versions after the Nuvolos Python version is known. | The Nuvolos Python version is not verified yet. |
| 2026-11-13 | No `.env.example`. | The project uses no secrets. |
| 2026-11-13 | scikit-learn for all models including the neural net; `sqlite3` to read the roof GeoPackage. | Small CPU-only dependencies for Nuvolos, no GDAL. |
| 2026-11-13 | New builds are excluded with GBAUJ >= 2020, or GBAUP 8023 when GBAUJ is missing. | Exact construction year is filled for only 37% of residential buildings. |
| 2026-11-13 | Paper source lives in paper/ and Gauthier writes it. | The text is his; AI only wires in figures and tables. |
| 2026-11-13 | The "explain every line" rule is dropped; Gauthier defends choices and numbers. PR notes are at most 8 lines with technical keywords. | Gauthier's instruction; long walkthroughs cost context. |
| 2026-11-13 | Tasks run in sequence, drafted by AI sessions; no parallel agents. | The pipeline is a chain and the course wants one file per stage. |
| 2026-11-13 | `.claude/` and the CI workflow are committed and declared in the paper appendix. | Project configuration, not editor settings; to be confirmed with the TA. |
| 2026-11-13 | Building-level extracts are committed in data/processed/; the aggregation rule applies to paper outputs. | Open federal data, and a fresh clone reproduces without the 1.5 GB download. Gauthier's choice. |
| 2026-11-13 | Tariffs stay as a feature and are reported as not identified. | For 2024, 106 of 119 municipalities share one operator and one price. |
| 2026-11-13 | Heating variables are out of the main model; a separate, labelled sensitivity run adds them. | Blanking heating by date leaks: PV adoption 2022-23 was 19.2% when the heating record was dated 2022-23, against 6.5% when dated 2021 or earlier. |
| 2026-11-13 | Headline test window stays 2024-2025; add a 2024-only robustness row and compare the September and November 2026 register files. | The register lags (Fribourg PV starts: 3,719 in 2024, 2,063 in 2025). |
| 2026-11-13 | Population is residential buildings only (GWR GKAT 1020, 1030, 1040, status existing). | They hold 95% of first installations in 2022-23 (6,062 of 6,387); the 80,429 non-residential and special buildings are mostly sheds with almost no attributes filled. |
