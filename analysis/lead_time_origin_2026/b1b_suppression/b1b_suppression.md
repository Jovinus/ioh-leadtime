# B1b - what suppressing the warm-up window recovers

Same threshold, same alert window, same first-crossing rule; the only change is that minutes at or before `suppress` minutes of elapsed monitoring are discarded before the rule is applied. `suppress = 0` reproduces Table 2, which is what makes the rest of each column comparable to it.

A case that can no longer alert is counted as a miss, not dropped.

## Suppression, family by family

### MOVER (EPIC) test

| Model | Suppress, min | Sensitivity (95% CI) | Specificity (95% CI) | Median lead (95% CI) | PPV | NNE |
|---|---|---|---|---|---|---|
| ITE Transformer | 0 | 0.777 (0.746–0.806) | 0.406 (0.368–0.443) | 24 (21–27) | 0.625 | 1.60 |
| ITE Transformer | 3 | 0.777 (0.748–0.807) | 0.406 (0.366–0.444) | 22 (19–24) | 0.625 | 1.60 |
| ITE Transformer | 5 | 0.739 (0.706–0.770) | 0.406 (0.369–0.445) | 21 (19–24) | 0.613 | 1.63 |
| ITE Transformer | 10 | 0.659 (0.625–0.692) | 0.409 (0.371–0.446) | 21 (18–23) | 0.587 | 1.70 |
| ITE Transformer | 15 | 0.567 (0.533–0.601) | 0.416 (0.377–0.454) | 20 (17–23) | 0.553 | 1.81 |
| LSTM | 0 | 0.807 (0.779–0.834) | 0.474 (0.433–0.513) | 23 (20–25) | 0.661 | 1.51 |
| LSTM | 3 | 0.799 (0.769–0.828) | 0.479 (0.440–0.519) | 21 (18–23) | 0.661 | 1.51 |
| LSTM | 5 | 0.767 (0.736–0.796) | 0.484 (0.443–0.522) | 21 (19–23) | 0.654 | 1.53 |
| LSTM | 10 | 0.684 (0.651–0.718) | 0.516 (0.477–0.553) | 21 (18–24) | 0.643 | 1.56 |
| LSTM | 15 | 0.585 (0.551–0.621) | 0.570 (0.530–0.606) | 20 (18–23) | 0.634 | 1.58 |
| XGBoost | 0 | 0.810 (0.782–0.835) | 0.608 (0.570–0.647) | 21 (18–23) | 0.725 | 1.38 |
| XGBoost | 3 | 0.789 (0.760–0.818) | 0.620 (0.580–0.659) | 19 (17–22) | 0.725 | 1.38 |
| XGBoost | 5 | 0.758 (0.729–0.788) | 0.628 (0.589–0.665) | 19 (17–22) | 0.722 | 1.39 |
| XGBoost | 10 | 0.679 (0.646–0.714) | 0.646 (0.607–0.684) | 20 (18–23) | 0.709 | 1.41 |
| XGBoost | 15 | 0.604 (0.569–0.639) | 0.665 (0.628–0.700) | 20 (18–24) | 0.696 | 1.44 |
| Random forest | 0 | 0.828 (0.801–0.854) | 0.555 (0.515–0.597) | 22 (20–24) | 0.703 | 1.42 |
| Random forest | 3 | 0.799 (0.771–0.825) | 0.565 (0.527–0.607) | 21 (18–23) | 0.700 | 1.43 |
| Random forest | 5 | 0.768 (0.737–0.797) | 0.574 (0.537–0.612) | 21 (19–23) | 0.697 | 1.44 |
| Random forest | 10 | 0.709 (0.677–0.739) | 0.599 (0.560–0.637) | 21 (18–24) | 0.692 | 1.45 |
| Random forest | 15 | 0.644 (0.607–0.678) | 0.618 (0.582–0.656) | 21 (18–24) | 0.682 | 1.47 |
| Logistic regression | 0 | 0.837 (0.810–0.864) | 0.518 (0.477–0.557) | 23 (21–26) | 0.688 | 1.45 |
| Logistic regression | 3 | 0.805 (0.777–0.832) | 0.534 (0.494–0.573) | 22 (19–24) | 0.687 | 1.45 |
| Logistic regression | 5 | 0.780 (0.752–0.809) | 0.550 (0.510–0.588) | 21 (18–24) | 0.688 | 1.45 |
| Logistic regression | 10 | 0.683 (0.650–0.715) | 0.579 (0.540–0.620) | 22 (19–25) | 0.674 | 1.48 |
| Logistic regression | 15 | 0.613 (0.578–0.647) | 0.605 (0.567–0.643) | 22 (20–26) | 0.664 | 1.51 |


### VitalDB

| Model | Suppress, min | Sensitivity (95% CI) | Specificity (95% CI) | Median lead (95% CI) | PPV | NNE |
|---|---|---|---|---|---|---|
| ITE Transformer | 0 | 0.679 (0.651–0.707) | 0.379 (0.358–0.403) | 17 (15–19) | 0.380 | 2.63 |
| ITE Transformer | 3 | 0.679 (0.652–0.709) | 0.380 (0.357–0.402) | 15 (14–16) | 0.380 | 2.63 |
| ITE Transformer | 5 | 0.616 (0.584–0.646) | 0.380 (0.358–0.403) | 15 (13–17) | 0.357 | 2.80 |
| ITE Transformer | 10 | 0.477 (0.446–0.510) | 0.383 (0.361–0.405) | 19 (15–22) | 0.302 | 3.31 |
| ITE Transformer | 15 | 0.383 (0.353–0.413) | 0.410 (0.388–0.433) | 22 (18–25) | 0.267 | 3.75 |
| LSTM | 0 | 0.492 (0.460–0.523) | 0.812 (0.795–0.830) | 9 (8–10) | 0.595 | 1.68 |
| LSTM | 3 | 0.477 (0.445–0.505) | 0.820 (0.802–0.838) | 8 (7–10) | 0.598 | 1.67 |
| LSTM | 5 | 0.424 (0.395–0.453) | 0.824 (0.807–0.842) | 9 (7–11) | 0.575 | 1.74 |
| LSTM | 10 | 0.297 (0.269–0.325) | 0.844 (0.827–0.861) | 11 (9–15) | 0.516 | 1.94 |
| LSTM | 15 | 0.204 (0.180–0.229) | 0.884 (0.869–0.900) | 13 (9–17) | 0.496 | 2.01 |
| XGBoost | 0 | 0.694 (0.665–0.721) | 0.754 (0.735–0.774) | 13 (12–16) | 0.613 | 1.63 |
| XGBoost | 3 | 0.677 (0.647–0.706) | 0.760 (0.740–0.779) | 13 (12–16) | 0.612 | 1.63 |
| XGBoost | 5 | 0.644 (0.615–0.673) | 0.763 (0.743–0.783) | 14 (12–16) | 0.604 | 1.65 |
| XGBoost | 10 | 0.564 (0.532–0.594) | 0.780 (0.760–0.798) | 16 (14–20) | 0.590 | 1.70 |
| XGBoost | 15 | 0.502 (0.471–0.532) | 0.790 (0.771–0.809) | 18 (16–21) | 0.573 | 1.75 |
| Random forest | 0 | 0.803 (0.778–0.827) | 0.674 (0.651–0.695) | 15 (12–18) | 0.580 | 1.72 |
| Random forest | 3 | 0.792 (0.766–0.818) | 0.679 (0.657–0.701) | 15 (12–17) | 0.580 | 1.72 |
| Random forest | 5 | 0.752 (0.726–0.778) | 0.683 (0.661–0.704) | 16 (13–19) | 0.570 | 1.75 |
| Random forest | 10 | 0.651 (0.620–0.680) | 0.698 (0.676–0.718) | 19 (16–23) | 0.547 | 1.83 |
| Random forest | 15 | 0.582 (0.552–0.611) | 0.713 (0.691–0.735) | 22 (19–25) | 0.532 | 1.88 |
| Logistic regression | 0 | 0.461 (0.431–0.492) | 0.825 (0.808–0.842) | 14 (10–16) | 0.596 | 1.68 |
| Logistic regression | 3 | 0.450 (0.418–0.482) | 0.830 (0.813–0.847) | 13 (10–15) | 0.598 | 1.67 |
| Logistic regression | 5 | 0.425 (0.394–0.456) | 0.832 (0.815–0.848) | 14 (12–17) | 0.587 | 1.70 |
| Logistic regression | 10 | 0.366 (0.337–0.395) | 0.845 (0.827–0.862) | 17 (13–20) | 0.569 | 1.76 |
| Logistic regression | 15 | 0.318 (0.290–0.344) | 0.853 (0.837–0.869) | 18 (15–21) | 0.548 | 1.82 |


### MOVER (SIS)

| Model | Suppress, min | Sensitivity (95% CI) | Specificity (95% CI) | Median lead (95% CI) | PPV | NNE |
|---|---|---|---|---|---|---|
| ITE Transformer | 0 | 0.657 (0.632–0.682) | 0.467 (0.441–0.494) | 22 (20–24) | 0.585 | 1.71 |
| ITE Transformer | 3 | 0.656 (0.632–0.680) | 0.472 (0.445–0.501) | 20 (18–22) | 0.587 | 1.70 |
| ITE Transformer | 5 | 0.610 (0.585–0.635) | 0.474 (0.445–0.503) | 21 (19–23) | 0.570 | 1.75 |
| ITE Transformer | 10 | 0.515 (0.489–0.541) | 0.490 (0.461–0.519) | 21 (19–23) | 0.536 | 1.87 |
| ITE Transformer | 15 | 0.371 (0.348–0.397) | 0.649 (0.624–0.675) | 19 (18–21) | 0.548 | 1.83 |
| LSTM | 0 | 0.551 (0.526–0.577) | 0.709 (0.683–0.735) | 15 (14–18) | 0.685 | 1.46 |
| LSTM | 3 | 0.522 (0.496–0.549) | 0.722 (0.696–0.747) | 14 (12–16) | 0.682 | 1.47 |
| LSTM | 5 | 0.490 (0.464–0.517) | 0.729 (0.705–0.755) | 14 (12–17) | 0.674 | 1.48 |
| LSTM | 10 | 0.414 (0.388–0.439) | 0.760 (0.736–0.782) | 15 (13–18) | 0.663 | 1.51 |
| LSTM | 15 | 0.330 (0.305–0.354) | 0.809 (0.788–0.831) | 14 (12–17) | 0.664 | 1.51 |
| XGBoost | 0 | 0.790 (0.768–0.810) | 0.638 (0.610–0.666) | 19 (18–22) | 0.714 | 1.40 |
| XGBoost | 3 | 0.771 (0.749–0.793) | 0.644 (0.617–0.670) | 19 (17–21) | 0.712 | 1.40 |
| XGBoost | 5 | 0.740 (0.717–0.763) | 0.653 (0.625–0.680) | 19 (18–22) | 0.709 | 1.41 |
| XGBoost | 10 | 0.686 (0.661–0.710) | 0.666 (0.641–0.692) | 20 (18–22) | 0.702 | 1.43 |
| XGBoost | 15 | 0.630 (0.604–0.656) | 0.683 (0.657–0.709) | 20 (19–23) | 0.695 | 1.44 |
| Random forest | 0 | 0.849 (0.830–0.867) | 0.559 (0.532–0.586) | 22 (20–25) | 0.688 | 1.45 |
| Random forest | 3 | 0.835 (0.816–0.854) | 0.567 (0.540–0.594) | 21 (19–24) | 0.688 | 1.45 |
| Random forest | 5 | 0.799 (0.777–0.821) | 0.574 (0.546–0.602) | 22 (20–24) | 0.682 | 1.47 |
| Random forest | 10 | 0.738 (0.716–0.760) | 0.588 (0.560–0.615) | 22 (20–24) | 0.672 | 1.49 |
| Random forest | 15 | 0.676 (0.652–0.701) | 0.606 (0.578–0.634) | 23 (20–26) | 0.662 | 1.51 |
| Logistic regression | 0 | 0.790 (0.769–0.812) | 0.585 (0.559–0.611) | 21 (19–23) | 0.685 | 1.46 |
| Logistic regression | 3 | 0.775 (0.753–0.797) | 0.592 (0.564–0.619) | 20 (18–23) | 0.685 | 1.46 |
| Logistic regression | 5 | 0.744 (0.720–0.767) | 0.598 (0.571–0.625) | 21 (19–23) | 0.679 | 1.47 |
| Logistic regression | 10 | 0.684 (0.658–0.710) | 0.617 (0.590–0.645) | 22 (20–25) | 0.671 | 1.49 |
| Logistic regression | 15 | 0.632 (0.607–0.657) | 0.632 (0.605–0.658) | 22 (20–25) | 0.663 | 1.51 |


## What the lead is measuring

For each detected event case, its lead against the length of its own observed pre-onset window, capped at the 60-minute alert window. A ratio near 1 means the alert fired at the first opportunity, so the reported lead is the window length rather than a warning. `above_fraction` is the median share of a case's monitored minutes spent at or above the threshold.

| Cohort | Model | n | Median lead, min | Median observed window, min | Lead / window (95% CI) | Spearman (95% CI) | Above thr, events | Above thr, controls |
|---|---|---|---|---|---|---|---|---|
| MOVER (EPIC) test | ITE Transformer | 611 | 24 | 32 | 0.94 (0.94–0.95) | 0.71 (0.62–0.79) | 0.523 | 0.150 |
| VitalDB | ITE Transformer | 684 | 17 | 20 | 0.92 (0.91–0.93) | 0.91 (0.86–0.94) | 0.444 | 0.183 |
| MOVER (SIS) | ITE Transformer | 926 | 22 | 29 | 0.90 (0.88–0.91) | 0.80 (0.75–0.85) | 0.200 | 0.025 |
| MOVER (EPIC) test | LSTM | 634 | 23 | 35 | 0.85 (0.83–0.87) | 0.65 (0.58–0.72) | 0.267 | 0.017 |
| VitalDB | LSTM | 495 | 9 | 18 | 0.62 (0.57–0.68) | 0.76 (0.70–0.81) | 0.000 | 0.000 |
| MOVER (SIS) | LSTM | 777 | 15 | 37 | 0.72 (0.67–0.77) | 0.50 (0.44–0.56) | 0.017 | 0.000 |
| MOVER (EPIC) test | XGBoost | 637 | 21 | 47 | 0.72 (0.67–0.76) | 0.56 (0.50–0.62) | 0.117 | 0.000 |
| VitalDB | XGBoost | 699 | 13 | 52 | 0.47 (0.40–0.52) | 0.60 (0.55–0.65) | 0.067 | 0.000 |
| MOVER (SIS) | XGBoost | 1113 | 19 | 60 | 0.60 (0.56–0.63) | 0.57 (0.53–0.61) | 0.100 | 0.000 |
| MOVER (EPIC) test | Random forest | 651 | 22 | 49 | 0.71 (0.67–0.76) | 0.58 (0.52–0.64) | 0.150 | 0.000 |
| VitalDB | Random forest | 809 | 15 | 49 | 0.53 (0.50–0.58) | 0.65 (0.60–0.70) | 0.133 | 0.000 |
| MOVER (SIS) | Random forest | 1196 | 22 | 60 | 0.67 (0.62–0.70) | 0.62 (0.58–0.65) | 0.172 | 0.000 |
| MOVER (EPIC) test | Logistic regression | 658 | 23 | 45 | 0.78 (0.74–0.83) | 0.60 (0.54–0.66) | 0.139 | 0.000 |
| VitalDB | Logistic regression | 464 | 14 | 48 | 0.45 (0.39–0.51) | 0.61 (0.54–0.67) | 0.000 | 0.000 |
| MOVER (SIS) | Logistic regression | 1113 | 21 | 60 | 0.62 (0.58–0.67) | 0.60 (0.56–0.64) | 0.117 | 0.000 |


## What a reader ranking by the published number would be ranking by

The unit here is a cell, not a patient, so the P values are permutations of which operating point is paired with which reported lead, not cluster bootstraps. Cohort confounds the pooled row -- VitalDB has both the lowest prevalence and the shortest leads -- so the per-cohort rows are the claim that does not depend on pooling. `PPV lift` is PPV minus prevalence, because raw PPV is not comparable across cohorts whose prevalence runs from 0.359 to 0.560.

| Scope | Cells | Median lead, min | Specificity | Spearman lead vs specificity | Spearman lead vs PPV lift | Longer lead / lower specificity |
|---|---|---|---|---|---|---|
| All cells | 15 | 9–24 | 0.379–0.825 | -0.803 (P = 0.0008) | -0.719 (P = 0.0040) | 86 of 99 pairs |
| MOVER (EPIC) test | 5 | 21–24 | 0.406–0.608 | -0.975 (P = 0.0330) | -0.975 (P = 0.0321) | 9 of 9 pairs |
| VitalDB | 5 | 9–17 | 0.379–0.825 | -0.700 (P = 0.2301) | -0.700 (P = 0.2297) | 8 of 10 pairs |
| MOVER (SIS) | 5 | 15–22 | 0.467–0.709 | -0.975 (P = 0.0318) | -0.154 (P = 0.8376) | 9 of 9 pairs |

