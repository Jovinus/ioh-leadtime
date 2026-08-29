# Twenty-four minutes of warning — analysis code

Code for the workshop paper *Twenty-four minutes of warning: what a reported lead time
licenses, and what reporting standards do not ask*. The paper as submitted is `paper.pdf`.

**No patient data is included in this repository, and none can be.** See
[Data](#data-and-why-none-of-it-is-here).

Licensed under the Apache License 2.0; see `LICENSE`.

## What the paper does, and what this code is

Five model families (ITE Transformer, LSTM, XGBoost, random forest, logistic regression) were
trained once to predict intraoperative hypotension and scored at every eligible minute of every
case in three perioperative cohorts. Everything the paper reports is **post-hoc on those cached
per-minute scores**: no model is retrained, refitted or re-scored anywhere in this tree, and no
threshold, split, seed or operating point is reselected.

| Directory | What it holds |
|---|---|
| `ioh_prediction/` | The model, the dataset/collate layer, and the deployment-simulation evaluation harness (time-window metrics, alert simulation, calibration, bootstrap) |
| `scripts/` | Training and external-evaluation entry points that produced the cached scores |
| `configs/` | Experiment configurations |
| `analysis/lead_time_origin_2026/` | Where a reported lead time comes from: lead against observed window, suppression checks (module B) |
| `analysis/lead_time_null_2026/` | Whether the lead-to-window relationship is more than arithmetic: uniform-placement and score-shuffle nulls, window-stratified leads, the two repairs (module N) |
| `analysis/patient_trajectory_2026/` | The three trajectory and observability steps this paper reads: event-versus-control divergence, the window-start sweep, and observable run-up length (module A) |
| `analysis/ioh_faithfulness_2026/lib.py` | Shared helper the analysis modules import: the highest-identifiable-cluster attachment, table-to-Markdown rendering, and the run-manifest writer |
| `analysis/conference_rcmlr_leadtime/` | The manuscript itself (`PAPER.md`), its LaTeX build, its figures, and the gates below |
| `tests/` | Unit tests for the split, eligibility and evaluation code |

## What reproduces what

| Paper object | Produced by | Reads |
|---|---|---|
| Figure 1, Figure A1 | `analysis/lead_time_null_2026/make_figure_lead_vs_window.py` | `n3_strata.csv`, `n2_score_shuffle.csv`, per-case leads recomputed from cached scores |
| Figures 2, A2, A3, A4 | `analysis/conference_rcmlr_leadtime/build_conf_figures.py` | `b1_score_profile.csv`, `b1_summary.csv`, `a7_auroc_by_sample.csv`, `a4_event_control_means.csv` |
| Table 1 and Tables A1–A12 | parsed from `PAPER.md` | the aggregate CSVs shipped beside each module |
| `main.pdf` | `analysis/conference_rcmlr_leadtime/latex/build_tex.py`, then `tectonic` | `PAPER.md`, `references.bib`, the figure PNGs |

The aggregate result CSVs are included, so the tables and the figures can be checked without
any data access. The per-minute score files cannot be included, so the stages that recompute
per-case leads cannot be re-executed here.

### Gates

Two of the paper's gates run against this tree as shipped:

```bash
cd analysis/conference_rcmlr_leadtime
python verify_tables.py     # 1583/1583 table cells agree with their source CSVs
python check_phrases.py     # terminology check over the manuscript sources
```

`verify_numbers.py` asserts that every number in the prose agrees with its source CSV. Most of
its checks read the shipped aggregate CSVs, but some recompute from the cached per-minute
scores, so it stops with a missing-file error on a tree without them. `measure_pages.py`
compiles page-count variants and needs a LaTeX engine (`tectonic`).

This tree carries the code the paper's results are made of, not every module of the wider
project it was developed in. Modules and scripts that produce internal run reports, and
analysis steps whose outputs this paper does not read, are not included.

## Data, and why none of it is here

Neither dataset may be redistributed, so neither is included and no derived per-patient file is
either. Both are obtained directly from their own project sites once access is granted:

- **VitalDB** — Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International, plus a
  data use agreement. Available from the VitalDB project site.
- **MOVER** — a data use agreement. Available from the UCI Machine Learning Repository; one
  download supplies both arms used in the paper.

Both cohorts are public, de-identified datasets obtained from their providers under the access
and license terms above. An institutional review board granted this secondary analysis an
exemption from review and a waiver of consent; its identity and protocol number are withheld for
anonymous review. This work added no data collection and no patient contact.

What is excluded for that reason: the per-minute vitals parquets, the cached per-minute model
scores (`outputs/runs/*/predictions/`), the fitted calibrators, and every case- or
episode-level table. What is included: aggregate result CSVs at the level of model family ×
cohort × time bin, which contain no patient rows.

## Environment

Python 3.13.5. PyTorch 2.10.0, scikit-learn 1.7.1, XGBoost 3.3.0, NumPy 2.2.6, pandas 2.3.2,
SciPy 1.16.1, pymannkendall 1.4.3, matplotlib 3.10.8.

```bash
conda env create -f environment.yml
# or
pip install -r requirements.txt
```

Seeds are fixed, not searched. The subject-aware train/validation/test split uses seed 1004.
Resampling uses 20260706 by default, with 20260729 for the truncated-window orientation family
and per-cell offsets recorded in each step's `run_manifest.json`. Every module writes a
`run_manifest.json` beside its outputs recording the seeds, the bootstrap count, the resampling
unit and the library versions it ran under.

Figure builds pin matplotlib 3.10.8; a different minor version changes text extents and
therefore the figure bytes.
