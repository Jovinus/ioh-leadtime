# Why the paper is shaped this way

This is the argument document. `PAPER.md` is the paper; this is the reasoning behind its
structure — what each section is for, which reader objection it answers, and what each
exhibit is doing there. It exists so that a decision about the shape of the paper can be
checked against the reason for it rather than re-argued, and it is inlined into `REVIEW.md`
so the circulating copy carries the reasoning with the text.

---

## Thesis

> A continuously read clinical prediction model reports a median alert lead time. The name
> promises warning time. On three cohorts and five model families the quantity substantially
> measures **how long the patient happened to be observed**. Following a reporting standard
> did not surface this: a TRIPOD+AI checklist was completed for the work, and TRIPOD+AI does
> not ask for anything that would have revealed it.

## The frame underneath it

The thesis is one instance of a general pattern, and the pattern is what makes this a paper
for this venue rather than a note about one metric.

> **Every quantity here is read as a claim about one patient's trajectory, and none of them
> is computed that way.**

| The quantity | How it is read | What it measures |
|---|---|---|
| Median alert lead time | "this system will give me about this much warning" | largely the length of the window the crossing was searched in (§3) |
| Event-aligned trend in discrimination | "the score sharpens as my patient deteriorates" | separation *between* cases at a fixed lead, on a risk set that shrinks and re-composes as the lead grows (A.6) |
| "The score rises before the event" | one patient's score climbing | a cohort average, arriving late, and carried as much by controls falling as by events rising (A.7) |

The gap in each row is the same gap: a population quantity given a name that describes an
individual experience. That is why the remedy in §6.2 is disclosure rather than a better
statistic — the numbers are not wrong, the reading of them is unlicensed, and what closes the
gap is reporting the denominator beside the quantity.

**This frame is deliberately not stated as a claim in the paper.** §3 to §5 are measurements;
promoting the frame to a thesis would require showing it in domains this data cannot reach.
It sits in §6.3 as "the general shape", one paragraph, and in the choice of what §6.2 asks
for. Reviewers who want the general claim will ask for it; the answer is that three
perioperative cohorts cannot settle it, which §7 says.

---

## The sections, and the objection each one answers

The order is not thematic. Each section exists because a reader who accepted the previous one
will raise a specific objection, and the section answers it before moving on.

| § | Its job | The objection it answers |
|---|---|---|
| **1** | Establish that lead time contains a dependence its name does not | — (sets up the claim) |
| **2** | Fix the measurement conditions: per-minute reading, transported thresholds, the alert rule | "you chose an operating point that produces this" — nothing is reselected anywhere |
| **3.1** | The finding in minutes, stratified | "a ratio can be made to say anything" — so the headline result is in the units the metric is read in, with no ratio |
| **3.2** | The same fact as a ratio, all fifteen cells | "you are showing me one model" |
| **3.3** | The two nulls | ⭐ **"a bounded search window guarantees some correlation"** — the sharpest objection, answered in place rather than in limitations |
| **4.1** | One model sits above its own threshold within a minute | "so what is the mechanism?" |
| **4.2** | Every family's trajectory is volatile rather than rising | ⭐ **"this is one architecture behaving badly"** |
| **4.3** | What the mechanisms do not license | "you are claiming the score sees the patient deteriorating" |
| **5.1** | Prevalent alerts are not the explanation | "the metric is just counting cases that arrived pre-flagged" |
| **5.2** | Suppressing the first minutes does not fix it | "then discard the warm-up" — tested, and it fails |
| **6.1** | The items the checklist did satisfy | "this is a non-adherence problem" |
| **6.2** | Four items that would have caught it | ⭐ **the contribution** |
| **6.3** | What generalises and what does not | "is this just about hypotension?" |
| **7** | Limitations | — |

The three starred rows are where the paper is won or lost. §3.3 decides whether the finding
survives; §4.2 decides whether it reads as a result about evaluation or as a complaint about
one model; §6.2 is what the venue is for.

### Why §3.3 comes before the mechanism rather than after it

A reader who has just been shown that lead correlates with window length has exactly one
thought, and it is that the correlation is structural: a crossing cannot be found outside the
window it is searched in, so the ratio is bounded in [0, 1] and some positive relationship is
guaranteed. Everything after §3 is worthless if that thought is left standing. Putting the
nulls in limitations would be answering it in the place a reader looks last.

The cross-case shuffle strengthens the finding beyond a raw correlation. It reassigns whole
score sequences across cases, so each recipient keeps its own window and reference time while
receiving another case's trajectory. Aggregate ratios and correlations remain high, but the
null changes the detected set and is biased upward. It therefore shows that generic
elapsed-time shape and the window can produce a strong association without preserving the
recipient--trajectory correspondence; it does not show that all patient-specific information
is absent.

### Why §4 separates a direct mechanism from a cross-family descriptive property

Because they carry different loads, and collapsing them loses one of them.

- **§4.1 is specific.** The transformer is above its own transported threshold within a
  minute of its first scored minute, in event and control cases alike. No other family does
  this. On its own, this invites the reply that the paper has found one badly behaved model,
  and the §3 result would be filed as a curiosity about transformers.
- **§4.2 is cross-family but descriptive.** Directedness is +0.021 to +0.151 across all
  fifteen cells in the spanning-event sample: these trajectories travel a great deal and end
  near where they started. This is consistent with fluctuation-driven crossings but does not
  establish when or whether a particular threshold is touched.

The split is load-bearing in both directions, and both guards matter:

- ⛔ Do **not** let §4.1 read as an architecture defect. It describes a pipeline as deployed
  with one scoring policy on these cohorts.
- ⛔ Do **not** soften that the transformer is the worst case on this axis. It is, and hedging
  it would be the mirror-image error.

### Why §5 reports two remedies that failed

Because a metric with a plausible-looking repair that fails is a worse problem than one with
no repair at all — the repair gets adopted. Both fixes are what a convinced reader reaches
for, so leaving them untested leaves the paper's conclusion optional.

Warm-up suppression is the one to watch. It follows so directly from §4.1 that a reader will
propose it, and it costs 3.6 to 6.8 points of sensitivity for 0 to 3.2 points of specificity
while not addressing §3 at all: the surviving alerts still fire at the first opportunity in
whatever window remains. ⛔ It is reported as a result and **never** recommended.

### Why §6 exists in this form

The paper could have said "this study under-reported" and been shorter. It would also have
been wrong, and the wrong version is less useful.

TRIPOD+AI is a **reporting** standard: it specifies what must be disclosed so a reader can
appraise a study. It does not claim to specify which quantities are valid measures of what
their names suggest. An author at full adherence can therefore report a median lead time as
evidence of validity and be entirely compliant, and a reviewer working the item list finds
nothing to raise. That motivates a **task-specific extension**, not a claim of non-adherence
or a correction to a general minimum reporting standard.

§6.1 walks the items that came closest so the gap is demonstrated rather than asserted. Item
14 is the instructive one: the study *did* report that arterial-line placement selects
toward longer, higher-risk operations, so the information that observation length is not
distributed at random **was already in the paper** — filed as a limitation, where it
reads as a caveat about which patients the findings extend to. Nothing in the standard
connects it to a timing metric three tables away.

---

## Exhibits: what each is for, and what dropping it would cost

| Exhibit | Where | What it shows | Cost of dropping it |
|---|---|---|---|
| **Table 1** | §1 | What the label invites, what the number supports, and the disclosure that would close the gap | ⛔ Not a candidate. The reader-facing exhibit the reporting argument turns on. `measure_pages.py` now prices removing it at 0.00 pp, which is a statement about page breaks, not about its value |
| **Table A7** | A.5 | Case-level operating point behind every reported lead time, all fifteen cells with intervals | It answers the "it just alerts constantly" objection, and it is what §6.1's TRIPOD item 23a argument points at. Moved out of the body on 2026-08-29 to pay for Table 1 |
| **Figure 1** | §3.3 | Every detected case's lead against its window, with the ceiling diagonal and the shuffle-null band | The null becomes a table of numbers; the reader cannot see that the null covers the observed points |
| **Figure 2** | §4.1 | Median score against elapsed time, five families, event and control, each family's own threshold drawn on the same axes | Mechanism 1 becomes an assertion. Drawing the threshold on the same axes is the whole point — what separates the transformer is not the shape of its rise but whether the rise clears its own cut |
| **Table A2** | A.1 | The quintile gradient in all fifteen cells | §3.1's "15 of 15" loses its per-cell backing |
| **Table A5** | A.2 | Observed ratio against both nulls, all fifteen cells | §3.3's ranges lose their per-cell backing |
| **Table A6** | A.3 | Path decomposition | §4.2 becomes prose ranges only; §6.2's fourth item loses its worked example |
| **Figure A1** | A.4 | Figure 1 for all five families | The "not one architecture" guard loses its picture |
| **Figure A4** | A.5 | Prevalent / warm-up / settled composition | §6.2's first item loses its worked example, and it is the item that would have made §4.1 visible on inspection |
| **Figure A5** | A.6 | Population AUROC with CI beside N(t): all cases against a cohort fixed to 60 minutes | ⭐ §6.2's third item goes back to being the only one of the four asserted without an exhibit |
| **Figure A3** | A.7 | Event and control mean score on the event-aligned axis, five families, three cohorts | ⭐ The shape the reader arrived with is never put on the page, and the paper never meets its own audience's expectation |

### The two newest exhibits, and why they were added

Both close the same hole: the paper proved that its metrics do not measure what their names
suggest, but it never showed the reader the picture they walked in with. Argument without
that picture is correct and abstract.

**Figure A5 (A.6) — the denominator moves.** §6.2's third item asks that N(t) be reported
beside any event-aligned trajectory. Items 1 and 4 point at exhibits; item 3 was asking the
reader to take it on trust, which made it the weakest of the four. The figure also carries a
result the prose did not: fixing the cohort to cases observable back to 60 minutes **raises
the far end and lowers the near end**, the curves cross at 16.4, 12.6 and 14.9 minutes, and
the first bin reaching AUROC 0.70 moves from 15 minutes in all three cohorts to 20, 35 and
20. The published convention *understates* far-horizon discrimination. Neither curve is the
true one — which denominator is used is a reporting choice worth up to twenty minutes of
quoted horizon, and it is not currently disclosed.

**Figure A3 (A.7) — the shape a reader expects.** Averaged over cases, the score does what
everyone expects: it rises where an event follows and is flat or falls where none does, in
all fifteen cells. Reporting that is not a concession, because two things about it are
invisible in any trend statistic:

1. **When the separation arrives runs opposite to near-onset discrimination.** The three
   tabular families are already apart 60 minutes out in every cohort (+0.049 to +0.109, every
   interval excluding zero). The transformer's gap covers zero at 60 minutes in all three
   cohorts and first excludes it at 35, 20 and 30 minutes. The family whose scores separate
   latest has the highest discrimination near onset.
2. **The widening is not only the event side.** The transformer's event mean rises +0.239,
   +0.266 and +0.269 while its control mean falls −0.252, −0.263 and −0.196 — about half the
   separation is the controls. For the tabular families the control mean moves between −0.070
   and +0.021, and in several cells it rises.

So "the score rises in patients who are about to have an event" describes part of one cell.
That is the same species of claim as the lead-time claim, and it fails in the same way.

⚠ **Three things A.7 must keep disclosing**, because a reader will otherwise think Figure A3
and Figure 2 contradict each other:

- Control cases are aligned on the **sampled pseudo-onset** of §2, not on an event, so the
  control fall is behaviour over the last hour of a comparable window rather than an approach
  to anything.
- **Figure 2 plots medians and Figure A3 plots means.** In these bins the two differ
  substantially, because the score's distribution within a bin is far from symmetric. They
  are not interchangeable.
- **The alignments differ.** Figure 2's axis is elapsed time from the case's first scored
  minute and covers the first ten minutes of the record, where the transformer has just
  settled above its own 0.894 threshold. Figure A3's bins sit far later in the case, where its
  event mean is 0.383. Both are the same cached raw score from the same run: the score does
  not stay at the level it reaches during warm-up, which is what §4.2's directedness measures.

---

## What the framing makes unnecessary

Kept out on purpose, so a reader of the review copy does not propose them back in:

| Left out | Why |
|---|---|
| A model contribution | The paper is a measurement and a reporting recommendation. No model is proposed for clinical use |
| Any discrimination ranking | Not disputed and not measured. A ranking would invite the reading that this is a critique of one model |
| A recommended repair | Both natural ones were tested and fail (§5). Proposing a third untested one would repeat the error the paper is about |
| Anything about physiology | The outcome is defined on MAP and MAP is an input channel, so the model reads the quantity the label is computed from. ⛔ Enforced by `check_phrases.py` |
| Per-patient trajectory statistics | A separate paper. A.7 is a cohort average by design, not a per-case claim |
| The 60→10 path window | The transformer's net displacement there is indistinguishable from zero and the ratio becomes a division by approximately nothing. Only 60→5 is quotable |

---

## Guards that must survive any edit

Carried here from `README.md` so this file holds the argument end to end.

- ⛔ **No claim that the model reads or foresees a disease process.** `check_phrases.py`
  enforces the common phrasings; the general case needs a reader.
- ⛔ **The plateau is not a defect of one architecture** — present in all five families as a
  matter of degree (ratio 0.455 to 0.944), the transformer the limiting case. Equally, **do
  not soften** that the transformer is the worst case on this axis.
- ⛔ **Never recommend warm-up suppression.** It was tested and it fails.
- ⛔ **The construct named in `check_phrases.py`'s first pattern is banned outright**, as a
  bare word rather than only in its usual two-word form: it would identify the authors, and a
  line break would defeat a bigram pattern.
- Report the N2 caveats at full strength — the observed ratio sits slightly *below* the
  shuffle null, and both variants bias **upward**, the direction that favours our own reading.
  The null is a ceiling, not a point estimate.
- ⛔ **Table 1 and §6.2's four items are not cut candidates.** The first is the reader-facing
  exhibit in the paper; the second is the contribution.
