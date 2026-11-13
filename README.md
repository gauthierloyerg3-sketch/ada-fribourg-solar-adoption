# Solar adoption in Fribourg buildings

## What it is
Semester project for Advanced Data Analytics (HEC Lausanne), autumn 2026, by Gauthier Loyer.
It ranks Fribourg residential buildings by the probability of a first photovoltaic installation within two years, using public data only.
The full design is in SPEC.md.

## Status
Setup stage. Only the test helper exists (`code/helpers.py`).
The pipeline stages arrive in later pull requests.

## Install
```
pip install -r requirements.txt
```
Python 3.12 is used in CI.

## Run
```
pytest
ruff check .
```
The stage run order (code/01 to code/05) will be documented here as the stages land.

## Data sources
All four are Swiss federal open data. Licences and citations will be completed before submission.
1. SFOE register of electricity production plants: photovoltaic plants, with the building identifier (EGID).
2. Federal building register (GWR), canton Fribourg: building category, age, floors, footprint, heating.
3. SFOE roof solar suitability (sonnendach.ch): roof area, irradiation and electricity yield per roof surface.
4. ElCom electricity tariffs per municipality, read from LINDAS.

## AI use
AI assistance is allowed by the course and is logged in docs/ai_log.md.
`.claude/` holds the assistant configuration.
