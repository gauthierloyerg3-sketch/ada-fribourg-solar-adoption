# Solar adoption in Fribourg buildings

## What it is
Semester project for Advanced Data Analytics (HEC Lausanne), autumn 2026, by Gauthier Loyer.
It ranks Fribourg residential buildings by the probability of a first photovoltaic installation within two years, using public data only.
The full design is in SPEC.md.

## Status
Walking skeleton: baseline 1 (rank buildings by roof electricity yield) runs through all five stages and is scored on the out-of-time test.
The other features of SPEC.md are added one at a time.

## Install
```
pip install -r requirements.txt
```
Python 3.12 is used in CI.

## Run
From the repository root, in this order:
1. `python code/01_get_data.py` downloads the three raw files (about 1.5 GB, needs the network) into `data/raw/` and writes the Fribourg extracts. It can be skipped: its outputs are committed in `data/processed/`.
2. Notebooks 02 to 05, each on a fresh kernel (each reads only what the previous stage saved):
```
for n in 02_clean 03_features 04_model 05_figures; do
  jupyter nbconvert --to notebook --execute --output-dir /tmp/nb code/$n.ipynb
done
```
Stages 02 to 05 take about 10 seconds in total on the development machine (a small cloud container, no GPU). Stage 01 takes about 15 seconds on top of the download.

Outputs:
- `data/processed/`: `pv_fr`, `buildings_fr`, `roofs_fr` (01), `buildings_clean` (02), `model_table` (03), `predictions` (04) as Parquet, and `sources.json` (URL, size, hash and time of each download).
- `figures/`: `metrics.csv` and `capture_curve.pdf` (05).

The executed copies of the notebooks go to `/tmp/nb`, so the committed notebooks stay untouched.
Checks: `pytest` and `ruff check .`.

## Paper
The LaTeX skeleton is in `paper/` (build with `latexmk -pdf main.tex` from that folder; see `paper/README.md`). It pulls every figure and table from `figures/`; the text is written by the author.

## Data sources
All four are Swiss federal open data. Licences and citations will be completed before submission.
1. SFOE register of electricity production plants: photovoltaic plants, with the building identifier (EGID).
2. Federal building register (GWR), canton Fribourg: building category, age, floors, footprint, heating.
3. SFOE roof solar suitability (sonnendach.ch): roof area, irradiation and electricity yield per roof surface.
4. ElCom electricity tariffs per municipality, read from LINDAS.

## AI use
AI assistance is allowed by the course and is logged in docs/ai_log.md.
`.claude/` holds the assistant configuration.
