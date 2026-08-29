# B1–B4 — where the reported alert lead time comes from

**One mechanism explains the contradiction, and it is not the one we went looking for.**
Table 2 reports a 21–24 minute median alert lead. A6 reports that the whole median net score
rise sits in the final 5 minutes. B1 was written to test the obvious reconciliation — that
detected cases were already above threshold when monitoring began — and that hypothesis
fails: prevalent alerts are 2.6–25.5% of detections and the median lead survives their
removal almost intact. What B1 found instead is that **76%, 83% and 67% of the transformer's
detected event alerts fire within the first five minutes of monitoring**, while the input
window is still filling. Those crossings are incident by the letter of the definition and
carry a long nominal lead, but nothing about the patient changed. B3 and B4 then show the
same plateau accounting for the transformer's near-zero directedness and for the control
side, not the event side, supplying most of its event–control divergence.

**B1b then corrected the first draft of this report.** Suppressing the warm-up window is
not a remedy — it costs 4 to 7 points of sensitivity and buys almost no specificity, in
every family — because the elevation persists well past those minutes. The finding that
survives is sharper and is not confined to one model: **the transformer alerts at 90 to 94%
of the way back to the start of its own observed window, with its lead correlating with
that window's length at ρ = 0.71 to 0.91**, and the ratio is 0.46 to 0.94 across all five
families. Median alert lead time, at these operating points, is substantially a measure of
how long the patient was watched.

Every number below is in `collect_results/b_results_long.csv`. Nothing was retrained, no
threshold was reselected, and no published number moved.

---

## B1 — prevalent, warm-up, and settled alerts

Thresholds are the validation-fixed raw-score cuts at the 70%, 80% and 90% case-level
sensitivity targets, read from `pre_submission_revision_2026` and transported unchanged. A
detected event case's first crossing is **prevalent** if the score was already at or above
threshold at the case's first eligible scored minute, **incident** otherwise. Elapsed
monitoring time at the crossing splits the incident alerts further: a **warm-up** crossing
happens at or before minute 5 of monitoring, a **settled** crossing later.

At the 80% target, held-out MOVER (EPIC) / VitalDB / MOVER (SIS), transformer:

| Quantity | MOVER (EPIC) | VitalDB | MOVER (SIS) |
|---|---:|---:|---:|
| Detected event cases | 611 | 684 | 926 |
| Prevalent | 8.7% (6.7–11.0) | 9.6% (7.5–12.0) | 9.0% (7.2–10.8) |
| Warm-up (≤5 min into monitoring) | **76.4%** | **82.9%** | **67.2%** |
| Settled | 14.9% | 7.5% | 23.9% |
| Median lead, all detected (published) | 24 | 17 | 22 |
| Median lead, incident only | 21 (19–24) | 15 (13–17) | 19 (17–21) |
| Median lead, settled only | 17 (13–22) | 26 (19–33) | 21 (18–24) |
| Median elapsed monitoring at crossing | 1 min | 1 min | 3 min |

**The prevalent-alert hypothesis fails, and must be reported as failing.** Restricting to
incident alerts costs 0–3 minutes of median lead in every one of the 15 family-by-cohort
cells. Under the stricter `record` definition — first scored minute of the whole case rather
than of the 60-minute window — the transformer's and LSTM's prevalent fraction is exactly
zero, because at the very first scored minute their score is ~0.53 for every case.

**The warm-up split is where the lead time actually comes from, for the two sequence
families.** Median score by minutes elapsed since each record's first scored minute, MOVER
(EPIC), event and control cases separately:

| Family | Group | min 0 | min 1 | min 2 | min 3 | min 5 | min 10 |
|---|---|---:|---:|---:|---:|---:|---:|
| Transformer | control | 0.530 | 0.938 | 0.967 | 0.971 | 0.973 | 0.974 |
| Transformer | event | 0.541 | 0.951 | 0.972 | 0.974 | 0.975 | 0.975 |
| LSTM | control | 0.528 | 0.684 | 0.807 | 0.885 | 0.957 | 0.985 |
| LSTM | event | 0.528 | 0.841 | 0.908 | 0.951 | 0.976 | 0.991 |
| XGBoost | control | 0.399 | 0.399 | 0.372 | 0.352 | 0.337 | 0.297 |
| XGBoost | event | 0.470 | 0.470 | 0.442 | 0.430 | 0.404 | 0.371 |

The transformer's raw score climbs to ~0.97 within two minutes of the first scored minute
**and does so equally in event and control cases** — 0.974 against 0.975 at minute 5. The
80%-target threshold is 0.894, so it is crossed almost immediately by nearly every case, in
both groups. The LOCF tabular families show no such profile; their warm-up fraction is
10.5–17.3%.

This is not an artefact of the analysis. It is what the deployed pipeline emits when it
starts scoring at the end of the induction exclusion, and it explains a number already in the
manuscript: the transformer's median time to a control's first false alert is 1 minute
against XGBoost's 11.5.

**Controls.** 17.6%, 14.4% and 9.3% of control cases are flagged at their own first eligible
minute. Counting prevalent and warm-up together, **90.5%, 92.3% and 72.6% of the transformer's
alerting controls were flagged on arrival or during warm-up** — against 25.6%, 16.3% and 20.2%
for XGBoost.

**Where prevalent alerts concentrate.** Cross-tabulated by observable run-up band and by A3
starting-score decile in `b1_crosstab.csv`. The decile relation is partly mechanical, since
prevalence is defined by the level at the window's first minute, and is reported as
concentration rather than as an independent association.

---

## B1b — suppression is not the remedy, and what the lead actually measures

Two things had to be checked before B1's warm-up split could be interpreted, and the first
of them **falsified the reading in the first draft of this report**.

**Suppressing the warm-up window does not fix the operating point.** B1's `settled` fraction
classifies each case by its *first* crossing, so it is a lower bound on post-suppression
sensitivity, not the answer. Running the actual rule — discard every minute at or before *N*
minutes of elapsed monitoring, then apply the unchanged threshold to the remainder — gives,
at *N* = 5 and across all five families: **4 to 7 points of case-level sensitivity lost, 0 to
2 points of specificity gained, 0 to 3 minutes of median lead lost.** `N = 0` reproduces
Table 2 exactly (transformer 0.777 / 0.406 / 24 min), which is what makes the column
comparable to it. So the elevation is not confined to the first minutes; suppression only
trades sensitivity away, and the earlier statement in this report that a warm-up suppression
rule "is also the obvious remedy" was wrong and is withdrawn.

**Which sharpens the question: if the lead survives both the removal of prevalent alerts and
the removal of the first minutes, what is it measuring?** For each detected event case,
compare its lead with the length of its own observed pre-onset window, capped at the
60-minute alert window:

| Model | Cohort | n | Median lead | Median window | Lead / window (95% CI) | Spearman (95% CI) |
|---|---|---:|---:|---:|---|---|
| Transformer | MOVER (EPIC) | 611 | 24 | 32 | **0.94 (0.94–0.95)** | 0.71 (0.63–0.79) |
| Transformer | VitalDB | 684 | 17 | 20 | **0.92 (0.91–0.93)** | 0.91 (0.86–0.95) |
| Transformer | MOVER (SIS) | 926 | 22 | 29 | **0.90 (0.88–0.91)** | 0.80 (0.75–0.85) |
| LSTM | MOVER (EPIC) | 634 | 23 | 35 | 0.85 (0.83–0.87) | 0.65 (0.58–0.72) |
| XGBoost | MOVER (EPIC) | 637 | 21 | 47 | 0.72 (0.67–0.77) | 0.56 (0.50–0.62) |
| XGBoost | VitalDB | 699 | 13 | 52 | 0.47 (0.40–0.52) | 0.60 (0.55–0.65) |
| Random forest | MOVER (SIS) | 1,196 | 22 | 60 | 0.67 (0.62–0.70) | 0.62 (0.58–0.66) |
| Logistic regression | VitalDB | 464 | 14 | 48 | 0.46 (0.39–0.51) | 0.61 (0.54–0.67) |

**The transformer alerts at 90 to 94% of the way back to the start of its own observed
window, and its lead correlates with that window's length at ρ = 0.71 to 0.91.** It alerts
almost as soon as it is switched on, so its reported median lead is close to a restatement of
how long the patient was watched before the event.

**This is not confined to one family.** The ratio is 0.46 to 0.94 and the Spearman
correlation 0.50 to 0.91 across all fifteen cells, every interval excluding zero. Median
alert lead time, at these transported operating points, is substantially a measure of
observation length for every model tested — most extremely for the transformer, and least for
XGBoost and logistic regression in VitalDB.

The share of monitored minutes spent at or above threshold says the same thing from the other
side: 20 to 52% for the transformer's event cases and 2.5 to 18% of its control minutes,
against 0 to 17% and 0% for the tabular families. A score that sits above threshold for half
the window has a first crossing determined by when the window opened.

**This supersedes the warm-up framing as the headline.** Warm-up is why the first crossing is
so early; the persistent elevation is why suppressing warm-up does not help; and the
lead-to-window ratio is the quantity that states the consequence for the reported metric.

---

## B2 — score departure against MAP departure

Event episodes with at least 30 observed pre-onset minutes; retention 406/786, 579/1,007 and
883/1,409. Baseline is the median over an episode's first 10 eligible minutes, the robust
scale is 1.4826 × MAD over the same minutes, and departure is the first minute beginning a
run of at least 3 consecutive minutes more than 1.5 scale units into the deteriorating
direction. Transformer and XGBoost only, per the tiering rule: this is a mechanism question.

**The permitted claim is temporal precedence under the stated rule. Nothing here is evidence
that the model anticipates physiology; the outcome is defined on MAP and MAP is an input.**

| Family | Cohort | Neither | Score only | MAP only | Both | Median difference, min | Score first |
|---|---|---:|---:|---:|---:|---:|---:|
| Transformer | MOVER (EPIC) | 30.5% | 2.0% | 57.4% | 10.1% | 0 | 43.9% (q=0.81) |
| Transformer | VitalDB | 19.0% | 0.7% | 69.6% | 10.7% | +3.5 | 67.7% (q=0.012) |
| Transformer | MOVER (SIS) | 25.3% | 0.9% | 59.8% | 14.0% | 0 | 46.8% (q=0.85) |
| XGBoost | MOVER (EPIC) | 23.9% | 10.1% | 12.1% | 55.4% | −1 | 26.7% (q=0.003) |
| XGBoost | VitalDB | 10.0% | 9.7% | 1.9% | 78.4% | 0 | 34.4% (q=0.003) |
| XGBoost | MOVER (SIS) | 16.8% | 6.7% | 6.0% | 67.8% | 0 | 35.2% (q=0.003) |

**Score departure does not precede MAP departure.** For XGBoost the share departing first is
significantly *below* one half in all three cohorts. For the transformer the score never
departs at all in 85% to 89% of episodes, and among the minority where both depart there is
no consistent order.

The reason the transformer almost never departs is the same warm-up plateau. Its median
baseline score is 0.94–0.97 with median headroom of 0.005–0.031, and **61–91% of episodes
have a baseline already above the 80%-target alert threshold**. A score that starts pinned
near the ceiling cannot depart upward, however low the bar — and its bar is 22× lower than
XGBoost's, because the plateau is flat. Both facts are tabulated in the module report so the
negative result cannot be read as the rule being unfair to one family.

Sensitivity: a 2.0-scale threshold, a 5-minute run, and a search capped at the published
60-minute window all leave the direction unchanged.

---

## B3 — is the path shape the transformer's, or the task's?

Read from `a6_window_trend.csv`; nothing recomputed. Event episodes, spanning sample, window
start 60 minutes, median step count 10–11 so nothing is excluded by the ≥3-step filter.

**Directedness intervals do not overlap across all five families** — in 5 of the 6
cohort-by-window cells at least one pair separates. So the shape is not simply a property of
the task. But the *kind* of shape is shared: over the 60-to-5-minute window, directedness is
between +0.02 and +0.15 for every family in every cohort, meaning 2–15% of the distance
travelled converts into displacement. Every family's trajectory is closer to a random walk
than to a climb. Over 60 to 10 minutes the transformer falls to 0.000 in held-out MOVER
(EPIC) and VitalDB while every other family stays positive.

The ordering is transformer < LSTM < XGBoost ≈ random forest ≈ logistic regression, and it
**contradicts the near-onset AUROC ordering**, on which the transformer is first or second.

| 60→5 window | MOVER (EPIC) | VitalDB | MOVER (SIS) |
|---|---|---|---|
| Transformer directedness | +0.025 (0.002–0.050) | +0.021 (0.005–0.038) | +0.089 (0.066–0.122) |
| Logistic regression | +0.061 (0.044–0.089) | +0.088 (0.063–0.108) | +0.134 (0.119–0.154) |
| Transformer path per unit net | 41 | **147** | 13 |
| Logistic regression path per unit net | 18 | 13 | 8 |

`path_per_net` is the quantity that reconciles B1 with A6. A series that travels 41–147 score
units for every unit of net displacement will touch a high threshold early without trending
toward it. The lead time is a first-passage time of a volatile series, not the crossing of a
rising one.

**Last-5-minute concentration is a matter of degree, present in every family, extreme in the
transformer.** The share of the 60→5 net rise that exists only when the final 5 minutes are
included: transformer 100%, 59%, 100%; other families 18–88%. It should not be described as a
defect of one architecture — but it is not family-invariant either, and the transformer is the
limiting case.

---

## B4 — which side of the event–control gap moves

Fixed sample: episodes with an observed bin at every centre from 60 to 5 minutes. The gap at
each bin is decomposed against each side's own 60-minute baseline, so
`gap(t) − gap(60) = [E(t) − E(60)] − [C(t) − C(60)]` and the two shares sum to 1.

At 5 minutes before the reference time:

| Family | Cohort | Event side | Control side | Event share | Control share |
|---|---|---:|---:|---:|---:|
| Transformer | MOVER (EPIC) | +0.052 | −0.274 | **0.16** | **0.84** |
| Transformer | VitalDB | +0.036 | −0.267 | **0.12** | **0.88** |
| Transformer | MOVER (SIS) | +0.153 | −0.194 | 0.44 | 0.56 |
| XGBoost | MOVER (EPIC) | +0.130 | −0.095 | 0.58 | 0.42 |
| XGBoost | VitalDB | +0.183 | −0.006 | 0.97 | 0.03 |
| XGBoost | MOVER (SIS) | +0.276 | +0.007 | 1.02 | −0.02 |
| Random forest | VitalDB | +0.167 | +0.001 | 1.01 | −0.01 |
| Logistic regression | MOVER (SIS) | +0.195 | +0.013 | 1.07 | −0.07 |

**For the transformer, 84% and 88% of the divergence in the two larger cohorts is the control
side falling, not the event side rising** (q=0.003 against an even split); in MOVER (SIS) it
is 56%. For XGBoost, random forest and logistic regression the event side supplies 58% to
107% — 97% to 107% in the two external cohorts, but 58% to 69% in held-out MOVER (EPIC),
where the control side still contributes about a third. Figure 3C plots the transformer, so the figure a reader
sees is the one case where the divergence is mostly the controls coming down from the warm-up
plateau.

A gap that widens because controls fall is still a real gap — discrimination is a
between-group statement — but it is not evidence that the score tracks an approaching event.

---

## What is not claimed

- No model was retrained, refitted or re-scored. No threshold, split, seed or operating point
  was reselected.
- No published number changed. `step0_repro.py` reproduces Table 2 three ways and asserts
  A6's transformer path values before any B step runs; 52 of 52 checks pass.
- B2's finding is about the order of two departures under one rule, not about physiology.
- The warm-up plateau is a property of the pipeline as deployed with this scoring policy, not
  a claim about the architecture in general. It is **not** offered as something a warm-up
  suppression rule would fix: B1b ran that rule and it does not (see B1b).
- No claim is made that a different operating point, threshold rule or alert-persistence
  requirement would behave the same way. Only the published transported operating points
  were evaluated.

## Multiplicity and seeds

B1–B4 are one Benjamini–Hochberg family of 93 tests, 35 significant at q<0.05, **not** pooled
with the 21-trajectory, 15-orientation, or A1–A5 families. Resampling used base seed 20260706
with offsets 100,000–130,000.

Three resampling bases coexist: a previously published analysis states 20260706 as its
default, records 20260729 for the truncated-window orientation family, and uses 20260729
throughout, while its main-text methods state 20260706 alone. This is **reported, not
harmonised** — rerunning the published families on one base would move *q* values that are
already published.
