# B2 - order of score departure and MAP departure inside an episode

**What this can and cannot say.** The outcome is defined on MAP and MAP is a model input, so an earlier score departure is a statement about the order of two departures under one pre-specified rule. It is not evidence that the model anticipates physiology, and nothing below is written as if it were.

Baseline is the median over an episode's first 10 eligible pre-onset minutes; departure is the first minute beginning a run of at least 3 consecutive minutes more than 1.5 robust scale units into the deteriorating direction. Positive difference means the score departed first.

## 1. Retention and the four-way breakdown

| cohort_label | family_label | n_event_cases | n_eligible | retention | n_neither | n_score_only | n_map_only | n_both | prop_neither | prop_score_only | prop_map_only | prop_both |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MOVER (EPIC) test | ITE Transformer | 786 | 406 | 0.5165 | 124 | 8 | 233 | 41 | 0.3054 | 0.0197 | 0.5739 | 0.101 |
| VitalDB | ITE Transformer | 1007 | 579 | 0.575 | 110 | 4 | 403 | 62 | 0.19 | 0.0069 | 0.696 | 0.1071 |
| MOVER (SIS) | ITE Transformer | 1409 | 883 | 0.6267 | 223 | 8 | 528 | 124 | 0.2525 | 0.0091 | 0.598 | 0.1404 |
| MOVER (EPIC) test | XGBoost | 786 | 406 | 0.5165 | 97 | 35 | 49 | 225 | 0.2389 | 0.0862 | 0.1207 | 0.5542 |
| VitalDB | XGBoost | 1007 | 579 | 0.575 | 58 | 56 | 11 | 454 | 0.1002 | 0.0967 | 0.019 | 0.7841 |
| MOVER (SIS) | XGBoost | 1409 | 883 | 0.6267 | 148 | 83 | 53 | 599 | 0.1676 | 0.094 | 0.06 | 0.6784 |


Episodes counted under `n_neither` and `n_map_only` are episodes in which the score never departed from its own baseline at all -- the model did not signal.

The rule normalises each series by its own robust scale, so a volatile series has to travel further to be called departed. The median bar each series had to clear, in its own units, is reported here rather than left implicit -- a low `prop_both` for a volatile score is partly a property of the rule.

| cohort_label | family_label | score_scale_median | score_bar_median | map_scale_median | map_bar_median | score_baseline_median | score_headroom_median | prop_baseline_above_alert_threshold |
|---|---|---|---|---|---|---|---|---|
| MOVER (EPIC) test | ITE Transformer | 0.0045 | 0.0067 | 6.672 | 10.01 | 0.9702 | 0.0049 | 0.8128 |
| VitalDB | ITE Transformer | 0.0072 | 0.0109 | 4.448 | 6.672 | 0.9662 | 0.0083 | 0.9136 |
| MOVER (SIS) | ITE Transformer | 0.0268 | 0.0403 | 5.189 | 7.784 | 0.9394 | 0.0314 | 0.6116 |
| MOVER (EPIC) test | XGBoost | 0.0985 | 0.1478 | 6.672 | 10.01 | 0.2875 | 0.6643 | 0.0788 |
| VitalDB | XGBoost | 0.018 | 0.027 | 4.448 | 6.672 | 0.061 | 0.8608 | 0.0207 |
| MOVER (SIS) | XGBoost | 0.0489 | 0.0733 | 5.189 | 7.784 | 0.1231 | 0.8076 | 0.06 |


## 2. MAP departure minus score departure, among episodes where both departed

| Cohort | Model | n | Median (IQR), min | Median (95% CI) | Score first (95% CI) | Simultaneous | P, share vs 0.5 |
|---|---|---|---|---|---|---|---|
| MOVER (EPIC) test | ITE Transformer | 41 | +0 (-1 to +7) | +0 (-1 to +3) | 43.9% (28.6%–60.0%) | 14.6% | 0.4720 |
| VitalDB | ITE Transformer | 62 | +4 (+0 to +17) | +4 (+1 to +10) | 67.7% (55.6%–78.7%) | 17.7% | 0.0040 |
| MOVER (SIS) | ITE Transformer | 124 | +0 (-1 to +11) | +0 (+0 to +4) | 46.8% (38.1%–55.7%) | 22.6% | 0.5260 |
| MOVER (EPIC) test | XGBoost | 225 | -1 (-4 to +1) | -1 (-1 to -1) | 26.7% (20.7%–32.4%) | 12.9% | 0.0010 |
| VitalDB | XGBoost | 454 | +0 (-1 to +2) | +0 (+0 to +0) | 34.4% (30.0%–38.8%) | 24.9% | 0.0010 |
| MOVER (SIS) | XGBoost | 599 | +0 (-2 to +3) | +0 (-1 to +0) | 35.2% (31.5%–39.3%) | 17.7% | 0.0010 |


## 3. Sensitivity to the rule

`scale_2.0` raises the departure threshold, `run_5` lengthens the run requirement, and `cap_60` restricts the search to the published 60-minute alert window so the baseline is taken 60-51 minutes before onset instead of at the start of the record.

| cohort_label | family_label | rule | n_eligible | n_difference | difference_median_min | prop_score_first | prop_both | prop_neither |
|---|---|---|---|---|---|---|---|---|
| MOVER (EPIC) test | ITE Transformer | primary | 406 | 41 | 0 | 0.439 | 0.101 | 0.3054 |
| MOVER (EPIC) test | ITE Transformer | scale_2.0 | 406 | 34 | 0 | 0.4706 | 0.0837 | 0.4212 |
| MOVER (EPIC) test | ITE Transformer | run_5 | 406 | 30 | 0 | 0.4333 | 0.0739 | 0.4212 |
| MOVER (EPIC) test | ITE Transformer | cap_60 | 406 | 159 | 0 | 0.3396 | 0.3916 | 0.2882 |
| VitalDB | ITE Transformer | primary | 579 | 62 | 3.5 | 0.6774 | 0.1071 | 0.19 |
| VitalDB | ITE Transformer | scale_2.0 | 579 | 32 | 11 | 0.8125 | 0.0553 | 0.2573 |
| VitalDB | ITE Transformer | run_5 | 579 | 38 | 6.5 | 0.7105 | 0.0656 | 0.2383 |
| VitalDB | ITE Transformer | cap_60 | 579 | 266 | 0 | 0.3759 | 0.4594 | 0.1848 |
| MOVER (SIS) | ITE Transformer | primary | 883 | 124 | 0 | 0.4677 | 0.1404 | 0.2525 |
| MOVER (SIS) | ITE Transformer | scale_2.0 | 883 | 95 | 0 | 0.4632 | 0.1076 | 0.3194 |
| MOVER (SIS) | ITE Transformer | run_5 | 883 | 89 | 0 | 0.4944 | 0.1008 | 0.3262 |
| MOVER (SIS) | ITE Transformer | cap_60 | 883 | 386 | 0 | 0.4715 | 0.4371 | 0.2424 |
| MOVER (EPIC) test | XGBoost | primary | 406 | 225 | -1 | 0.2667 | 0.5542 | 0.2389 |
| MOVER (EPIC) test | XGBoost | scale_2.0 | 406 | 187 | -1 | 0.3048 | 0.4606 | 0.2956 |
| MOVER (EPIC) test | XGBoost | run_5 | 406 | 184 | -1 | 0.2989 | 0.4532 | 0.3399 |
| MOVER (EPIC) test | XGBoost | cap_60 | 406 | 221 | 0 | 0.3122 | 0.5443 | 0.2537 |
| VitalDB | XGBoost | primary | 579 | 454 | 0 | 0.3436 | 0.7841 | 0.1002 |
| VitalDB | XGBoost | scale_2.0 | 579 | 416 | 0 | 0.4375 | 0.7185 | 0.1261 |
| VitalDB | XGBoost | run_5 | 579 | 431 | 0 | 0.3155 | 0.7444 | 0.1399 |
| VitalDB | XGBoost | cap_60 | 579 | 413 | 0 | 0.3753 | 0.7133 | 0.1451 |
| MOVER (SIS) | XGBoost | primary | 883 | 599 | 0 | 0.3523 | 0.6784 | 0.1676 |
| MOVER (SIS) | XGBoost | scale_2.0 | 883 | 527 | 0 | 0.4175 | 0.5968 | 0.2072 |
| MOVER (SIS) | XGBoost | run_5 | 883 | 538 | 0 | 0.3494 | 0.6093 | 0.2265 |
| MOVER (SIS) | XGBoost | cap_60 | 883 | 531 | 0 | 0.3917 | 0.6014 | 0.2242 |

