# Index of figures/

Index for the author, not paper text. Every file in this folder is listed once; `tests/test_data.py` fails if the list and the folder differ. Stage numbers refer to `code/` (03 = `03_features.ipynb`, 04 = `04_model.ipynb`, 05 = `05_figures.ipynb`). Paper outputs are aggregated (rates by group, grid cells with at least 10 buildings, metrics); nothing is per building.

| File | Shows | Stage |
|---|---|---|
| `metrics.csv` | Capture at 5% and 10%, ROC AUC, average precision per model, split and label, with 95% bootstrap intervals on test rows | 05 |
| `table_metrics.tex` | Test pool, first PV 2024-2025: capture at 5% and 10% with intervals, main models then heating sensitivity runs | 05 |
| `table_metrics_rank.tex` | Same label: ROC AUC and average precision with intervals | 05 |
| `table_metrics_2024.tex` | Test pool, first PV 2024 only: capture at 5% and 10% with intervals | 05 |
| `table_metrics_2024_rank.tex` | Same label: ROC AUC and average precision with intervals | 05 |
| `table_model_gaps.tex` | Paired gaps between models in capture at 10% and ROC AUC, with intervals | 05 |
| `capture_curve.pdf` | Share of adopters captured against share of buildings ranked, test pool, four ranking models and random | 05 |
| `adoption_by_yield.pdf` | Adoption rate by decile of yearly roof yield, train and test pools (inverted U) | 05 |
| `adoption_by_neighbour_share.pdf` | Adoption rate by quintile of the neighbour PV share at 250 m, train and test pools | 05 |
| `table_adoption_by_type.tex` | Buildings and adoption rate by building category (gkat) and number of dwellings, both pools | 05 |
| `map_adoption.pdf` | 1 km cell maps, test pool: observed adoption rate and mean LASSO score percentile | 05 |
| `table_lasso_coef.tex` | The 25 largest non-zero LASSO coefficients (standardised features), readable labels, chosen C | 04 |
| `table_lasso_coef_full.tex` | All non-zero LASSO coefficients, same format | 04 |
| `lasso_cv.csv` | Grouped cross-validation by penalty C: mean ROC AUC, standard error, mean number of non-zero coefficients | 04 |
| `lasso_cv.pdf` | Cross-validation curve of the LASSO with one-standard-error bars, chosen C marked | 05 |
| `table_pool_filters.tex` | Buildings removed by each pool filter at both cut-offs | 03 |
| `table_register_lag.tex` | First installations by start year in the September and November 2026 plant files | 03 |
| `table_heating_leak.tex` | Adoption by date of the heating record (the leak of the heating sensitivity run) | 03 |
| `gp_summary.csv` | Gaussian process on LASSO residuals: fitted parameters, log marginal likelihoods, neighbour correlation, per split | 04 |
| `gp_residual_map.pdf` | Observed and GP-smoothed LASSO residual per 500 m cell, test pool | 05 |
| `segments_summary.csv` | Size, adoption rate and mean traits of the k-means segments | 04 |
| `table_segments.tex` | Segment sizes, adoption rates and the five most distinguishing traits | 05 |
| `pca_segments.pdf` | Test pool on the first two principal components with the segment centres | 05 |
