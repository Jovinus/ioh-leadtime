# B1-B4 collected results

1007 numbers. `b_results_long.csv` and `.json` are the machine-readable forms; every write-up number should come from there rather than from a REPORT.md.

## Multiplicity

Benjamini-Hochberg across the 93 formal tests in B1-B4, treated as one family and **not** pooled with the 21-trajectory, 15-orientation or A1-A5 families. Pooling would move published *q* values.

The 8 `B1b-cells` tests are adjusted separately. Their unit is a model-by-cohort cell rather than a patient, and they are permutations of which operating point is paired with which reported lead, so they are not the same kind of test as the rest of B; folding them in would resize a published family.

| analysis | quantity | family_label | cohort_label | value | p_value | q_value | significant_q05 |
|---|---|---|---|---|---|---|---|
| B1b-cells | spearman_lead_vs_specificity | all | pooled | -0.8033 | 0.0008 | 0.0064 | True |
| B1 | lead_shift_all_minus_incident | ITE Transformer | MOVER (EPIC) test | 3 | 0.001 | 0.00321 | True |
| B4 | event_side_share | Random forest | MOVER (EPIC) test | 0.6935 | 0.001 | 0.00321 | True |
| B4 | event_side_share | XGBoost | MOVER (SIS) | 1.025 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | XGBoost | MOVER (SIS) | 0.3523 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | ITE Transformer | MOVER (EPIC) test | 0.3396 | 0.001 | 0.00321 | True |
| B2 | difference_median_min | ITE Transformer | VitalDB | 11 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | ITE Transformer | VitalDB | 0.8125 | 0.001 | 0.00321 | True |
| B4 | event_side_share | LSTM | MOVER (SIS) | 0.7746 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | ITE Transformer | VitalDB | 0.3759 | 0.001 | 0.00321 | True |
| B4 | event_side_share | LSTM | MOVER (EPIC) test | 0.2825 | 0.001 | 0.00321 | True |
| B4 | event_side_share | ITE Transformer | VitalDB | 0.1177 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | XGBoost | MOVER (EPIC) test | 0.2667 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | XGBoost | MOVER (EPIC) test | 0.3048 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | XGBoost | MOVER (EPIC) test | 0.2989 | 0.001 | 0.00321 | True |
| B4 | event_side_share | ITE Transformer | MOVER (EPIC) test | 0.1598 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | XGBoost | MOVER (EPIC) test | 0.3122 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | XGBoost | MOVER (SIS) | 0.3917 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | XGBoost | VitalDB | 0.3436 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | XGBoost | MOVER (SIS) | 0.3494 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | XGBoost | MOVER (SIS) | 0.4175 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | XGBoost | VitalDB | 0.3155 | 0.001 | 0.00321 | True |
| B4 | event_side_share | Random forest | VitalDB | 1.006 | 0.001 | 0.00321 | True |
| B4 | event_side_share | Random forest | MOVER (SIS) | 1.066 | 0.001 | 0.00321 | True |
| B4 | event_side_share | XGBoost | VitalDB | 0.968 | 0.001 | 0.00321 | True |
| B4 | event_side_share | Logistic regression | VitalDB | 1.033 | 0.001 | 0.00321 | True |
| B1 | lead_shift_all_minus_incident | ITE Transformer | VitalDB | 2 | 0.001 | 0.00321 | True |
| B1 | lead_shift_all_minus_incident | ITE Transformer | MOVER (SIS) | 3 | 0.001 | 0.00321 | True |
| B4 | event_side_share | Logistic regression | MOVER (SIS) | 1.07 | 0.001 | 0.00321 | True |
| B2 | prop_score_first | XGBoost | VitalDB | 0.3753 | 0.001 | 0.00321 | True |
| B2 | difference_median_min | ITE Transformer | VitalDB | 3.5 | 0.002 | 0.0062 | True |
| B1b-cells | spearman_lead_vs_ppv_lift | all | pooled | -0.7188 | 0.004 | 0.016 | True |
| B2 | difference_median_min | XGBoost | MOVER (EPIC) test | -1 | 0.004 | 0.01162 | True |
| B2 | prop_score_first | ITE Transformer | VitalDB | 0.6774 | 0.004 | 0.01162 | True |
| B2 | difference_median_min | ITE Transformer | VitalDB | 6.5 | 0.007 | 0.01973 | True |
| B2 | prop_score_first | XGBoost | VitalDB | 0.4375 | 0.011 | 0.03009 | True |
| B2 | prop_score_first | ITE Transformer | VitalDB | 0.7105 | 0.013 | 0.03454 | True |
| B1 | lead_shift_all_minus_incident | XGBoost | MOVER (EPIC) test | 2 | 0.02 | 0.05167 | False |
| B2 | difference_median_min | XGBoost | MOVER (EPIC) test | -1 | 0.024 | 0.06032 | False |
| B1 | lead_shift_all_minus_incident | LSTM | MOVER (EPIC) test | 2 | 0.029 | 0.07097 | False |
| B1b-cells | spearman_lead_vs_specificity | all | MOVER (SIS) | -0.9747 | 0.0318 | 0.05279 | False |
| B1b-cells | spearman_lead_vs_ppv_lift | all | MOVER (EPIC) test | -0.9747 | 0.0321 | 0.05279 | False |
| B1b-cells | spearman_lead_vs_specificity | all | MOVER (EPIC) test | -0.9747 | 0.033 | 0.05279 | False |
| B2 | difference_median_min | XGBoost | MOVER (EPIC) test | -1 | 0.064 | 0.1526 | False |
| B1 | lead_shift_all_minus_incident | Random forest | VitalDB | 1.5 | 0.067 | 0.1558 | False |
| B4 | event_side_share | ITE Transformer | MOVER (SIS) | 0.4407 | 0.078 | 0.1769 | False |
| B4 | event_side_share | Logistic regression | MOVER (EPIC) test | 0.6067 | 0.118 | 0.2613 | False |
| B1 | lead_shift_all_minus_incident | Random forest | MOVER (SIS) | 2 | 0.163 | 0.3525 | False |
| B1 | lead_shift_all_minus_settled | ITE Transformer | VitalDB | -9 | 0.189 | 0.3995 | False |
| B1 | lead_shift_all_minus_settled | LSTM | MOVER (SIS) | 1 | 0.207 | 0.4278 | False |
| B4 | event_side_share | XGBoost | MOVER (EPIC) test | 0.5789 | 0.223 | 0.4508 | False |
| B1b-cells | spearman_lead_vs_ppv_lift | all | VitalDB | -0.7 | 0.2297 | 0.263 | False |
| B1b-cells | spearman_lead_vs_specificity | all | VitalDB | -0.7 | 0.2301 | 0.263 | False |
| B1 | lead_shift_all_minus_incident | LSTM | MOVER (SIS) | 1 | 0.239 | 0.4729 | False |
| B1 | lead_shift_all_minus_incident | Random forest | MOVER (EPIC) test | 1 | 0.256 | 0.496 | False |
| B2 | prop_score_first | ITE Transformer | MOVER (SIS) | 0.4715 | 0.267 | 0.5068 | False |
| B4 | event_side_share | LSTM | VitalDB | 0.5539 | 0.326 | 0.6064 | False |
| B1 | lead_shift_all_minus_settled | Random forest | VitalDB | -1 | 0.345 | 0.6291 | False |
| B1 | lead_shift_all_minus_incident | Logistic regression | MOVER (SIS) | 1 | 0.394 | 0.7046 | False |
| B1 | lead_shift_all_minus_incident | XGBoost | MOVER (SIS) | 0 | 0.424 | 0.744 | False |
| B2 | prop_score_first | ITE Transformer | MOVER (EPIC) test | 0.439 | 0.472 | 0.8129 | False |
| B1 | lead_shift_all_minus_settled | ITE Transformer | MOVER (EPIC) test | 7 | 0.502 | 0.8482 | False |
| B2 | prop_score_first | ITE Transformer | MOVER (SIS) | 0.4632 | 0.522 | 0.8482 | False |
| B2 | prop_score_first | ITE Transformer | MOVER (SIS) | 0.4677 | 0.526 | 0.8482 | False |
| B2 | prop_score_first | ITE Transformer | MOVER (EPIC) test | 0.4333 | 0.529 | 0.8482 | False |
| B1 | lead_shift_all_minus_settled | XGBoost | VitalDB | -1 | 0.606 | 0.9552 | False |
| B1 | lead_shift_all_minus_settled | Logistic regression | VitalDB | 0 | 0.63 | 0.9765 | False |
| B1 | lead_shift_all_minus_incident | Logistic regression | VitalDB | 1 | 0.711 | 1 | False |
| B1 | lead_shift_all_minus_settled | XGBoost | MOVER (EPIC) test | 1 | 0.73 | 1 | False |
| B2 | prop_score_first | ITE Transformer | MOVER (EPIC) test | 0.4706 | 0.787 | 1 | False |
| B1b-cells | spearman_lead_vs_ppv_lift | all | MOVER (SIS) | -0.1539 | 0.8376 | 0.8376 | False |
| B1 | lead_shift_all_minus_incident | Logistic regression | MOVER (EPIC) test | 1 | 0.84 | 1 | False |
| B1 | lead_shift_all_minus_incident | XGBoost | VitalDB | 0 | 0.887 | 1 | False |
| B1 | lead_shift_all_minus_settled | ITE Transformer | MOVER (SIS) | 1 | 0.911 | 1 | False |
| B2 | prop_score_first | ITE Transformer | MOVER (SIS) | 0.4944 | 0.963 | 1 | False |
| B2 | difference_median_min | XGBoost | VitalDB | 0 | 1 | 1 | False |
| B1 | lead_shift_all_minus_settled | LSTM | MOVER (EPIC) test | 0 | 1 | 1 | False |
| B1 | lead_shift_all_minus_incident | LSTM | VitalDB | 0 | 1 | 1 | False |
| B1 | lead_shift_all_minus_settled | LSTM | VitalDB | 0 | 1 | 1 | False |
| B1 | lead_shift_all_minus_settled | XGBoost | MOVER (SIS) | 0 | 1 | 1 | False |
| B1 | lead_shift_all_minus_settled | Random forest | MOVER (EPIC) test | 0 | 1 | 1 | False |
| B1 | lead_shift_all_minus_settled | Random forest | MOVER (SIS) | 0 | 1 | 1 | False |
| B1 | lead_shift_all_minus_settled | Logistic regression | MOVER (EPIC) test | 0 | 1 | 1 | False |
| B1 | lead_shift_all_minus_settled | Logistic regression | MOVER (SIS) | 0 | 1 | 1 | False |
| B2 | difference_median_min | ITE Transformer | MOVER (EPIC) test | 0 | 1 | 1 | False |
| B2 | difference_median_min | ITE Transformer | MOVER (EPIC) test | 0 | 1 | 1 | False |
| B2 | difference_median_min | ITE Transformer | MOVER (EPIC) test | 0 | 1 | 1 | False |
| B2 | difference_median_min | ITE Transformer | MOVER (EPIC) test | 0 | 1 | 1 | False |
| B2 | difference_median_min | ITE Transformer | VitalDB | 0 | 1 | 1 | False |
| B2 | difference_median_min | ITE Transformer | MOVER (SIS) | 0 | 1 | 1 | False |
| B2 | difference_median_min | ITE Transformer | MOVER (SIS) | 0 | 1 | 1 | False |
| B2 | difference_median_min | ITE Transformer | MOVER (SIS) | 0 | 1 | 1 | False |
| B2 | difference_median_min | XGBoost | MOVER (EPIC) test | 0 | 1 | 1 | False |
| B2 | difference_median_min | XGBoost | VitalDB | 0 | 1 | 1 | False |
| B2 | difference_median_min | XGBoost | MOVER (SIS) | 0 | 1 | 1 | False |
| B2 | difference_median_min | XGBoost | VitalDB | 0 | 1 | 1 | False |
| B2 | difference_median_min | XGBoost | MOVER (SIS) | 0 | 1 | 1 | False |
| B2 | difference_median_min | XGBoost | VitalDB | 0 | 1 | 1 | False |
| B2 | difference_median_min | XGBoost | MOVER (SIS) | 0 | 1 | 1 | False |
| B2 | difference_median_min | XGBoost | MOVER (SIS) | 0 | 1 | 1 | False |
| B2 | difference_median_min | ITE Transformer | MOVER (SIS) | 0 | 1 | 1 | False |


## Candidate destinations

| analysis | destination | n_numbers |
|---|---|---|
| A7-figure | main text candidate | 9 |
| B1 | main text candidate | 135 |
| B1 | supplement | 15 |
| B1b | main text candidate | 180 |
| B1b | supplement | 255 |
| B1b-cells | main text candidate | 4 |
| B1b-cells | supplement | 4 |
| B2 | main text candidate | 36 |
| B2 | supplement | 108 |
| B3 | main text candidate | 66 |
| B3 | supplement | 120 |
| B4 | main text candidate | 60 |
| B4 | supplement | 15 |


## Outstanding seed inconsistency

Three resampling bases coexist. A previously published analysis states 20260706 as its default and records 20260729 for the truncated-window orientation family, which is the base it uses throughout; its main-text methods state 20260706 alone. B1-B4 use 20260706 with offsets 100,000-130,000. This is reported, not harmonised: rerunning the published families on one base would move *q* values that are already published.
