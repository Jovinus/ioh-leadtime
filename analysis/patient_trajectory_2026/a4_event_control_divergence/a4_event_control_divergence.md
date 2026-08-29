# A4 - event versus control score divergence

Per-bin mean score with cluster-bootstrap bands, 2000 replicates, event and control weighted by the same replicate so the gap is paired. Slopes are read from the published mixed-model output; no model is fitted here.

Published statements re-derived from the stored output: interaction range 0.9687 to 4.5106 score units per hour, control slope negative in 13 of 15 cells, interaction interval excluding zero in 15 of 15.

## Transformer, published 13-bin grid

| cohort_label | bin_center_min | mean_score_event | mean_score_control | gap_event_minus_control | gap_ci_lo | gap_ci_hi |
|---|---|---|---|---|---|---|
| MOVER (EPIC) test | 60 | 0.3825 | 0.4054 | -0.0229 | -0.0802 | 0.0346 |
| MOVER (EPIC) test | 55 | 0.3897 | 0.4023 | -0.0126 | -0.0685 | 0.0433 |
| MOVER (EPIC) test | 50 | 0.4074 | 0.418 | -0.0107 | -0.0642 | 0.045 |
| MOVER (EPIC) test | 45 | 0.4428 | 0.4235 | 0.0193 | -0.0337 | 0.0729 |
| MOVER (EPIC) test | 40 | 0.4524 | 0.4174 | 0.035 | -0.014 | 0.0839 |
| MOVER (EPIC) test | 35 | 0.473 | 0.4094 | 0.0636 | 0.0149 | 0.1106 |
| MOVER (EPIC) test | 30 | 0.4932 | 0.4014 | 0.0918 | 0.0477 | 0.1379 |
| MOVER (EPIC) test | 25 | 0.5067 | 0.3482 | 0.1585 | 0.1165 | 0.2055 |
| MOVER (EPIC) test | 20 | 0.5326 | 0.3065 | 0.2261 | 0.1859 | 0.2692 |
| MOVER (EPIC) test | 15 | 0.5449 | 0.2642 | 0.2807 | 0.2432 | 0.3205 |
| MOVER (EPIC) test | 10 | 0.5957 | 0.2051 | 0.3906 | 0.3566 | 0.4263 |
| MOVER (EPIC) test | 5 | 0.622 | 0.153 | 0.469 | 0.4394 | 0.4981 |
| MOVER (EPIC) test | 0 | nan | nan | nan | nan | nan |
| VitalDB | 60 | 0.35 | 0.364 | -0.014 | -0.0567 | 0.0299 |
| VitalDB | 55 | 0.3455 | 0.3655 | -0.02 | -0.0602 | 0.0224 |
| VitalDB | 50 | 0.3343 | 0.3543 | -0.02 | -0.0583 | 0.0209 |
| VitalDB | 45 | 0.3455 | 0.3628 | -0.0173 | -0.0529 | 0.0231 |
| VitalDB | 40 | 0.3692 | 0.3879 | -0.0187 | -0.0546 | 0.02 |
| VitalDB | 35 | 0.3862 | 0.3955 | -0.0093 | -0.0456 | 0.0258 |
| VitalDB | 30 | 0.3828 | 0.414 | -0.0311 | -0.0662 | 0.0034 |
| VitalDB | 25 | 0.3978 | 0.3796 | 0.0182 | -0.0163 | 0.0525 |
| VitalDB | 20 | 0.4346 | 0.3171 | 0.1175 | 0.0837 | 0.1522 |
| VitalDB | 15 | 0.4716 | 0.2342 | 0.2374 | 0.2072 | 0.2698 |
| VitalDB | 10 | 0.5294 | 0.1497 | 0.3798 | 0.3517 | 0.4075 |
| VitalDB | 5 | 0.6165 | 0.1014 | 0.5151 | 0.4919 | 0.5398 |
| VitalDB | 0 | nan | nan | nan | nan | nan |
| MOVER (SIS) | 60 | 0.3333 | 0.3388 | -0.0056 | -0.0434 | 0.0318 |
| MOVER (SIS) | 55 | 0.3503 | 0.3482 | 0.0022 | -0.0343 | 0.0423 |
| MOVER (SIS) | 50 | 0.3601 | 0.3552 | 0.0049 | -0.0297 | 0.0412 |
| MOVER (SIS) | 45 | 0.3458 | 0.354 | -0.0082 | -0.0418 | 0.0254 |
| MOVER (SIS) | 40 | 0.3507 | 0.3417 | 0.009 | -0.0228 | 0.042 |
| MOVER (SIS) | 35 | 0.379 | 0.3527 | 0.0263 | -0.0048 | 0.0607 |
| MOVER (SIS) | 30 | 0.4106 | 0.3581 | 0.0525 | 0.0233 | 0.0855 |
| MOVER (SIS) | 25 | 0.4391 | 0.337 | 0.1021 | 0.0726 | 0.1345 |
| MOVER (SIS) | 20 | 0.4626 | 0.2815 | 0.1812 | 0.1541 | 0.2108 |
| MOVER (SIS) | 15 | 0.4931 | 0.2176 | 0.2755 | 0.2511 | 0.3005 |
| MOVER (SIS) | 10 | 0.5309 | 0.1602 | 0.3707 | 0.3481 | 0.3934 |
| MOVER (SIS) | 5 | 0.6027 | 0.1425 | 0.4603 | 0.4398 | 0.4806 |
| MOVER (SIS) | 0 | nan | nan | nan | nan | nan |


## Paired event-minus-control slope, all cells

| family_label | cohort_label | control_slope | event_slope | interaction | interaction_lo | interaction_hi |
|---|---|---|---|---|---|---|
| ITE Transformer | MOVER (EPIC) test | -1.429 | 0.8631 | 2.292 | 1.94 | 2.644 |
| ITE Transformer | VitalDB | -1.763 | 1.874 | 3.636 | 3.355 | 3.917 |
| ITE Transformer | MOVER (SIS) | -1.096 | 1.489 | 2.585 | 2.351 | 2.819 |
| XGBoost | MOVER (EPIC) test | -0.1861 | 1.038 | 1.224 | 0.9415 | 1.506 |
| XGBoost | VitalDB | 0.0288 | 2.4 | 2.371 | 2.171 | 2.571 |
| XGBoost | MOVER (SIS) | -0.0007 | 2.023 | 2.023 | 1.824 | 2.223 |
| LSTM | MOVER (EPIC) test | -1.387 | 2.065 | 3.452 | 2.964 | 3.941 |
| LSTM | VitalDB | -0.6933 | 3.817 | 4.511 | 4.193 | 4.829 |
| LSTM | MOVER (SIS) | -0.6109 | 2.52 | 3.131 | 2.872 | 3.39 |
| Random forest | MOVER (EPIC) test | -0.0784 | 0.945 | 1.023 | 0.7872 | 1.26 |
| Random forest | VitalDB | -0.0003 | 2.046 | 2.046 | 1.874 | 2.219 |
| Random forest | MOVER (SIS) | 0.0061 | 1.901 | 1.895 | 1.705 | 2.084 |
| Logistic regression | MOVER (EPIC) test | -0.2229 | 0.7458 | 0.9687 | 0.6806 | 1.257 |
| Logistic regression | VitalDB | -0.005 | 1.412 | 1.417 | 1.249 | 1.585 |
| Logistic regression | MOVER (SIS) | -0.0133 | 1.242 | 1.255 | 1.095 | 1.415 |

