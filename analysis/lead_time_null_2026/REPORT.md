# N1–N3 — is the lead-to-window relationship anything more than arithmetic?

**Bottom line: the objection does not survive, and N2 converts the finding from a
correlation into a null result.** A cross-case shuffle that destroys every trace of the
individual patient reproduces the reported lead-to-window relationship in full — median
ratio 0.72–0.97 and Spearman 0.63–0.94 — against observed values of 0.455–0.944 and
0.501–0.906. Nothing about the patient is needed to generate the number that is read as
warning time.

N3 is the legible form and should lead the Results: median lead rises from the shortest to
the longest quintile of observed window in **15 of 15** cells, by **+26 to +54 minutes**, at
**0.51 to 1.02 minutes of reported lead per minute of observation**. On the transformer in
VitalDB the slope is 1.02 — one extra minute of watching buys one extra minute of "lead".

Post-hoc on cached per-minute scores. No model was trained, refitted or re-scored; no
threshold, split, seed or operating point was reselected. `step0_repro` passes 105/105, and
both upstream gates still pass unchanged (B 52/52, A 108/108).

---

## The objection

B1b reported that median alert lead time is substantially a measure of observation length:
ratio 0.455–0.944, Spearman 0.501–0.906, all fifteen family-by-cohort cells, every interval
excluding zero. The weak link is that lead is bounded above by the observed window, so the
ratio lives in [0, 1] by construction and a positive correlation is partly structural. An
ML reviewer raises this immediately. N1–N3 answer it three ways.

## N1 — a crossing placed at random

Placing the crossing uniformly inside each case's own window gives a median ratio of 0.5 by
construction, which fixes the reference point. Excess over that null runs **−0.067 to
+0.421**.

The transformer is far above it (+0.372 to +0.421). But **2 of 15 cells sit below the
uniform null** — XGBoost on VitalDB (−0.054) and logistic regression on VitalDB (−0.067) —
and random forest on VitalDB is indistinguishable from it (+0.011, p = 0.824). So the
crudest reading is ruled out for most cells and not for all, and the paper says so.

N1 is necessary but weak alone. It cannot tell a ratio that reflects case-specific timing
from one that is a property of the scoring policy.

## N2 — the shuffle, and the result that decides the framing

Whole score sequences are permuted across cases. Each recipient keeps its own window
length, reference time and denominator; only the sequence comes from somebody else. The
crossing is recomputed against the unchanged transported threshold. Donors are laid on by
elapsed minutes from the start of the recipient's own window, so the generic profile —
including the plateau — survives and only case-specific information is destroyed. 1,000
derangements per cell, two length-mismatch variants.

**Observed sits at or below the shuffle null in all 15 cells on the primary variant**
(excess −0.267 to −0.025) and in 14 of 15 on the sensitivity variant (−0.151 to +0.016,
with 4 cells not distinguishable from the null). The null's median ratio is 0.72–0.97
(primary) and 0.58–0.96 (sensitivity).

The Spearman is the sharper result. On the sensitivity variant the observed correlation is
**not distinguishable from the shuffle null in 9 of 15 cells**, and in 9 cells the null is
*higher* than the observed value. The transformer's headline ρ = 0.71–0.91 is matched by a
null of 0.78–0.93.

**Reading.** This is the outcome that states the claim as a null result: alert timing
carries essentially no case-specific information, and the lead-to-window relationship is a
property of the scoring policy interacting with the observation window. It is stronger than
"the shuffled value is close to observed" — the shuffled value slightly *exceeds* it.

**Two things must be reported with it, and are.** First, the small negative excess means the
real sequences delay the crossing a little relative to random ones: there is some
case-specific information and it acts to *postpone* alerts, not to generate them. Second,
both variants bias the null **upward** — `longer` because a long donor's window starts
mid-case where the score is already plateaued, `hold` because a held plateau value sustains
a crossing across the recipient's tail. Upward bias is the direction that makes agreement
easier to obtain, which is the direction that favours the paper's own reading. The null is
therefore best read as a **ceiling**, not a point estimate, and the two variants bracket it.

## N3 — median lead inside quintiles of window length

Stratifying takes the ratio out of the argument. Inside a quintile the window is nearly
constant, so median **absolute lead in minutes** is directly comparable.

| Transformer | Q1 window → lead | Q5 window → lead | Slope |
|---|---|---|---|
| MOVER (EPIC) test | 10 min → **9 min** | 60 min → **46 min** | 0.74 |
| VitalDB | 7 min → **5 min** | 60 min → **59 min** | 1.02 |
| MOVER (SIS) | 8 min → **6 min** | 60 min → **46 min** | 0.77 |

All fifteen cells rise; the slope runs 0.51–1.02. The published headline of 17–24 minutes
of median lead is an average over a window-length distribution, not a property of the
model: the same model on the same cohort reports 5–9 minutes for its shortest-observed
quintile and 46–59 for its longest.

Quintile edges are cut within cell. Where the window is censored at the 60-minute alert-
window cap the upper quintiles collapse; `n3_summary.csv` reports the realised band count
(3 to 5) rather than assuming five.

## Multiplicity

N1–N3 are a new Benjamini–Hochberg family of **75 formal tests, 57 significant at q < 0.05**,
adjusted within N alone. Not pooled with the 21-trajectory, 15-orientation, A1–A5 or B1–B4
families — pooling would move *q* values already in the manuscript. N3 produces intervals
rather than tests and does not enter the family. Base seed 20260706 with offsets
140,000–170,000, chosen to collide with neither the A block (≤90,000) nor the B block
(100,000–130,000).

## Files

| Step | Script | Output |
|---|---|---|
| gate | `step0_repro.py` | `step0_repro/step0_repro.csv` — 105 checks |
| N1 | `n1_uniform_placement.py` | `n1_uniform_placement/n1_uniform_placement.csv` |
| N2 | `n2_score_shuffle.py` | `n2_score_shuffle/n2_score_shuffle.csv` |
| N3 | `n3_stratified.py` | `n3_stratified/n3_strata.csv`, `n3_summary.csv` |
| figure | `make_figure_lead_vs_window.py` | `figures/Figure_lead_vs_window_{wide,narrow}.pdf` |
| roll-up | `collect_results.py` | `collect_results/n_results_long.csv` — 233 quantities |

Run with `bash run_all.sh` after activating the `torch` environment. Do not wrap it in
`conda run -n torch bash -lc` — the login shell re-runs conda init and resolves `python` to
base.
