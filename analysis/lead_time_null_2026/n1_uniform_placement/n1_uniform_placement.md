# N1 — uniform-placement null

A crossing placed uniformly at random inside each case's own observed window gives a median ratio of 0.5 by construction. This fixes the reference point so that the observed ratio cannot be dismissed as an artefact of the bound.

Excess over the uniform null ranges **-0.067 to +0.421** across the fifteen cells.

**This is necessary but weak alone.** It rules out only the crudest reading of the objection. It does not distinguish a ratio that reflects case-specific timing from one that is a property of the scoring policy; that is N2's question.

| Model | Cohort | n | Observed ratio (95% CI) | Uniform-null ratio (95% CI) | Excess | Observed lead, min | Uniform-null lead, min | p |
|---|---|---|---|---|---|---|---|---|
| ITE Transformer | MOVER (EPIC) test | 611 | 0.944 (0.941–0.950) | 0.524 (0.491–0.567) | +0.421 | 24 | 12.5 | 0.002 |
| ITE Transformer | VitalDB | 684 | 0.923 (0.909–0.929) | 0.532 (0.500–0.573) | +0.391 | 17 | 8.9 | 0.002 |
| ITE Transformer | MOVER (SIS) | 926 | 0.899 (0.882–0.909) | 0.527 (0.500–0.567) | +0.372 | 22 | 11.5 | 0.002 |
| LSTM | MOVER (EPIC) test | 634 | 0.851 (0.833–0.867) | 0.522 (0.483–0.563) | +0.329 | 23 | 13.6 | 0.002 |
| LSTM | VitalDB | 495 | 0.619 (0.571–0.683) | 0.534 (0.500–0.583) | +0.085 | 9 | 8.2 | 0.002 |
| LSTM | MOVER (SIS) | 777 | 0.717 (0.667–0.778) | 0.524 (0.500–0.562) | +0.192 | 15 | 13.8 | 0.002 |
| XGBoost | MOVER (EPIC) test | 637 | 0.719 (0.667–0.758) | 0.519 (0.483–0.558) | +0.200 | 21 | 16.4 | 0.002 |
| XGBoost | VitalDB | 699 | 0.467 (0.400–0.517) | 0.521 (0.483–0.556) | -0.054 | 13 | 15.5 | 0.016 |
| XGBoost | MOVER (SIS) | 1113 | 0.600 (0.556–0.633) | 0.518 (0.500–0.550) | +0.082 | 19 | 17.9 | 0.002 |
| Random forest | MOVER (EPIC) test | 651 | 0.714 (0.667–0.755) | 0.519 (0.483–0.556) | +0.196 | 22 | 16.7 | 0.002 |
| Random forest | VitalDB | 809 | 0.533 (0.500–0.583) | 0.523 (0.500–0.556) | +0.011 | 15 | 14.7 | 0.824 |
| Random forest | MOVER (SIS) | 1196 | 0.667 (0.623–0.705) | 0.518 (0.500–0.550) | +0.149 | 22 | 17.6 | 0.002 |
| Logistic regression | MOVER (EPIC) test | 658 | 0.781 (0.738–0.833) | 0.520 (0.483–0.557) | +0.260 | 23 | 16.0 | 0.002 |
| Logistic regression | VitalDB | 464 | 0.455 (0.389–0.517) | 0.521 (0.471–0.567) | -0.067 | 14 | 15.2 | 0.016 |
| Logistic regression | MOVER (SIS) | 1113 | 0.618 (0.583–0.667) | 0.518 (0.500–0.550) | +0.100 | 21 | 18.0 | 0.002 |


## Method

Per case the null draws a crossing minute uniformly from the integers 1..L, where L is the case's own pre-onset observation length capped at the published 60-minute alert window -- the same L the observed ratio is divided by. The null is redrawn 1,000 times. The observed side carries a 2,000-replicate cluster bootstrap, clustering on patient for MOVER (EPIC) and VitalDB and on case for MOVER (SIS). `p` is two-sided by interval inversion on the null draws, floored at 2/1,000.
