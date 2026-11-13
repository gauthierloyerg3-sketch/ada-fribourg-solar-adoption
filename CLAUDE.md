# Mission
Individual semester project for Advanced Data Analytics (HEC Lausanne, Master in Finance, autumn 2026).
Rank Fribourg residential buildings by the probability of a first PV installation within two years, with public data only.
Gauthier Loyer is the author and defends the choices and the numbers. AI assistance is allowed and declared in the paper appendix.
Full spec: @SPEC.md
The approved proposal belongs in docs/proposal.md and is not in the repo yet. Do not widen the scope without asking.

# Commands
- Test: `pytest` (run a single test while iterating, e.g. `pytest tests/test_helpers.py -k capture`; full suite before commit)
- Lint: `ruff check .`
- Stage 01 (network, about 1.5 GB, optional because its outputs are committed): `python code/01_get_data.py`
- Run stages 02 to 05 on fresh kernels: `for n in 02_clean 03_features 04_model 05_figures; do jupyter nbconvert --to notebook --execute --output-dir /tmp/nb code/$n.ipynb; done` (data go to data/processed and figures/; `--output-dir` keeps the committed notebooks clean)

# Architecture
- Five stages, one file each: code/01_get_data.py, 02_clean.ipynb, 03_features.ipynb, 04_model.ipynb, 05_figures.ipynb. Each stage reads only what the previous one saved. Only stage 01 touches the network.
- Shared logic lives in code/helpers.py and is unit-tested in tests/.
- `code/` is not a Python package (the name clashes with the standard-library module `code`): never add `__init__.py` there; import with `import helpers` (pytest gets the path from pyproject.toml).
- data/raw/ is git-ignored; data/processed/ (Parquet extracts) and figures/ are committed.
- paper/ will hold the SIAM LaTeX source. Gauthier writes the text; AI sessions only wire figures and tables in and check numbers against code output.

# Workflow
- One task = one branch = one PR into main. Never push to main directly.
- AI sessions merge their own PR once CI is green; code PRs also need a PASS from the reviewer subagent. Merge commit only (no squash, no force). Report each merge.
- Phase gates and choices that are Gauthier's (scope, methods) still wait for his OK.
- Tasks run one at a time, in sequence. No parallel agents.
- Done = tests pass + output pasted as evidence.
- Only edit files listed in your task.
- Decisions go in docs/decisions.md, not here. Do not reopen them unasked.
- Each PR description: at most 8 lines (what, why, key numbers), written for an expert, with the technical keywords so Gauthier can ask for detail. No long walkthroughs unless asked.
- Session start: read this file, docs/progress.md, docs/decisions.md. Session end: one entry on top of docs/progress.md (done, found, next), one line in docs/ai_log.md (what was asked, files touched).

# Model policy
Before every task, write: Task: X -> model: Y, effort: Z, because ...

| Work | Model | Effort |
|---|---|---|
| Spec, architecture, data model, bug that failed twice | fable (opus if unavailable) | high |
| Planning a multi-file feature | opus | high |
| Implementing an approved plan, tests, refactors | sonnet | medium |
| PR review | sonnet (reviewer subagent) | medium |
| Search, lookups, renames, formatting, docs | haiku (explorer subagent) | low |

- The default is sonnet.
- Escalate one level only after two failures or for clearly architectural work, and say so first.
- Ask before starting any task on fable.
- A session cannot change its own model: name the `/model` to run, or delegate to a subagent.
- After two failed corrections on the same issue, stop and write a better prompt for a fresh session.

# Course rules (binding)
- Every notebook runs top to bottom on a fresh kernel. Each stage loads what the previous one saved.
- Code used twice lives in `code/helpers.py` and is imported.
- Fixed random seeds. Relative paths only (`data/...`). No API keys or passwords.
- Every figure and table in the paper is produced by code in this repo, saved to `figures/`.
- No caches, checkpoints, virtual environments or editor settings in git. `.claude/` and `.github/` are project configuration: committed, and declared in the paper appendix.
- Code not written by Gauthier (forums, repos, blogs): a comment with source and licence where it appears, and listed in the paper appendix. Code from other students of this course or previous years: never.
- Code drafted by an AI assistant: say so in a comment or the appendix, with what was asked.
- Must also run in the course's Nuvolos workspace (modest CPU, no GPU): no long grid searches, keep models small.
- Never rewrite git history (no force-push, no rebase of pushed commits). The graded commit must be on `main`.
- Paper outputs are aggregated (grid-cell or municipality maps, metrics, segments): no per-building results in the paper or in figures. Building-level extracts in data/processed/ are committed (open federal data).
- Nothing about any employer or private client data belongs in this repo.

# Deadlines
Submission: Sunday 2026-12-20, 23:59 Zurich time. Late = zero.
- `paper.pdf`: SIAM article template, about 10 pages (at least 8 excluding references). Sections in order: Abstract, Introduction, Research question and literature, Methodology, Data set (source and cleaning), Implementation, Results, Conclusion, Appendix (declaration of tools).
- Recording of about 15 minutes (file or link in README).
- README: what it does, install, run order, runtime and machine, data sources and licences.

| By | Milestone |
|---|---|
| Sun 22 Nov | Final building table (roof extract, neighbour feature, labels) |
| Sun 29 Nov | Baselines + LASSO, first results |
| Sun 6 Dec | Neural net + GP on residuals |
| Sun 13 Dec | PCA + k-means, all figures, paper draft |
| Week of 14 Dec | Reproduction test in Nuvolos (fresh clone, follow README) |
| Sun 20 Dec | Recording, README, submit repo URL + commit SHA |

Cut order if late: neural net first, then k-means. Never the baselines or the out-of-time test.

# Working style
- Reader is an expert (Master in Finance; strong in statistics and regression): explanations are terse and use the technical keywords.
- Gauthier works 60% alongside two courses: prefer the smallest step that moves the project forward and flag scope creep.
- Be direct when an idea is weak or a result is not what it seems.
- Report the numbers that matter, not whole outputs.
- State each method's assumptions and check them on the data.
- English everywhere in the repo.

# Gotchas
- (none yet; add one only when a mistake repeats)
