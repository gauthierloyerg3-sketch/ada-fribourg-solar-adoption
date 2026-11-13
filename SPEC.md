# SPEC: PV adoption in Fribourg residential buildings (v1)

Status: draft for approval, 2026-11-13. Built from the CLAUDE.md draft and the kickoff interview.
`docs/proposal.md` is not in the repo yet, so this spec has not been checked against the approved proposal.

## Goal
Rank Fribourg residential buildings by their probability of a first photovoltaic (PV) installation within two years, using public data only, and report which building traits carry the ranking. Evaluation is out-of-time.

## Users
- **Marker** (professor, TA): fresh clone in Nuvolos, follows the README, regenerates every figure and table of the paper.
- **Gauthier**: author; writes the paper; defends the choices and the numbers in the recording.
- **AI sessions**: draft code, one small PR at a time, each with a note of at most 8 lines (what, why, key numbers, technical keywords). Detail on request only.

## Definitions
- **Population**: buildings in the federal building register (GWR), canton FR, status existing (`GSTAT` 1004), category residential (`GKAT` 1020, 1030, 1040). 76,171 buildings.
- **Pool at cut-off T**: population, minus buildings with a PV start date <= T, minus new builds (`GBAUJ` >= 2020, or `GBAUP` 8023 with `GBAUJ` missing), minus buildings with under 20 m2 of suitable roof (class >= 3).
- **Label**: y = 1 if the building's first PV start date falls in the two years after T.
- **Train**: T = 2021-12-31, label window 2022-2023. **Test**: T = 2023-12-31, label window 2024-2025.
- **Robustness label**: same test pool and ranking, scored on 2024 only (2025 is not fully registered yet).

## v1 features (in build order)
1. Fribourg extracts of the four sources, committed as Parquet.
2. Building table with roof aggregates, neighbour PV share (100 m, 250 m, installations <= T only), tariff, and labels for both cut-offs.
3. Two baselines: rank by roof electricity yield; rank by neighbour PV share.
4. L1-penalised logistic regression (class weights; penalty chosen by cross-validation grouped by municipality).
5. Small neural network (scikit-learn MLP): do interactions add anything?
6. Gaussian process on LASSO residuals averaged per grid cell: leftover spatial structure?
7. PCA + k-means: building segments, descriptive only.
8. Heating sensitivity run: main model plus heating variables, reported as an upper bound contaminated by leakage.
9. Register-lag check: compare the September and November 2026 plant files.
10. Figures and tables for the paper; `paper/` holds the SIAM LaTeX source, written by Gauthier.

Metrics on the test pool: share of adopters captured in the top 5% and 10% of the ranking (versus random and both baselines), ROC AUC, average precision, with bootstrap intervals. A model that does not beat the baselines is a valid result.

Cut order if late: neural net, then k-means. Never the baselines or the out-of-time test.

## Out of scope
Non-residential buildings; other cantons; causal claims; predicting system size; socio-economic data; heating variables in the headline model; grid searches; GPU; AI-drafted paper text; per-building results in the paper (paper outputs are aggregated).

## Stack
| Choice | Why |
|---|---|
| Python, pandas, pyarrow | Course standard; Parquet keeps extracts small and typed |
| `sqlite3` (standard library) to read the roof GeoPackage | A GeoPackage is a SQLite file and the join is on EGID, so no GDAL install is needed in Nuvolos |
| scipy `cKDTree` | Neighbour counts for ~76k points in seconds |
| scikit-learn for all models, including the MLP | One small CPU-only dependency; PyTorch only if the course requires it |
| matplotlib grid maps | Aggregated maps without a boundary dataset or geopandas |
| pytest, ruff, `nbconvert --execute`, GitHub Actions | Tests for `helpers.py`, lint, and a fresh-kernel run of notebooks 02-05 on every PR |

## Data model
Raw downloads go to `data/raw/` (git-ignored). Everything below is committed in `data/processed/`.

| File | One row per | Key | Written by |
|---|---|---|---|
| `pv_fr.parquet` | PV plant in FR | `xtf_id`, `egid` | 01 |
| `buildings_fr.parquet` | GWR building in FR | `egid` | 01 |
| `roofs_fr.parquet` | roof surface in FR, attributes only | `egid` | 01 |
| `tariffs_fr.parquet` | municipality x year (profile H4) | `bfs_nr`, `year` | 01 |
| `buildings_clean.parquet` | population building, with roof aggregates | `egid` | 02 |
| `model_table.parquet` | pool building x cut-off: features, `y`, `y_2024` | `egid`, `cutoff` | 03 |
| `predictions.parquet` | pool building x model: score | `egid`, `cutoff`, `model` | 04 |

## Interfaces
- Stages: `code/01_get_data.py` -> `02_clean.ipynb` -> `03_features.ipynb` -> `04_model.ipynb` -> `05_figures.ipynb`. Each reads only what the previous stage saved. Only 01 touches the network.
- `code/helpers.py`: `build_pool(buildings, pv, cutoff)`, `make_label(pool, pv, start, end)`, `neighbour_pv_share(xy, has_pv, radius)`, `capture_at_k(y, score, k)`, `grouped_cv(...)`.
- Outputs: `figures/*.pdf` and `figures/*.tex` (tables), plus `figures/metrics.csv`.

## Verified on the files of 2026-11-13
- Plant register: `EGID` column present. FR PV: 22,360 plants, 99.1% with EGID, 99.8% of those found in GWR FR. 628 plants share a building.
- Residential holds 6,062 of 6,387 first installations in 2022-23 (95%) and 5,234 of 5,605 in 2024-25. Base rate before roof and new-build filters: 9.0% (train), 8.5% (test).
- Non-residential and special: 80,429 buildings, median footprint 26-30 m2, 323 first installations in 2022-23, heating and floors about 10% filled.
- Exact construction year (`GBAUJ`) is filled for 37% of residential buildings; period (`GBAUP`) for 97%.
- Heating leak: among residential buildings without PV at end-2021, 6.5% adopted in 2022-23 when the heating record was dated <= 2021, against 19.2% when it was dated 2022-23.
- Tariffs 2024, H4: 4 operators, 106 of 119 municipalities under one operator, 7 distinct prices.
- Sources: plants `data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/csv/2056/ch.bfe.elektrizitaetsproduktionsanlagen.zip` (19 MB); GWR `public.madd.bfs.admin.ch/fr.zip` (43 MB); roofs `data.geo.admin.ch/ch.bfe.solarenergie-eignung-daecher/solarenergie-eignung-daecher/solarenergie-eignung-daecher_2056.gpkg.zip` (1.51 GB); tariffs by SPARQL at `lindas.admin.ch/query`, cube `energy.ld.admin.ch/elcom/electricityprice`.

## Risks
1. **Register lag.** FR PV starts: 3,719 in 2024, 2,063 in 2025. How much of the drop is late registration is unknown until feature 9 runs.
2. **Roof file not opened yet.** Column names, size of the FR extract and the share of buildings without a roof record are unverified.
3. **Snapshot register.** Building attributes are today's values; demolished buildings are missing.
4. **Tariff and heating effects are not identified** (see verified facts). The paper must say so.
5. **Same buildings in train and test.** The test is out-of-time, not out-of-sample across buildings. Train is the 2022-23 boom, test is after it.
6. **GP size.** Hectare cells probably give far more than the ~3,000 points an exact GP handles on a small CPU; expect 500 m or 1 km cells.
7. **Unregistered systems.** The 50-building aerial-photo check is manual work for Gauthier.
8. **Environment.** Nuvolos Python version and CPU are unverified. The opendata.swiss API returns 403 from the cloud sessions; tariffs come from LINDAS instead. Two GWR municipality numbers (2056, 2239) have no tariff row.
9. **Time.** Five weeks at 60% employment; first milestone (building table) is 22 November.

## Acceptance test (proves v1)
On a fresh clone in Nuvolos:
1. `pip install -r requirements.txt`, then `pytest` passes, including the leakage tests: no pool building has a PV start <= T, and the neighbour share ignores installations after T.
2. Notebooks 02 to 05 run in order on a fresh kernel from the committed extracts, with no network, in under 15 minutes.
3. `figures/metrics.csv` is regenerated and equals the committed file. It holds, for the 2024-25 test and the 2024-only row: capture at 5% and 10%, ROC AUC and average precision for random, both baselines, LASSO, the neural net, and the heating sensitivity run.
4. Every figure and table referenced in `paper/` exists in `figures/` and was rewritten by step 2.

First slice (Phase 2): baseline 1 (roof yield) through all five stages, ending in one row of `metrics.csv` and one figure.
