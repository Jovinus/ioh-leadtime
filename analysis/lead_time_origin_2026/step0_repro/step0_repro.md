# B step 0 - reproduction gate

Alert window `0 < t_to_event <= 60`, alarm rule `score >= threshold`, thresholds read from `validation_calibration_and_thresholds.csv` and not reselected.

| check | expected | observed | tolerance | status |
|---|---|---|---|---|
| table2/transformer/sensitivity | 0.78 | 0.7774 | 0.005 | pass |
| table2/transformer/specificity | 0.41 | 0.4061 | 0.005 | pass |
| table2/transformer/ppv | 0.625 | 0.6247 | 0.0005 | pass |
| table2/transformer/nne | 1.6 | 1.601 | 0.005 | pass |
| table2/transformer/median_lead_min | 24 | 24 | 0 | pass |
| table2/xgb/sensitivity | 0.81 | 0.8104 | 0.005 | pass |
| table2/xgb/specificity | 0.61 | 0.6084 | 0.005 | pass |
| table2/xgb/ppv | 0.725 | 0.7247 | 0.0005 | pass |
| table2/xgb/nne | 1.38 | 1.38 | 0.005 | pass |
| table2/xgb/median_lead_min | 21 | 21 | 0 | pass |
| table2/rf/sensitivity | 0.83 | 0.8282 | 0.005 | pass |
| table2/rf/specificity | 0.56 | 0.555 | 0.005 | pass |
| table2/rf/ppv | 0.703 | 0.703 | 0.0005 | pass |
| table2/rf/nne | 1.42 | 1.422 | 0.005 | pass |
| table2/rf/median_lead_min | 22 | 22 | 0 | pass |
| table2/lstm/sensitivity | 0.81 | 0.8066 | 0.005 | pass |
| table2/lstm/specificity | 0.47 | 0.4741 | 0.005 | pass |
| table2/lstm/ppv | 0.661 | 0.6611 | 0.0005 | pass |
| table2/lstm/nne | 1.51 | 1.513 | 0.005 | pass |
| table2/lstm/median_lead_min | 23 | 23 | 0 | pass |
| table2/logreg/sensitivity | 0.84 | 0.8372 | 0.005 | pass |
| table2/logreg/specificity | 0.52 | 0.5178 | 0.005 | pass |
| table2/logreg/ppv | 0.688 | 0.6883 | 0.0005 | pass |
| table2/logreg/nne | 1.45 | 1.453 | 0.005 | pass |
| table2/logreg/median_lead_min | 23 | 23 | 0 | pass |
| recompute/transformer/sensitivity | 0.7774 | 0.7774 | 1e-09 | pass |
| recompute/transformer/specificity | 0.4061 | 0.4061 | 1e-09 | pass |
| recompute/transformer/median_lead_min | 24 | 24 | 0 | pass |
| recompute/lstm/sensitivity | 0.8066 | 0.8066 | 1e-09 | pass |
| recompute/lstm/specificity | 0.4741 | 0.4741 | 1e-09 | pass |
| recompute/lstm/median_lead_min | 23 | 23 | 0 | pass |
| recompute/xgb/sensitivity | 0.8104 | 0.8104 | 1e-09 | pass |
| recompute/xgb/specificity | 0.6084 | 0.6084 | 1e-09 | pass |
| recompute/xgb/median_lead_min | 21 | 21 | 0 | pass |
| recompute/rf/sensitivity | 0.8282 | 0.8282 | 1e-09 | pass |
| recompute/rf/specificity | 0.555 | 0.555 | 1e-09 | pass |
| recompute/rf/median_lead_min | 22 | 22 | 0 | pass |
| recompute/logreg/sensitivity | 0.8372 | 0.8372 | 1e-09 | pass |
| recompute/logreg/specificity | 0.5178 | 0.5178 | 1e-09 | pass |
| recompute/logreg/median_lead_min | 23 | 23 | 0 | pass |
| a6/epic_test/60-5/delta | 0.04647 | 0.04647 | 1e-06 | pass |
| a6/epic_test/60-5/directedness | 0.0252 | 0.0252 | 1e-06 | pass |
| a6/epic_test/60-5/max_up_share | 0.4879 | 0.4879 | 1e-06 | pass |
| a6/epic_test/60-10/delta | -3e-05 | -2.965e-05 | 1e-06 | pass |
| a6/epic_test/60-10/directedness | -5.2e-05 | -5.229e-05 | 1e-06 | pass |
| a6/epic_test/60-10/max_up_share | 0.51 | 0.51 | 1e-06 | pass |
| a6/vitaldb/60-5/delta | 0.01271 | 0.01271 | 1e-06 | pass |
| a6/vitaldb/60-5/directedness | 0.0208 | 0.0208 | 1e-06 | pass |
| a6/vitaldb/60-5/max_up_share | 0.4895 | 0.4895 | 1e-06 | pass |
| a6/vitaldb/60-10/delta | -1.8e-05 | -1.754e-05 | 1e-06 | pass |
| a6/vitaldb/60-10/directedness | -1.8e-05 | -1.812e-05 | 1e-06 | pass |
| a6/vitaldb/60-10/max_up_share | 0.5251 | 0.5251 | 1e-06 | pass |

