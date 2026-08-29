# N2 — cross-case score-sequence shuffle null

Whole score sequences are permuted across cases inside a cell. Each recipient keeps its own window length, reference time and denominator; only the sequence it is scored with comes from somebody else. The crossing is recomputed against the unchanged transported threshold.

The permutation keeps the score's generic temporal profile, including the plateau, and destroys any correspondence between a sequence and the patient it came from.

## Headline

On the primary `hold` variant, the observed median ratio exceeds the shuffled null in **0 of 15** cells, by **-0.267 to -0.025**, with **15 of 15** at p < 0.05. Excess Spearman ranges **-0.182 to -0.027**.

## Primary variant — `hold`

Donor drawn uniformly from every case in the cell; its last observed value held forward over any recipient minutes it does not reach.

| Model | Cohort | Observed ratio | Shuffled ratio (95% CI) | Excess | p | Observed ρ | Shuffled ρ (95% CI) | Excess ρ | p (ρ) |
|---|---|---|---|---|---|---|---|---|---|
| ITE Transformer | MOVER (EPIC) test | 0.944 | 0.970 (0.967–0.974) | -0.025 | 0.002 | 0.706 | 0.888 (0.855–0.920) | -0.182 | 0.002 |
| ITE Transformer | VitalDB | 0.923 | 0.966 (0.963–0.967) | -0.043 | 0.002 | 0.906 | 0.941 (0.926–0.955) | -0.035 | 0.002 |
| ITE Transformer | MOVER (SIS) | 0.899 | 0.949 (0.941–0.950) | -0.050 | 0.002 | 0.801 | 0.877 (0.855–0.895) | -0.076 | 0.002 |
| LSTM | MOVER (EPIC) test | 0.851 | 0.913 (0.900–0.923) | -0.062 | 0.002 | 0.650 | 0.825 (0.784–0.860) | -0.174 | 0.002 |
| LSTM | VitalDB | 0.619 | 0.870 (0.850–0.883) | -0.251 | 0.002 | 0.759 | 0.845 (0.798–0.886) | -0.086 | 0.002 |
| LSTM | MOVER (SIS) | 0.717 | 0.873 (0.857–0.887) | -0.156 | 0.002 | 0.501 | 0.682 (0.636–0.727) | -0.181 | 0.002 |
| XGBoost | MOVER (EPIC) test | 0.719 | 0.842 (0.814–0.867) | -0.123 | 0.002 | 0.558 | 0.701 (0.651–0.751) | -0.143 | 0.002 |
| XGBoost | VitalDB | 0.467 | 0.723 (0.667–0.768) | -0.257 | 0.002 | 0.599 | 0.636 (0.569–0.698) | -0.038 | 0.26 |
| XGBoost | MOVER (SIS) | 0.600 | 0.779 (0.750–0.800) | -0.179 | 0.002 | 0.573 | 0.632 (0.590–0.673) | -0.058 | 0.018 |
| Random forest | MOVER (EPIC) test | 0.714 | 0.839 (0.816–0.867) | -0.125 | 0.002 | 0.584 | 0.714 (0.665–0.764) | -0.130 | 0.002 |
| Random forest | VitalDB | 0.533 | 0.764 (0.721–0.800) | -0.231 | 0.002 | 0.651 | 0.678 (0.622–0.729) | -0.027 | 0.326 |
| Random forest | MOVER (SIS) | 0.667 | 0.811 (0.783–0.833) | -0.145 | 0.002 | 0.618 | 0.659 (0.625–0.692) | -0.041 | 0.014 |
| Logistic regression | MOVER (EPIC) test | 0.781 | 0.872 (0.849–0.898) | -0.092 | 0.002 | 0.597 | 0.739 (0.694–0.779) | -0.141 | 0.002 |
| Logistic regression | VitalDB | 0.455 | 0.721 (0.667–0.781) | -0.267 | 0.002 | 0.607 | 0.642 (0.549–0.720) | -0.035 | 0.428 |
| Logistic regression | MOVER (SIS) | 0.618 | 0.782 (0.750–0.800) | -0.165 | 0.002 | 0.597 | 0.644 (0.607–0.682) | -0.047 | 0.014 |


## Sensitivity variant — `longer`

Donor drawn only from cases whose window is at least as long as the recipient's, so no filling is needed. Selects donors on length, which biases the null ratio up.

| Model | Cohort | Observed ratio | Shuffled ratio (95% CI) | Excess | p | Observed ρ | Shuffled ρ (95% CI) | Excess ρ | p (ρ) |
|---|---|---|---|---|---|---|---|---|---|
| ITE Transformer | MOVER (EPIC) test | 0.944 | 0.962 (0.951–0.971) | -0.018 | 0.004 | 0.706 | 0.783 (0.705–0.856) | -0.077 | 0.052 |
| ITE Transformer | VitalDB | 0.923 | 0.957 (0.947–0.969) | -0.034 | 0.002 | 0.906 | 0.933 (0.890–0.967) | -0.027 | 0.194 |
| ITE Transformer | MOVER (SIS) | 0.899 | 0.918 (0.900–0.938) | -0.019 | 0.024 | 0.801 | 0.775 (0.713–0.827) | +0.026 | 0.34 |
| LSTM | MOVER (EPIC) test | 0.851 | 0.866 (0.833–0.893) | -0.015 | 0.298 | 0.650 | 0.673 (0.596–0.743) | -0.022 | 0.51 |
| LSTM | VitalDB | 0.619 | 0.752 (0.667–0.833) | -0.133 | 0.002 | 0.759 | 0.705 (0.593–0.804) | +0.054 | 0.326 |
| LSTM | MOVER (SIS) | 0.717 | 0.700 (0.633–0.767) | +0.016 | 0.634 | 0.501 | 0.455 (0.368–0.547) | +0.046 | 0.282 |
| XGBoost | MOVER (EPIC) test | 0.719 | 0.760 (0.705–0.800) | -0.040 | 0.104 | 0.558 | 0.581 (0.503–0.649) | -0.023 | 0.54 |
| XGBoost | VitalDB | 0.467 | 0.591 (0.517–0.652) | -0.124 | 0.002 | 0.599 | 0.493 (0.400–0.580) | +0.105 | 0.018 |
| XGBoost | MOVER (SIS) | 0.600 | 0.681 (0.633–0.722) | -0.081 | 0.002 | 0.573 | 0.488 (0.429–0.541) | +0.086 | 0.002 |
| Random forest | MOVER (EPIC) test | 0.714 | 0.777 (0.733–0.817) | -0.063 | 0.004 | 0.584 | 0.599 (0.531–0.667) | -0.015 | 0.654 |
| Random forest | VitalDB | 0.533 | 0.685 (0.625–0.733) | -0.151 | 0.002 | 0.651 | 0.555 (0.479–0.627) | +0.096 | 0.01 |
| Random forest | MOVER (SIS) | 0.667 | 0.741 (0.700–0.783) | -0.074 | 0.002 | 0.618 | 0.536 (0.486–0.589) | +0.083 | 0.002 |
| Logistic regression | MOVER (EPIC) test | 0.781 | 0.802 (0.767–0.842) | -0.022 | 0.236 | 0.597 | 0.612 (0.544–0.676) | -0.014 | 0.72 |
| Logistic regression | VitalDB | 0.455 | 0.577 (0.500–0.650) | -0.122 | 0.004 | 0.607 | 0.486 (0.374–0.584) | +0.121 | 0.014 |
| Logistic regression | MOVER (SIS) | 0.618 | 0.734 (0.692–0.767) | -0.116 | 0.002 | 0.597 | 0.548 (0.495–0.595) | +0.049 | 0.044 |


## How to read this, and what it cannot show

Both variants bias the null **upward**, by different amounts and for different reasons -- `longer` because a long donor's window starts mid-case where the score is already on the plateau, `hold` because a held plateau value sustains a crossing across the recipient's tail. Upward bias is the direction that makes "shuffled is close to observed" easier to obtain, which is the direction that favours reading the ratio as a property of the scoring policy. A null that agrees with the observed value is therefore weaker evidence than it appears, and that is stated rather than left for a reader to notice.

What the two variants together do establish is a bracket. Where the observed ratio sits **above** both nulls, the upward bias cannot account for it, and the timing carries information the shuffle destroyed.

## Method

Donor sequences are laid onto recipients by elapsed minutes from the start of the recipient's own alert window, never by `t_to_event`: aligning by `t_to_event` would carry the donor's distance-to-onset structure across and destroy the generic start-of-sequence profile the null exists to preserve. Permutations are derangements, so no case is ever scored with its own sequence. 1,000 permutations per cell per variant. The alert window is `0 < t_to_event <= 60` and the threshold is the transported 80%-target raw-score cut, neither re-derived nor reselected. `p` is two-sided by interval inversion on the null draws, floored at 2/1,000.
