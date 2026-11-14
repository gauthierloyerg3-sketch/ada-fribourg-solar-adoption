# Solar adoption in Fribourg buildings

Semester project for Advanced Data Analytics (HEC Lausanne, Master in Finance), autumn 2026, by Gauthier Loyer.
It ranks Fribourg residential buildings by the probability of a first photovoltaic (PV) installation within two years, using public Swiss federal data only.
Evaluation is out-of-time: train cut-off 2021-12-31 (label window 2022-2023), test cut-off 2023-12-31 (label window 2024-2025). The design is in `SPEC.md`.

Main result (`figures/metrics.csv`, test pool of 51,725 buildings, 4,020 first installations in 2024-2025): the share of adopters captured in the top 10% of the ranking is 0.195 for the LASSO, 0.131 for the neighbour PV share baseline and 0.073 for the roof yield baseline (random: 0.100); ROC AUC is 0.664, 0.598 and 0.481.

## Repository map
- `code/`: `01_get_data.py` (only stage that uses the network), notebooks `02_clean`, `03_features`, `04_model`, `05_figures`, shared functions in `helpers.py`.
- `data/processed/`: committed Parquet extracts and tables (building level, open federal data) and `sources.json`. `data/raw/` is git-ignored.
- `figures/`: every figure and table of the paper, `metrics.csv`; `figures/README.md` is the index.
- `paper/`: LaTeX source. `tests/`: pytest. `docs/`: progress, decisions, AI log, data sources.
- `.claude/`, `.github/`: assistant configuration and CI.

## Install
Python 3.12 or later is needed (pandas 3 and scikit-learn 1.8 or later require 3.11 or later). The pinned versions in `requirements.txt` were run on Python 3.13 (development container) and 3.12 (CI). The Python version of the Nuvolos workspace is not verified yet.
```
pip install -r requirements.txt
```

## Run
From the repository root, in this order.
1. Optional: `python code/01_get_data.py` downloads the raw files (about 1.5 GB, needs the network) into `data/raw/` and rewrites the Fribourg extracts. Its outputs are committed, so skip it for a reproduction: the registers change daily, a new download gives newer data and different numbers.
2. Stages 02 to 05, each on a fresh kernel, no network:
```
for n in 02_clean 03_features 04_model 05_figures; do
  jupyter nbconvert --to notebook --execute --output-dir /tmp/nb code/$n.ipynb
done
```
The executed copies go to `/tmp/nb`; the committed notebooks stay untouched. Data are written to `data/processed/` and figures to `figures/`.
3. Checks: `pytest` and `ruff check .`

## Runtime and machine
Development: a small cloud container (4 CPU cores, 15 GB memory, no GPU). Stages 02 to 05 measured end to end on fresh kernels on 2026-11-14: 5 minutes 24 seconds in total (02: 7 s, 03: 5 s, 04: 209 s, 05: 103 s), with every output identical to the committed files. CI (GitHub-hosted ubuntu runner, Python 3.12) runs install, lint, tests and stages 02 to 05 in about 5 minutes. Nuvolos: not measured yet. Stage 01 takes about 15 seconds on top of the 1.5 GB download.

## Outputs
`figures/` holds the PDF figures, the `.tex` table fragments used by the paper and `metrics.csv`; `figures/README.md` lists each file and the stage that writes it. Paper outputs are aggregated; the building-level extracts are only in `data/processed/`.

## Paper
The LaTeX skeleton is in `paper/` (build with `latexmk -pdf main.tex` from that folder; see `paper/README.md`). It pulls every figure and table from `figures/`; the text is written by the author.

## Data sources
All four are Swiss federal open data, with source attribution required. URLs, versions, terms and suggested citations are in `docs/data_sources.md`.
1. SFOE register of electricity production plants: PV plants with the building identifier (EGID).
2. FSO federal register of buildings and dwellings (GWR), canton Fribourg, public level.
3. SFOE roof solar suitability (sonnendach.ch): roof area, irradiation and electricity yield per roof surface.
4. ElCom electricity tariffs per municipality, read from LINDAS.

## Reproducibility notes
- The extracts in `data/processed/` are committed; `data/processed/sources.json` holds the URL, size, time and sha256 of each download.
- CI re-runs stages 02 to 05 and fails if the regenerated tables (`figures/*.tex`) and the CSVs `metrics.csv`, `lasso_cv.csv`, `segments_summary.csv` differ from the committed files. PDFs and `gp_summary.csv` are not compared because they can differ between machines.
- Seeds are fixed. The neural network scores are stored at 4 decimals, the others at 6, so that small floating-point differences between machines do not change the ranking.

## AI use
AI assistance is allowed by the course. Requests and touched files are logged in `docs/ai_log.md`, design decisions in `docs/decisions.md`, and `.claude/` holds the assistant configuration. The paper text is written by the author.

## Recording
TODO (owner): link to the recording of about 15 minutes.
