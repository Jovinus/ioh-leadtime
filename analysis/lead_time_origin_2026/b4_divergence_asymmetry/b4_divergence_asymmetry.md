# B4 - which side of the event-control gap is moving?

The gap at each lead-time bin is measured against each side's own 60-minute baseline, so `gap(t) - gap(60)` splits exactly into an event-side change and a control-side change. Shares sum to 1; a share outside [0, 1] means that side moved against the widening. Fixed sample: only episodes observed in every bin from 60 to 5 minutes.

## Sample retention when the denominator is fixed

| family | cohort | n_spanning_edges_only | n_complete_all_bins | retention | n_event_complete | n_control_complete |
|---|---|---|---|---|---|---|
| transformer | epic_test | 708 | 708 | 1 | 313 | 395 |
| transformer | vitaldb | 1433 | 1433 | 1 | 433 | 1000 |
| transformer | mover | 1374 | 1374 | 1 | 670 | 704 |
| lstm | epic_test | 708 | 708 | 1 | 313 | 395 |
| lstm | vitaldb | 1433 | 1433 | 1 | 433 | 1000 |
| lstm | mover | 1374 | 1374 | 1 | 670 | 704 |
| xgb | epic_test | 708 | 708 | 1 | 313 | 395 |
| xgb | vitaldb | 1433 | 1433 | 1 | 433 | 1000 |
| xgb | mover | 1374 | 1374 | 1 | 670 | 704 |
| rf | epic_test | 708 | 708 | 1 | 313 | 395 |
| rf | vitaldb | 1433 | 1433 | 1 | 433 | 1000 |
| rf | mover | 1374 | 1374 | 1 | 670 | 704 |
| logreg | epic_test | 708 | 708 | 1 | 313 | 395 |
| logreg | vitaldb | 1433 | 1433 | 1 | 433 | 1000 |
| logreg | mover | 1374 | 1374 | 1 | 670 | 704 |


## The endpoint bin, 5 minutes before the reference time

### MOVER (EPIC) test

| Model | Event side (95% CI) | Control side (95% CI) | Widening | Event share (95% CI) | Control share (95% CI) | P, event share vs 0.5 |
|---|---|---|---|---|---|---|
| ITE Transformer | +0.052 (+0.004 to +0.101) | -0.274 (-0.317 to -0.232) | +0.326 | 0.16 (0.02–0.27) | 0.84 (0.73–0.98) | 0.0010 |
| LSTM | +0.088 (+0.037 to +0.136) | -0.223 (-0.263 to -0.185) | +0.310 | 0.28 (0.14–0.40) | 0.72 (0.60–0.86) | 0.0010 |
| XGBoost | +0.130 (+0.086 to +0.175) | -0.095 (-0.127 to -0.062) | +0.225 | 0.58 (0.45–0.71) | 0.42 (0.29–0.55) | 0.2230 |
| Random forest | +0.133 (+0.094 to +0.171) | -0.059 (-0.087 to -0.032) | +0.192 | 0.69 (0.57–0.82) | 0.31 (0.18–0.43) | 0.0010 |
| Logistic regression | +0.107 (+0.068 to +0.150) | -0.069 (-0.098 to -0.043) | +0.176 | 0.61 (0.47–0.74) | 0.39 (0.26–0.53) | 0.1180 |


### VitalDB

| Model | Event side (95% CI) | Control side (95% CI) | Widening | Event share (95% CI) | Control share (95% CI) | P, event share vs 0.5 |
|---|---|---|---|---|---|---|
| ITE Transformer | +0.036 (-0.007 to +0.078) | -0.267 (-0.294 to -0.240) | +0.303 | 0.12 (-0.03–0.22) | 0.88 (0.78–1.03) | 0.0010 |
| LSTM | +0.106 (+0.068 to +0.144) | -0.085 (-0.104 to -0.065) | +0.191 | 0.55 (0.44–0.65) | 0.45 (0.35–0.56) | 0.3260 |
| XGBoost | +0.183 (+0.144 to +0.222) | -0.006 (-0.021 to +0.009) | +0.189 | 0.97 (0.89–1.05) | 0.03 (-0.05–0.11) | 0.0010 |
| Random forest | +0.167 (+0.132 to +0.200) | +0.001 (-0.013 to +0.014) | +0.166 | 1.01 (0.93–1.10) | -0.01 (-0.10–0.07) | 0.0010 |
| Logistic regression | +0.131 (+0.105 to +0.158) | +0.004 (-0.009 to +0.018) | +0.127 | 1.03 (0.93–1.16) | -0.03 (-0.16–0.07) | 0.0010 |


### MOVER (SIS)

| Model | Event side (95% CI) | Control side (95% CI) | Widening | Event share (95% CI) | Control share (95% CI) | P, event share vs 0.5 |
|---|---|---|---|---|---|---|
| ITE Transformer | +0.153 (+0.120 to +0.186) | -0.194 (-0.225 to -0.166) | +0.347 | 0.44 (0.37–0.50) | 0.56 (0.50–0.63) | 0.0780 |
| LSTM | +0.245 (+0.211 to +0.279) | -0.071 (-0.097 to -0.046) | +0.316 | 0.77 (0.71–0.84) | 0.23 (0.16–0.29) | 0.0010 |
| XGBoost | +0.276 (+0.245 to +0.304) | +0.007 (-0.016 to +0.030) | +0.269 | 1.02 (0.94–1.12) | -0.02 (-0.12–0.06) | 0.0010 |
| Random forest | +0.256 (+0.228 to +0.285) | +0.016 (-0.005 to +0.036) | +0.240 | 1.07 (0.98–1.17) | -0.07 (-0.17–0.02) | 0.0010 |
| Logistic regression | +0.195 (+0.173 to +0.219) | +0.013 (-0.007 to +0.032) | +0.182 | 1.07 (0.97–1.20) | -0.07 (-0.20–0.03) | 0.0010 |


## Every bin

| cohort_label | family_label | bin_center_min | event_side_change | control_side_change | gap_widening | event_side_share | control_side_share |
|---|---|---|---|---|---|---|---|
| MOVER (EPIC) test | ITE Transformer | 55 | -0.0233 | -0.0279 | 0.0046 | -5.032 | 6.032 |
| MOVER (EPIC) test | ITE Transformer | 50 | -0.0491 | -0.0603 | 0.0112 | -4.397 | 5.397 |
| MOVER (EPIC) test | ITE Transformer | 45 | -0.0481 | -0.1113 | 0.0632 | -0.7621 | 1.762 |
| MOVER (EPIC) test | ITE Transformer | 40 | -0.0954 | -0.1503 | 0.0549 | -1.739 | 2.739 |
| MOVER (EPIC) test | ITE Transformer | 35 | -0.1171 | -0.2133 | 0.0962 | -1.216 | 2.216 |
| MOVER (EPIC) test | ITE Transformer | 30 | -0.1022 | -0.2482 | 0.1459 | -0.7006 | 1.701 |
| MOVER (EPIC) test | ITE Transformer | 25 | -0.0919 | -0.2627 | 0.1707 | -0.5383 | 1.538 |
| MOVER (EPIC) test | ITE Transformer | 20 | -0.0751 | -0.2663 | 0.1912 | -0.3928 | 1.393 |
| MOVER (EPIC) test | ITE Transformer | 15 | -0.0681 | -0.2755 | 0.2074 | -0.3284 | 1.328 |
| MOVER (EPIC) test | ITE Transformer | 10 | 0.003 | -0.2797 | 0.2827 | 0.0107 | 0.9893 |
| MOVER (EPIC) test | ITE Transformer | 5 | 0.0521 | -0.274 | 0.3261 | 0.1598 | 0.8402 |
| VitalDB | ITE Transformer | 55 | -0.0269 | -0.0355 | 0.0086 | -3.118 | 4.118 |
| VitalDB | ITE Transformer | 50 | -0.0688 | -0.1036 | 0.0348 | -1.974 | 2.974 |
| VitalDB | ITE Transformer | 45 | -0.0972 | -0.1594 | 0.0622 | -1.562 | 2.562 |
| VitalDB | ITE Transformer | 40 | -0.1102 | -0.2098 | 0.0997 | -1.105 | 2.105 |
| VitalDB | ITE Transformer | 35 | -0.1119 | -0.2645 | 0.1526 | -0.7334 | 1.733 |
| VitalDB | ITE Transformer | 30 | -0.1117 | -0.2621 | 0.1504 | -0.7426 | 1.743 |
| VitalDB | ITE Transformer | 25 | -0.0976 | -0.2537 | 0.1561 | -0.6253 | 1.625 |
| VitalDB | ITE Transformer | 20 | -0.0601 | -0.2558 | 0.1957 | -0.307 | 1.307 |
| VitalDB | ITE Transformer | 15 | -0.0372 | -0.2649 | 0.2278 | -0.1632 | 1.163 |
| VitalDB | ITE Transformer | 10 | -0.03 | -0.2629 | 0.2329 | -0.1286 | 1.129 |
| VitalDB | ITE Transformer | 5 | 0.0356 | -0.2673 | 0.3029 | 0.1177 | 0.8823 |
| MOVER (SIS) | ITE Transformer | 55 | -0.0003 | -0.0206 | 0.0203 | -0.0151 | 1.015 |
| MOVER (SIS) | ITE Transformer | 50 | -0.0141 | -0.0661 | 0.052 | -0.2715 | 1.272 |
| MOVER (SIS) | ITE Transformer | 45 | -0.0575 | -0.1323 | 0.0748 | -0.7681 | 1.768 |
| MOVER (SIS) | ITE Transformer | 40 | -0.0774 | -0.1879 | 0.1105 | -0.7008 | 1.701 |
| MOVER (SIS) | ITE Transformer | 35 | -0.0717 | -0.1932 | 0.1215 | -0.59 | 1.59 |
| MOVER (SIS) | ITE Transformer | 30 | -0.0537 | -0.1887 | 0.135 | -0.3975 | 1.397 |
| MOVER (SIS) | ITE Transformer | 25 | -0.0302 | -0.1794 | 0.1492 | -0.2023 | 1.202 |
| MOVER (SIS) | ITE Transformer | 20 | -0.0061 | -0.1898 | 0.1837 | -0.0333 | 1.033 |
| MOVER (SIS) | ITE Transformer | 15 | 0.0331 | -0.1928 | 0.2259 | 0.1463 | 0.8537 |
| MOVER (SIS) | ITE Transformer | 10 | 0.0775 | -0.1894 | 0.2669 | 0.2903 | 0.7097 |
| MOVER (SIS) | ITE Transformer | 5 | 0.153 | -0.1942 | 0.3472 | 0.4407 | 0.5593 |
| MOVER (EPIC) test | LSTM | 55 | -0.0134 | -0.0225 | 0.0091 | -1.475 | 2.475 |
| MOVER (EPIC) test | LSTM | 50 | -0.0262 | -0.0492 | 0.0231 | -1.133 | 2.133 |
| MOVER (EPIC) test | LSTM | 45 | -0.0224 | -0.0871 | 0.0647 | -0.3459 | 1.346 |
| MOVER (EPIC) test | LSTM | 40 | -0.0483 | -0.1132 | 0.0649 | -0.7436 | 1.744 |
| MOVER (EPIC) test | LSTM | 35 | -0.0701 | -0.143 | 0.0729 | -0.9614 | 1.961 |
| MOVER (EPIC) test | LSTM | 30 | -0.0587 | -0.1891 | 0.1304 | -0.4499 | 1.45 |
| MOVER (EPIC) test | LSTM | 25 | -0.0612 | -0.2134 | 0.1522 | -0.4023 | 1.402 |
| MOVER (EPIC) test | LSTM | 20 | -0.0413 | -0.2228 | 0.1815 | -0.2277 | 1.228 |
| MOVER (EPIC) test | LSTM | 15 | -0.0315 | -0.2226 | 0.1911 | -0.1649 | 1.165 |
| MOVER (EPIC) test | LSTM | 10 | 0.0431 | -0.2246 | 0.2677 | 0.1611 | 0.8389 |
| MOVER (EPIC) test | LSTM | 5 | 0.0877 | -0.2228 | 0.3105 | 0.2825 | 0.7175 |
| VitalDB | LSTM | 55 | -0.0102 | -0.0065 | -0.0037 | 2.764 | -1.764 |
| VitalDB | LSTM | 50 | -0.0293 | -0.0317 | 0.0024 | -12.05 | 13.05 |
| VitalDB | LSTM | 45 | -0.0454 | -0.0486 | 0.0032 | -14.02 | 15.02 |
| VitalDB | LSTM | 40 | -0.0372 | -0.0674 | 0.0302 | -1.23 | 2.23 |
| VitalDB | LSTM | 35 | -0.0389 | -0.0796 | 0.0407 | -0.9565 | 1.956 |
| VitalDB | LSTM | 30 | -0.0411 | -0.0813 | 0.0402 | -1.022 | 2.022 |
| VitalDB | LSTM | 25 | -0.0378 | -0.0756 | 0.0379 | -0.997 | 1.997 |
| VitalDB | LSTM | 20 | 0.001 | -0.0814 | 0.0824 | 0.0122 | 0.9878 |
| VitalDB | LSTM | 15 | 0.0359 | -0.0851 | 0.121 | 0.2967 | 0.7033 |
| VitalDB | LSTM | 10 | 0.0509 | -0.0839 | 0.1349 | 0.3776 | 0.6224 |
| VitalDB | LSTM | 5 | 0.1059 | -0.0853 | 0.1913 | 0.5539 | 0.4461 |
| MOVER (SIS) | LSTM | 55 | 0.0126 | -0.0096 | 0.0223 | 0.5676 | 0.4324 |
| MOVER (SIS) | LSTM | 50 | 0.0293 | -0.0244 | 0.0537 | 0.546 | 0.454 |
| MOVER (SIS) | LSTM | 45 | 0.0068 | -0.0476 | 0.0544 | 0.1251 | 0.8749 |
| MOVER (SIS) | LSTM | 40 | 0.007 | -0.0675 | 0.0745 | 0.0945 | 0.9055 |
| MOVER (SIS) | LSTM | 35 | 0.0141 | -0.0653 | 0.0794 | 0.1781 | 0.8219 |
| MOVER (SIS) | LSTM | 30 | 0.0294 | -0.0667 | 0.0961 | 0.3058 | 0.6942 |
| MOVER (SIS) | LSTM | 25 | 0.0507 | -0.0625 | 0.1132 | 0.4477 | 0.5523 |
| MOVER (SIS) | LSTM | 20 | 0.0757 | -0.0664 | 0.1421 | 0.5325 | 0.4675 |
| MOVER (SIS) | LSTM | 15 | 0.119 | -0.0708 | 0.1898 | 0.6271 | 0.3729 |
| MOVER (SIS) | LSTM | 10 | 0.1724 | -0.0759 | 0.2483 | 0.6943 | 0.3057 |
| MOVER (SIS) | LSTM | 5 | 0.2445 | -0.0712 | 0.3157 | 0.7746 | 0.2254 |
| MOVER (EPIC) test | XGBoost | 55 | -0.0241 | -0.0129 | -0.0112 | 2.152 | -1.152 |
| MOVER (EPIC) test | XGBoost | 50 | -0.0247 | -0.0238 | -0.0009 | 28.91 | -27.91 |
| MOVER (EPIC) test | XGBoost | 45 | 0.0038 | -0.0293 | 0.0331 | 0.1135 | 0.8865 |
| MOVER (EPIC) test | XGBoost | 40 | -0.0157 | -0.0266 | 0.0109 | -1.446 | 2.446 |
| MOVER (EPIC) test | XGBoost | 35 | -0.0099 | -0.045 | 0.0352 | -0.2811 | 1.281 |
| MOVER (EPIC) test | XGBoost | 30 | 0.0124 | -0.0553 | 0.0677 | 0.1832 | 0.8168 |
| MOVER (EPIC) test | XGBoost | 25 | -0.0042 | -0.0668 | 0.0626 | -0.0666 | 1.067 |
| MOVER (EPIC) test | XGBoost | 20 | 0.0302 | -0.0777 | 0.1079 | 0.2795 | 0.7205 |
| MOVER (EPIC) test | XGBoost | 15 | 0.0331 | -0.0871 | 0.1202 | 0.2752 | 0.7248 |
| MOVER (EPIC) test | XGBoost | 10 | 0.1012 | -0.0949 | 0.1961 | 0.5161 | 0.4839 |
| MOVER (EPIC) test | XGBoost | 5 | 0.1305 | -0.0949 | 0.2254 | 0.5789 | 0.4211 |
| VitalDB | XGBoost | 55 | 0.0154 | 0.0046 | 0.0108 | 1.429 | -0.4286 |
| VitalDB | XGBoost | 50 | 0.0144 | -0.0114 | 0.0258 | 0.5584 | 0.4416 |
| VitalDB | XGBoost | 45 | 0.0146 | -0.0089 | 0.0235 | 0.6203 | 0.3797 |
| VitalDB | XGBoost | 40 | 0.0346 | -0.0021 | 0.0366 | 0.9428 | 0.0572 |
| VitalDB | XGBoost | 35 | 0.051 | -0.0072 | 0.0582 | 0.8761 | 0.1239 |
| VitalDB | XGBoost | 30 | 0.0482 | -0.0028 | 0.051 | 0.9452 | 0.0548 |
| VitalDB | XGBoost | 25 | 0.065 | 0.0078 | 0.0573 | 1.136 | -0.1358 |
| VitalDB | XGBoost | 20 | 0.0994 | -0.0003 | 0.0997 | 0.997 | 0.003 |
| VitalDB | XGBoost | 15 | 0.1296 | -0.0062 | 0.1357 | 0.9546 | 0.0454 |
| VitalDB | XGBoost | 10 | 0.129 | -0.0006 | 0.1297 | 0.995 | 0.005 |
| VitalDB | XGBoost | 5 | 0.1828 | -0.006 | 0.1889 | 0.968 | 0.032 |
| MOVER (SIS) | XGBoost | 55 | 0.019 | 0.0046 | 0.0144 | 1.319 | -0.3193 |
| MOVER (SIS) | XGBoost | 50 | 0.04 | 0.0071 | 0.0329 | 1.217 | -0.2169 |
| MOVER (SIS) | XGBoost | 45 | 0.0329 | 0.0097 | 0.0232 | 1.42 | -0.4201 |
| MOVER (SIS) | XGBoost | 40 | 0.0528 | -0.0071 | 0.0598 | 0.882 | 0.118 |
| MOVER (SIS) | XGBoost | 35 | 0.0671 | 0.0078 | 0.0592 | 1.132 | -0.1323 |
| MOVER (SIS) | XGBoost | 30 | 0.0888 | 0.007 | 0.0818 | 1.086 | -0.0856 |
| MOVER (SIS) | XGBoost | 25 | 0.1078 | 0.0149 | 0.0929 | 1.161 | -0.1605 |
| MOVER (SIS) | XGBoost | 20 | 0.1266 | 0.0068 | 0.1198 | 1.057 | -0.057 |
| MOVER (SIS) | XGBoost | 15 | 0.1686 | 0.0012 | 0.1674 | 1.007 | -0.0072 |
| MOVER (SIS) | XGBoost | 10 | 0.2141 | 0.0024 | 0.2117 | 1.012 | -0.0115 |
| MOVER (SIS) | XGBoost | 5 | 0.276 | 0.0066 | 0.2694 | 1.025 | -0.0246 |
| MOVER (EPIC) test | Random forest | 55 | -0.0191 | -0.0122 | -0.0069 | 2.778 | -1.778 |
| MOVER (EPIC) test | Random forest | 50 | -0.0175 | -0.0092 | -0.0083 | 2.107 | -1.107 |
| MOVER (EPIC) test | Random forest | 45 | 0.0121 | -0.0177 | 0.0298 | 0.4059 | 0.5941 |
| MOVER (EPIC) test | Random forest | 40 | -0.0084 | -0.006 | -0.0024 | 3.457 | -2.457 |
| MOVER (EPIC) test | Random forest | 35 | 0.0009 | -0.0189 | 0.0198 | 0.0471 | 0.9529 |
| MOVER (EPIC) test | Random forest | 30 | 0.017 | -0.0307 | 0.0476 | 0.3561 | 0.6439 |
| MOVER (EPIC) test | Random forest | 25 | 0.0072 | -0.0386 | 0.0458 | 0.1573 | 0.8427 |
| MOVER (EPIC) test | Random forest | 20 | 0.041 | -0.048 | 0.089 | 0.4611 | 0.5389 |
| MOVER (EPIC) test | Random forest | 15 | 0.0453 | -0.058 | 0.1033 | 0.4388 | 0.5612 |
| MOVER (EPIC) test | Random forest | 10 | 0.1046 | -0.0638 | 0.1685 | 0.621 | 0.379 |
| MOVER (EPIC) test | Random forest | 5 | 0.1332 | -0.0589 | 0.1921 | 0.6935 | 0.3065 |
| VitalDB | Random forest | 55 | 0.014 | 0.0092 | 0.0048 | 2.894 | -1.894 |
| VitalDB | Random forest | 50 | 0.0158 | -0.0048 | 0.0206 | 0.7662 | 0.2338 |
| VitalDB | Random forest | 45 | 0.0149 | -0.0001 | 0.015 | 0.9919 | 0.0081 |
| VitalDB | Random forest | 40 | 0.0279 | 0.0057 | 0.0222 | 1.257 | -0.257 |
| VitalDB | Random forest | 35 | 0.0431 | 0.0005 | 0.0427 | 1.011 | -0.011 |
| VitalDB | Random forest | 30 | 0.0465 | 0.0042 | 0.0423 | 1.1 | -0.0996 |
| VitalDB | Random forest | 25 | 0.0564 | 0.0112 | 0.0452 | 1.248 | -0.2483 |
| VitalDB | Random forest | 20 | 0.0888 | 0.0053 | 0.0835 | 1.064 | -0.0638 |
| VitalDB | Random forest | 15 | 0.1156 | 0.0001 | 0.1155 | 1.001 | -0.0012 |
| VitalDB | Random forest | 10 | 0.1174 | 0.0053 | 0.1121 | 1.047 | -0.0471 |
| VitalDB | Random forest | 5 | 0.1674 | 0.001 | 0.1664 | 1.006 | -0.0057 |
| MOVER (SIS) | Random forest | 55 | 0.0234 | 0.0122 | 0.0112 | 2.094 | -1.094 |
| MOVER (SIS) | Random forest | 50 | 0.0427 | 0.013 | 0.0297 | 1.438 | -0.4384 |
| MOVER (SIS) | Random forest | 45 | 0.0317 | 0.0157 | 0.016 | 1.978 | -0.9777 |
| MOVER (SIS) | Random forest | 40 | 0.0514 | 0.002 | 0.0495 | 1.04 | -0.04 |
| MOVER (SIS) | Random forest | 35 | 0.062 | 0.0186 | 0.0435 | 1.428 | -0.4276 |
| MOVER (SIS) | Random forest | 30 | 0.0816 | 0.0147 | 0.067 | 1.219 | -0.2189 |
| MOVER (SIS) | Random forest | 25 | 0.0962 | 0.021 | 0.0752 | 1.279 | -0.2791 |
| MOVER (SIS) | Random forest | 20 | 0.1181 | 0.0187 | 0.0994 | 1.188 | -0.1885 |
| MOVER (SIS) | Random forest | 15 | 0.1535 | 0.0107 | 0.1429 | 1.075 | -0.0746 |
| MOVER (SIS) | Random forest | 10 | 0.1953 | 0.0103 | 0.185 | 1.056 | -0.0555 |
| MOVER (SIS) | Random forest | 5 | 0.2563 | 0.016 | 0.2403 | 1.066 | -0.0664 |
| MOVER (EPIC) test | Logistic regression | 55 | -0.0209 | -0.0206 | -0.0003 | 64.13 | -63.13 |
| MOVER (EPIC) test | Logistic regression | 50 | -0.0205 | -0.0222 | 0.0017 | -12.02 | 13.02 |
| MOVER (EPIC) test | Logistic regression | 45 | -0.0009 | -0.0302 | 0.0293 | -0.0307 | 1.031 |
| MOVER (EPIC) test | Logistic regression | 40 | -0.0212 | -0.0269 | 0.0057 | -3.705 | 4.705 |
| MOVER (EPIC) test | Logistic regression | 35 | -0.0071 | -0.0329 | 0.0258 | -0.2732 | 1.273 |
| MOVER (EPIC) test | Logistic regression | 30 | 0.0112 | -0.0558 | 0.067 | 0.167 | 0.833 |
| MOVER (EPIC) test | Logistic regression | 25 | 0.0065 | -0.0542 | 0.0607 | 0.1069 | 0.8931 |
| MOVER (EPIC) test | Logistic regression | 20 | 0.0351 | -0.0501 | 0.0853 | 0.412 | 0.588 |
| MOVER (EPIC) test | Logistic regression | 15 | 0.024 | -0.0619 | 0.0858 | 0.2794 | 0.7206 |
| MOVER (EPIC) test | Logistic regression | 10 | 0.0706 | -0.0697 | 0.1403 | 0.5033 | 0.4967 |
| MOVER (EPIC) test | Logistic regression | 5 | 0.1068 | -0.0693 | 0.1761 | 0.6067 | 0.3933 |
| VitalDB | Logistic regression | 55 | 0.0134 | 0.0082 | 0.0052 | 2.59 | -1.59 |
| VitalDB | Logistic regression | 50 | 0.0186 | -0.0016 | 0.0202 | 0.9188 | 0.0812 |
| VitalDB | Logistic regression | 45 | 0.0175 | 0.0018 | 0.0157 | 1.111 | -0.1115 |
| VitalDB | Logistic regression | 40 | 0.0372 | 0.0079 | 0.0293 | 1.271 | -0.2712 |
| VitalDB | Logistic regression | 35 | 0.0434 | 0.0025 | 0.0409 | 1.06 | -0.0601 |
| VitalDB | Logistic regression | 30 | 0.042 | 0.0077 | 0.0343 | 1.225 | -0.2254 |
| VitalDB | Logistic regression | 25 | 0.0517 | 0.0125 | 0.0392 | 1.318 | -0.3183 |
| VitalDB | Logistic regression | 20 | 0.0746 | 0.0073 | 0.0673 | 1.108 | -0.1077 |
| VitalDB | Logistic regression | 15 | 0.0912 | 0.0061 | 0.0851 | 1.072 | -0.0718 |
| VitalDB | Logistic regression | 10 | 0.0901 | 0.0095 | 0.0806 | 1.118 | -0.1178 |
| VitalDB | Logistic regression | 5 | 0.131 | 0.0041 | 0.1269 | 1.032 | -0.0325 |
| MOVER (SIS) | Logistic regression | 55 | 0.0167 | 0.0087 | 0.008 | 2.085 | -1.085 |
| MOVER (SIS) | Logistic regression | 50 | 0.0353 | 0.0159 | 0.0194 | 1.819 | -0.8188 |
| MOVER (SIS) | Logistic regression | 45 | 0.0295 | 0.0141 | 0.0154 | 1.918 | -0.9181 |
| MOVER (SIS) | Logistic regression | 40 | 0.0416 | 0.0032 | 0.0384 | 1.084 | -0.0842 |
| MOVER (SIS) | Logistic regression | 35 | 0.0522 | 0.0103 | 0.042 | 1.245 | -0.2448 |
| MOVER (SIS) | Logistic regression | 30 | 0.0629 | 0.0116 | 0.0513 | 1.226 | -0.2258 |
| MOVER (SIS) | Logistic regression | 25 | 0.0814 | 0.0197 | 0.0617 | 1.32 | -0.3199 |
| MOVER (SIS) | Logistic regression | 20 | 0.0917 | 0.0171 | 0.0746 | 1.229 | -0.2291 |
| MOVER (SIS) | Logistic regression | 15 | 0.1226 | 0.0107 | 0.1119 | 1.096 | -0.0958 |
| MOVER (SIS) | Logistic regression | 10 | 0.1563 | 0.0067 | 0.1497 | 1.045 | -0.0447 |
| MOVER (SIS) | Logistic regression | 5 | 0.1952 | 0.0128 | 0.1825 | 1.07 | -0.0699 |

