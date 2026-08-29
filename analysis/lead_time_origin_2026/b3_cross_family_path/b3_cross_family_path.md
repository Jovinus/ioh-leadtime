# B3 - is the path shape a property of the transformer or of the task?

Event episodes, spanning sample, window start 60 minutes before the reference time. `directedness` is net change divided by total path length: +1 a monotone rise, 0 a pure wobble, -1 a monotone fall. `path_per_net` is total path length divided by the absolute net change -- how much travelling bought one unit of displacement. All values are medians over episodes with cluster-bootstrap 95% intervals, read from A6; nothing is recomputed. Windows with median step count below 3 are excluded because directedness and the largest-step share are then pinned by arithmetic.

## The 60-to-5 window

### MOVER (EPIC) test

| Model | n | Up path | Down path | Net | Directedness (95% CI) | Largest step / gross rise | Path per unit net |
|---|---|---|---|---|---|---|---|
| ITE Transformer | 313 | 0.969 | 0.951 | +0.046 | +0.025 (+0.002 to +0.050) | 0.488 | 41 |
| LSTM | 313 | 1.044 | 0.921 | +0.076 | +0.043 (+0.024 to +0.057) | 0.478 | 26 |
| XGBoost | 313 | 1.160 | 1.034 | +0.108 | +0.049 (+0.033 to +0.070) | 0.422 | 20 |
| Random forest | 313 | 1.042 | 0.886 | +0.117 | +0.067 (+0.038 to +0.093) | 0.405 | 16 |
| Logistic regression | 313 | 0.963 | 0.838 | +0.100 | +0.061 (+0.044 to +0.089) | 0.387 | 18 |


### VitalDB

| Model | n | Up path | Down path | Net | Directedness (95% CI) | Largest step / gross rise | Path per unit net |
|---|---|---|---|---|---|---|---|
| ITE Transformer | 433 | 0.959 | 0.950 | +0.013 | +0.021 (+0.005 to +0.038) | 0.490 | 147 |
| LSTM | 433 | 0.860 | 0.771 | +0.057 | +0.059 (+0.035 to +0.070) | 0.482 | 28 |
| XGBoost | 433 | 1.055 | 0.872 | +0.108 | +0.069 (+0.049 to +0.099) | 0.433 | 18 |
| Random forest | 433 | 1.002 | 0.800 | +0.126 | +0.075 (+0.053 to +0.094) | 0.419 | 14 |
| Logistic regression | 433 | 0.796 | 0.655 | +0.115 | +0.088 (+0.063 to +0.108) | 0.366 | 13 |


### MOVER (SIS)

| Model | n | Up path | Down path | Net | Directedness (95% CI) | Largest step / gross rise | Path per unit net |
|---|---|---|---|---|---|---|---|
| ITE Transformer | 670 | 0.998 | 0.868 | +0.139 | +0.089 (+0.066 to +0.122) | 0.455 | 13 |
| LSTM | 670 | 1.022 | 0.751 | +0.222 | +0.142 (+0.118 to +0.183) | 0.442 | 8 |
| XGBoost | 670 | 1.122 | 0.846 | +0.268 | +0.144 (+0.120 to +0.167) | 0.409 | 7 |
| Random forest | 670 | 1.061 | 0.787 | +0.261 | +0.151 (+0.132 to +0.168) | 0.405 | 7 |
| Logistic regression | 670 | 0.835 | 0.633 | +0.187 | +0.134 (+0.119 to +0.154) | 0.365 | 8 |


## The 60-to-10 window

### MOVER (EPIC) test

| Model | n | Up path | Down path | Net | Directedness (95% CI) | Largest step / gross rise | Path per unit net |
|---|---|---|---|---|---|---|---|
| ITE Transformer | 313 | 0.825 | 0.897 | -0.000 | -0.000 (-0.012 to +0.017) | 0.510 | 57754 |
| LSTM | 313 | 0.915 | 0.889 | +0.023 | +0.021 (+0.004 to +0.050) | 0.501 | 77 |
| XGBoost | 313 | 1.009 | 0.943 | +0.059 | +0.042 (+0.018 to +0.065) | 0.456 | 34 |
| Random forest | 313 | 0.936 | 0.814 | +0.070 | +0.047 (+0.022 to +0.069) | 0.438 | 24 |
| Logistic regression | 313 | 0.835 | 0.765 | +0.052 | +0.037 (+0.016 to +0.064) | 0.418 | 31 |


### VitalDB

| Model | n | Up path | Down path | Net | Directedness (95% CI) | Largest step / gross rise | Path per unit net |
|---|---|---|---|---|---|---|---|
| ITE Transformer | 433 | 0.818 | 0.851 | -0.000 | -0.000 (-0.018 to +0.007) | 0.525 | 92859 |
| LSTM | 433 | 0.729 | 0.718 | +0.007 | +0.013 (+0.001 to +0.037) | 0.524 | 208 |
| XGBoost | 433 | 0.938 | 0.765 | +0.049 | +0.042 (+0.019 to +0.068) | 0.462 | 35 |
| Random forest | 433 | 0.869 | 0.729 | +0.061 | +0.043 (+0.021 to +0.071) | 0.438 | 26 |
| Logistic regression | 433 | 0.694 | 0.585 | +0.067 | +0.056 (+0.029 to +0.085) | 0.391 | 19 |


### MOVER (SIS)

| Model | n | Up path | Down path | Net | Directedness (95% CI) | Largest step / gross rise | Path per unit net |
|---|---|---|---|---|---|---|---|
| ITE Transformer | 670 | 0.848 | 0.794 | +0.058 | +0.058 (+0.039 to +0.082) | 0.501 | 27 |
| LSTM | 670 | 0.896 | 0.682 | +0.152 | +0.096 (+0.079 to +0.139) | 0.483 | 10 |
| XGBoost | 670 | 0.984 | 0.761 | +0.208 | +0.119 (+0.097 to +0.143) | 0.444 | 8 |
| Random forest | 670 | 0.919 | 0.684 | +0.184 | +0.123 (+0.099 to +0.141) | 0.436 | 8 |
| Logistic regression | 670 | 0.738 | 0.572 | +0.154 | +0.124 (+0.105 to +0.144) | 0.393 | 8 |


## Do the directedness intervals separate?

Every pair of families within a cohort and window. `ALL PAIRS` is true only if every pairwise interval overlaps in that cell.

| endpoint_min | cohort | cohort_label | family_a | family_b | directedness_a | directedness_b | ci_a | ci_b | intervals_overlap |
|---|---|---|---|---|---|---|---|---|---|
| 5 | epic_test | MOVER (EPIC) test | transformer | lstm | 0.0252 | 0.04315 | 0.002–0.050 | 0.024–0.057 | True |
| 5 | epic_test | MOVER (EPIC) test | transformer | xgb | 0.0252 | 0.04858 | 0.002–0.050 | 0.033–0.070 | True |
| 5 | epic_test | MOVER (EPIC) test | transformer | rf | 0.0252 | 0.06672 | 0.002–0.050 | 0.038–0.093 | True |
| 5 | epic_test | MOVER (EPIC) test | transformer | logreg | 0.0252 | 0.06121 | 0.002–0.050 | 0.044–0.089 | True |
| 5 | epic_test | MOVER (EPIC) test | lstm | xgb | 0.04315 | 0.04858 | 0.024–0.057 | 0.033–0.070 | True |
| 5 | epic_test | MOVER (EPIC) test | lstm | rf | 0.04315 | 0.06672 | 0.024–0.057 | 0.038–0.093 | True |
| 5 | epic_test | MOVER (EPIC) test | lstm | logreg | 0.04315 | 0.06121 | 0.024–0.057 | 0.044–0.089 | True |
| 5 | epic_test | MOVER (EPIC) test | xgb | rf | 0.04858 | 0.06672 | 0.033–0.070 | 0.038–0.093 | True |
| 5 | epic_test | MOVER (EPIC) test | xgb | logreg | 0.04858 | 0.06121 | 0.033–0.070 | 0.044–0.089 | True |
| 5 | epic_test | MOVER (EPIC) test | rf | logreg | 0.06672 | 0.06121 | 0.038–0.093 | 0.044–0.089 | True |
| 5 | epic_test | MOVER (EPIC) test | ALL PAIRS |  | nan | nan |  |  | True |
| 5 | vitaldb | VitalDB | transformer | lstm | 0.0208 | 0.0591 | 0.005–0.038 | 0.035–0.070 | True |
| 5 | vitaldb | VitalDB | transformer | xgb | 0.0208 | 0.06933 | 0.005–0.038 | 0.049–0.099 | False |
| 5 | vitaldb | VitalDB | transformer | rf | 0.0208 | 0.07517 | 0.005–0.038 | 0.053–0.094 | False |
| 5 | vitaldb | VitalDB | transformer | logreg | 0.0208 | 0.08821 | 0.005–0.038 | 0.063–0.108 | False |
| 5 | vitaldb | VitalDB | lstm | xgb | 0.0591 | 0.06933 | 0.035–0.070 | 0.049–0.099 | True |
| 5 | vitaldb | VitalDB | lstm | rf | 0.0591 | 0.07517 | 0.035–0.070 | 0.053–0.094 | True |
| 5 | vitaldb | VitalDB | lstm | logreg | 0.0591 | 0.08821 | 0.035–0.070 | 0.063–0.108 | True |
| 5 | vitaldb | VitalDB | xgb | rf | 0.06933 | 0.07517 | 0.049–0.099 | 0.053–0.094 | True |
| 5 | vitaldb | VitalDB | xgb | logreg | 0.06933 | 0.08821 | 0.049–0.099 | 0.063–0.108 | True |
| 5 | vitaldb | VitalDB | rf | logreg | 0.07517 | 0.08821 | 0.053–0.094 | 0.063–0.108 | True |
| 5 | vitaldb | VitalDB | ALL PAIRS |  | nan | nan |  |  | False |
| 5 | mover | MOVER (SIS) | transformer | lstm | 0.08903 | 0.1423 | 0.066–0.122 | 0.118–0.183 | True |
| 5 | mover | MOVER (SIS) | transformer | xgb | 0.08903 | 0.1437 | 0.066–0.122 | 0.120–0.167 | True |
| 5 | mover | MOVER (SIS) | transformer | rf | 0.08903 | 0.1509 | 0.066–0.122 | 0.132–0.168 | False |
| 5 | mover | MOVER (SIS) | transformer | logreg | 0.08903 | 0.1336 | 0.066–0.122 | 0.119–0.154 | True |
| 5 | mover | MOVER (SIS) | lstm | xgb | 0.1423 | 0.1437 | 0.118–0.183 | 0.120–0.167 | True |
| 5 | mover | MOVER (SIS) | lstm | rf | 0.1423 | 0.1509 | 0.118–0.183 | 0.132–0.168 | True |
| 5 | mover | MOVER (SIS) | lstm | logreg | 0.1423 | 0.1336 | 0.118–0.183 | 0.119–0.154 | True |
| 5 | mover | MOVER (SIS) | xgb | rf | 0.1437 | 0.1509 | 0.120–0.167 | 0.132–0.168 | True |
| 5 | mover | MOVER (SIS) | xgb | logreg | 0.1437 | 0.1336 | 0.120–0.167 | 0.119–0.154 | True |
| 5 | mover | MOVER (SIS) | rf | logreg | 0.1509 | 0.1336 | 0.132–0.168 | 0.119–0.154 | True |
| 5 | mover | MOVER (SIS) | ALL PAIRS |  | nan | nan |  |  | False |
| 10 | epic_test | MOVER (EPIC) test | transformer | lstm | -5.229e-05 | 0.02093 | -0.012–0.017 | 0.004–0.050 | True |
| 10 | epic_test | MOVER (EPIC) test | transformer | xgb | -5.229e-05 | 0.04218 | -0.012–0.017 | 0.018–0.065 | False |
| 10 | epic_test | MOVER (EPIC) test | transformer | rf | -5.229e-05 | 0.04656 | -0.012–0.017 | 0.022–0.069 | False |
| 10 | epic_test | MOVER (EPIC) test | transformer | logreg | -5.229e-05 | 0.03679 | -0.012–0.017 | 0.016–0.064 | True |
| 10 | epic_test | MOVER (EPIC) test | lstm | xgb | 0.02093 | 0.04218 | 0.004–0.050 | 0.018–0.065 | True |
| 10 | epic_test | MOVER (EPIC) test | lstm | rf | 0.02093 | 0.04656 | 0.004–0.050 | 0.022–0.069 | True |
| 10 | epic_test | MOVER (EPIC) test | lstm | logreg | 0.02093 | 0.03679 | 0.004–0.050 | 0.016–0.064 | True |
| 10 | epic_test | MOVER (EPIC) test | xgb | rf | 0.04218 | 0.04656 | 0.018–0.065 | 0.022–0.069 | True |
| 10 | epic_test | MOVER (EPIC) test | xgb | logreg | 0.04218 | 0.03679 | 0.018–0.065 | 0.016–0.064 | True |
| 10 | epic_test | MOVER (EPIC) test | rf | logreg | 0.04656 | 0.03679 | 0.022–0.069 | 0.016–0.064 | True |
| 10 | epic_test | MOVER (EPIC) test | ALL PAIRS |  | nan | nan |  |  | False |
| 10 | vitaldb | VitalDB | transformer | lstm | -1.812e-05 | 0.01343 | -0.018–0.007 | 0.001–0.037 | True |
| 10 | vitaldb | VitalDB | transformer | xgb | -1.812e-05 | 0.04231 | -0.018–0.007 | 0.019–0.068 | False |
| 10 | vitaldb | VitalDB | transformer | rf | -1.812e-05 | 0.04301 | -0.018–0.007 | 0.021–0.071 | False |
| 10 | vitaldb | VitalDB | transformer | logreg | -1.812e-05 | 0.05568 | -0.018–0.007 | 0.029–0.085 | False |
| 10 | vitaldb | VitalDB | lstm | xgb | 0.01343 | 0.04231 | 0.001–0.037 | 0.019–0.068 | True |
| 10 | vitaldb | VitalDB | lstm | rf | 0.01343 | 0.04301 | 0.001–0.037 | 0.021–0.071 | True |
| 10 | vitaldb | VitalDB | lstm | logreg | 0.01343 | 0.05568 | 0.001–0.037 | 0.029–0.085 | True |
| 10 | vitaldb | VitalDB | xgb | rf | 0.04231 | 0.04301 | 0.019–0.068 | 0.021–0.071 | True |
| 10 | vitaldb | VitalDB | xgb | logreg | 0.04231 | 0.05568 | 0.019–0.068 | 0.029–0.085 | True |
| 10 | vitaldb | VitalDB | rf | logreg | 0.04301 | 0.05568 | 0.021–0.071 | 0.029–0.085 | True |
| 10 | vitaldb | VitalDB | ALL PAIRS |  | nan | nan |  |  | False |
| 10 | mover | MOVER (SIS) | transformer | lstm | 0.05835 | 0.09597 | 0.039–0.082 | 0.079–0.139 | True |
| 10 | mover | MOVER (SIS) | transformer | xgb | 0.05835 | 0.1192 | 0.039–0.082 | 0.097–0.143 | False |
| 10 | mover | MOVER (SIS) | transformer | rf | 0.05835 | 0.1228 | 0.039–0.082 | 0.099–0.141 | False |
| 10 | mover | MOVER (SIS) | transformer | logreg | 0.05835 | 0.1239 | 0.039–0.082 | 0.105–0.144 | False |
| 10 | mover | MOVER (SIS) | lstm | xgb | 0.09597 | 0.1192 | 0.079–0.139 | 0.097–0.143 | True |
| 10 | mover | MOVER (SIS) | lstm | rf | 0.09597 | 0.1228 | 0.079–0.139 | 0.099–0.141 | True |
| 10 | mover | MOVER (SIS) | lstm | logreg | 0.09597 | 0.1239 | 0.079–0.139 | 0.105–0.144 | True |
| 10 | mover | MOVER (SIS) | xgb | rf | 0.1192 | 0.1228 | 0.097–0.143 | 0.099–0.141 | True |
| 10 | mover | MOVER (SIS) | xgb | logreg | 0.1192 | 0.1239 | 0.097–0.143 | 0.105–0.144 | True |
| 10 | mover | MOVER (SIS) | rf | logreg | 0.1228 | 0.1239 | 0.099–0.141 | 0.105–0.144 | True |
| 10 | mover | MOVER (SIS) | ALL PAIRS |  | nan | nan |  |  | False |


## What the final 5 minutes carry

`delta_last5` is the 60-to-5 net change minus the 60-to-10 net change: the displacement that exists only when the last 5 minutes are included.

| family_label | cohort_label | delta_median_ep5 | delta_median_ep10 | delta_last5 | delta_last5_share_of_60_5 | directedness_median_ep5 | directedness_median_ep10 |
|---|---|---|---|---|---|---|---|
| Logistic regression | MOVER (EPIC) test | 0.0995 | 0.05222 | 0.04728 | 0.4752 | 0.06121 | 0.03679 |
| Logistic regression | MOVER (SIS) | 0.1869 | 0.154 | 0.03286 | 0.1759 | 0.1336 | 0.1239 |
| Logistic regression | VitalDB | 0.115 | 0.06674 | 0.04829 | 0.4198 | 0.08821 | 0.05568 |
| LSTM | MOVER (EPIC) test | 0.07647 | 0.02346 | 0.05301 | 0.6932 | 0.04315 | 0.02093 |
| LSTM | MOVER (SIS) | 0.2224 | 0.1517 | 0.0707 | 0.3179 | 0.1423 | 0.09597 |
| LSTM | VitalDB | 0.05686 | 0.006783 | 0.05008 | 0.8807 | 0.0591 | 0.01343 |
| Random forest | MOVER (EPIC) test | 0.1175 | 0.07 | 0.0475 | 0.4043 | 0.06672 | 0.04656 |
| Random forest | MOVER (SIS) | 0.2606 | 0.1837 | 0.07687 | 0.295 | 0.1509 | 0.1228 |
| Random forest | VitalDB | 0.1262 | 0.06125 | 0.065 | 0.5149 | 0.07517 | 0.04301 |
| ITE Transformer | MOVER (EPIC) test | 0.04647 | -2.965e-05 | 0.0465 | 1.001 | 0.0252 | -5.229e-05 |
| ITE Transformer | MOVER (SIS) | 0.139 | 0.05765 | 0.08132 | 0.5851 | 0.08903 | 0.05835 |
| ITE Transformer | VitalDB | 0.01271 | -1.754e-05 | 0.01273 | 1.001 | 0.0208 | -1.812e-05 |
| XGBoost | MOVER (EPIC) test | 0.1078 | 0.05874 | 0.04905 | 0.4551 | 0.04858 | 0.04218 |
| XGBoost | MOVER (SIS) | 0.2681 | 0.2083 | 0.05981 | 0.2231 | 0.1437 | 0.1192 |
| XGBoost | VitalDB | 0.1076 | 0.04941 | 0.0582 | 0.5408 | 0.06933 | 0.04231 |

