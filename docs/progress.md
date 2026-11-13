# Progress

Newest on top.

## 2026-11-13 (T09)
- Done: `lasso_heat_source` and `lasso_heat_date` (same pipeline and C = 0.1 as `lasso`, no second CV) in 04; heating travels in `heating_clean.parquet` (02) and `heating_features.parquet` (03) and enters only through `helpers.fit_features(..., extra=...)`, the main path still refuses it; `heat_source_group` helper; `figures/table_heating_leak.tex` (03); gap rows in `table_model_gaps.tex`; tests. Main files, `lasso` scores and old metrics rows unchanged.
- Found: leak is large: adoption 15.3% (train) and 13.1% (test) when the heating record is dated after the cut-off, 6.1% and 7.1% otherwise. Test y: ROC AUC 0.664 (lasso), 0.720 (`lasso_heat_source`), 0.720 (`lasso_heat_date`); capture_10 0.195, 0.245, 0.253. `heat_source` alone carries the gain (heat pump 17.8% and undetermined 13.6% adoption in the train pool, oil 3.5%), the date flag adds little on top. 04 about 130 s, 02 to 05 about 3.5 min.
- Next: T10 (MLP).

## 2026-11-13 (T08)
- Done: `helpers.cluster_bootstrap_indices` (whole municipalities drawn with replacement, `default_rng`) with tests; 05 adds `<metric>_lo` / `<metric>_hi` (2.5th and 97.5th percentiles, B = 200, seed 0, same draws for all models) on test rows, and `figures/table_model_gaps.tex` with paired gaps (capture_10, ROC AUC) for lasso vs nbr_share, lasso vs roof_yield, nbr_share vs roof_yield. Old metrics.csv columns are byte-identical.
- Found: 119 municipalities in the test pool; replicate size 41,252 to 65,929 rows. Test y, lasso capture_10 0.195 [0.179, 0.214] and ROC AUC 0.664 [0.648, 0.678]. Paired gap lasso minus nbr_share: capture_10 0.064 [0.048, 0.079], ROC AUC 0.066 [0.054, 0.079], so the LASSO beats both baselines by more than the sampling noise on the test pool. Municipality clustering widens the lasso capture_10 interval to 0.035 against 0.020 for a plain building bootstrap. 05 takes about 40 s; two runs give identical files.
- Next: T09 (heating sensitivity run).

## 2026-11-13 (T07)
- Done: `helpers.fit_features`, `apply_features` (51 standardised columns, heating columns raise) and `grouped_cv` (GroupKFold on `ggdenr`) with tests; `lasso` model in 04 (L1 logistic, `balanced`, grouped 5-fold CV over 10 C on a log grid, refit on train); `figures/table_lasso_coef.tex`; `lasso` rows in `metrics.csv`; capture curve with three models.
- Found: chosen C = 0.1 (top of the grid, on a plateau: mean CV AUC 0.6777, SE 0.0024), 44 of 51 coefficients non-zero; one-SE C = 0.0046 gives 31. Test y: capture_10 0.195 (nbr_share 0.131, random 0.10), ROC AUC 0.664, AP 0.129; test y_2024: capture_10 0.210, AUC 0.675; train (in-sample) AUC 0.682. 04 takes about 100 s (CV fit about 100 s), 02 to 05 about 115 s; two runs give identical files. Scores are not calibrated (mean 0.48 on test against 0.078 observed).
- Next: T08 (bootstrap intervals).

## 2026-11-13 (T06)
- Done: `nbr_share` model (score = `nbr_pv_share_250`) in 04, which now builds one frame per model and writes one sorted `predictions.parquet` (scores float64, 6 decimals); 05 sorts by (split, model, egid) before scoring so ties are broken deterministically.
- Found: test y capture_10 0.131 (random 0.10, roof_yield 0.073), ROC AUC 0.598, AP 0.099; test y_2024 capture_10 0.133, AUC 0.607; train AUC 0.591. Rounding to 6 decimals left the `roof_yield` rows unchanged. 3,621 distinct scores on test (8% of buildings at 0), but reversing the tie order leaves capture_10 unchanged (0.130846 / 0.133058).
- Next: T07 (LASSO).

## 2026-11-13 (T05)
- Done: `tariff_total`, `tariff_filled`, `tariff_dev` (year T+1 H4 price minus canton median of that year) and id columns `ggdenr`, `gkode`, `gkodn` in `model_table.parquet`; `helpers.pool_status` (reason per building, `build_pool` now uses it); `figures/table_pool_filters.tex`; tests.
- Found: pool sizes 56,572 / 51,725, earlier columns and metrics.csv unchanged; filter table matches the baseline-1 numbers (new builds adopt 21.7% train and 27.9% test, no roof 5.0% / 5.4%, small roof 4.4% / 3.7%). 3 municipalities filled in train (1,136 pool buildings), 2 in test (784); 88% of pool buildings sit at the canton median (tariff_dev 0), so the tariff effect rests on about 12% of buildings in 6 to 7 price groups.
- Next: T06 (baseline 2).

## 2026-11-13 (T04)
- Done: `helpers.neighbour_pv_share` (cKDTree, count and share, self excluded) and `helpers.has_pv_by` (shared `<= T` rule); `nbr_n_100`, `nbr_pv_share_100`, `nbr_n_250`, `nbr_pv_share_250` in `model_table.parquet` (population buildings as neighbours, PV dated <= T); unit tests and a brute-force data test on 100 sampled pool buildings per cut-off.
- Found: pool sizes and all earlier columns unchanged; metrics.csv identical; stage 03 runs in about 3 s. Mean share at 250 m 0.111 (train) and 0.186 (test); 1% of pool buildings have no neighbour within 250 m, 4.4 to 4.5% within 100 m. Adoption rises from 4.6% (lowest share quintile) to 11.7% (highest) in train.
- Next: T05 (final building table).

## 2026-11-13 (T02)
- Done: `01_get_data.py tariffs` (SPARQL POST to LINDAS, H4 standard, 2020-2025, raw CSV in data/raw); `tariffs_fr.parquet` (697 rows, one per `bfs_nr` x `year`, mean over operators, `n_operators`); `sources.json` tariff entry (query hash); 3 tests in test_data.py.
- Found: 2024 has 119 rows, 117 municipalities, 4 operators, 7 distinct totals, median 32.402 Rp/kWh (as expected). GWR numbers 2056 and 2239 have no tariff row in 2024; 2022 also lacks 2138 (Jaun). 1,141 population buildings (2024) and 1,464 (2022) have no tariff. The cube holds 2027 tariffs today, so the year T+1 tariff is known at the end of year T.
- Next: T04 (neighbour PV share).

## 2026-11-13 (T03)
- Done: `01_get_data.py` takes source names (default all) and ran only `plants_2026_09`; `pv_fr_2026_09.parquet` (22,082 FR PV plants) and its `sources.json` entry; register-lag table in `03_features.ipynb` -> `figures/table_register_lag.tex`.
- Found: the older file is the register as of 2026-09-14 (zip entries), published 2026-09-16; its latest start date is 2026-07-24. First installations on population buildings, September vs November file: 2022 2,339 vs 2,340; 2023 3,714 vs 3,722; 2024 3,385 vs 3,395; 2025 1,793 vs 1,839 (+46, +2.5%). Overall FR PV starts in 2025: 2,011 vs 2,063 (the documented figure).
- Next: T02 (tariff extract from LINDAS).
- Found (lag by start quarter, all FR PV plants): the November file adds 1 to 2% to each of 2025 Q1 to Q3, 6% to 2025 Q4, 15% to 2026 Q1 and 50% to 2026 Q2, against 0.1 to 0.5% for 2024 quarters. Registration is mostly complete about three quarters after start-up, so most of the 2025 drop is real and the undercount sits in 2025 Q4.

## 2026-11-13 (task plan)
- Done: TASKS.md (16 sequential tasks) merged; T01 done (SPEC.md brought up to date); phase gates removed.
- Found: nothing new.
- Next: T03 (September plant snapshot and register-lag table), then T02, T04, T05.

## 2026-11-13 (walking skeleton)
- Done: baseline 1 (rank by roof electricity yield) through all five stages; helpers `first_pv_date`, `build_pool`, `make_label`; tests on the helpers and on the committed data; CI runs notebooks 02 to 05 and diffs `figures/metrics.csv`.
- Found: roof file columns are upper case (`GWR_EGID`, `KLASSE`, `FLAECHE`, `STROMERTRAG`); 12.5% of the 76,171 residential buildings have no roof record. Roof yield does not beat random on the test (ROC AUC 0.48, capture at 5% of 3.6%): adoption peaks in the middle of the yield range and falls for the largest roofs.
- Found (filters, train cut-off): of 67,482 at-risk buildings, 4,049 new builds are dropped (21.7% adopt), 5,567 without a roof record (5.0% adopt) and 1,294 with a small roof (4.4% adopt); the 56,572 kept adopt at 8.6%.
- Open: stage 01 needs Python 3.11 or later (`datetime.UTC`); check against Nuvolos.
- Next: baseline 2 (neighbour PV share), then tariffs and LASSO.

## 2026-11-13
- Done: spec interview and SPEC.md; data sources checked (the plant register has EGID); repo setup files.
- Found: register lag in 2025; heating-date leakage; tariffs nearly constant. See docs/decisions.md.
- Next: walking skeleton (baseline 1, roof yield, through all five stages). Open items: add docs/proposal.md, confirm `.claude/` with the TA, check the Nuvolos Python version, open the 1.5 GB roof file.
