# Decisions

Newest entries go on top.

| Date | Decision | Why |
|---|---|---|
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
