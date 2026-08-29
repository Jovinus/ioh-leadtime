# B1 - prevalent versus incident alerts

A **prevalent** alert is a detected case whose score was already at or above the transported threshold at its first eligible scored minute: the alert reports a starting level, not an observed change. An **incident** alert crossed from below. Thresholds are the published validation-fixed ones, transported unchanged.

## 1. The headline split, 80% validation sensitivity target, first minute taken inside the 60-minute alert window

### MOVER (EPIC) test

| Model | Detected | Prevalent, n (%) | Lead, prevalent, median (IQR) | Lead, incident, median (IQR) | Published lead (all detected) | Lead, incident only (95% CI) | Shift (95% CI) | Warm-up, n (%) | Lead, settled only (95% CI) |
|---|---|---|---|---|---|---|---|---|---|
| ITE Transformer | 611 | 53 (8.7%; 6.7%–11.0%) | 60 (60–60) | 21 (11–36) | 24 | 21 (19–24) | +3 (+1 to +5) | 467 (76.4%) | 17 (12–28) |
| LSTM | 634 | 34 (5.4%; 3.6%–7.2%) | 60 (60–60) | 21 (9–37) | 23 | 21 (18–23) | +2 (+1 to +3) | 342 (53.9%) | 23 (17–27) |
| XGBoost | 637 | 139 (21.8%; 18.5%–25.0%) | 28 (17–60) | 19 (8–39) | 21 | 19 (16–22) | +2 (+1 to +4) | 110 (17.3%) | 20 (17–24) |
| Random forest | 651 | 130 (20.0%; 16.9%–22.9%) | 37 (15–60) | 21 (8–38) | 22 | 21 (18–23) | +1 (+0 to +3) | 112 (17.2%) | 22 (19–25) |
| Logistic regression | 658 | 168 (25.5%; 22.4%–29.0%) | 26 (14–55) | 22 (9–41) | 23 | 22 (19–25) | +1 (-1 to +3) | 108 (16.4%) | 23 (19–26) |


### VitalDB

| Model | Detected | Prevalent, n (%) | Lead, prevalent, median (IQR) | Lead, incident, median (IQR) | Published lead (all detected) | Lead, incident only (95% CI) | Shift (95% CI) | Warm-up, n (%) | Lead, settled only (95% CI) |
|---|---|---|---|---|---|---|---|---|---|
| ITE Transformer | 684 | 66 (9.6%; 7.5%–12.0%) | 60 (60–60) | 15 (8–30) | 17 | 15 (13–17) | +2 (+1 to +3) | 567 (82.9%) | 26 (14–31) |
| LSTM | 495 | 13 (2.6%; 1.2%–4.2%) | 60 (60–60) | 9 (4–21) | 9 | 9 (8–10) | +0 (+0 to +1) | 224 (45.3%) | 9 (7–13) |
| XGBoost | 699 | 55 (7.9%; 6.0%–9.9%) | 25 (10–60) | 13 (3–32) | 13 | 13 (11–15) | +0 (+0 to +2) | 89 (12.7%) | 14 (12–17) |
| Random forest | 809 | 93 (11.5%; 9.4%–13.7%) | 48 (11–60) | 14 (3–36) | 15 | 14 (11–16) | +2 (+0 to +3) | 111 (13.7%) | 16 (14–19) |
| Logistic regression | 464 | 33 (7.1%; 4.8%–9.5%) | 18 (11–60) | 13 (4–31) | 14 | 13 (10–16) | +1 (+0 to +2) | 52 (11.2%) | 14 (12–18) |


### MOVER (SIS)

| Model | Detected | Prevalent, n (%) | Lead, prevalent, median (IQR) | Lead, incident, median (IQR) | Published lead (all detected) | Lead, incident only (95% CI) | Shift (95% CI) | Warm-up, n (%) | Lead, settled only (95% CI) |
|---|---|---|---|---|---|---|---|---|---|
| ITE Transformer | 926 | 83 (9.0%; 7.2%–10.8%) | 60 (60–60) | 19 (9–33) | 22 | 19 (17–21) | +3 (+2 to +4) | 622 (67.2%) | 21 (17–26) |
| LSTM | 777 | 31 (4.0%; 2.7%–5.4%) | 60 (60–60) | 14 (6–32) | 15 | 14 (13–16) | +1 (+0 to +2) | 295 (38.0%) | 14 (12–17) |
| XGBoost | 1113 | 146 (13.1%; 11.1%–15.1%) | 29 (12–60) | 19 (6–38) | 19 | 19 (17–21) | +0 (+0 to +2) | 124 (11.1%) | 19 (17–22) |
| Random forest | 1196 | 209 (17.5%; 15.3%–19.6%) | 29 (11–60) | 20 (8–42) | 22 | 20 (19–23) | +2 (+0 to +3) | 126 (10.5%) | 22 (20–24) |
| Logistic regression | 1113 | 154 (13.8%; 11.8%–15.8%) | 33 (12–60) | 20 (7–41) | 21 | 20 (18–22) | +1 (+0 to +2) | 121 (10.9%) | 21 (19–24) |


## 2. Where in the case the crossing happens, and the score profile that explains it

`crossing_elapsed_median` is the monitoring time already elapsed when the alert fired. A **warm-up** crossing is an incident crossing at or before minute 5 of monitoring: the score was genuinely below threshold at the first minute and above it later, so it is incident by definition, but the input window was filling rather than the patient changing. `settled` alerts are the remainder -- neither prevalent nor warm-up.

| cohort_label | family_label | n_detected | crossing_elapsed_median | prop_prevalent | prop_warmup | prop_settled | lead_median_all | lead_median_settled | lead_shift_all_minus_settled |
|---|---|---|---|---|---|---|---|---|---|
| MOVER (EPIC) test | ITE Transformer | 611 | 1 | 0.0867 | 0.7643 | 0.1489 | 24 | 17 | 7 |
| VitalDB | ITE Transformer | 684 | 1 | 0.0965 | 0.8289 | 0.0746 | 17 | 26 | -9 |
| MOVER (SIS) | ITE Transformer | 926 | 3 | 0.0896 | 0.6717 | 0.2387 | 22 | 21 | 1 |
| MOVER (EPIC) test | LSTM | 634 | 5 | 0.0536 | 0.5394 | 0.4069 | 23 | 23 | 0 |
| VitalDB | LSTM | 495 | 6 | 0.0263 | 0.4525 | 0.5212 | 9 | 9 | 0 |
| MOVER (SIS) | LSTM | 777 | 8 | 0.0399 | 0.3797 | 0.5804 | 15 | 14 | 1 |
| MOVER (EPIC) test | XGBoost | 637 | 16 | 0.2182 | 0.1727 | 0.6091 | 21 | 20 | 1 |
| VitalDB | XGBoost | 699 | 29 | 0.0787 | 0.1273 | 0.794 | 13 | 14 | -1 |
| MOVER (SIS) | XGBoost | 1113 | 28 | 0.1312 | 0.1114 | 0.7574 | 19 | 19 | 0 |
| MOVER (EPIC) test | Random forest | 651 | 19 | 0.1997 | 0.172 | 0.6283 | 22 | 22 | 0 |
| VitalDB | Random forest | 809 | 23 | 0.115 | 0.1372 | 0.7478 | 15 | 16 | -1 |
| MOVER (SIS) | Random forest | 1196 | 25 | 0.1747 | 0.1054 | 0.7199 | 22 | 22 | 0 |
| MOVER (EPIC) test | Logistic regression | 658 | 14.5 | 0.2553 | 0.1641 | 0.5805 | 23 | 23 | 0 |
| VitalDB | Logistic regression | 464 | 25 | 0.0711 | 0.1121 | 0.8168 | 14 | 14 | 0 |
| MOVER (SIS) | Logistic regression | 1113 | 28 | 0.1384 | 0.1087 | 0.7529 | 21 | 21 | 0 |


Sensitivity to the warm-up cut, at 3 and 10 minutes:

| cohort_label | family_label | prop_warmup | prop_warmup_le_3 | prop_warmup_le_10 |
|---|---|---|---|---|
| MOVER (EPIC) test | ITE Transformer | 0.7643 | 0.7365 | 0.7741 |
| VitalDB | ITE Transformer | 0.8289 | 0.7953 | 0.8523 |
| MOVER (SIS) | ITE Transformer | 0.6717 | 0.5756 | 0.7786 |
| MOVER (EPIC) test | LSTM | 0.5394 | 0.4101 | 0.6751 |
| VitalDB | LSTM | 0.4525 | 0.2586 | 0.7192 |
| MOVER (SIS) | LSTM | 0.3797 | 0.3024 | 0.5328 |
| MOVER (EPIC) test | XGBoost | 0.1727 | 0.1083 | 0.2606 |
| VitalDB | XGBoost | 0.1273 | 0.0615 | 0.2489 |
| MOVER (SIS) | XGBoost | 0.1114 | 0.0692 | 0.2246 |
| MOVER (EPIC) test | Random forest | 0.172 | 0.0937 | 0.2627 |
| VitalDB | Random forest | 0.1372 | 0.0655 | 0.2781 |
| MOVER (SIS) | Random forest | 0.1054 | 0.0635 | 0.2216 |
| MOVER (EPIC) test | Logistic regression | 0.1641 | 0.1049 | 0.2568 |
| VitalDB | Logistic regression | 0.1121 | 0.0366 | 0.2629 |
| MOVER (SIS) | Logistic regression | 0.1087 | 0.0611 | 0.2228 |


Median score by minutes elapsed since each record's first scored minute. This is the evidence for the warm-up split, not an assumption behind it.

| family | cohort | label | min 0 | min 1 | min 2 | min 3 | min 4 | min 5 | min 6 | min 7 | min 8 | min 9 | min 10 | min 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| logreg | epic_test | 0 | 0.656 | 0.656 | 0.642 | 0.625 | 0.618 | 0.606 | 0.599 | 0.582 | 0.583 | 0.565 | 0.517 | 0.531 |
| logreg | epic_test | 1 | 0.692 | 0.692 | 0.683 | 0.668 | 0.669 | 0.661 | 0.653 | 0.645 | 0.63 | 0.628 | 0.605 | 0.623 |
| logreg | mover | 0 | 0.218 | 0.218 | 0.242 | 0.244 | 0.243 | 0.258 | 0.264 | 0.27 | 0.26 | 0.261 | 0.256 | 0.266 |
| logreg | mover | 1 | 0.368 | 0.368 | 0.375 | 0.375 | 0.399 | 0.376 | 0.389 | 0.408 | 0.396 | 0.417 | 0.419 | 0.414 |
| logreg | vitaldb | 0 | 0.084 | 0.084 | 0.09 | 0.092 | 0.101 | 0.11 | 0.111 | 0.121 | 0.124 | 0.123 | 0.13 | 0.13 |
| logreg | vitaldb | 1 | 0.202 | 0.202 | 0.218 | 0.233 | 0.249 | 0.255 | 0.264 | 0.273 | 0.281 | 0.294 | 0.302 | 0.318 |
| lstm | epic_test | 0 | 0.528 | 0.684 | 0.807 | 0.885 | 0.937 | 0.957 | 0.971 | 0.976 | 0.978 | 0.983 | 0.985 | 0.985 |
| lstm | epic_test | 1 | 0.528 | 0.841 | 0.908 | 0.951 | 0.966 | 0.976 | 0.985 | 0.987 | 0.99 | 0.99 | 0.991 | 0.992 |
| lstm | mover | 0 | 0.528 | 0.011 | 0.03 | 0.081 | 0.157 | 0.203 | 0.231 | 0.251 | 0.269 | 0.272 | 0.251 | 0.219 |
| lstm | mover | 1 | 0.528 | 0.044 | 0.092 | 0.224 | 0.425 | 0.487 | 0.55 | 0.592 | 0.624 | 0.64 | 0.625 | 0.619 |
| lstm | vitaldb | 0 | 0.528 | 0.006 | 0.018 | 0.053 | 0.102 | 0.144 | 0.174 | 0.185 | 0.193 | 0.196 | 0.184 | 0.162 |
| lstm | vitaldb | 1 | 0.528 | 0.017 | 0.061 | 0.214 | 0.397 | 0.528 | 0.568 | 0.621 | 0.65 | 0.671 | 0.66 | 0.728 |
| rf | epic_test | 0 | 0.459 | 0.459 | 0.402 | 0.381 | 0.362 | 0.366 | 0.352 | 0.346 | 0.335 | 0.338 | 0.314 | 0.291 |
| rf | epic_test | 1 | 0.542 | 0.542 | 0.511 | 0.478 | 0.465 | 0.44 | 0.432 | 0.432 | 0.428 | 0.412 | 0.399 | 0.418 |
| rf | mover | 0 | 0.128 | 0.128 | 0.122 | 0.12 | 0.126 | 0.125 | 0.14 | 0.135 | 0.134 | 0.136 | 0.132 | 0.135 |
| rf | mover | 1 | 0.2 | 0.2 | 0.198 | 0.205 | 0.222 | 0.201 | 0.21 | 0.225 | 0.224 | 0.231 | 0.238 | 0.238 |
| rf | vitaldb | 0 | 0.088 | 0.088 | 0.088 | 0.09 | 0.09 | 0.09 | 0.095 | 0.098 | 0.098 | 0.1 | 0.1 | 0.1 |
| rf | vitaldb | 1 | 0.14 | 0.14 | 0.15 | 0.158 | 0.165 | 0.161 | 0.17 | 0.176 | 0.18 | 0.198 | 0.192 | 0.202 |
| transformer | epic_test | 0 | 0.53 | 0.938 | 0.967 | 0.971 | 0.973 | 0.973 | 0.974 | 0.974 | 0.974 | 0.974 | 0.974 | 0.974 |
| transformer | epic_test | 1 | 0.541 | 0.951 | 0.972 | 0.974 | 0.975 | 0.975 | 0.975 | 0.975 | 0.975 | 0.975 | 0.975 | 0.975 |
| transformer | mover | 0 | 0.517 | 0.715 | 0.833 | 0.902 | 0.931 | 0.942 | 0.948 | 0.951 | 0.954 | 0.957 | 0.958 | 0.956 |
| transformer | mover | 1 | 0.53 | 0.815 | 0.906 | 0.944 | 0.959 | 0.962 | 0.963 | 0.966 | 0.967 | 0.968 | 0.967 | 0.966 |
| transformer | vitaldb | 0 | 0.502 | 0.886 | 0.939 | 0.955 | 0.963 | 0.966 | 0.969 | 0.97 | 0.97 | 0.971 | 0.971 | 0.971 |
| transformer | vitaldb | 1 | 0.503 | 0.932 | 0.964 | 0.97 | 0.972 | 0.973 | 0.973 | 0.973 | 0.973 | 0.973 | 0.974 | 0.974 |
| xgb | epic_test | 0 | 0.488 | 0.488 | 0.418 | 0.39 | 0.349 | 0.386 | 0.367 | 0.329 | 0.308 | 0.326 | 0.295 | 0.268 |
| xgb | epic_test | 1 | 0.65 | 0.65 | 0.614 | 0.577 | 0.556 | 0.541 | 0.511 | 0.512 | 0.503 | 0.487 | 0.477 | 0.486 |
| xgb | mover | 0 | 0.088 | 0.088 | 0.079 | 0.083 | 0.082 | 0.079 | 0.08 | 0.079 | 0.082 | 0.085 | 0.081 | 0.084 |
| xgb | mover | 1 | 0.167 | 0.167 | 0.167 | 0.155 | 0.186 | 0.165 | 0.156 | 0.184 | 0.176 | 0.181 | 0.174 | 0.182 |
| xgb | vitaldb | 0 | 0.042 | 0.042 | 0.041 | 0.042 | 0.043 | 0.043 | 0.044 | 0.045 | 0.045 | 0.046 | 0.047 | 0.048 |
| xgb | vitaldb | 1 | 0.074 | 0.074 | 0.077 | 0.088 | 0.093 | 0.095 | 0.095 | 0.098 | 0.108 | 0.113 | 0.111 | 0.131 |


## 3. Controls

`prop_control_prevalent` is the fraction of control cases already above threshold at their own first eligible minute -- a false alert no monitoring produced.

| cohort_label | family_label | n_control_cases | prop_control_alerting | n_control_prevalent | prop_control_prevalent | prop_control_prevalent_of_alerting | n_control_warmup | prop_control_warmup | prop_control_prevalent_or_warmup_of_alerting |
|---|---|---|---|---|---|---|---|---|---|
| MOVER (EPIC) test | ITE Transformer | 618 | 0.5939 | 109 | 0.1764 | 0.297 | 223 | 0.3608 | 0.9046 |
| VitalDB | ITE Transformer | 1797 | 0.621 | 259 | 0.1441 | 0.2321 | 771 | 0.429 | 0.9229 |
| MOVER (SIS) | ITE Transformer | 1232 | 0.5333 | 115 | 0.09334 | 0.175 | 362 | 0.2938 | 0.726 |
| MOVER (EPIC) test | LSTM | 618 | 0.5259 | 53 | 0.08576 | 0.1631 | 130 | 0.2104 | 0.5631 |
| VitalDB | LSTM | 1797 | 0.1875 | 31 | 0.01725 | 0.09199 | 112 | 0.06233 | 0.4243 |
| MOVER (SIS) | LSTM | 1232 | 0.2906 | 24 | 0.01948 | 0.06704 | 119 | 0.09659 | 0.3994 |
| MOVER (EPIC) test | XGBoost | 618 | 0.3916 | 40 | 0.06472 | 0.1653 | 22 | 0.0356 | 0.2562 |
| VitalDB | XGBoost | 1797 | 0.246 | 35 | 0.01948 | 0.07919 | 37 | 0.02059 | 0.1629 |
| MOVER (SIS) | XGBoost | 1232 | 0.362 | 46 | 0.03734 | 0.1031 | 44 | 0.03571 | 0.2018 |
| MOVER (EPIC) test | Random forest | 618 | 0.445 | 47 | 0.07605 | 0.1709 | 24 | 0.03883 | 0.2582 |
| VitalDB | Random forest | 1797 | 0.3261 | 60 | 0.03339 | 0.1024 | 48 | 0.02671 | 0.1843 |
| MOVER (SIS) | Random forest | 1232 | 0.4407 | 74 | 0.06006 | 0.1363 | 49 | 0.03977 | 0.2265 |
| MOVER (EPIC) test | Logistic regression | 618 | 0.4822 | 52 | 0.08414 | 0.1745 | 45 | 0.07282 | 0.3255 |
| VitalDB | Logistic regression | 1797 | 0.1747 | 30 | 0.01669 | 0.09554 | 26 | 0.01447 | 0.1783 |
| MOVER (SIS) | Logistic regression | 1232 | 0.4148 | 55 | 0.04464 | 0.1076 | 48 | 0.03896 | 0.2016 |


## 4. Sensitivity to the definition of the first eligible minute

`record` takes the first scored minute of the whole case rather than of the 60-minute window, so a long case is judged against a minute a real monitor would have seen.

| cohort_label | family_label | lead_median_incident record | lead_median_incident window | prop_prevalent record | prop_prevalent window |
|---|---|---|---|---|---|
| MOVER (EPIC) test | ITE Transformer | 24 | 21 | 0 | 0.08674 |
| MOVER (EPIC) test | LSTM | 23 | 21 | 0 | 0.05363 |
| MOVER (EPIC) test | Logistic regression | 24 | 22 | 0.2812 | 0.2553 |
| MOVER (EPIC) test | Random forest | 22 | 21 | 0.1935 | 0.1997 |
| MOVER (EPIC) test | XGBoost | 20 | 19 | 0.2214 | 0.2182 |
| MOVER (SIS) | ITE Transformer | 22 | 19 | 0 | 0.08963 |
| MOVER (SIS) | LSTM | 15 | 14 | 0 | 0.0399 |
| MOVER (SIS) | Logistic regression | 21.5 | 20 | 0.1141 | 0.1384 |
| MOVER (SIS) | Random forest | 23 | 20 | 0.1564 | 0.1747 |
| MOVER (SIS) | XGBoost | 19 | 19 | 0.1186 | 0.1312 |
| VitalDB | ITE Transformer | 17 | 15 | 0 | 0.09649 |
| VitalDB | LSTM | 9 | 9 | 0 | 0.02626 |
| VitalDB | Logistic regression | 14 | 13 | 0.06034 | 0.07112 |
| VitalDB | Random forest | 15 | 13.5 | 0.08035 | 0.115 |
| VitalDB | XGBoost | 13 | 13 | 0.06152 | 0.07868 |


## 5. All three sensitivity targets

| cohort_label | family_label | target_sensitivity | n_detected | prop_prevalent | lead_median_all | lead_median_incident | lead_shift_all_minus_incident | prop_control_prevalent |
|---|---|---|---|---|---|---|---|---|
| MOVER (EPIC) test | ITE Transformer | 0.7 | 535 | 0.09533 | 25 | 21 | 4 | 0.1748 |
| MOVER (EPIC) test | ITE Transformer | 0.8 | 611 | 0.08674 | 24 | 21 | 3 | 0.1764 |
| MOVER (EPIC) test | ITE Transformer | 0.9 | 674 | 0.0905 | 25 | 22 | 3 | 0.1796 |
| VitalDB | ITE Transformer | 0.7 | 651 | 0.09831 | 17 | 15 | 2 | 0.1402 |
| VitalDB | ITE Transformer | 0.8 | 684 | 0.09649 | 17 | 15 | 2 | 0.1441 |
| VitalDB | ITE Transformer | 0.9 | 780 | 0.09103 | 18 | 16 | 2 | 0.1475 |
| MOVER (SIS) | ITE Transformer | 0.7 | 832 | 0.09375 | 22 | 19 | 3 | 0.09172 |
| MOVER (SIS) | ITE Transformer | 0.8 | 926 | 0.08963 | 22 | 19 | 3 | 0.09334 |
| MOVER (SIS) | ITE Transformer | 0.9 | 1059 | 0.0831 | 23 | 20 | 3 | 0.09578 |
| MOVER (EPIC) test | LSTM | 0.7 | 550 | 0.04727 | 21 | 19 | 2 | 0.05825 |
| MOVER (EPIC) test | LSTM | 0.8 | 634 | 0.05363 | 23 | 21 | 2 | 0.08576 |
| MOVER (EPIC) test | LSTM | 0.9 | 690 | 0.07246 | 26 | 23.5 | 2.5 | 0.1197 |
| VitalDB | LSTM | 0.7 | 354 | 0.01977 | 9 | 8 | 1 | 0.0128 |
| VitalDB | LSTM | 0.8 | 495 | 0.02626 | 9 | 9 | 0 | 0.01725 |
| VitalDB | LSTM | 0.9 | 657 | 0.04262 | 13 | 11 | 2 | 0.02671 |
| MOVER (SIS) | LSTM | 0.7 | 498 | 0.03414 | 15 | 14 | 1 | 0.008929 |
| MOVER (SIS) | LSTM | 0.8 | 777 | 0.0399 | 15 | 14 | 1 | 0.01948 |
| MOVER (SIS) | LSTM | 0.9 | 1054 | 0.05313 | 18 | 16 | 2 | 0.0349 |
| MOVER (EPIC) test | XGBoost | 0.7 | 567 | 0.1534 | 19 | 16.5 | 2.5 | 0.04045 |
| MOVER (EPIC) test | XGBoost | 0.8 | 637 | 0.2182 | 21 | 19 | 2 | 0.06472 |
| MOVER (EPIC) test | XGBoost | 0.9 | 728 | 0.3777 | 26 | 24 | 2 | 0.1505 |
| VitalDB | XGBoost | 0.7 | 594 | 0.05724 | 13 | 12 | 1 | 0.0128 |
| VitalDB | XGBoost | 0.8 | 699 | 0.07868 | 13 | 13 | 0 | 0.01948 |
| VitalDB | XGBoost | 0.9 | 828 | 0.1159 | 15.5 | 14 | 1.5 | 0.0345 |
| MOVER (SIS) | XGBoost | 0.7 | 1012 | 0.1047 | 17 | 16 | 1 | 0.01867 |
| MOVER (SIS) | XGBoost | 0.8 | 1113 | 0.1312 | 19 | 19 | 0 | 0.03734 |
| MOVER (SIS) | XGBoost | 0.9 | 1255 | 0.2207 | 24 | 22 | 2 | 0.08847 |
| MOVER (EPIC) test | Random forest | 0.7 | 565 | 0.131 | 19 | 17 | 2 | 0.03236 |
| MOVER (EPIC) test | Random forest | 0.8 | 651 | 0.1997 | 22 | 21 | 1 | 0.07605 |
| MOVER (EPIC) test | Random forest | 0.9 | 737 | 0.3636 | 28 | 27 | 1 | 0.1489 |
| VitalDB | Random forest | 0.7 | 721 | 0.08044 | 14 | 12 | 2 | 0.02337 |
| VitalDB | Random forest | 0.8 | 809 | 0.115 | 15 | 13.5 | 1.5 | 0.03339 |
| VitalDB | Random forest | 0.9 | 880 | 0.1557 | 17 | 15 | 2 | 0.05843 |
| MOVER (SIS) | Random forest | 0.7 | 1101 | 0.1417 | 20 | 19 | 1 | 0.04058 |
| MOVER (SIS) | Random forest | 0.8 | 1196 | 0.1747 | 22 | 20 | 2 | 0.06006 |
| MOVER (SIS) | Random forest | 0.9 | 1291 | 0.2378 | 26 | 24 | 2 | 0.1039 |
| MOVER (EPIC) test | Logistic regression | 0.7 | 555 | 0.1405 | 20 | 19 | 1 | 0.04531 |
| MOVER (EPIC) test | Logistic regression | 0.8 | 658 | 0.2553 | 23 | 22 | 1 | 0.08414 |
| MOVER (EPIC) test | Logistic regression | 0.9 | 733 | 0.4202 | 27 | 24 | 3 | 0.2136 |
| VitalDB | Logistic regression | 0.7 | 314 | 0.03185 | 12 | 11.5 | 0.5 | 0.008347 |
| VitalDB | Logistic regression | 0.8 | 464 | 0.07112 | 14 | 13 | 1 | 0.01669 |
| VitalDB | Logistic regression | 0.9 | 710 | 0.1225 | 14 | 13 | 1 | 0.04174 |
| MOVER (SIS) | Logistic regression | 0.7 | 959 | 0.08446 | 18 | 17 | 1 | 0.02192 |
| MOVER (SIS) | Logistic regression | 0.8 | 1113 | 0.1384 | 21 | 20 | 1 | 0.04464 |
| MOVER (SIS) | Logistic regression | 0.9 | 1262 | 0.2242 | 26 | 23 | 3 | 0.09659 |


## 6. Where the prevalent alerts sit

By observable run-up length and by A3 starting-score decile, among detected event cases at the headline target. The decile relation is partly mechanical -- prevalence is defined by the level at the window's first minute, and the A3 starting score is the level at the first minute of the 30-minute window -- so it measures where prevalent alerts concentrate, not an independent association.

| family | cohort | target_sensitivity | first_minute_definition | stratifier | stratum | n_detected | n_prevalent | prop_prevalent | lead_median_all | start_score_lo | start_score_hi |
|---|---|---|---|---|---|---|---|---|---|---|---|
| transformer | epic_test | 0.8 | window | observable_min_band | <20 | 203 | 0 | 0 | 11 | nan | nan |
| transformer | epic_test | 0.8 | window | observable_min_band | 20-39 | 162 | 0 | 0 | 27 | nan | nan |
| transformer | epic_test | 0.8 | window | observable_min_band | 40-59 | 109 | 0 | 0 | 46 | nan | nan |
| transformer | epic_test | 0.8 | window | observable_min_band | >=60 | 137 | 53 | 0.3869 | 47 | nan | nan |
| transformer | epic_test | 0.8 | window | start_score_30_decile | 1 | 15 | 7 | 0.4667 | 13 | 0.02697 | 0.0278 |
| transformer | epic_test | 0.8 | window | start_score_30_decile | 2 | 17 | 6 | 0.3529 | 12 | 0.0278 | 0.03992 |
| transformer | epic_test | 0.8 | window | start_score_30_decile | 3 | 25 | 8 | 0.32 | 55 | 0.03992 | 0.1169 |
| transformer | epic_test | 0.8 | window | start_score_30_decile | 4 | 36 | 15 | 0.4167 | 56 | 0.1169 | 0.2822 |
| transformer | epic_test | 0.8 | window | start_score_30_decile | 5 | 94 | 3 | 0.03191 | 17 | 0.2822 | 0.4895 |
| transformer | epic_test | 0.8 | window | start_score_30_decile | 6 | 125 | 2 | 0.016 | 15 | 0.4895 | 0.5667 |
| transformer | epic_test | 0.8 | window | start_score_30_decile | 7 | 121 | 4 | 0.03306 | 16 | 0.5667 | 0.6629 |
| transformer | epic_test | 0.8 | window | start_score_30_decile | 8 | 46 | 8 | 0.1739 | 41 | 0.6629 | 0.9312 |
| transformer | epic_test | 0.8 | window | start_score_30_decile | 9 | 57 | 0 | 0 | 43 | 0.9312 | 0.9733 |
| transformer | epic_test | 0.8 | window | start_score_30_decile | 10 | 75 | 0 | 0 | 37 | 0.9733 | 0.977 |
| transformer | vitaldb | 0.8 | window | observable_min_band | <20 | 339 | 0 | 0 | 9 | nan | nan |
| transformer | vitaldb | 0.8 | window | observable_min_band | 20-39 | 138 | 0 | 0 | 25.5 | nan | nan |
| transformer | vitaldb | 0.8 | window | observable_min_band | 40-59 | 101 | 0 | 0 | 45 | nan | nan |
| transformer | vitaldb | 0.8 | window | observable_min_band | >=60 | 106 | 66 | 0.6226 | 60 | nan | nan |
| transformer | vitaldb | 0.8 | window | start_score_30_decile | 1 | 6 | 1 | 0.1667 | 57.5 | 0.02695 | 0.0272 |
| transformer | vitaldb | 0.8 | window | start_score_30_decile | 2 | 11 | 7 | 0.6364 | 60 | 0.0272 | 0.02804 |
| transformer | vitaldb | 0.8 | window | start_score_30_decile | 3 | 21 | 12 | 0.5714 | 60 | 0.02804 | 0.04076 |
| transformer | vitaldb | 0.8 | window | start_score_30_decile | 4 | 28 | 15 | 0.5357 | 60 | 0.04076 | 0.1128 |
| transformer | vitaldb | 0.8 | window | start_score_30_decile | 5 | 51 | 16 | 0.3137 | 53 | 0.1128 | 0.4301 |
| transformer | vitaldb | 0.8 | window | start_score_30_decile | 6 | 231 | 3 | 0.01299 | 11 | 0.4301 | 0.5101 |
| transformer | vitaldb | 0.8 | window | start_score_30_decile | 7 | 199 | 3 | 0.01508 | 11 | 0.5101 | 0.7103 |
| transformer | vitaldb | 0.8 | window | start_score_30_decile | 8 | 42 | 9 | 0.2143 | 40.5 | 0.7103 | 0.9359 |
| transformer | vitaldb | 0.8 | window | start_score_30_decile | 9 | 39 | 0 | 0 | 43 | 0.9359 | 0.9713 |
| transformer | vitaldb | 0.8 | window | start_score_30_decile | 10 | 56 | 0 | 0 | 38 | 0.9713 | 0.9768 |
| transformer | mover | 0.8 | window | observable_min_band | <20 | 340 | 0 | 0 | 8 | nan | nan |
| transformer | mover | 0.8 | window | observable_min_band | 20-39 | 263 | 0 | 0 | 27 | nan | nan |
| transformer | mover | 0.8 | window | observable_min_band | 40-59 | 121 | 0 | 0 | 45 | nan | nan |
| transformer | mover | 0.8 | window | observable_min_band | >=60 | 202 | 83 | 0.4109 | 57 | nan | nan |
| transformer | mover | 0.8 | window | start_score_30_decile | 1 | 16 | 7 | 0.4375 | 59 | 0.02696 | 0.02755 |
| transformer | mover | 0.8 | window | start_score_30_decile | 2 | 22 | 8 | 0.3636 | 55.5 | 0.02755 | 0.03311 |
| transformer | mover | 0.8 | window | start_score_30_decile | 3 | 43 | 13 | 0.3023 | 52 | 0.03311 | 0.08123 |
| transformer | mover | 0.8 | window | start_score_30_decile | 4 | 44 | 14 | 0.3182 | 53.5 | 0.08123 | 0.1867 |
| transformer | mover | 0.8 | window | start_score_30_decile | 5 | 70 | 18 | 0.2571 | 31 | 0.1867 | 0.4255 |
| transformer | mover | 0.8 | window | start_score_30_decile | 6 | 199 | 2 | 0.01005 | 12 | 0.4255 | 0.5116 |
| transformer | mover | 0.8 | window | start_score_30_decile | 7 | 206 | 4 | 0.01942 | 11 | 0.5116 | 0.5904 |
| transformer | mover | 0.8 | window | start_score_30_decile | 8 | 130 | 9 | 0.06923 | 16 | 0.5904 | 0.7802 |
| transformer | mover | 0.8 | window | start_score_30_decile | 9 | 86 | 8 | 0.09302 | 34.5 | 0.7802 | 0.9503 |
| transformer | mover | 0.8 | window | start_score_30_decile | 10 | 110 | 0 | 0 | 35 | 0.9503 | 0.977 |
| lstm | epic_test | 0.8 | window | observable_min_band | <20 | 188 | 0 | 0 | 8.5 | nan | nan |
| lstm | epic_test | 0.8 | window | observable_min_band | 20-39 | 158 | 0 | 0 | 24 | nan | nan |
| lstm | epic_test | 0.8 | window | observable_min_band | 40-59 | 102 | 0 | 0 | 43 | nan | nan |
| lstm | epic_test | 0.8 | window | observable_min_band | >=60 | 186 | 34 | 0.1828 | 39.5 | nan | nan |
| lstm | epic_test | 0.8 | window | start_score_30_decile | 1 | 14 | 1 | 0.07143 | 8 | 0.0005232 | 0.007046 |
| lstm | epic_test | 0.8 | window | start_score_30_decile | 2 | 22 | 5 | 0.2273 | 48 | 0.007046 | 0.02677 |
| lstm | epic_test | 0.8 | window | start_score_30_decile | 3 | 32 | 6 | 0.1875 | 42.5 | 0.02677 | 0.08253 |
| lstm | epic_test | 0.8 | window | start_score_30_decile | 4 | 32 | 4 | 0.125 | 35 | 0.08253 | 0.272 |
| lstm | epic_test | 0.8 | window | start_score_30_decile | 5 | 35 | 5 | 0.1429 | 32 | 0.272 | 0.5277 |
| lstm | epic_test | 0.8 | window | start_score_30_decile | 6 | 286 | 0 | 0 | 12 | 0.5277 | 0.5531 |
| lstm | epic_test | 0.8 | window | start_score_30_decile | 7 | 64 | 7 | 0.1094 | 43 | 0.5531 | 0.8486 |
| lstm | epic_test | 0.8 | window | start_score_30_decile | 8 | 67 | 6 | 0.08955 | 40 | 0.8486 | 0.9806 |
| lstm | epic_test | 0.8 | window | start_score_30_decile | 9 | 82 | 0 | 0 | 37.5 | 0.9806 | 0.9997 |
| lstm | vitaldb | 0.8 | window | observable_min_band | <20 | 264 | 0 | 0 | 5 | nan | nan |
| lstm | vitaldb | 0.8 | window | observable_min_band | 20-39 | 96 | 0 | 0 | 20 | nan | nan |
| lstm | vitaldb | 0.8 | window | observable_min_band | 40-59 | 49 | 0 | 0 | 40 | nan | nan |
| lstm | vitaldb | 0.8 | window | observable_min_band | >=60 | 86 | 13 | 0.1512 | 33 | nan | nan |
| lstm | vitaldb | 0.8 | window | start_score_30_decile | 1 | 2 | 0 | 0 | 29.5 | 0.0008162 | 0.003654 |
| lstm | vitaldb | 0.8 | window | start_score_30_decile | 2 | 7 | 1 | 0.1429 | 53 | 0.003654 | 0.006621 |
| lstm | vitaldb | 0.8 | window | start_score_30_decile | 3 | 5 | 0 | 0 | 24 | 0.006621 | 0.01251 |
| lstm | vitaldb | 0.8 | window | start_score_30_decile | 4 | 10 | 1 | 0.1 | 31.5 | 0.01251 | 0.02604 |
| lstm | vitaldb | 0.8 | window | start_score_30_decile | 5 | 23 | 3 | 0.1304 | 26 | 0.02604 | 0.05784 |
| lstm | vitaldb | 0.8 | window | start_score_30_decile | 6 | 19 | 2 | 0.1053 | 27 | 0.05784 | 0.1689 |
| lstm | vitaldb | 0.8 | window | start_score_30_decile | 7 | 33 | 3 | 0.09091 | 35 | 0.1689 | 0.5146 |
| lstm | vitaldb | 0.8 | window | start_score_30_decile | 8 | 0 | 0 | nan | nan | 0.5146 | 0.5277 |
| lstm | vitaldb | 0.8 | window | start_score_30_decile | 9 | 338 | 1 | 0.002959 | 6 | 0.5277 | 0.7206 |
| lstm | vitaldb | 0.8 | window | start_score_30_decile | 10 | 58 | 2 | 0.03448 | 34 | 0.7206 | 0.9989 |
| lstm | mover | 0.8 | window | observable_min_band | <20 | 241 | 0 | 0 | 6 | nan | nan |
| lstm | mover | 0.8 | window | observable_min_band | 20-39 | 166 | 0 | 0 | 23 | nan | nan |
| lstm | mover | 0.8 | window | observable_min_band | 40-59 | 82 | 0 | 0 | 41 | nan | nan |
| lstm | mover | 0.8 | window | observable_min_band | >=60 | 288 | 31 | 0.1076 | 28 | nan | nan |
| lstm | mover | 0.8 | window | start_score_30_decile | 1 | 16 | 0 | 0 | 7.5 | 0.0006276 | 0.003311 |
| lstm | mover | 0.8 | window | start_score_30_decile | 2 | 29 | 1 | 0.03448 | 23 | 0.003311 | 0.009107 |
| lstm | mover | 0.8 | window | start_score_30_decile | 3 | 29 | 4 | 0.1379 | 15 | 0.009107 | 0.02482 |
| lstm | mover | 0.8 | window | start_score_30_decile | 4 | 45 | 4 | 0.08889 | 23 | 0.02482 | 0.06961 |
| lstm | mover | 0.8 | window | start_score_30_decile | 5 | 48 | 3 | 0.0625 | 24 | 0.06961 | 0.2153 |
| lstm | mover | 0.8 | window | start_score_30_decile | 6 | 74 | 5 | 0.06757 | 23.5 | 0.2153 | 0.5007 |
| lstm | mover | 0.8 | window | start_score_30_decile | 7 | 4 | 1 | 0.25 | 11.5 | 0.5007 | 0.5277 |
| lstm | mover | 0.8 | window | start_score_30_decile | 8 | 416 | 10 | 0.02404 | 11 | 0.5277 | 0.8481 |
| lstm | mover | 0.8 | window | start_score_30_decile | 9 | 116 | 3 | 0.02586 | 36 | 0.8481 | 0.999 |
| xgb | epic_test | 0.8 | window | observable_min_band | <20 | 145 | 47 | 0.3241 | 8 | nan | nan |
| xgb | epic_test | 0.8 | window | observable_min_band | 20-39 | 131 | 34 | 0.2595 | 21 | nan | nan |
| xgb | epic_test | 0.8 | window | observable_min_band | 40-59 | 98 | 21 | 0.2143 | 38 | nan | nan |
| xgb | epic_test | 0.8 | window | observable_min_band | >=60 | 263 | 37 | 0.1407 | 40 | nan | nan |
| xgb | epic_test | 0.8 | window | start_score_30_decile | 1 | 27 | 2 | 0.07407 | 18 | 0.006888 | 0.03242 |
| xgb | epic_test | 0.8 | window | start_score_30_decile | 2 | 38 | 4 | 0.1053 | 39.5 | 0.03242 | 0.05589 |
| xgb | epic_test | 0.8 | window | start_score_30_decile | 3 | 38 | 7 | 0.1842 | 16.5 | 0.05589 | 0.0985 |
| xgb | epic_test | 0.8 | window | start_score_30_decile | 4 | 59 | 4 | 0.0678 | 18 | 0.0985 | 0.1708 |
| xgb | epic_test | 0.8 | window | start_score_30_decile | 5 | 49 | 5 | 0.102 | 22 | 0.1708 | 0.2824 |
| xgb | epic_test | 0.8 | window | start_score_30_decile | 6 | 66 | 3 | 0.04545 | 15 | 0.2824 | 0.4497 |
| xgb | epic_test | 0.8 | window | start_score_30_decile | 7 | 62 | 9 | 0.1452 | 21 | 0.4497 | 0.6599 |
| xgb | epic_test | 0.8 | window | start_score_30_decile | 8 | 85 | 8 | 0.09412 | 21 | 0.6599 | 0.82 |
| xgb | epic_test | 0.8 | window | start_score_30_decile | 9 | 101 | 13 | 0.1287 | 20 | 0.82 | 0.9257 |
| xgb | epic_test | 0.8 | window | start_score_30_decile | 10 | 112 | 84 | 0.75 | 23.5 | 0.9257 | 0.9914 |
| xgb | vitaldb | 0.8 | window | observable_min_band | <20 | 193 | 25 | 0.1295 | 3 | nan | nan |
| xgb | vitaldb | 0.8 | window | observable_min_band | 20-39 | 102 | 4 | 0.03922 | 14 | nan | nan |
| xgb | vitaldb | 0.8 | window | observable_min_band | 40-59 | 77 | 3 | 0.03896 | 17 | nan | nan |
| xgb | vitaldb | 0.8 | window | observable_min_band | >=60 | 327 | 23 | 0.07034 | 33 | nan | nan |
| xgb | vitaldb | 0.8 | window | start_score_30_decile | 1 | 18 | 1 | 0.05556 | 10.5 | 0.007988 | 0.02055 |
| xgb | vitaldb | 0.8 | window | start_score_30_decile | 2 | 37 | 1 | 0.02703 | 7 | 0.02055 | 0.02778 |
| xgb | vitaldb | 0.8 | window | start_score_30_decile | 3 | 37 | 0 | 0 | 6 | 0.02778 | 0.03568 |
| xgb | vitaldb | 0.8 | window | start_score_30_decile | 4 | 52 | 0 | 0 | 6 | 0.03568 | 0.04548 |
| xgb | vitaldb | 0.8 | window | start_score_30_decile | 5 | 55 | 0 | 0 | 8 | 0.04548 | 0.06322 |
| xgb | vitaldb | 0.8 | window | start_score_30_decile | 6 | 54 | 3 | 0.05556 | 9.5 | 0.06322 | 0.09856 |
| xgb | vitaldb | 0.8 | window | start_score_30_decile | 7 | 82 | 6 | 0.07317 | 10.5 | 0.09856 | 0.1805 |
| xgb | vitaldb | 0.8 | window | start_score_30_decile | 8 | 91 | 2 | 0.02198 | 13 | 0.1805 | 0.3339 |
| xgb | vitaldb | 0.8 | window | start_score_30_decile | 9 | 102 | 2 | 0.01961 | 21 | 0.3339 | 0.6046 |
| xgb | vitaldb | 0.8 | window | start_score_30_decile | 10 | 171 | 40 | 0.2339 | 30 | 0.6046 | 0.9834 |
| xgb | mover | 0.8 | window | observable_min_band | <20 | 223 | 57 | 0.2556 | 5 | nan | nan |
| xgb | mover | 0.8 | window | observable_min_band | 20-39 | 219 | 26 | 0.1187 | 17 | nan | nan |
| xgb | mover | 0.8 | window | observable_min_band | 40-59 | 103 | 10 | 0.09709 | 30 | nan | nan |
| xgb | mover | 0.8 | window | observable_min_band | >=60 | 568 | 53 | 0.09331 | 37 | nan | nan |
| xgb | mover | 0.8 | window | start_score_30_decile | 1 | 50 | 0 | 0 | 13 | 0.008008 | 0.02187 |
| xgb | mover | 0.8 | window | start_score_30_decile | 2 | 66 | 1 | 0.01515 | 9 | 0.02187 | 0.03656 |
| xgb | mover | 0.8 | window | start_score_30_decile | 3 | 68 | 1 | 0.01471 | 12.5 | 0.03656 | 0.05806 |
| xgb | mover | 0.8 | window | start_score_30_decile | 4 | 86 | 0 | 0 | 14 | 0.05806 | 0.09804 |
| xgb | mover | 0.8 | window | start_score_30_decile | 5 | 109 | 8 | 0.07339 | 13 | 0.09804 | 0.181 |
| xgb | mover | 0.8 | window | start_score_30_decile | 6 | 107 | 7 | 0.06542 | 13 | 0.181 | 0.3092 |
| xgb | mover | 0.8 | window | start_score_30_decile | 7 | 115 | 5 | 0.04348 | 20 | 0.3092 | 0.4955 |
| xgb | mover | 0.8 | window | start_score_30_decile | 8 | 151 | 12 | 0.07947 | 26 | 0.4955 | 0.7164 |
| xgb | mover | 0.8 | window | start_score_30_decile | 9 | 154 | 13 | 0.08442 | 31 | 0.7164 | 0.8895 |
| xgb | mover | 0.8 | window | start_score_30_decile | 10 | 207 | 99 | 0.4783 | 30 | 0.8895 | 0.9891 |
| rf | epic_test | 0.8 | window | observable_min_band | <20 | 142 | 46 | 0.3239 | 8 | nan | nan |
| rf | epic_test | 0.8 | window | observable_min_band | 20-39 | 135 | 23 | 0.1704 | 20 | nan | nan |
| rf | epic_test | 0.8 | window | observable_min_band | 40-59 | 96 | 18 | 0.1875 | 34 | nan | nan |
| rf | epic_test | 0.8 | window | observable_min_band | >=60 | 278 | 43 | 0.1547 | 41 | nan | nan |
| rf | epic_test | 0.8 | window | start_score_30_decile | 1 | 33 | 3 | 0.09091 | 22 | 0.0025 | 0.05 |
| rf | epic_test | 0.8 | window | start_score_30_decile | 2 | 46 | 4 | 0.08696 | 23.5 | 0.05 | 0.1075 |
| rf | epic_test | 0.8 | window | start_score_30_decile | 3 | 49 | 8 | 0.1633 | 20 | 0.1075 | 0.175 |
| rf | epic_test | 0.8 | window | start_score_30_decile | 4 | 53 | 2 | 0.03774 | 22 | 0.175 | 0.2505 |
| rf | epic_test | 0.8 | window | start_score_30_decile | 5 | 52 | 4 | 0.07692 | 16.5 | 0.2505 | 0.3387 |
| rf | epic_test | 0.8 | window | start_score_30_decile | 6 | 61 | 7 | 0.1148 | 16 | 0.3387 | 0.445 |
| rf | epic_test | 0.8 | window | start_score_30_decile | 7 | 69 | 11 | 0.1594 | 23 | 0.445 | 0.5625 |
| rf | epic_test | 0.8 | window | start_score_30_decile | 8 | 78 | 5 | 0.0641 | 23.5 | 0.5625 | 0.6725 |
| rf | epic_test | 0.8 | window | start_score_30_decile | 9 | 98 | 21 | 0.2143 | 16.5 | 0.6725 | 0.8225 |
| rf | epic_test | 0.8 | window | start_score_30_decile | 10 | 112 | 65 | 0.5804 | 31 | 0.8225 | 0.995 |
| rf | vitaldb | 0.8 | window | observable_min_band | <20 | 241 | 37 | 0.1535 | 4 | nan | nan |
| rf | vitaldb | 0.8 | window | observable_min_band | 20-39 | 114 | 7 | 0.0614 | 15 | nan | nan |
| rf | vitaldb | 0.8 | window | observable_min_band | 40-59 | 89 | 5 | 0.05618 | 23 | nan | nan |
| rf | vitaldb | 0.8 | window | observable_min_band | >=60 | 365 | 44 | 0.1205 | 40 | nan | nan |
| rf | vitaldb | 0.8 | window | start_score_30_decile | 1 | 30 | 3 | 0.1 | 10.5 | 0 | 0.0325 |
| rf | vitaldb | 0.8 | window | start_score_30_decile | 2 | 45 | 0 | 0 | 9 | 0.0325 | 0.0525 |
| rf | vitaldb | 0.8 | window | start_score_30_decile | 3 | 56 | 3 | 0.05357 | 8 | 0.0525 | 0.075 |
| rf | vitaldb | 0.8 | window | start_score_30_decile | 4 | 66 | 2 | 0.0303 | 7 | 0.075 | 0.1005 |
| rf | vitaldb | 0.8 | window | start_score_30_decile | 5 | 59 | 3 | 0.05085 | 7 | 0.1005 | 0.1375 |
| rf | vitaldb | 0.8 | window | start_score_30_decile | 6 | 73 | 6 | 0.08219 | 13 | 0.1375 | 0.185 |
| rf | vitaldb | 0.8 | window | start_score_30_decile | 7 | 80 | 6 | 0.075 | 14 | 0.185 | 0.265 |
| rf | vitaldb | 0.8 | window | start_score_30_decile | 8 | 104 | 4 | 0.03846 | 15.5 | 0.265 | 0.395 |
| rf | vitaldb | 0.8 | window | start_score_30_decile | 9 | 129 | 8 | 0.06202 | 20 | 0.395 | 0.615 |
| rf | vitaldb | 0.8 | window | start_score_30_decile | 10 | 167 | 58 | 0.3473 | 32 | 0.615 | 0.99 |
| rf | mover | 0.8 | window | observable_min_band | <20 | 248 | 81 | 0.3266 | 6 | nan | nan |
| rf | mover | 0.8 | window | observable_min_band | 20-39 | 233 | 36 | 0.1545 | 18 | nan | nan |
| rf | mover | 0.8 | window | observable_min_band | 40-59 | 110 | 16 | 0.1455 | 32 | nan | nan |
| rf | mover | 0.8 | window | observable_min_band | >=60 | 605 | 76 | 0.1256 | 42 | nan | nan |
| rf | mover | 0.8 | window | start_score_30_decile | 1 | 67 | 0 | 0 | 9 | 0 | 0.025 |
| rf | mover | 0.8 | window | start_score_30_decile | 2 | 77 | 3 | 0.03896 | 11 | 0.025 | 0.0475 |
| rf | mover | 0.8 | window | start_score_30_decile | 3 | 95 | 4 | 0.04211 | 11 | 0.0475 | 0.0925 |
| rf | mover | 0.8 | window | start_score_30_decile | 4 | 94 | 6 | 0.06383 | 16 | 0.0925 | 0.145 |
| rf | mover | 0.8 | window | start_score_30_decile | 5 | 106 | 7 | 0.06604 | 14.5 | 0.145 | 0.225 |
| rf | mover | 0.8 | window | start_score_30_decile | 6 | 115 | 7 | 0.06087 | 21 | 0.225 | 0.3275 |
| rf | mover | 0.8 | window | start_score_30_decile | 7 | 132 | 9 | 0.06818 | 22 | 0.3275 | 0.4525 |
| rf | mover | 0.8 | window | start_score_30_decile | 8 | 127 | 15 | 0.1181 | 31 | 0.4525 | 0.615 |
| rf | mover | 0.8 | window | start_score_30_decile | 9 | 177 | 37 | 0.209 | 33 | 0.615 | 0.845 |
| rf | mover | 0.8 | window | start_score_30_decile | 10 | 206 | 121 | 0.5874 | 31 | 0.845 | 1 |
| logreg | epic_test | 0.8 | window | observable_min_band | <20 | 156 | 65 | 0.4167 | 9 | nan | nan |
| logreg | epic_test | 0.8 | window | observable_min_band | 20-39 | 136 | 44 | 0.3235 | 22 | nan | nan |
| logreg | epic_test | 0.8 | window | observable_min_band | 40-59 | 101 | 21 | 0.2079 | 40 | nan | nan |
| logreg | epic_test | 0.8 | window | observable_min_band | >=60 | 265 | 38 | 0.1434 | 42 | nan | nan |
| logreg | epic_test | 0.8 | window | start_score_30_decile | 1 | 40 | 6 | 0.15 | 22 | 1.107e-07 | 0.01961 |
| logreg | epic_test | 0.8 | window | start_score_30_decile | 2 | 40 | 4 | 0.1 | 19.5 | 0.01961 | 0.07496 |
| logreg | epic_test | 0.8 | window | start_score_30_decile | 3 | 52 | 4 | 0.07692 | 21.5 | 0.07496 | 0.1784 |
| logreg | epic_test | 0.8 | window | start_score_30_decile | 4 | 48 | 4 | 0.08333 | 31 | 0.1784 | 0.3472 |
| logreg | epic_test | 0.8 | window | start_score_30_decile | 5 | 66 | 3 | 0.04545 | 26.5 | 0.3472 | 0.5214 |
| logreg | epic_test | 0.8 | window | start_score_30_decile | 6 | 62 | 8 | 0.129 | 16 | 0.5214 | 0.6146 |
| logreg | epic_test | 0.8 | window | start_score_30_decile | 7 | 63 | 6 | 0.09524 | 16 | 0.6146 | 0.683 |
| logreg | epic_test | 0.8 | window | start_score_30_decile | 8 | 76 | 6 | 0.07895 | 25 | 0.683 | 0.7543 |
| logreg | epic_test | 0.8 | window | start_score_30_decile | 9 | 98 | 47 | 0.4796 | 24 | 0.7543 | 0.8085 |
| logreg | epic_test | 0.8 | window | start_score_30_decile | 10 | 113 | 80 | 0.708 | 27 | 0.8085 | 0.9983 |
| logreg | vitaldb | 0.8 | window | observable_min_band | <20 | 130 | 17 | 0.1308 | 3 | nan | nan |
| logreg | vitaldb | 0.8 | window | observable_min_band | 20-39 | 74 | 3 | 0.04054 | 14.5 | nan | nan |
| logreg | vitaldb | 0.8 | window | observable_min_band | 40-59 | 50 | 2 | 0.04 | 18.5 | nan | nan |
| logreg | vitaldb | 0.8 | window | observable_min_band | >=60 | 210 | 11 | 0.05238 | 31 | nan | nan |
| logreg | vitaldb | 0.8 | window | start_score_30_decile | 1 | 15 | 0 | 0 | 17 | 6.595e-06 | 0.02098 |
| logreg | vitaldb | 0.8 | window | start_score_30_decile | 2 | 17 | 3 | 0.1765 | 15 | 0.02098 | 0.05324 |
| logreg | vitaldb | 0.8 | window | start_score_30_decile | 3 | 25 | 0 | 0 | 8 | 0.05324 | 0.08818 |
| logreg | vitaldb | 0.8 | window | start_score_30_decile | 4 | 22 | 0 | 0 | 5 | 0.08818 | 0.139 |
| logreg | vitaldb | 0.8 | window | start_score_30_decile | 5 | 34 | 0 | 0 | 9.5 | 0.139 | 0.1978 |
| logreg | vitaldb | 0.8 | window | start_score_30_decile | 6 | 36 | 0 | 0 | 7 | 0.1978 | 0.2793 |
| logreg | vitaldb | 0.8 | window | start_score_30_decile | 7 | 37 | 0 | 0 | 13 | 0.2793 | 0.3786 |
| logreg | vitaldb | 0.8 | window | start_score_30_decile | 8 | 72 | 1 | 0.01389 | 15.5 | 0.3786 | 0.4831 |
| logreg | vitaldb | 0.8 | window | start_score_30_decile | 9 | 80 | 3 | 0.0375 | 12 | 0.4831 | 0.6214 |
| logreg | vitaldb | 0.8 | window | start_score_30_decile | 10 | 126 | 26 | 0.2063 | 28.5 | 0.6214 | 0.997 |
| logreg | mover | 0.8 | window | observable_min_band | <20 | 222 | 61 | 0.2748 | 5 | nan | nan |
| logreg | mover | 0.8 | window | observable_min_band | 20-39 | 212 | 23 | 0.1085 | 16 | nan | nan |
| logreg | mover | 0.8 | window | observable_min_band | 40-59 | 109 | 8 | 0.07339 | 28 | nan | nan |
| logreg | mover | 0.8 | window | observable_min_band | >=60 | 570 | 62 | 0.1088 | 40 | nan | nan |
| logreg | mover | 0.8 | window | start_score_30_decile | 1 | 55 | 3 | 0.05455 | 13 | 9.038e-06 | 0.03752 |
| logreg | mover | 0.8 | window | start_score_30_decile | 2 | 69 | 0 | 0 | 12 | 0.03752 | 0.1011 |
| logreg | mover | 0.8 | window | start_score_30_decile | 3 | 78 | 3 | 0.03846 | 14.5 | 0.1011 | 0.1874 |
| logreg | mover | 0.8 | window | start_score_30_decile | 4 | 88 | 1 | 0.01136 | 11.5 | 0.1874 | 0.2878 |
| logreg | mover | 0.8 | window | start_score_30_decile | 5 | 96 | 4 | 0.04167 | 20 | 0.2878 | 0.4077 |
| logreg | mover | 0.8 | window | start_score_30_decile | 6 | 107 | 5 | 0.04673 | 15 | 0.4077 | 0.506 |
| logreg | mover | 0.8 | window | start_score_30_decile | 7 | 132 | 8 | 0.06061 | 20.5 | 0.506 | 0.6148 |
| logreg | mover | 0.8 | window | start_score_30_decile | 8 | 145 | 8 | 0.05517 | 23 | 0.6148 | 0.6866 |
| logreg | mover | 0.8 | window | start_score_30_decile | 9 | 140 | 16 | 0.1143 | 28 | 0.6866 | 0.7696 |
| logreg | mover | 0.8 | window | start_score_30_decile | 10 | 203 | 106 | 0.5222 | 32 | 0.7696 | 0.9965 |

