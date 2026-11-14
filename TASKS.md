# TASKS: remaining work to v1

**How to start a task:** read CLAUDE.md, SPEC.md, docs/progress.md, docs/decisions.md and this file; take the first `todo` task, write the model line (CLAUDE.md), set its status to `in progress` on a fresh branch, and set it to `done` in the same PR.

Rules for every task (not repeated below):
- Each task also owns TASKS.md (its own status line), docs/progress.md, docs/ai_log.md and docs/decisions.md (new entries only).
- Code tasks: `pytest` and `ruff check .` pass, CI green (Python 3.12), reviewer subagent PASS, then merge (merge commit).
- `figures/metrics.csv` must regenerate byte-identically on CI: fixed seeds (`random_state=0`), scores rounded to 6 decimals in 04, metrics rounded as in 05.
- Copy the walking-skeleton pattern: logic used twice goes in `code/helpers.py` with a unit test; notebooks read only `data/processed/`.
- Tables are `.tex` in `figures/`, written by the stage that holds the data. Paper outputs are aggregated: no per-building points in figures.
- Stages 02 to 05 together stay under 15 minutes on a small CPU (today: about 10 s).
- Never regenerate `pv_fr`, `buildings_fr` or `roofs_fr`: the registers change daily and a fresh session has no `data/raw/`, so a full run of 01 would download newer files (and 1.5 GB of roofs) and move every number. A task that adds a source to 01 first gives 01 a way to run one source only (T03 adds it), runs only its own source, and checks with `git status` that the other extracts are untouched.

## Order

| id | title | status | depends on | model, effort | milestone | cuttable |
|---|---|---|---|---|---|---|
| T01 | Bring SPEC.md up to date | done | none | haiku, low | 22 Nov | no |
| T03 | September plant snapshot and register-lag table | done | none | sonnet, medium | 22 Nov | no |
| T02 | Tariff extract from LINDAS | done | T03 (same file) | sonnet, medium | 22 Nov | no |
| T04 | Neighbour PV share helper and feature | done | none | sonnet, medium | 22 Nov | no |
| T05 | Final building table: tariff join, ids, pool-filter table | done | T02, T04 | sonnet, medium | 22 Nov | no |
| T06 | Baseline 2: rank by neighbour PV share | done | T05 | sonnet, medium | 29 Nov | no |
| T07 | LASSO logistic with grouped CV | done | T06 | sonnet, medium | 29 Nov | no |
| T08 | Bootstrap intervals in metrics.csv | done | T07 | sonnet, medium | 29 Nov | no |
| T09 | Heating sensitivity run | done | T08 | sonnet, medium | 6 Dec | no |
| T10 | Small MLP | done | T08 | sonnet, medium | 6 Dec | yes (first) |
| T11 | GP on LASSO residuals per grid cell | done | T07 | sonnet, medium | 6 Dec | no |
| T12 | PCA and k-means segments | done | T07 | sonnet, medium | 13 Dec | yes (second) |
| T13 | Paper figures and tables | done | T08 to T12 | sonnet, medium | 13 Dec | no |
| T14 | Wire figures into paper/ and check them in CI | done | T13, owner adds SIAM template | sonnet, medium | 13 Dec | no |
| T15 | Reproducibility: pin, Python version, README | todo | T14, owner checks Nuvolos | sonnet, medium | week of 14 Dec | no |
| T16 | Final freeze: executed notebooks, number check | todo | T15, owner's paper draft | haiku, low | 20 Dec | no |

Tasks run in the row order of this table, not in id order. Why this order where it is not obvious: T03 runs before T02 because the September snapshot can be overwritten at the next register update. T09 comes before T10 because the heating run is never cut. T11 runs before T12 because the GP is not cuttable.

## Tasks

**T01 Bring SPEC.md up to date.** Goal: SPEC matches what is verified.
Files: SPEC.md. Acceptance: status line states what Gauthier confirms (ask; do not write "approved" otherwise); risk 2 replaced by the verified roof facts (2023 release, 12.5% of residential buildings without record, upper-case columns); baseline 1 finding added (test ROC AUC 0.48, inverted U in yield, adoption 8.6% for one dwelling vs 3.9% for four or more; GKAT 1020 8.5%, 1030 4.6%, 1040 4.2%). No other section changed.

**T02 Tariff extract from LINDAS.** Goal: `tariffs_fr.parquet` committed, one row per `bfs_nr` x `year`.
Files: code/01_get_data.py, data/processed/tariffs_fr.parquet, data/processed/sources.json, tests/test_data.py.
Facts: POST SPARQL to https://lindas.admin.ch/query, header `Accept: text/csv`; graph <https://lindas.admin.ch/elcom/electricityprice>, cube <https://energy.ld.admin.ch/elcom/electricityprice>; dimensions under .../electricityprice/dimension/: period, category (.../category/H4), product (standard), operator, municipality (https://ld.admin.ch/municipality/<BFS>), total, energy, gridusage, charge, aidfee. opendata.swiss returns 403 from cloud sessions. Fetch years 2020 to 2025 only. Two municipalities have two operators: keep the mean and an `n_operators` column.
Acceptance: test that (`bfs_nr`, `year`) is unique and 2022 and 2024 are present; 2024 has 117 municipalities (119 rows before averaging two operators) and 7 distinct `total` values; `sources.json` has a tariff entry (query text hash, time). Network run done once in the session; CI does not run 01.

**T03 September plant snapshot and register-lag table.** Goal: count how many plants with a 2024 or 2025 start were registered between 16 Sep and 12 Nov 2026.
Files: code/01_get_data.py, data/processed/pv_fr_2026_09.parquet, data/processed/sources.json, code/03_features.ipynb, figures/table_register_lag.tex, tests/test_data.py.
Facts: older snapshot is the STAC asset https://data.geo.admin.ch/ch.bfe.elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen/elektrizitaetsproduktionsanlagen_2056.csv.zip (updated 2026-09-16); current file is .../csv/2056/ch.bfe.elektrizitaetsproduktionsanlagen.zip (2026-11-12). Same columns unverified: check first, map if they differ, stop and report if EGID or start date is missing. Add a command-line argument to 01 that selects the sources to run (default: all).
Acceptance: table with FR residential first installations by start year 2022 to 2025 in both files and the difference; the 2025 count in the November file equals the one in docs (2,063 FR PV starts overall); same schema test as `pv_fr.parquet`.

**T04 Neighbour PV share helper and feature.** Goal: `nbr_pv_share_100`, `nbr_pv_share_250` in `model_table`, free of leakage.
Files: code/helpers.py, tests/test_helpers.py, tests/test_data.py, code/03_features.ipynb, data/processed/model_table.parquet, requirements.txt (add scipy).
Facts: coordinates `gkode`, `gkodn` (LV95, metres) in buildings_clean, 100% filled. `neighbour_pv_share(xy, has_pv, radius)` with scipy `cKDTree`; neighbours are all population buildings within the radius (not only the pool), self excluded; `has_pv` = first PV <= T. Keep the neighbour count as a column; zero neighbours gives share 0.
Acceptance: unit test where a neighbour PV dated T + 1 day is not counted and one dated T is; self-exclusion test; data test that recomputing the share for 100 sampled pool buildings matches; stage 03 still under 1 minute.

**T05 Final building table.** Goal: the 22 Nov building table: roof aggregates, neighbour share, tariff, labels, ids for CV and maps.
Files: code/03_features.ipynb, data/processed/model_table.parquet, figures/table_pool_filters.tex, tests/test_data.py.
Facts: tariff known at T is the year T+1 price (ElCom publishes next-year tariffs by end of summer): 2022 for train, 2024 for test; record this in decisions.md and flag it in the PR for Gauthier. Missing tariff rows (found in T02): 2056 Fétigny-Ménières and 2239 Grolley-Ponthaux in every year, and 2138 Jaun in 2022 only (1,464 population buildings in 2022, 1,141 in 2024). The raw answer (data/raw, or re-run `python code/01_get_data.py tariffs`) holds pre-merger numbers 2016, 2027, 2200, 2217, 2259, 2260, all under operator 609 at the canton median in 2022 and 2024, so fill the three municipalities with the canton median of the year and set a `tariff_filled` flag; do not build a merger mapping. The price level shifts between cut-offs (median 21.2 in 2022, 32.4 in 2024), so the feature is `tariff_dev` = total minus the canton median of that year (keep `tariff_total` as an id-like column, not a model feature); record this in decisions.md. Add `ggdenr`, `gkode`, `gkodn` as id columns (not features).
Acceptance: `tariff_total` and `tariff_dev` have no missing value; `tariff_dev` is 0 for at least 100 municipalities per cut-off; pool-filter table shows, at the train cut-off, 67,482 at risk, 4,049 new builds (21.7%), 5,567 without roof record (5.0%), 1,294 small roof (4.4%), 56,572 kept (8.6%), plus the same for test; pool sizes 56,572 and 51,725 unchanged.

**T06 Baseline 2.** Goal: rank by neighbour PV share at 250 m (declared here, not chosen on test).
Files: code/04_model.ipynb, code/05_figures.ipynb, data/processed/predictions.parquet, figures/metrics.csv, figures/capture_curve.pdf.
Acceptance: metrics.csv has `nbr_share` rows for train y, test y, test y_2024; roof_yield rows unchanged; CI green.

**T07 LASSO logistic with grouped CV.** Goal: the headline model, scored on the test pool.
Files: code/helpers.py (`grouped_cv`, feature-matrix builder), tests/test_helpers.py, code/04_model.ipynb, code/05_figures.ipynb, data/processed/predictions.parquet, figures/metrics.csv, figures/table_lasso_coef.tex.
Facts: yield is an inverted U (about 5% in the lowest and top two deciles, 9% between): use train-quantile decile bins for yield and log area plus its square; dwellings binned 1, 2, 3, 4+; one-hot `gkat`, `gbaup`; neighbour shares; `tariff_dev`. Missing `gastw`/`garea`: train median plus flag. Standardise on train. `LogisticRegressionCV(penalty="l1", solver="liblinear", Cs=10, class_weight="balanced", scoring="roc_auc")` with GroupKFold(5) on `ggdenr`. No heating column.
Acceptance: test that `grouped_cv` never puts one municipality in two folds; test that the feature list has no heating column; `lasso` rows in metrics.csv for all three labels; coefficient table lists nonzero terms and chosen C; train metrics labelled in-sample in the notebook; CI green.

**T08 Bootstrap intervals.** Goal: 95% percentile intervals for every test metric.
Files: code/helpers.py, tests/test_helpers.py, code/05_figures.ipynb, figures/metrics.csv.
Facts: resampling unit is Gauthier's call before the task starts (default: municipality clusters, because neighbour shares correlate within municipality). B = 200, seed 0, same draws for all models.
Acceptance: columns `<metric>_lo`, `<metric>_hi` for capture_5, capture_10, roc_auc, avg_precision on test rows; unit test that intervals contain the point estimate on a toy case and are reproducible with the seed; 05 under 2 minutes; CI green.

**T09 Heating sensitivity run.** Goal: `lasso_heating` rows, reported as a leakage-contaminated upper bound.
Files: code/02_clean.ipynb, code/03_features.ipynb, code/04_model.ipynb, code/05_figures.ipynb, data/processed/heating_clean.parquet, data/processed/heating_features.parquet, data/processed/predictions.parquet, figures/metrics.csv, tests/test_data.py, SPEC.md (data-model rows only).
Facts: heating columns `genh1`, `gwaerzh1`, `gwaerdath1`; `test_no_heating_columns` forbids them in buildings_clean and model_table, so they travel in separate files keyed `egid` (02) and `egid`, `cutoff` (03). Leak: 19.2% adoption when the heating record is dated 2022-23 vs 6.5% when dated <= 2021.
Acceptance: `test_no_heating_columns` still passes; `lasso_heating` rows for test y and y_2024; same C-selection as T07; CI green.

**T10 Small MLP (cut first).** Goal: do interactions add anything over LASSO?
Files: code/04_model.ipynb, code/05_figures.ipynb, data/processed/predictions.parquet, figures/metrics.csv.
Facts: same feature matrix as T07; `MLPClassifier(hidden_layer_sizes=(16,), random_state=0)`, no tuning; epoch count chosen by validation ROC AUC on held-out municipalities of the train split (scikit-learn's accuracy-based `early_stopping` was tried first and under-fitted, see docs/decisions.md). Float results may differ between Python 3.13 (container) and 3.12 (CI): if CI diffs, round MLP scores to 4 decimals; if it still diffs, stop and report.
Acceptance: `mlp` rows for all three labels with bootstrap columns; fit under 3 minutes; CI green two runs in a row.

**T11 GP on LASSO residuals.** Goal: is spatial structure left after LASSO?
Files: code/04_model.ipynb (fit, writes data/processed/gp_cells.parquet), code/05_figures.ipynb (map and summary), data/processed/gp_cells.parquet, figures/gp_residual_map.pdf, figures/gp_summary.csv, SPEC.md (data-model row only).
Facts: residual = y - p_lasso on test, label y, averaged per grid cell from `gkode`, `gkodn`. Exact GP limit about 3,000 points: count cells first, use 500 m if under 3,000 cells with >= 10 buildings, else 1 km. sklearn GaussianProcessRegressor, RBF + WhiteKernel, per-cell noise `alpha` = residual variance / n.
Acceptance: gp_summary.csv holds cell size, n cells, fitted length scale, signal and noise variance (3 decimals); cells with < 10 buildings are dropped from the map; 04 still under 5 minutes; CI green (gp_summary.csv is not diffed).

**T12 PCA and k-means segments (cut second).** Goal: descriptive building segments with their adoption rates.
Files: code/04_model.ipynb (fit, writes data/processed/segments.parquet), code/05_figures.ipynb (table and plot), data/processed/segments.parquet, figures/table_segments.tex, figures/pca_segments.pdf, SPEC.md (data-model row only).
Facts: standardised building traits from model_table (test pool); k chosen from 3 to 6 by silhouette on a 5,000-building sample, seed 0. Plot density or centroids, not building points.
Acceptance: table with segment size, test adoption rate and mean traits per segment; explained variance of the first two components printed; CI green.

**T13 Paper figures and tables.** Goal: every paper figure and table exists in `figures/`.
Files: code/05_figures.ipynb, figures/*.pdf, figures/*.tex.
Content: metrics table with intervals (`table_metrics.tex`); capture curves for all models; adoption by yield decile (inverted U); adoption by dwellings and GKAT table; 1 km grid maps of adoption rate and mean LASSO score (cells with >= 10 buildings).
Acceptance: each listed file is written by 05 from a fresh kernel; no figure plots individual buildings; CI green.

**T14 Wire figures into paper/.** Goal: paper/main.tex pulls every figure and table from figures/, with the SPEC section headings only.
Files: paper/main.tex (headings, `\input` and `\includegraphics` only; no prose), tests/test_paper.py, .github/workflows/ci.yml.
Acceptance: test that every path referenced in paper/*.tex exists in figures/; CI diff extended to `figures/*.tex`; no AI-written paper text.

**T15 Reproducibility.** Goal: a fresh Nuvolos clone follows the README to the same metrics.
Files: requirements.txt, code/01_get_data.py, .github/workflows/ci.yml, pyproject.toml, README.md.
Facts: stage 01 uses `datetime.UTC` (3.11+): use `timezone.utc` if Nuvolos is older. Pin exact versions that work there; set CI to the Nuvolos Python version.
Acceptance: CI green on pinned versions; README has run order, measured runtime and machine, data sources with licences; timed run of 02 to 05 under 15 minutes pasted in the PR.

**T16 Final freeze.** Goal: the graded commit shows results and the numbers match.
Files: code/02_clean.ipynb to code/05_figures.ipynb (executed in place, per decisions.md), README.md (recording link).
Acceptance: notebooks executed top to bottom on fresh kernels; every number in paper/ checked against figures/ and mismatches listed for Gauthier (no edits to his text); CI green.

## Owner tasks (not for AI sessions)

| What | Blocks |
|---|---|
| Add docs/proposal.md and check SPEC against it | T01 (22 Nov) |
| Write to the TA: `.claude/` and CI files in the graded repo, residential-only population, heating out of the main model | T09 (6 Dec) |
| Choose the bootstrap resampling unit (building or municipality) | T08 (29 Nov) |
| Manual aerial-photo check of 50 "no PV" buildings | paper data section (13 Dec) |
| Check the Python version and CPU of the Nuvolos workspace | T15 (14 Dec) |
| Add the SIAM template to paper/ (`siamart220329.cls`, see paper/README.md; check its licence) | T14 (13 Dec) |
| Write the paper | draft 13 Dec, final 20 Dec |
| Reproduction test in Nuvolos (fresh clone, README) | week of 14 Dec |
| Record the 15-minute video; submit repo URL and commit SHA | 20 Dec, 23:59 Zurich |

## Coverage

| SPEC item | Covered by |
|---|---|
| v1 feature 2: building table (roof, neighbour share, tariff, labels) | T02, T04, T05 |
| 3: two baselines | done (roof yield), T06 |
| 4: LASSO with grouped CV | T07 |
| 5: MLP | T10 |
| 6: GP on residuals | T11 |
| 7: PCA + k-means | T12 |
| 8: heating sensitivity | T09 |
| 9: register-lag check | T03 |
| 10: figures, tables, paper/ | T13, T14, owner (text) |
| Metrics with bootstrap intervals | T08 |
| Acceptance 1: pytest incl. leakage tests | existing pool test, T04 |
| Acceptance 2: 02 to 05 fresh kernel, no network, < 15 min | CI, T15, owner (Nuvolos run) |
| Acceptance 3: metrics.csv regenerated and equal, all rows | T06 to T10, CI diff |
| Acceptance 4: paper figures exist and are rewritten | T13, T14 |
| Risks 1, 2, 7, 8 | T03, T01, owner, T15 |
