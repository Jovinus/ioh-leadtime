---
title: "What a median alert lead time measures: a reporting gap in continuously evaluated clinical models"
---

<!--
PAPER.md is the single source of truth. PAPER_REVIEW.md, PAPER.docx, latex/body.tex and
latex/main.pdf are all generated. Edits go here, then ./render.sh.

Every number below is verified against its source CSV by verify_numbers.py. Do not
transcribe from a REPORT.md.
-->

# Abstract

A median alert lead time is read as a statement about the model: how much warning it gives. It
is also a statement about the cohort, because the first threshold crossing can only be found
inside the pre-onset window each patient happened to supply, so the same model reports a longer
lead wherever patients are watched longer. A single median cannot separate the two, which makes
this a reporting problem before it is a modelling one.

That a lead time cannot exceed its search window is definitional; what has not been measured is
how much of a reported number that window accounts for. Across three perioperative cohorts and
five model families, at thresholds transported unchanged from a development validation split,
median lead rises from the shortest to the longest realized pre-onset window group in all
fifteen model-by-cohort combinations, by 26 to 54 minutes. Read beside its operating point, the
longest median lead here, 24 minutes, comes from the combination with the lowest case-level
specificity, 0.406. Two natural repairs leave the dependence in place.

This is an empirical measurement-and-reporting case study; we do not measure what clinicians
understand from the term. A median lead remains a descriptive interval among detected cases,
but on its own it does not support a model-intrinsic or cohort-comparable reading of warning
capability. We recommend reporting the pre-onset window distribution, the operating point, and
a window-conditional or fixed-horizon timing measure beside any single median, and set out four
candidate disclosures, a task-specific complement to TRIPOD+AI.

# 1 Introduction

**Why a warning interval matters here.** Mean arterial pressure is the average arterial pressure
over one heartbeat, and it is the number an anesthetist watches most closely during an operation.
When it falls below roughly 65 mmHg and stays there the episode is intraoperative hypotension, and
how much a patient accumulates is associated with kidney and myocardial injury after surgery
[@walsh2013map; @salmasi2017ioh; @wesselink2018ioh; @sessler2019poqi]. The responses are ordinary
anesthetic care, and none acts the instant it is chosen, so a warning interval is worth something
to the extent that it is time in which a clinician can choose and deliver one. That is why
monitors here are marketed and evaluated on how far ahead they alert [@hatib2018hpi;
@davies2020hpi; @wijnberge2020hype; @maheshwari2020hpi]. This paper is about that reported interval
and not about physiology: the outcome is defined on mean arterial pressure, which is also a model
input, and Section 4.2 says what that does and does not license.

A model that is read continuously is asked how early it warns, and the **median alert lead time**
is the statistic reported in answer across acute care: the interval between the first minute a
case's score crosses an alert threshold and the onset of the event. We have not surveyed how often
it is reported, so what follows is a multi-cohort case study rather than a field-level audit. It appears across acute care, for sepsis
[@wong2021sepsis], for acute kidney injury [@lee2026aki], and for intraoperative hypotension,
where a commercial index is marketed on the interval between its alert and the event. The statement
that a system has a **median alert lead time of 24 minutes** invites the reading that it will
usually give around twenty-four minutes of warning, and that reading is what makes the number worth
reporting. We study the correspondence between the statistic and that invited reading; we do not
measure clinician comprehension directly.

The definition is the same in every one of those settings, and it carries a dependence that
its name conceals. Score every eligible minute, compare against a threshold, and record the
interval between the first crossing and the event. The first crossing is searched for inside
the interval the patient was observed, so the lead is bounded above by the observation
window. The available run-up to onset is set by event timing relative to eligibility, by
monitoring practice and by case mix rather than by the model.

**What is already known, and what is new here.** Criticism of early-warning evaluation is not
new: the C-statistic has been argued uninformative for early warning scores, with per-alert and
workload measures proposed instead [@romerobrufau2015cstatistic]; monitor alerting has been
quantified as a per-hour burden [@paine2016alerts]; choice of evaluation sample moves reported
performance for this exact task on these public data [@yang2025selection]; and cross-center
evaluation separates learned methods from pressure-derived rules far less cleanly than
single-center reports suggest [@chaari2026crosscenter]. That a lead time cannot exceed the window
it is searched in is likewise definitional, and Section 3.3 treats it as such. What is not
established is **how much of a reported lead time is the window**, and the substitutes those
critiques recommend are what Section 6.2's second item asks for.

**We make four contributions.** We measure the dependence, in the metric's own units and against
two explicit references rather than against the ceiling (Section 3). We report the operating point
beside the lead, which no lead-time statistic carries, and find the two run opposite to one another
across combinations (Section 4). We implement the two repairs the first two sections invite and
neither works, while a window-conditional statistic that does work disagrees with the median
(Section 5). And we map the case study onto an author-completed TRIPOD+AI
[@collins2024tripodai] checklist, which did not request the disclosures that would have made any
of this visible, and propose four candidate additions for continuously monitored models
(Section 6). The argument is about a reported quantity, not about how well any model discriminates,
which is not in dispute here.

# 2 Setting

**Task and outcome.** Intraoperative hypotension is mean arterial pressure below 65 mmHg sustained
for at least three consecutive minutes, the conventional threshold in this literature
[@walsh2013map; @salmasi2017ioh; @sessler2019poqi]. Mean arterial pressure is also one of the
models' input channels, so the label is computed from a signal the models read; Sections 4.2 and 7
say what that does not license.


**Cohorts.** Development used MOVER's EPIC arm; we evaluate on its held-out test split (1,404
cases, 786 with a sustained event) and on two external cohorts, VitalDB [@lee2022vitaldb;
@lee2022vitaldbdataset] with 2,804 cases and 1,007 events, and the SIS-derived arm of MOVER
[@samad2023mover; @samad2023moverdataset] with 2,641 cases and 1,409 events. MOVER (SIS)
releases no usable subject key, so cases are the clustering unit there and subjects in the other
two; all intervals in this paper are 95% cluster bootstrap on that unit unless a caption says
otherwise.

**Models.** Five families, spanning the range a clinical team would realistically compare: a
transformer over irregularly sampled triplets [@tipirneni2022strats], referred to throughout as
the ITE Transformer, an LSTM, XGBoost, random forest and logistic regression. Two read the
window as a sequence and three a per-minute feature vector; Appendix A.1 has the architectures
and training. No model is proposed for clinical use and none of what follows is a ranking.

**Deployment simulation.** Every model is read forward at **every eligible minute of every
case**, using only measurements recorded strictly before the prediction minute and after a
source-specific exclusion for the induction artifact (Appendix A.1), so a 1,404-case cohort yields
tens of thousands of scored case-minutes from cached data after the fact.

**Operating points.** An **operating point** is the score threshold at which the system is read as
alerting, with the sensitivity and specificity that follow. **Case-level sensitivity** is the share
of event cases that alert at some point in their alert window and **case-level specificity** the
share of control cases that never do. Calibration and thresholds were fitted on the development
cohort's validation split at an 80% case-level sensitivity target and then **transported**
unchanged, applied to every other cohort as fitted rather than re-estimated there. Nothing here
reselects a threshold, split, seed or operating point, and no model is retrained or re-scored.

**The alert rule and the window it searches.** A case alerts if its score reaches the threshold
at any minute in the 60 minutes before the event, and its lead time is the interval from the
first such minute to the event. The interval the rule searches is the case's **available
pre-onset evaluation window**: its realized observable run-up to onset, after the induction
exclusion, capped at the 60-minute alert window. A short window is therefore not a briefly or
incompletely monitored case. For an event case it means the event arrived early in the record,
so the run-up *is* the time to onset and there is no missing data to recover. An alert already active at a case's first eligible minute is **prevalent**; one that
begins later is **incident**. Cases without an event take a sampled pseudo-onset drawn from the
event cases' timing distribution, so controls are scored over a comparable window. Every lead
time reported here uses this rule unchanged.

**Ethics.** An institutional review board granted an exemption from review and waived consent for
this secondary analysis (Appendix A.1).

# 3 Lead time tracks the available pre-onset window

## 3.1 The number moves with the window, in minutes

This section splits detected cases by the length of their available pre-onset window and reads the
median lead separately in each group, which puts the dependence in the metric's own units.

**The reported lead time moves with the group** (Table A9), the same way in every cell. Median
lead rises from the shortest to the longest realized band in **15 of 15** model-by-cohort cells,
by **+26 to +54 minutes**, every interval excluding zero (Table A1), an endpoint contrast of
**0.51 to 1.02 minutes of lead per minute of window difference**. A single headline figure
therefore describes the cohort's observation-length distribution as much as the model: across
its three cohorts the transformer reports 5 to 9 minutes of median lead for its shortest-observed
band and 46 to 59 for its longest, and the pooled 17 to 24 minutes sits between them because
that is where the median case happens to fall.

**Detection is itself a function of window length, so we report that rate rather than conditioning
on it silently.** Re-cut on all event cases, the detected share moves with window length in every
cell, by 0.105 to 0.556, falling in the two families that read the window as a sequence and rising
in the three that read a per-minute vector (Table A5). For the transformer the selection runs
*against* the reported gradient, which survives it; for the tabular families it runs with the
gradient, so part of theirs may be survivorship.


## 3.2 The same fact as a ratio, in every family

Section 3.1 gives the dependence in minutes; as a fraction of each case's own window it separates
what is universal here from what is model-dependent.

**The gradient is universal; its magnitude is not.** The median ratio of a case's lead to its own
observed window is 0.455 to 0.944 and the Spearman correlation between lead and window length is
0.501 to 0.906 across all fifteen cells, again with no interval covering zero. The transformer is the
limiting case at 0.899 to 0.944 with ρ = 0.706 to 0.906, its first alert falling 90 to 94% of the
way back to the start of the window it was given; the mildest cells are logistic regression in
VitalDB (0.455) and XGBoost in VitalDB (0.467), where the first alert falls closer to the middle
of the window than to its start. The direction holds in every family and cohort while the strength
ranges from near-total to moderate, so a claim that the quantity *is* the window fits the
transformer and overstates the tabular families.

![](figures/Figure_2_wide.png)

**Figure 1 | Alert lead time against the available pre-onset window.** Every detected event case
under the ITE Transformer, three held-out cohorts. The dashed diagonal is the ceiling: no crossing
can be found outside the case's own window. The shaded band is the 2.5th to 97.5th percentile
envelope of the cross-case shuffle reference, not a per-case prediction interval. Red markers are
the band medians of Table A9 with 95% cluster bootstrap intervals; all five families are
Figure A1.

## 3.3 Explicit references for the ceiling dependence

Part of the relationship is built into the definition: a lead time cannot exceed the window it is
searched in, so the ratio is bounded in [0, 1] by construction and positive dependence can arise
without patient-specific timing. A bound does not specify a distribution, so we use two explicit
references rather than treating the diagonal as a null.

**The interpretive rule comes before the numbers, because it decides what they can mean.** Both
references are biased *toward* agreement with the observed values, in the direction that favors our
own reading, so each is an upper bound on what a window-only process could produce. A reference
that reaches or exceeds the observed value is therefore the expected and uninformative outcome;
what would be informative is one falling clearly short, and neither does.

**A continuous uniform reference has median 0.5.** Placing a pseudo-crossing uniformly on each
case's own window gives a reference median of 0.518 to 0.534, which the observed ratio exceeds by
**+0.372 to +0.421** for the transformer. It does not exceed it everywhere: in **2 of 15** cells
the observed ratio sits *below* the reference and in one more it is indistinguishable from it, all
three VitalDB cells (Table A2).

**A cross-case shuffle preserves the aggregate relationship** (Figure 1). Each recipient keeps its
window and reference time but receives another case's whole score sequence, aligned by elapsed
window time, so generic elapsed-time shape survives while the match between trajectory and
recipient is destroyed. Permutations are derangements, 1,000 per cell, so no case keeps its own
sequence. The shuffled median ratio is **0.72 to 0.97** and
Spearman **0.63 to 0.94**, so the reference exceeds the observed ratio in **15 of 15** cells,
which under the rule above is what an upward-biased reference is expected to do. Under a
length-matched variant the observed correlation is **not distinguishable from the reference in 9
of 15 cells**, and the reference is the larger in 6 of 15 (Table A2).

**Under these deliberately conservative references the observed association did not exceed what a
window-only reassignment can produce.** That is not the same as showing that a window-only process
generates it, nor that patient-specific information is absent. Reassignment also changes which
event cases are detected, and both variants bias upward, by selecting longer, already-settled
donors or holding a short donor's last value. They bound the dependence rather than estimating a
case-independent process.

# 4 Score behavior behind the reported lead

Section 4.1 identifies a direct mechanism for one model. A cross-family property of the score
paths is consistent with it without establishing its cause, and is reported in Appendix A.4
beside Table A3.

## 4.1 The transformer is above its own alert threshold almost immediately, in event and control alike

This section asks what the score is doing at the minutes the alert rule reads, and what the
operating point behind the reported lead looks like.

**Within one minute of its first scored minute the transformer's median score is already
above the threshold its operating point uses, and it is there for event and control cases
equally** (Figure A5).

In MOVER (EPIC) the median score rises from 0.530 at the first scored minute to 0.938 one
minute later in control cases, and from 0.541 to 0.951 in event cases, against a transported
threshold of **0.894**. By minute five the two groups are at 0.973 and 0.975, a separation of
0.002 in a score whose scale runs to 1. VitalDB behaves the same way, reaching 0.966 and
0.973. MOVER (SIS) settles more slowly, at 0.833 and 0.906 by minute two and 0.942 and 0.962
by minute five, but it too clears the threshold and it too does so in both groups.

The consequence for the metric is direct. A case whose score settles above the threshold
within its first monitored minutes will register its first crossing as soon as its alert
window opens, whatever else happens, so its lead time is whatever that window holds. That is
the near one-for-one contrast in Table A9.

**No other family does this** (Figure A5). Sustained elevation is visible in the share of
monitored minutes at or above threshold: **20.0 to 52.3% of the transformer's event minutes and
2.5 to 18.3% of its control minutes, against 0 to 26.7% and 0 to 1.7% for the other four
families**.


**The obvious objection is that this model simply alerts continuously, and reporting the
operating point beside the lead shows that it largely does** (Table 1). Its case-level
specificity is 0.406, 0.379 and 0.467, so it alerts on 53 to 62% of control cases, and its
positive predictive value of 0.625, 0.380 and 0.585 sits 0.065, 0.021 and 0.051 above the
prevalence it is measured against. This is not a competing explanation of Section 3 but the same
fact: a score above threshold most of the time alerts at the first opportunity, which is what
makes the lead the window. The point is that **the reported lead carries none of it.** A median
lead of 24, 17 and 22 minutes is the largest of the fifteen combinations and comes from the one
with the least usable operating point.

That holds beyond one model. **Across the fifteen combinations the reported median lead runs
opposite to case-level specificity** (Spearman −0.803, permutation *P* = 0.0008, *q* = 0.006; 86
of 99 untied pairs), and opposite to PPV in excess of prevalence at −0.719. Within a cohort the
ordering is 9 of 9 untied pairs in both MOVER cohorts and 8 of 10 in VitalDB, but five
combinations per cohort is thin and none survives adjustment alone, so the pooled figure carries
the claim and cohort confounds it. Two further limits belong with it. The unit is a combination
and not a patient, so these are permutations of the pairing rather than cluster bootstraps. And a
transported threshold does not deliver the same realized sensitivity everywhere: it runs from
0.461 to 0.849 across these combinations (Table A4), so this is a descriptive association among
the operating points as transported, not a sensitivity-matched ranking of models. What it
supports is narrower and still worth stating: a reader ranking these systems by the number they
publish would not be ranking them by how usable their operating points are.

**Table 1 | Case-level operating point behind each reported lead time.** ITE Transformer, three
held-out cohorts, at the transported 80%-sensitivity operating point every lead time in this paper
uses. `Min. above thr.` is the median share of an event case's monitored minutes at or above
threshold. Event prevalence is a property of the cohort, not the cell: 0.560, 0.359 and 0.534.
**All five families, every interval, the number needed to evaluate, the control-side burden and PPV
in excess of prevalence are Table A4**, where the cross-family claim below is checked.

| Model | Cohort | Sens. | Spec. | PPV | Min. above thr. | Lead, min |
|---|---|---:|---:|---:|---:|---:|
| Transformer | EPIC test | 0.777 | 0.406 | 0.625 | 0.523 | 24 |
| Transformer | VitalDB | 0.679 | 0.379 | 0.380 | 0.444 | 17 |
| Transformer | MOVER SIS | 0.657 | 0.467 | 0.585 | 0.200 | 22 |


## 4.2 What these findings do and do not license

Both findings are properties of a pipeline as deployed with this scoring policy rather than claims
about what any architecture must do; Section 7 states the scope. Neither is a claim about
physiology. The outcome is a sustained excursion of mean arterial pressure and mean arterial
pressure is one of the model's input channels, so the model has direct access to the quantity the
label is computed from, and nothing here shows that a score anticipates a physiological process.

# 5 Two natural remedies, and why neither works

Two fixes follow naturally from Sections 3 and 4, and neither works. A metric with a
plausible-looking repair that fails is a worse problem than one with none, because the repair
gets adopted.

## 5.1 Prevalent alerts are not the explanation

The first thought is that the metric is dominated by cases already above threshold at their first
eligible minute. Such cases are
**2.6 to 25.5%** of detected event cases across
the fifteen cells, and removing them to recompute the median lead on incident alerts alone costs
**0 to 3 minutes in all fifteen cells**, the transformer included (Appendix A, alert composition).
The relationship of Section 3 is therefore carried by the ordinary cases. Prevalence stays this low
alongside the settling of Section 4.1 because most detected event cases have an available window
shorter than 60 minutes, so it opens while the score is still settling: prevalence and a warm-up
crossing are the same behavior on either side of that minute.


## 5.2 Suppressing the first minutes of monitoring is not the fix

The second thought follows from Section 4.1: if the score is unreliable while it settles, discard
alerts raised during that period. We implemented exactly that, discarding every minute at or before
*N* minutes of elapsed monitoring and then applying the unchanged threshold.

At *N* = 5, across all five families and three cohorts, the rule costs **3.6 to 6.8
percentage points of case-level sensitivity** and returns **0 to 3.2 percentage points of
specificity**. Median lead changes by **−3 to +1 minutes**; in two of the fifteen cells it
*increases*, because discarding early minutes removes some short-window cases from the detected
set entirely and shifts the median. The trade is poor in every cell, and it does not address
Section 3: the surviving alerts still fire at the first opportunity within whatever window
remains.

The comparison holds the transported threshold fixed, so it is deliberately unmatched on
sensitivity; reselecting a threshold is the one thing this paper does nowhere. The direction is not
expected to reverse under matching: suppression removes alerting minutes and cannot add crossings,
so after lowering the threshold to restore sensitivity, any specificity gain cannot exceed the
fixed-threshold gain above.

**We therefore do not recommend the rule.** The problem is not that early minutes are noisy.
It is that the reported quantity is coupled to the length of the window it was measured in.

## 5.3 What does work, and why it is only a partial fix

Both repairs above change the alert rule and leave the estimand alone. The remaining option
reverses that: condition on window length, or treat the first alert as a time-to-event whose
follow-up ends when the window does, the landmarking treatment of a prediction made at a fixed
point in a run-up [@vanhouwelingen2007landmark]. Both are computable from the same cached scores,
so we report them rather than only recommending them (Tables A6 and A7).


**A fixed-horizon detection rate does not inherit the window's length.** Among event cases
observed for at least *X* minutes before onset, the share whose first alert came at least *X*
minutes before onset moves numerator and denominator together, so a cohort watched for longer
cannot inflate it. It runs 0.278 to 0.692 at a 10-minute horizon and 0.173 to 0.547 at 30 minutes,
declining smoothly with the horizon, which is the shape a single median destroys (Table A6).
Restricted instead to cases observed for the whole 60-minute window, so the window is a constant,
the transformer reports the longest median lead of the five families in all three cohorts, 47, 60
and 57 minutes, while detecting only 0.441, 0.247 and 0.304 of them against 0.762 to 0.910 for
XGBoost and the random forest (Table A7): conditioning turns its reported advantage into a deficit.

**It is a partial fix.** It changes the estimand and the population, discarding 53 to 60% of event
cases, and those are the short-window cases a deployed monitor will meet; it leaves the pooled
headline figure unrepaired; and for the reason given in Section 2, the censoring is not independent
of the event, with short- and long-run-up cases differing in surgery duration and case mix
(Appendix A, risk-set composition).

# 6 A task-specific reporting extension

Reporting conventions decide what interpretation is available to a reader. A clinician,
policymaker or science writer meets a number and a name, not the scoring policy behind them, so
what a standard asks for bounds what any of them can conclude. That is why auditing one metric is
a communication result and not only a metrology one.

**This section maps that case study onto what a general standard explicitly asks for.** A
TRIPOD+AI checklist was completed for this work by its own authors, before Sections 3 to 5 were
conducted, and it did not request the disclosures that reveal the dependence. TRIPOD+AI is a
general minimum **reporting** standard rather than a validity tool, and one author-completed
checklist cannot assess a general framework in either direction. So what follows is a mapping,
and the items in Section 6.2 are task-specific candidate disclosures that complement the standard
rather than correct, invalidate or demonstrate non-adherence to it.

## 6.1 The items that were satisfied

**Item 12e, performance measures and rationale**, is where a lead time is declared: it asks
*which* measures were used and *why*, not what else a measure could be responding to. **Item 23a,
model performance**, asks for performance with uncertainty, and Table 1 satisfies it. So Table 1
is a compliant table in which a 24-minute lead sits beside a specificity of 0.406, with nothing in
either item requiring a reader to put the two together. Four further items came close and missed
(Table A8), and one pattern runs across them: the available pre-onset window distribution is never
requested, and it is the variable the reported lead correlates with at ρ = 0.501 to 0.906.

**Item 14, model fairness, is the near miss**, and the most instructive item on the list. The
checklist's own fairness answer records that arterial-line placement selects toward longer,
higher-risk operations. The information that observation length is not distributed at random was
therefore **already disclosed**, filed as a limitation, where it reads as a caveat about which
patients the findings extend to. Nothing in the standard connects it to the timing metric three
tables away.

## 6.2 Four candidate disclosures for continuously monitored models

Each is tied to a measurement in this paper, each is computable from artifacts a study of this
kind already produces, and none requires a new experiment. They have not been validated as a
general reporting framework.

1. **Report alert composition by elapsed observation time**: for every operating point, the share
   of alerts already active at the first eligible minute, those that fired within a short settling
   period, and those that fired later (Figure A2). One stacked bar would have made Section 4.1
   visible on inspection.

2. **Report a window-conditional or fixed-horizon statistic as the primary timing quantity**, with
   any single median secondary and stratified by the window distribution it was measured within. A
   median is uninterpretable without its denominator: the transformer reports 5 to 9 minutes for
   its shortest-observed band and 46 to 59 for its longest, and the pooled 17 to 24 carries
   neither. Both substitutes are already conventional in early-warning evaluation
   [@romerobrufau2015cstatistic; @paine2016alerts] and computable from what such a study already
   has (Tables A6, A7); Section 5.3 gives the cost.

3. **Report N(t) beside any event-aligned trajectory.** Here the risk set roughly halves between
   the event and 60 minutes before it (1,404 to 708, 2,804 to 1,433 and 2,641 to 1,374), and the
   cases surviving to the far end are the long-window ones, the same selection that drives
   Section 3. **The denominator is not cosmetic**: recomputing the same bins on only the cases
   observable back to 60 minutes moves the first bin reaching AUROC 0.70 from 15 minutes in all
   three cohorts to 20, 35 and 20, so the horizon a reader would quote changes by up to twenty
   minutes on a reporting choice alone, and neither curve is the true one (Figure A3).

4. **Report a path-versus-displacement summary for any score read as a trend**, so that a series
   travelling much farther than its net displacement is qualified before it is described as rising
   or falling (Table A3 and Appendix A.4).

The first three are disclosure items in the ordinary TRIPOD sense, naming a quantity that must
appear beside one already required; the fourth is closer to a diagnostic, and we offer it as the
weakest of the four for that reason.

## 6.3 What this does and does not generalize to

The specific artifact does not generalize; its shape does. The shape is a quantity named for what
a clinician would experience,
computed from a window whose length varies across patients and is not reported, under a standard
that requires the quantity and not the window. Any continuously read model evaluated with a
first-crossing statistic over variable available windows is structurally susceptible to this
dependence. Its empirical magnitude has to be measured in each setting, and the four items are the
disclosure that would let a reader see it.

# 7 Limitations and scope

**Retrospective, and one label.** Every score is computed from cached data after the fact: a
retrospective forward-running simulation, not deployment clearance. The outcome is a sustained
excursion of mean arterial pressure below a fixed level, and both the level and the duration are
conventions we did not vary; the label's dependence on a channel the models read is in Section 4.2.

**One model fit, one family of operating points, and one draw of the control reference times.**
Models were trained at one seed and thresholds come from one validation split at one sensitivity
target, transported unchanged; a different fit or target could move the composition of Section 5.1,
the magnitudes of Section 3 and the operating points of Table 1, and we varied none of them.
Control cases have no onset, so each is assigned a pseudo-onset sampled once at a fixed seed from
the event cases' timing distribution. **Every control-side quantity here is conditional on that
one draw**: the case-level specificity and positive predictive value of Table 1, the control-side
minute share, and the cross-combination association of Section 4.1 that rests on them. Its
resampling variability is not propagated into any interval we report. Redrawing the reference
times would require rerunning the complete control-side evaluation pipeline for every model and
cohort, so we report all control-side quantities as conditional on the single pre-specified draw
rather than presenting an unperformed sensitivity analysis.

**Properties of a pipeline, not of an architecture.** Section 4.1 describes what one model does
under one scoring policy on these cohorts, not what sequence models must do. Section 3's effect is
present in all five families, the ratio running 0.455 to 0.944, with the transformer the limiting
case rather than the exception.

**The references bias upward.** Both shuffle variants make agreement easier to obtain, in the
direction that favors our own reading, and they change the detected-case set. They bound the
dependence rather than estimating a case-independent process.

**Communication and reporting claims, and one clinical domain.** We analyze the interpretation
invited by the metric's name, not measured clinician comprehension. The TRIPOD+AI assessment was
author-completed, and the four disclosures were demonstrated here rather than validated across
reporting settings or stakeholder groups. Three cohorts, two health systems and two countries
still give one procedure setting and one monitored variable, so they cannot settle whether
Section 6.2's four items are the right four elsewhere.

# Appendix A: methods and complete per-cell results

## Cohorts, models, training and compute

**Cohorts and eligibility.** Two public datasets supply the three cohorts: VitalDB, and
MOVER, whose single release carries both an EPIC-derived and an SIS-derived arm. Both are
de-identified and both are obtained under their providers' data use agreements. Development
used MOVER's EPIC arm. The subject-aware split at
seed 1004 gave 6,409 training, 1,375 validation and 1,404 test cases
out of 9,188, split on unique subject identifiers so that a patient with several operations
lands in one fold. The test split holds 1,404 cases, 786 with a sustained event, 1,145 subjects.
External evaluation used VitalDB, with 2,804 cases, 1,007 events and 2,730 subjects, and the
SIS-derived arm of MOVER, with 2,641 cases and 1,409 events, neither of which contributed to
training, calibration or threshold selection. Per-minute eligibility
drops the induction prefix, 25 minutes where the record is anchored on anesthesia start, 10
where it is anchored on surgical start, and every minute at or after first onset, so no
model is asked to predict an event already in progress. Event cases required five valid
pre-onset minutes after that exclusion and controls thirty. Procedure group is never a model
input in any family: it separates the cohorts almost perfectly and would be learned as cohort
identity.

**Features.** The same twenty inputs for every family: sixteen per-minute channels, being
MAP, systolic and diastolic pressure, their non-invasive counterparts, heart rate, SpO2,
end-tidal CO2, temperature, FiO2, MAC, tidal volume, respiratory rate, PEEP and peak
inspiratory pressure, and four demographics, being age, sex, height and weight. The families
differ in how they consume them. The transformer takes each non-missing cell as a
(type, time, value) triplet with demographics as a fixed prefix at time zero, up to 2,048
tokens over a 120-minute window, so missing cells produce no token and are never imputed. The
LSTM takes the normalized per-minute window as a value-and-mask pair per channel. Logistic
regression, random forest and XGBoost take the last observation carried forward per channel
plus the demographics. Per-channel median and interquartile scaling was fitted on the
training cases alone and applied unchanged everywhere else.

**Architectures and training.** Seed 1004 throughout. The transformer is a STraTS-style
encoder, a type embedding plus a value MLP plus a time MLP summed per triplet, two encoder
layers, model width 128, four heads, feed-forward width 512, dropout 0.1, a learnable
classification token and a two-class softmax head; AdamW at learning rate 1.2e-3, weight
decay 1e-2 applied to two-dimensional tensors only, gradient clipping at 1.0, a cosine
schedule with 5% warmup, batch size 64, cross-entropy, up to 50 epochs with early stopping on
validation AUROC at patience 10, under bfloat16 autocast. The LSTM is one layer of width 128
with dropout 0.1, AdamW at 1e-3 with weight decay 1e-2, batch size 64, up to 40 epochs at
patience 8. Logistic regression is median imputation and standardization followed by an L2
fit at up to 2,000 iterations. The random forest is 400 trees. XGBoost is 600 rounds at depth
6, learning rate 0.05, row and column subsampling at 0.8, histogram tree method, early
stopping after 40 rounds on validation AUC. No hyperparameter search was run over any of
these values.

**Compute.** Every model was trained on one Apple M3 Ultra desktop with 512 GB of unified
memory, using PyTorch 2.10 on the Metal backend with bfloat16 autocast; no GPU cluster was
used. Wall clock for the five models reported here was 40.3 minutes for the transformer, 14.5
for the LSTM, 3.6 for the random forest, and 34 and 33 seconds for XGBoost and logistic
regression. The project trained more than this paper reports: each family was also trained at
seven lead-time offsets, of which the transformer arm alone took 3.8 hours. The analyses in
this paper add no training and read cached per-minute scores on the same machine. Software
was PyTorch 2.10.0, scikit-learn 1.7.1, XGBoost 3.3.0, NumPy
2.2.6, pandas 2.3.2 and SciPy 1.16.1.

**Data and code.** Both datasets are obtained from their own project sites once access is
granted: VitalDB under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0
International license and a data use agreement, MOVER from the UCI Machine Learning
Repository under a data use agreement, one download supplying both arms used here. Each
original collection was approved by its own institutional review board with consent waived
after de-identification. The exemption from review and the consent waiver for the present
secondary analysis were granted by an institutional review board whose identity and protocol
number are withheld for anonymous review. This work added no data collection and no patient
contact. Analysis code is available at an anonymized repository, [ANONYMIZED URL]. Neither
dataset may be redistributed under the agreements above, so the repository carries the analysis
code and the aggregate result files behind the tables and figures, and no patient-level data of
any kind.

## Lead time by quantile-derived band of observed window, all fifteen cells

**Table A1 | Median alert lead time by quantile-derived band of observed window, all fifteen
cells.** Main text Section 3.1 reports the ITE Transformer. The gradient is positive in
every cell.
`Bands` is the number of quantile-derived groups actually realized: where the observed window is censored
at the 60-minute alert window the upper quintiles collapse onto a single value, and
duplicate edges are dropped rather than bands invented.
The gradient is the difference of the highest and lowest band medians, and its interval is the
paired cluster bootstrap of that difference: one weight matrix is drawn per cell and reused
across bands, and the band edges and the window span are held fixed at their full-sample values
so the ratio's denominator is not itself resampled. The interval excludes zero in all fifteen
cells.

| Model | Cohort | Bands | Window Q1→last, min | Lead Q1→last, min | Gradient, min (95% CI) | Lead min per window min (95% CI) |
|---|---|---:|---|---|---|---|
| Transformer | MOVER (EPIC) test | 4 | 10 → 60 | 9 → 46 | +37 [+35, +41] | 0.74 [0.70, 0.82] |
| Transformer | VitalDB | 5 | 7 → 60 | 5 → 59 | +54 [+51, +55] | 1.02 [0.96, 1.04] |
| Transformer | MOVER (SIS) | 4 | 8 → 60 | 6 → 46 | +40 [+37, +43] | 0.77 [0.71, 0.83] |
| LSTM | MOVER (EPIC) test | 4 | 10 → 60 | 6 → 44 | +38 [+35, +41] | 0.77 [0.70, 0.82] |
| LSTM | VitalDB | 5 | 6 → 60 | 3 → 34 | +31 [+21, +48] | 0.57 [0.39, 0.89] |
| LSTM | MOVER (SIS) | 4 | 9 → 60 | 5 → 31 | +26 [+19, +30] | 0.51 [0.37, 0.59] |
| XGBoost | MOVER (EPIC) test | 3 | 12 → 60 | 8 → 38 | +30 [+26, +34] | 0.62 [0.54, 0.71] |
| XGBoost | VitalDB | 3 | 9 → 60 | 3 → 30 | +27 [+22, +30] | 0.53 [0.43, 0.58] |
| XGBoost | MOVER (SIS) | 3 | 12 → 60 | 5 → 36 | +31 [+28, +33] | 0.65 [0.58, 0.69] |
| Random forest | MOVER (EPIC) test | 3 | 13 → 60 | 8 → 38 | +30 [+26, +34] | 0.64 [0.55, 0.72] |
| Random forest | VitalDB | 3 | 9 → 60 | 3 → 34 | +31 [+29, +34] | 0.61 [0.57, 0.67] |
| Random forest | MOVER (SIS) | 3 | 12 → 60 | 6 → 40 | +34 [+31, +36] | 0.71 [0.65, 0.75] |
| Logistic reg. | MOVER (EPIC) test | 3 | 11 → 60 | 8 → 40 | +32 [+28, +35] | 0.65 [0.57, 0.71] |
| Logistic reg. | VitalDB | 3 | 10 → 60 | 3 → 28 | +26 [+20, +28] | 0.51 [0.40, 0.56] |
| Logistic reg. | MOVER (SIS) | 3 | 12 → 60 | 5 → 38 | +33 [+29, +36] | 0.69 [0.61, 0.75] |

## Both nulls, all fifteen cells

**Table A2 | Both nulls, all fifteen cells.** Observed ratio against the
uniform-placement null of Section 3.3 and both variants of the
cross-case shuffle. The uniform null's expectation is 0.5 by construction; the two shuffle
variants differ only in how a donor shorter than its recipient is handled, and both bias
the null upward. Intervals are the 2.5th and 97.5th percentiles of the null distribution.

| Model | Cohort | Observed ratio | Uniform null | Shuffle null, hold | Shuffle null, length-matched | Observed ρ | Shuffle ρ, hold | Shuffle ρ, length-matched |
|---|---|---:|---|---|---|---:|---|---|
| Transformer | MOVER (EPIC) test | 0.944 | 0.524 [0.491, 0.567] | 0.970 [0.967, 0.974] | 0.962 [0.951, 0.971] | 0.706 | 0.888 [0.855, 0.920] | 0.783 [0.705, 0.856] |
| Transformer | VitalDB | 0.923 | 0.532 [0.500, 0.573] | 0.966 [0.963, 0.967] | 0.957 [0.947, 0.969] | 0.906 | 0.941 [0.926, 0.955] | 0.933 [0.890, 0.967] |
| Transformer | MOVER (SIS) | 0.899 | 0.527 [0.500, 0.567] | 0.949 [0.941, 0.950] | 0.918 [0.900, 0.938] | 0.801 | 0.877 [0.855, 0.895] | 0.775 [0.713, 0.827] |
| LSTM | MOVER (EPIC) test | 0.851 | 0.522 [0.483, 0.563] | 0.913 [0.900, 0.923] | 0.866 [0.833, 0.893] | 0.650 | 0.825 [0.784, 0.860] | 0.673 [0.596, 0.743] |
| LSTM | VitalDB | 0.619 | 0.534 [0.500, 0.583] | 0.870 [0.850, 0.883] | 0.752 [0.667, 0.833] | 0.759 | 0.845 [0.798, 0.886] | 0.705 [0.593, 0.804] |
| LSTM | MOVER (SIS) | 0.717 | 0.524 [0.500, 0.562] | 0.873 [0.857, 0.887] | 0.700 [0.633, 0.767] | 0.501 | 0.682 [0.636, 0.727] | 0.455 [0.368, 0.547] |
| XGBoost | MOVER (EPIC) test | 0.719 | 0.519 [0.483, 0.558] | 0.842 [0.814, 0.867] | 0.760 [0.705, 0.800] | 0.558 | 0.701 [0.651, 0.751] | 0.581 [0.503, 0.649] |
| XGBoost | VitalDB | 0.467 | 0.521 [0.483, 0.556] | 0.723 [0.667, 0.768] | 0.591 [0.517, 0.652] | 0.599 | 0.636 [0.569, 0.698] | 0.493 [0.400, 0.580] |
| XGBoost | MOVER (SIS) | 0.600 | 0.518 [0.500, 0.550] | 0.779 [0.750, 0.800] | 0.681 [0.633, 0.722] | 0.573 | 0.632 [0.590, 0.673] | 0.488 [0.429, 0.541] |
| Random forest | MOVER (EPIC) test | 0.714 | 0.519 [0.483, 0.556] | 0.839 [0.816, 0.867] | 0.777 [0.733, 0.817] | 0.584 | 0.714 [0.665, 0.764] | 0.599 [0.531, 0.667] |
| Random forest | VitalDB | 0.533 | 0.523 [0.500, 0.556] | 0.764 [0.721, 0.800] | 0.685 [0.625, 0.733] | 0.651 | 0.678 [0.622, 0.729] | 0.555 [0.479, 0.627] |
| Random forest | MOVER (SIS) | 0.667 | 0.518 [0.500, 0.550] | 0.811 [0.783, 0.833] | 0.741 [0.700, 0.783] | 0.618 | 0.659 [0.625, 0.692] | 0.536 [0.486, 0.589] |
| Logistic reg. | MOVER (EPIC) test | 0.781 | 0.520 [0.483, 0.557] | 0.872 [0.849, 0.898] | 0.802 [0.767, 0.842] | 0.597 | 0.739 [0.694, 0.779] | 0.612 [0.544, 0.676] |
| Logistic reg. | VitalDB | 0.455 | 0.521 [0.471, 0.567] | 0.721 [0.667, 0.781] | 0.577 [0.500, 0.650] | 0.607 | 0.642 [0.549, 0.720] | 0.486 [0.374, 0.584] |
| Logistic reg. | MOVER (SIS) | 0.618 | 0.518 [0.500, 0.550] | 0.782 [0.750, 0.800] | 0.734 [0.692, 0.767] | 0.597 | 0.644 [0.607, 0.682] | 0.548 [0.495, 0.595] |

Three cells in this table are the ones Section 3.3 names as not exceeding the uniform
reference, all of them VitalDB. The observed ratio sits below it for XGBoost by −0.054 and for
logistic regression by −0.067, and random forest is indistinguishable from it (+0.011,
*P* = 0.824). For the transformer the excess over the uniform reference is +0.372 to +0.421.
Under the length-matched shuffle variant the transformer's null spans 0.77 to 0.93.

## Path decomposition

**Table A3 | Path decomposition over the window 60 to 5 minutes before onset.** Event
episodes have observed scores at both window edges. Directedness
is net displacement divided by total distance traveled, so 1 is a monotone climb and 0 is a
round trip. Path per net is total distance divided by the absolute net change. Episodes
observed at every bin center in the window; median 11 steps per episode. Intervals are 95%
cluster bootstrap. Only this window is reported: over 60 to 10 minutes the transformer's net
displacement is indistinguishable from zero in two cohorts, and the ratio is then a division
by approximately nothing.

| Cohort | Model | Episodes | Directedness (95% CI) | Path per unit net |
|---|---|---:|---|---:|
| MOVER (EPIC) test | Transformer | 313 | 0.025 [0.002, 0.050] | 40.7 |
| MOVER (EPIC) test | LSTM | 313 | 0.043 [0.024, 0.057] | 25.9 |
| MOVER (EPIC) test | XGBoost | 313 | 0.049 [0.033, 0.070] | 20.0 |
| MOVER (EPIC) test | Random forest | 313 | 0.067 [0.038, 0.093] | 16.3 |
| MOVER (EPIC) test | Logistic reg. | 313 | 0.061 [0.044, 0.089] | 17.6 |
| VitalDB | Transformer | 433 | 0.021 [0.005, 0.038] | 146.6 |
| VitalDB | LSTM | 433 | 0.059 [0.035, 0.070] | 28.2 |
| VitalDB | XGBoost | 433 | 0.069 [0.049, 0.099] | 17.9 |
| VitalDB | Random forest | 433 | 0.075 [0.053, 0.094] | 14.4 |
| VitalDB | Logistic reg. | 433 | 0.088 [0.063, 0.108] | 12.6 |
| MOVER (SIS) | Transformer | 670 | 0.089 [0.066, 0.122] | 13.1 |
| MOVER (SIS) | LSTM | 670 | 0.142 [0.118, 0.183] | 7.9 |
| MOVER (SIS) | XGBoost | 670 | 0.144 [0.120, 0.167] | 7.5 |
| MOVER (SIS) | Random forest | 670 | 0.151 [0.132, 0.168] | 7.0 |
| MOVER (SIS) | Logistic reg. | 670 | 0.134 [0.119, 0.154] | 7.9 |

Directedness is net displacement divided by total distance traveled: over the window from 60 to 5
minutes before onset it is **+0.021 to +0.151 across all fifteen cells**, every interval excluding
zero, so no family approaches a directed climb. **Directedness describes path shape and does not
establish when or whether a particular threshold is touched.** Three further things belong here. The ratio of the median path length to the absolute median net displacement is 7.0 to
146.6 across the fifteen cells; because that ratio becomes unstable as net displacement
approaches zero, directedness is the primary summary and both quantities describe path shape
rather than prove a crossing mechanism. The transformer sits at the volatile end of both
(directedness +0.021 to +0.089, path per unit net displacement 13.1 to 146.6) and logistic
regression at the least volatile (+0.061 to +0.134, 7.9 to 17.6). And averaged over cases the
score still behaves as a reader expects, rising where an event follows and staying much flatter
where none does, but the transformer's event and control means are indistinguishable an hour
before onset where the tabular families' are already apart (Figure A4). The property is present
under this task and scoring policy and the transformer is its limiting case; the design does not
isolate architecture from representation or training.

## Case-level operating point, complete detail

**Table A4 | Case-level operating point, all fifteen cells.** Main text Table 1 carries the ITE
Transformer's three rows without intervals; this is every family and every interval, and it is
where the cross-combination claim of Section 4.1 is checked. Sensitivity and specificity are
case-level as defined in Section 2, NNE is alerting cases per detected event and equals 1/PPV, and
`Min. above thr.` is the median share of an event case's monitored minutes at or above the
transported threshold. Cohort composition, prevalence, PPV in excess of prevalence, the
control-side minute share and the share of event cases already alerting by the first elapsed
minute are Table A10. Intervals are 95% cluster bootstrap over subjects, or over cases in MOVER
(SIS).

| Model | Cohort | Sensitivity (95% CI) | Specificity (95% CI) | PPV (95% CI) | NNE (95% CI) | Min. above thr., events (95% CI) | Median lead, min (95% CI) |
|---|---|---|---|---|---|---|---|
| ITE Transformer | MOVER (EPIC) test | 0.777 [0.746, 0.806] | 0.406 [0.368, 0.443] | 0.625 [0.594, 0.656] | 1.60 [1.53, 1.68] | 0.523 [0.444, 0.575] | 24 [21, 27] |
| ITE Transformer | VitalDB | 0.679 [0.651, 0.707] | 0.379 [0.358, 0.403] | 0.380 [0.357, 0.402] | 2.63 [2.49, 2.80] | 0.444 [0.389, 0.500] | 17 [15, 19] |
| ITE Transformer | MOVER (SIS) | 0.657 [0.632, 0.682] | 0.467 [0.441, 0.494] | 0.585 [0.561, 0.609] | 1.71 [1.64, 1.78] | 0.200 [0.150, 0.238] | 22 [20, 24] |
| LSTM | MOVER (EPIC) test | 0.807 [0.779, 0.834] | 0.474 [0.433, 0.513] | 0.661 [0.631, 0.690] | 1.51 [1.45, 1.58] | 0.267 [0.209, 0.308] | 23 [20, 25] |
| LSTM | VitalDB | 0.492 [0.460, 0.523] | 0.812 [0.795, 0.830] | 0.595 [0.563, 0.629] | 1.68 [1.59, 1.78] | 0.000 [0.000, 0.017] | 9 [8, 10] |
| LSTM | MOVER (SIS) | 0.551 [0.526, 0.577] | 0.709 [0.683, 0.735] | 0.685 [0.657, 0.712] | 1.46 [1.40, 1.52] | 0.017 [0.017, 0.020] | 15 [14, 18] |
| XGBoost | MOVER (EPIC) test | 0.810 [0.782, 0.835] | 0.608 [0.570, 0.647] | 0.725 [0.696, 0.754] | 1.38 [1.33, 1.44] | 0.117 [0.100, 0.133] | 21 [18, 23] |
| XGBoost | VitalDB | 0.694 [0.665, 0.721] | 0.754 [0.735, 0.774] | 0.613 [0.584, 0.640] | 1.63 [1.56, 1.71] | 0.067 [0.050, 0.067] | 13 [12, 16] |
| XGBoost | MOVER (SIS) | 0.790 [0.768, 0.810] | 0.638 [0.610, 0.666] | 0.714 [0.691, 0.736] | 1.40 [1.36, 1.45] | 0.100 [0.100, 0.117] | 19 [18, 22] |
| Random forest | MOVER (EPIC) test | 0.828 [0.801, 0.854] | 0.555 [0.515, 0.597] | 0.703 [0.674, 0.732] | 1.42 [1.37, 1.48] | 0.150 [0.133, 0.167] | 22 [20, 24] |
| Random forest | VitalDB | 0.803 [0.778, 0.827] | 0.674 [0.651, 0.695] | 0.580 [0.553, 0.604] | 1.72 [1.65, 1.81] | 0.133 [0.118, 0.150] | 15 [12, 18] |
| Random forest | MOVER (SIS) | 0.849 [0.830, 0.867] | 0.559 [0.532, 0.586] | 0.688 [0.666, 0.710] | 1.45 [1.41, 1.50] | 0.172 [0.167, 0.183] | 22 [20, 25] |
| Logistic regression | MOVER (EPIC) test | 0.837 [0.810, 0.864] | 0.518 [0.477, 0.557] | 0.688 [0.658, 0.719] | 1.45 [1.39, 1.52] | 0.139 [0.114, 0.162] | 23 [21, 26] |
| Logistic regression | VitalDB | 0.461 [0.431, 0.492] | 0.825 [0.808, 0.842] | 0.596 [0.565, 0.631] | 1.68 [1.59, 1.77] | 0.000 [0.000, 0.000] | 14 [10, 16] |
| Logistic regression | MOVER (SIS) | 0.790 [0.769, 0.812] | 0.585 [0.559, 0.611] | 0.685 [0.662, 0.708] | 1.46 [1.41, 1.51] | 0.117 [0.100, 0.130] | 21 [19, 23] |

## Detection rate by band of observed window, all fifteen cells

**Table A5 | Detection rate by band of observed pre-onset window, all fifteen cells.** Bands are
quantiles of the observed window cut over **all** event cases with a positive observed window,
not over the detected subset Table A9 and Table A1 cut on, because a within-band detection rate
needs every event case of that window length in its denominator. The two banding schemes are
therefore not interchangeable, the band counts here are event-case counts rather than detected
counts, and the median leads differ slightly from Table A1's. The detection rate summed over
bands reproduces the case-level sensitivity of Table 1 exactly in all fifteen cells, which is the
check that the denominators are the same event cases. Intervals are 95% cluster bootstrap.

| Model | Cohort | Band | Event cases | Detected | Window median, min | Detection rate (95% CI) | Median lead, min (95% CI) |
|---|---|---:|---:|---:|---:|---|---|
| ITE Transformer | MOVER (EPIC) test | 1 | 159 | 159 | 11 | 1.000 [1.000, 1.000] | 9 [8, 10] |
| ITE Transformer | MOVER (EPIC) test | 2 | 164 | 164 | 23 | 1.000 [1.000, 1.000] | 22 [20, 24] |
| ITE Transformer | MOVER (EPIC) test | 3 | 150 | 149 | 44 | 0.993 [0.979, 1.000] | 42 [40, 43] |
| ITE Transformer | MOVER (EPIC) test | 4 | 313 | 139 | 60 | 0.444 [0.388, 0.498] | 54 [33, 58] |
| ITE Transformer | VitalDB | 1 | 204 | 204 | 8 | 1.000 [1.000, 1.000] | 6 [6, 7] |
| ITE Transformer | VitalDB | 2 | 203 | 203 | 18 | 1.000 [1.000, 1.000] | 16 [14, 17] |
| ITE Transformer | VitalDB | 3 | 600 | 277 | 60 | 0.462 [0.421, 0.500] | 44 [42, 46] |
| ITE Transformer | MOVER (SIS) | 1 | 287 | 283 | 10 | 0.986 [0.971, 0.997] | 7 [7, 8] |
| ITE Transformer | MOVER (SIS) | 2 | 285 | 281 | 25 | 0.986 [0.971, 0.997] | 23 [22, 24] |
| ITE Transformer | MOVER (SIS) | 3 | 837 | 362 | 60 | 0.432 [0.398, 0.465] | 46 [43, 49] |
| LSTM | MOVER (EPIC) test | 1 | 159 | 148 | 11 | 0.931 [0.889, 0.970] | 7 [6, 8] |
| LSTM | MOVER (EPIC) test | 2 | 164 | 157 | 23 | 0.957 [0.925, 0.987] | 20 [18, 21] |
| LSTM | MOVER (EPIC) test | 3 | 150 | 141 | 44 | 0.940 [0.897, 0.974] | 39 [37, 41] |
| LSTM | MOVER (EPIC) test | 4 | 313 | 188 | 60 | 0.601 [0.545, 0.652] | 40 [34, 46] |
| LSTM | VitalDB | 1 | 204 | 166 | 8 | 0.814 [0.760, 0.868] | 3 [3, 4] |
| LSTM | VitalDB | 2 | 203 | 147 | 18 | 0.724 [0.660, 0.783] | 10 [9, 12] |
| LSTM | VitalDB | 3 | 600 | 182 | 60 | 0.303 [0.268, 0.340] | 32 [28, 34] |
| LSTM | MOVER (SIS) | 1 | 287 | 196 | 10 | 0.683 [0.628, 0.738] | 6 [5, 6] |
| LSTM | MOVER (SIS) | 2 | 285 | 188 | 25 | 0.660 [0.604, 0.714] | 18 [16, 21] |
| LSTM | MOVER (SIS) | 3 | 837 | 393 | 60 | 0.470 [0.437, 0.504] | 33 [29, 36] |
| XGBoost | MOVER (EPIC) test | 1 | 159 | 110 | 11 | 0.692 [0.619, 0.760] | 7 [5, 9] |
| XGBoost | MOVER (EPIC) test | 2 | 164 | 132 | 23 | 0.805 [0.743, 0.865] | 17 [16, 19] |
| XGBoost | MOVER (EPIC) test | 3 | 150 | 130 | 44 | 0.867 [0.806, 0.918] | 32 [28, 36] |
| XGBoost | MOVER (EPIC) test | 4 | 313 | 265 | 60 | 0.847 [0.806, 0.885] | 40 [34, 44] |
| XGBoost | VitalDB | 1 | 204 | 110 | 8 | 0.539 [0.471, 0.606] | 3 [2, 3] |
| XGBoost | VitalDB | 2 | 203 | 132 | 18 | 0.650 [0.587, 0.718] | 7 [5, 9] |
| XGBoost | VitalDB | 3 | 600 | 457 | 60 | 0.762 [0.728, 0.794] | 26 [23, 30] |
| XGBoost | MOVER (SIS) | 1 | 287 | 179 | 10 | 0.624 [0.570, 0.678] | 5 [4, 5] |
| XGBoost | MOVER (SIS) | 2 | 285 | 228 | 25 | 0.800 [0.753, 0.844] | 14 [13, 16] |
| XGBoost | MOVER (SIS) | 3 | 837 | 706 | 60 | 0.843 [0.819, 0.866] | 35 [33, 37] |
| Random forest | MOVER (EPIC) test | 1 | 159 | 107 | 11 | 0.673 [0.596, 0.746] | 6 [5, 8] |
| Random forest | MOVER (EPIC) test | 2 | 164 | 135 | 23 | 0.823 [0.762, 0.880] | 17 [15, 18] |
| Random forest | MOVER (EPIC) test | 3 | 150 | 129 | 44 | 0.860 [0.800, 0.914] | 30 [27, 34] |
| Random forest | MOVER (EPIC) test | 4 | 313 | 280 | 60 | 0.895 [0.861, 0.928] | 41 [35, 45] |
| Random forest | VitalDB | 1 | 204 | 140 | 8 | 0.686 [0.626, 0.747] | 3 [2, 3] |
| Random forest | VitalDB | 2 | 203 | 157 | 18 | 0.773 [0.711, 0.831] | 7 [6, 10] |
| Random forest | VitalDB | 3 | 600 | 512 | 60 | 0.853 [0.825, 0.882] | 32 [30, 35] |
| Random forest | MOVER (SIS) | 1 | 287 | 201 | 10 | 0.700 [0.646, 0.752] | 5 [5, 6] |
| Random forest | MOVER (SIS) | 2 | 285 | 245 | 25 | 0.860 [0.819, 0.899] | 16 [14, 17] |
| Random forest | MOVER (SIS) | 3 | 837 | 750 | 60 | 0.896 [0.875, 0.916] | 38 [36, 41] |
| Logistic regression | MOVER (EPIC) test | 1 | 159 | 119 | 11 | 0.748 [0.678, 0.814] | 7 [6, 9] |
| Logistic regression | MOVER (EPIC) test | 2 | 164 | 138 | 23 | 0.841 [0.787, 0.896] | 18 [17, 20] |
| Logistic regression | MOVER (EPIC) test | 3 | 150 | 134 | 44 | 0.893 [0.843, 0.940] | 36 [32, 38] |
| Logistic regression | MOVER (EPIC) test | 4 | 313 | 267 | 60 | 0.853 [0.812, 0.892] | 42 [36, 46] |
| Logistic regression | VitalDB | 1 | 204 | 71 | 8 | 0.348 [0.283, 0.412] | 3 [2, 3] |
| Logistic regression | VitalDB | 2 | 203 | 95 | 18 | 0.468 [0.404, 0.539] | 7 [6, 8] |
| Logistic regression | VitalDB | 3 | 600 | 298 | 60 | 0.497 [0.454, 0.537] | 26 [22, 30] |
| Logistic regression | MOVER (SIS) | 1 | 287 | 178 | 10 | 0.620 [0.566, 0.676] | 5 [5, 5] |
| Logistic regression | MOVER (SIS) | 2 | 285 | 221 | 25 | 0.775 [0.727, 0.821] | 14 [12, 16] |
| Logistic regression | MOVER (SIS) | 3 | 837 | 714 | 60 | 0.853 [0.829, 0.876] | 36 [34, 38] |

## Replacement estimands, all horizons

**Table A6 | Fixed-horizon detection rate at all seven horizons, and time to first alert.** The
fixed-horizon detection rate is the share of event cases observed for at least the stated number
of minutes before onset whose first alert came at least that many minutes before onset. Point
estimates are shown here; each is a share of the cases in its own column, and its 95% cluster
bootstrap interval is computed exactly as elsewhere in this appendix. Section 5.3 quotes the
range across cells at the 10- and 30-minute horizons. `n observed` is the denominator at the
first and last horizon, and its fall is the reason a single median is not comparable across cohorts. The
60-minute column is the share of fully observed cases that alerted at the very first opportunity.

| Model | Cohort | 5 min | 10 min | 15 min | 20 min | 30 min | 45 min | 60 min | n observed ≥5 → ≥60 |
|---|---|---|---|---|---|---|---|---|---|
| ITE Transformer | MOVER (EPIC) test | 0.733 | 0.690 | 0.646 | 0.605 | 0.512 | 0.339 | 0.170 | 786 → 311 |
| ITE Transformer | VitalDB | 0.638 | 0.560 | 0.509 | 0.463 | 0.390 | 0.261 | 0.154 | 1007 → 429 |
| ITE Transformer | MOVER (SIS) | 0.594 | 0.547 | 0.504 | 0.469 | 0.377 | 0.247 | 0.125 | 1409 → 665 |
| LSTM | MOVER (EPIC) test | 0.721 | 0.663 | 0.635 | 0.597 | 0.490 | 0.331 | 0.109 | 786 → 311 |
| LSTM | VitalDB | 0.343 | 0.278 | 0.265 | 0.223 | 0.173 | 0.102 | 0.030 | 1007 → 429 |
| LSTM | MOVER (SIS) | 0.453 | 0.392 | 0.346 | 0.319 | 0.253 | 0.167 | 0.047 | 1409 → 665 |
| XGBoost | MOVER (EPIC) test | 0.688 | 0.651 | 0.615 | 0.575 | 0.484 | 0.367 | 0.119 | 786 → 311 |
| XGBoost | VitalDB | 0.502 | 0.470 | 0.453 | 0.425 | 0.366 | 0.237 | 0.054 | 1007 → 429 |
| XGBoost | MOVER (SIS) | 0.656 | 0.597 | 0.565 | 0.520 | 0.460 | 0.326 | 0.080 | 1409 → 665 |
| Random forest | MOVER (EPIC) test | 0.709 | 0.674 | 0.638 | 0.611 | 0.506 | 0.393 | 0.138 | 786 → 311 |
| Random forest | VitalDB | 0.589 | 0.559 | 0.559 | 0.530 | 0.478 | 0.347 | 0.103 | 1007 → 429 |
| Random forest | MOVER (SIS) | 0.736 | 0.674 | 0.640 | 0.600 | 0.526 | 0.403 | 0.114 | 1409 → 665 |
| Logistic regression | MOVER (EPIC) test | 0.726 | 0.692 | 0.658 | 0.630 | 0.547 | 0.401 | 0.122 | 786 → 311 |
| Logistic regression | VitalDB | 0.338 | 0.307 | 0.303 | 0.274 | 0.233 | 0.137 | 0.026 | 1007 → 429 |
| Logistic regression | MOVER (SIS) | 0.664 | 0.611 | 0.573 | 0.546 | 0.474 | 0.353 | 0.093 | 1409 → 665 |

## The full alert window as a constant

**Table A7 | Event cases observed for the whole 60-minute alert window.** Restricting to these
cases makes the observation window a constant rather than a covariate, which is the
window-conditional estimand of Section 5.3. `n` is the number of event cases observed for the
whole window and `Detected` the share of them that alert at all. `Alerted by min 1` is one minus the
Kaplan-Meier survival of time to first alert at the first elapsed monitoring minute, with each
case censored at the end of its own window; it is the censoring-aware form of Section 4.1's
settling. The censoring is not independent of the event, because for an event case a short
observable run-up is an early-onset event rather than missing data, so this describes what the
rule did under the observation these cohorts supplied. Intervals are 95% cluster bootstrap.

| Model | Cohort | n | Detected | Median lead, min (95% CI) | Alerted by min 1 (95% CI) |
|---|---|---:|---:|---|---|
| ITE Transformer | MOVER (EPIC) test | 311 | 0.441 | 47 [33, 59] | 0.532 [0.497, 0.565] |
| ITE Transformer | VitalDB | 429 | 0.247 | 60 [60, 60] | 0.460 [0.428, 0.491] |
| ITE Transformer | MOVER (SIS) | 665 | 0.304 | 57 [51, 59] | 0.308 [0.285, 0.332] |
| LSTM | MOVER (EPIC) test | 311 | 0.598 | 40 [34, 46] | 0.228 [0.198, 0.257] |
| LSTM | VitalDB | 429 | 0.200 | 33 [21, 45] | 0.087 [0.071, 0.105] |
| LSTM | MOVER (SIS) | 665 | 0.433 | 28 [22, 33] | 0.138 [0.120, 0.157] |
| XGBoost | MOVER (EPIC) test | 311 | 0.846 | 40 [34, 44] | 0.188 [0.161, 0.215] |
| XGBoost | VitalDB | 429 | 0.762 | 33 [30, 36] | 0.062 [0.047, 0.077] |
| XGBoost | MOVER (SIS) | 665 | 0.854 | 37 [34, 41] | 0.119 [0.101, 0.136] |
| Random forest | MOVER (EPIC) test | 311 | 0.894 | 41 [35, 45] | 0.183 [0.157, 0.212] |
| Random forest | VitalDB | 429 | 0.851 | 40 [36, 44] | 0.101 [0.082, 0.121] |
| Random forest | MOVER (SIS) | 665 | 0.910 | 42 [39, 45] | 0.166 [0.147, 0.186] |
| Logistic regression | MOVER (EPIC) test | 311 | 0.852 | 42 [36, 45] | 0.226 [0.198, 0.255] |
| Logistic regression | VitalDB | 429 | 0.490 | 31 [26, 37] | 0.036 [0.025, 0.048] |
| Logistic regression | MOVER (SIS) | 665 | 0.857 | 40 [37, 43] | 0.121 [0.104, 0.138] |

## The reporting items that came close

**Table A8 | The four TRIPOD+AI items that came close and missed.** Main text Section 6.1 keeps
items 12e, 23a and 14. The item numbering is that of the TRIPOD+AI statement
[@collins2024tripodai]. This is an author-completed self-assessment of one study, not a validity
assessment of the standard.

| Item | What it asked for | What it did not ask for |
|---|---|---|
| 12a, how the model was applied in validation | Calibration and thresholds fitted on the development validation split and transported unchanged, which is reported | Anything about what that disciplined choice implies; it is the exact setting in which Section 3 holds, so doing the right thing here does not help |
| 20b, participant characteristics | Participant characteristics, which are reported | The distribution of the observed pre-onset window, the variable the reported lead correlates with at ρ = 0.501 to 0.906 |
| 21, event counts | Event and non-event counts, which are reported | How long each case was observed before its event |
| 8c, blinding of outcome assessment | A blinding statement; answered "not applicable" because the outcome is computed from a monitored channel that is also a predictor | The closest the checklist comes to Section 4, and still about blinding rather than about what a timing metric measures |
| 15, model output | The model output and its threshold; answered with the transported threshold itself | Anything about the operating point that threshold defines, which is where the artifact lives (Table 1) |

## The relationship in all five families

Figure 1 plots the transformer in three cohorts. The lead-to-window relationship it shows is
not particular to that model: in the per-case scatter for MOVER (EPIC) test it is present in
every family, with the transformer the limiting case rather than the exception. Figure A1 covers
that cohort only; the other two are in Table A1, where the gradient is positive with its interval
excluding zero in every cell.

![](figures/Figure_A2_wide.png)

**Figure A1 | Alert lead time against observed window length, five model families, MOVER
(EPIC) test.** Axes and overlays as in Figure 1. The relationship holds in every family; the
transformer is the limiting case rather than the exception.

## Alert composition

Section 5.1 reports the prevalent share as a single number per cell. For the transformer that
share is 8.7, 9.6 and 9.0% in the three cohorts, and removing those cases moves its median lead
from 24, 17 and 22 minutes to 21, 15 and 19. Splitting detected event cases by when their first
crossing fell separates alerts that were already active at the first eligible minute from those
raised while the score was still settling and those raised later, which is the disclosure
Section 6.2's first item asks for.

![](figures/Figure_3_wide.png)

**Figure A2 | Composition of detected event cases by elapsed monitoring time at the first
crossing.** Prevalent cases are above threshold at their first eligible minute; warm-up
cases cross within five minutes of it; settled cases cross later. Five model families,
three cohorts, at the transported 80%-sensitivity operating point. The composition differs
sharply across families, in that the transformer's alerts are concentrated in the first five
minutes, the LSTM's are partly so and the tabular families' are not, while the lead-to-window
relationship of Section 3 holds in all of them. That is why Section 4 separates the
transformer's direct mechanism from the cross-family directedness result.

## Risk-set composition, and what fixing the cohort does

The population trajectory scores every case that has a minute in the bin, so its denominator
shrinks and its composition shifts as the bin moves away from onset. For an event case the
observable run-up *is* its time to onset, so a short run-up is not missing data. It is an
early-onset event, and the far bins keep only the long run-ups. That is the same selection
that drives Section 3.

**Fixing the cohort moves the trajectory in both directions** (Figure A3). Recomputing the
same bins on the cases observable back to 60 minutes raises the far end and lowers the near
end, and the two curves cross at 16.4, 12.6 and 14.9 minutes before onset. The first bin
reaching AUROC 0.70 moves from 15 minutes in all three cohorts to 20, 35 and 20. Neither
curve is the true one: which denominator is used is a reporting choice, it changes the
horizon a reader would quote by up to twenty minutes, and it is not currently disclosed.
That is the whole of Section 6.2's third item.

![](figures/Figure_A3_wide.png)

**Figure A3 | Population AUROC with its own risk set, event-aligned.** ITE Transformer, 2-minute
bins from 60 minutes before onset to onset, in three held-out cohorts. Solid and filled is every
case with a minute in the bin, the convention in the published literature, whose denominator
varies; dashed and
open is the cohort fixed to cases observable back to 60 minutes. Bands are 95% cluster bootstrap
over subjects, or over cases in MOVER (SIS). The lower row is the number of cases contributing to
each bin, on its own scale per cohort. The dotted line marks 0.5, the solid rule 0.70, and the
cross marks where the two curves meet.

## Event and control score on the event-aligned axis

The shape a reader expects of a continuously read score, rising in the cases that go on to
have an event and much flatter in the rest, is **present in all fifteen cells** (Figure A4).
Three things about it are worth reporting, and none is visible in a trend statistic.

**When the separation arrives runs opposite to near-onset discrimination.** For the three
tabular families the event and control means are already distinguishable 60 minutes before
onset in every cohort, the gap at that range running +0.049 to +0.109 with every interval
excluding zero. For the transformer the gap at 60 minutes **covers zero in all three
cohorts** (−0.023 [−0.080, 0.035], −0.014 [−0.057, 0.030] and −0.006 [−0.043, 0.032]), and
first excludes it at 35, 20 and 30 minutes. The LSTM sits between the two. The family whose
scores separate latest is the one with the highest discrimination near onset.

**The event mean rises toward onset, and for the transformer the control mean falls by as
much.** Over the hour the transformer's event mean rises +0.239, +0.266 and +0.269, which is
the tendency a reader expects and it is substantial, while its control mean falls −0.252,
−0.263 and −0.196, so about half of the widening is carried by the controls. The LSTM's
control mean also falls, by 0.059 to 0.185. For the tabular families the control mean moves
between −0.070 and +0.021, rising in several cells, and the widening is almost entirely
event-side. So "the score rises in patients who are about to have an event" holds in every
cell here; what it leaves out is that for the transformer an equal share of the widening is
the control mean coming down, and an event-only trend statistic cannot separate the two.

**The split follows the representation more than the architecture.** The control side
contributes most where the window is read as a sequence and least where the model reads one
feature vector per scored minute, carrying each channel's last observation forward, so it sees
a level and has little shape to drift with. The ordering is not clean: the tabular families'
control means fall in MOVER (EPIC) as well and only flatten in the two external cohorts.
Representation and family are not crossed in this design, so this is a reading the data
supports rather than a hypothesis it tests. It does say where to look: **the control-side contribution is a thing
to measure in models given freer access to the input series**, and reporting the two sides of
a widening gap separately is what makes it visible.

Three things this figure is not. The control series is aligned on the sampled pseudo-onset of
Section 2 rather than on an event, so its fall is behavior over the last hour of a comparable
window and not an approach to anything. Figure A5 plots medians and this figure means, and the
two are not interchangeable here. And the two figures use different alignments: Figure A5's
axis is elapsed time from the case's first scored minute and covers the first ten minutes of
the record, where the transformer has just settled above its own 0.894 threshold, whereas the bins here
sit far later in the case, where its event mean is 0.383. **The two are not in conflict, and
the length of the plateau is what reconciles them.** The median score holds at or above the
transported threshold through elapsed minute 24, 21 and 17 in event cases and 23, 20 and 16
in controls, then falls to 0.03 to 0.31 by minute 30. Figure A5 covers the first ten of those
minutes and stops inside the plateau; every bin in this figure falls after it in all but the
shortest records.

![](figures/Figure_A4_wide.png)

**Figure A4 | Mean score in event and control cases against minutes before onset.** Rows are
cohorts, columns are model families, the same grid as Figure A5, on the event-aligned axis
instead of the elapsed one. Event cases solid and filled, control cases dashed and open; bands
are 95% cluster bootstrap. Bins are the 13 centers at five-minute spacing from 60 minutes
before onset; the
bin at onset is empty by construction, because no minute is strictly before its own reference
time, so the series ends at 5 minutes. Control cases are aligned on a sampled pseudo-onset.

## Score against elapsed monitoring time

Section 4.1 reads the first ten monitored minutes of every case, and reports that only the ITE
Transformer clears its own threshold there. The margins for the others are wide. Over those ten
minutes the highest median score reached in either group is 0.69 against a threshold of 0.78 for
logistic regression in MOVER (EPIC), 0.65 against a threshold of 0.91 for XGBoost, and 0.54
against a threshold of 0.79 for random forest; the LSTM clears its threshold in MOVER (EPIC)
event cases and nowhere else. This is that view for all fifteen cells, on the elapsed axis rather
than the event-aligned one of Figure A4.

![](figures/Figure_1_wide.png)

**Figure A5 | Median score against elapsed monitoring time, with each family's own alert
threshold.** Rows are cohorts, columns are model families. Elapsed time is measured from the
case's first scored minute. The dashed rule in each panel is that family's transported
raw-score threshold at the 80%-sensitivity target, transferred unchanged from the MOVER
(EPIC) validation split. Only the ITE Transformer's early rise clears its own threshold, and
it does so in event and control cases together. The elevation ends around minute 20, past the
right edge of this axis. This axis is elapsed time; the event-aligned view is Figure A4.

## Departure timing: searched for, not found

We asked whether the score departs from its own baseline before mean arterial pressure
departs from its, within an episode, under a pre-specified rule: baseline is the median of
the episode's first ten eligible minutes, the robust scale is 1.4826 × the median absolute
deviation over the same minutes, and a departure is the first minute beginning a run of at
least three consecutive minutes more than 1.5 scale units in the deteriorating direction.

**Score departure does not precede MAP departure.** For XGBoost the share of episodes in
which the score departs first is significantly *below* one half in all three cohorts. For the
transformer the score does not depart at all in most episodes, because its baseline sits at the
top of its range: a median baseline of 0.94 to 0.97 leaves median headroom of 0.005 to 0.031,
which is less than the bar its own rule sets in all three cohorts, so there is not enough room
above baseline for a departure to register.
Both facts are reported so the negative cannot be read as an unfair rule. Sensitivity
analyses at a 2.0 scale threshold, a five-minute run length, and a search capped at the
60-minute window all leave the direction unchanged.

The question was pre-specified and the answer constrains Section 4: whatever produces the
reported lead, it is not the score moving before the monitored variable does.

## Lead time by band, the transformer's three cohorts

**Table A9 | Median alert lead time inside quantile-derived bands of observed window, ITE Transformer.** ITE
Transformer, three held-out cohorts, at the transported 80%-sensitivity operating point.
Quintile edges are cut within each cell on detected cases; where the observed window is censored
at the 60-minute alert window the upper quintiles collapse and the realized band count is
reported rather than assumed. `Observed window, min` is the median observed pre-onset window of that band's cases rather than
an edge. Intervals are 95% cluster bootstrap over subjects, or over cases in MOVER (SIS). All fifteen cells are Table A1; the detection rate these bands condition on is Table A5.
Section 3.1 reports the contrast this table carries.

| Cohort | Band | n | Observed window, min | Median lead, min (95% CI) | Lead / window (95% CI) |
|---|---:|---:|---:|---|---|
| MOVER (EPIC) test | 1 | 139 | 10 | 9 [8, 9] | 0.88 [0.85, 0.89] |
| MOVER (EPIC) test | 2 | 111 | 19 | 18 [17, 18] | 0.94 [0.94, 0.95] |
| MOVER (EPIC) test | 3 | 121 | 33 | 31 [29, 32] | 0.97 [0.96, 0.97] |
| MOVER (EPIC) test | 4 | 240 | 60 | 46 [44, 50] | 0.98 [0.96, 0.98] |
| VitalDB | 1 | 143 | 7 | 5 [5, 6] | 0.83 [0.83, 0.83] |
| VitalDB | 2 | 140 | 12 | 10 [10, 11] | 0.91 [0.90, 0.91] |
| VitalDB | 3 | 132 | 20 | 19 [18, 20] | 0.94 [0.94, 0.95] |
| VitalDB | 4 | 134 | 40 | 38 [37, 40] | 0.97 [0.97, 0.97] |
| VitalDB | 5 | 135 | 60 | 59 [57, 60] | 0.98 [0.98, 1.00] |
| MOVER (SIS) | 1 | 199 | 8 | 6 [5, 6] | 0.80 [0.80, 0.82] |
| MOVER (SIS) | 2 | 179 | 17 | 14 [13, 15] | 0.86 [0.84, 0.91] |
| MOVER (SIS) | 3 | 186 | 29 | 27 [26, 28] | 0.94 [0.93, 0.96] |
| MOVER (SIS) | 4 | 362 | 60 | 46 [43, 49] | 0.95 [0.93, 0.97] |

## Cohort composition and the control side

**Table A10 | Cohort composition, PPV against prevalence, and the control side.** `PPV −
prevalence` is the lift over the base rate of the cohort the PPV is measured in, because raw PPV
is not comparable across cohorts whose prevalence runs from 0.359 to 0.560. `Alerted by elapsed
min 1` is one minus the Kaplan-Meier survival of time to first alert at the first elapsed
monitoring minute, censored at the end of each case's own window; it is the censoring-aware form
of Section 4.1's settling. Intervals are 95% cluster bootstrap.

| Model | Cohort | Event cases | Control cases | Prevalence | PPV − prevalence | Min. above thr., controls (95% CI) | Alerted by elapsed min 1 (95% CI) |
|---|---|---:|---:|---:|---:|---|---|
| ITE Transformer | MOVER (EPIC) test | 786 | 618 | 0.560 | +0.065 | 0.150 [0.050, 0.233] | 0.532 [0.497, 0.565] |
| ITE Transformer | VitalDB | 1007 | 1797 | 0.359 | +0.021 | 0.183 [0.163, 0.233] | 0.460 [0.428, 0.491] |
| ITE Transformer | MOVER (SIS) | 1409 | 1232 | 0.534 | +0.051 | 0.025 [0.017, 0.047] | 0.308 [0.285, 0.332] |
| LSTM | MOVER (EPIC) test | 786 | 618 | 0.560 | +0.101 | 0.017 [0.000, 0.027] | 0.228 [0.198, 0.257] |
| LSTM | VitalDB | 1007 | 1797 | 0.359 | +0.236 | 0.000 [0.000, 0.000] | 0.087 [0.071, 0.105] |
| LSTM | MOVER (SIS) | 1409 | 1232 | 0.534 | +0.151 | 0.000 [0.000, 0.000] | 0.138 [0.120, 0.157] |
| XGBoost | MOVER (EPIC) test | 786 | 618 | 0.560 | +0.165 | 0.000 [0.000, 0.000] | 0.188 [0.161, 0.215] |
| XGBoost | VitalDB | 1007 | 1797 | 0.359 | +0.253 | 0.000 [0.000, 0.000] | 0.062 [0.047, 0.077] |
| XGBoost | MOVER (SIS) | 1409 | 1232 | 0.534 | +0.180 | 0.000 [0.000, 0.000] | 0.119 [0.101, 0.136] |
| Random forest | MOVER (EPIC) test | 786 | 618 | 0.560 | +0.143 | 0.000 [0.000, 0.000] | 0.183 [0.157, 0.212] |
| Random forest | VitalDB | 1007 | 1797 | 0.359 | +0.221 | 0.000 [0.000, 0.000] | 0.101 [0.082, 0.121] |
| Random forest | MOVER (SIS) | 1409 | 1232 | 0.534 | +0.154 | 0.000 [0.000, 0.000] | 0.166 [0.147, 0.186] |
| Logistic regression | MOVER (EPIC) test | 786 | 618 | 0.560 | +0.128 | 0.000 [0.000, 0.017] | 0.226 [0.198, 0.255] |
| Logistic regression | VitalDB | 1007 | 1797 | 0.359 | +0.237 | 0.000 [0.000, 0.000] | 0.036 [0.025, 0.048] |
| Logistic regression | MOVER (SIS) | 1409 | 1232 | 0.534 | +0.152 | 0.000 [0.000, 0.000] | 0.121 [0.104, 0.138] |

## Multiplicity

The two nulls of Section 3.3 form one Benjamini–Hochberg family of 75 formal tests,
adjusted within that family, of which 57 are significant at *q* < 0.05. The stratification of Section 3.1 produces intervals rather than tests and does not enter the family.

## Seeds and reproducibility

Cluster bootstraps use 2,000 replicates and permutation nulls 1,000, with the clustering
unit the subject for two cohorts and the case for MOVER (SIS), whose released subject key is
a copy of the case identifier. Model training and the reference-time construction are fixed
at a single seed, reported in Appendix A.1.
