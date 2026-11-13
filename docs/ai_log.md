# AI log

Feeds the declaration of tools in the paper appendix.

| Date | Asked | Files touched |
|---|---|---|
| 2026-11-13 | Spec interview and data-source checks | SPEC.md |
| 2026-11-13 | Repository setup | README.md, .gitignore, CLAUDE.md, docs/, .claude/, .github/workflows/ci.yml, requirements.txt, pyproject.toml, code/helpers.py, tests/test_helpers.py |
| 2026-11-13 | Walking skeleton: baseline 1 (roof yield) through the five stages, with tests | code/helpers.py, code/01_get_data.py, code/02_clean.ipynb, code/03_features.ipynb, code/04_model.ipynb, code/05_figures.ipynb, tests/test_helpers.py, tests/test_data.py, data/processed/, figures/, requirements.txt, .github/workflows/ci.yml, README.md, CLAUDE.md, docs/ |
| 2026-11-13 | Record the new merge rule (sessions merge their own PRs once CI is green) | CLAUDE.md, docs/decisions.md, docs/ai_log.md |
| 2026-11-13 | Task plan (TASKS.md) | TASKS.md |
| 2026-11-13 | T01: bring SPEC.md up to date; record the no-gate rule and three approved choices | SPEC.md, TASKS.md, CLAUDE.md, docs/decisions.md, docs/progress.md, docs/ai_log.md |
| 2026-11-13 | T03: add source selection to 01, older plant snapshot extract, register-lag table | code/01_get_data.py, data/processed/pv_fr_2026_09.parquet, data/processed/sources.json, code/03_features.ipynb, figures/table_register_lag.tex, tests/test_data.py, TASKS.md, docs/progress.md, docs/ai_log.md, docs/decisions.md |
| 2026-11-13 | T02: tariff extract from LINDAS (source `tariffs` in 01, parquet, tests) | code/01_get_data.py, data/processed/tariffs_fr.parquet, data/processed/sources.json, tests/test_data.py, TASKS.md, docs/ |
