# Progress

Newest on top.

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
