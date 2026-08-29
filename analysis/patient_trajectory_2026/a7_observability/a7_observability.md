# A7 - observable run-up, and whether its length is informative

## 1. How long the run-up actually is

| Cohort | Group | n | Observable min, median (IQR) | >=20 min | >=40 min | >=60 min |
|---|---|---|---|---|---|---|
| MOVER (EPIC) test | event | 786 | 43 (19-113) | 74% | 54% | 40% |
| MOVER (EPIC) test | control | 618 | 72 (48-124) | 100% | 83% | 64% |
| VitalDB | event | 1007 | 44 (14-106) | 66% | 53% | 43% |
| VitalDB | control | 1797 | 65 (42-103) | 100% | 80% | 55% |
| MOVER (SIS) | event | 1409 | 52 (20-120) | 76% | 57% | 47% |
| MOVER (SIS) | control | 1232 | 66 (44-109) | 100% | 80% | 57% |


## 2. AUROC(t) with a varying denominator, against the common-start subsets

The `all` rows are the paper's convention: every case that has a minute in the bin. The `reaches_L` rows keep only cases whose observation reaches bin L, which fixes the denominator across the bins at or inside L. N(t) is printed beside AUROC(t) so the widening interval is attributable.

### MOVER (EPIC) test

| Sample | Bin, min | N cases | N event cases | AUROC (95% CI) |
|---|---|---|---|---|
| all | 60 | 708 | 313 | 0.501 (0.460-0.539) |
| all | 55 | 759 | 337 | 0.506 (0.467-0.544) |
| all | 50 | 826 | 364 | 0.508 (0.470-0.545) |
| all | 45 | 887 | 390 | 0.527 (0.487-0.565) |
| all | 40 | 946 | 425 | 0.542 (0.504-0.578) |
| all | 35 | 1036 | 463 | 0.560 (0.527-0.594) |
| all | 30 | 1117 | 499 | 0.590 (0.559-0.621) |
| all | 25 | 1160 | 542 | 0.634 (0.604-0.665) |
| all | 20 | 1220 | 602 | 0.683 (0.653-0.711) |
| all | 15 | 1282 | 664 | 0.731 (0.704-0.757) |
| all | 10 | 1355 | 737 | 0.800 (0.777-0.822) |
| all | 5 | 1404 | 786 | 0.862 (0.844-0.879) |
| all | 0 | 1404 | 786 | 0.966 (0.958-0.974) |
| reaches_20 | 20 | 1220 | 602 | 0.683 (0.653-0.711) |
| reaches_20 | 15 | 1220 | 602 | 0.715 (0.687-0.741) |
| reaches_20 | 10 | 1220 | 602 | 0.764 (0.736-0.787) |
| reaches_20 | 5 | 1220 | 602 | 0.821 (0.798-0.842) |
| reaches_20 | 0 | 1220 | 602 | 0.956 (0.946-0.966) |
| reaches_30 | 30 | 1117 | 499 | 0.590 (0.559-0.621) |
| reaches_30 | 25 | 1117 | 499 | 0.616 (0.584-0.648) |
| reaches_30 | 20 | 1117 | 499 | 0.642 (0.610-0.673) |
| reaches_30 | 15 | 1117 | 499 | 0.661 (0.629-0.692) |
| reaches_30 | 10 | 1117 | 499 | 0.716 (0.686-0.743) |
| reaches_30 | 5 | 1117 | 499 | 0.785 (0.759-0.808) |
| reaches_30 | 0 | 1117 | 499 | 0.949 (0.937-0.960) |
| reaches_40 | 40 | 946 | 425 | 0.542 (0.504-0.578) |
| reaches_40 | 35 | 946 | 425 | 0.568 (0.532-0.604) |
| reaches_40 | 30 | 946 | 425 | 0.617 (0.582-0.652) |
| reaches_40 | 25 | 946 | 425 | 0.655 (0.620-0.688) |
| reaches_40 | 20 | 946 | 425 | 0.696 (0.665-0.728) |
| reaches_40 | 15 | 946 | 425 | 0.713 (0.681-0.745) |
| reaches_40 | 10 | 946 | 425 | 0.744 (0.713-0.775) |
| reaches_40 | 5 | 946 | 425 | 0.797 (0.770-0.822) |
| reaches_40 | 0 | 946 | 425 | 0.951 (0.937-0.963) |
| reaches_60 | 60 | 708 | 313 | 0.501 (0.460-0.539) |
| reaches_60 | 55 | 708 | 313 | 0.503 (0.463-0.541) |
| reaches_60 | 50 | 708 | 313 | 0.514 (0.473-0.556) |
| reaches_60 | 45 | 708 | 313 | 0.560 (0.519-0.603) |
| reaches_60 | 40 | 708 | 313 | 0.564 (0.520-0.606) |
| reaches_60 | 35 | 708 | 313 | 0.598 (0.558-0.639) |
| reaches_60 | 30 | 708 | 313 | 0.656 (0.617-0.692) |
| reaches_60 | 25 | 708 | 313 | 0.675 (0.637-0.713) |
| reaches_60 | 20 | 708 | 313 | 0.707 (0.668-0.743) |
| reaches_60 | 15 | 708 | 313 | 0.721 (0.685-0.756) |
| reaches_60 | 10 | 708 | 313 | 0.767 (0.730-0.801) |
| reaches_60 | 5 | 708 | 313 | 0.816 (0.787-0.844) |
| reaches_60 | 0 | 708 | 313 | 0.947 (0.930-0.960) |


### VitalDB

| Sample | Bin, min | N cases | N event cases | AUROC (95% CI) |
|---|---|---|---|---|
| all | 60 | 1433 | 433 | 0.540 (0.510-0.571) |
| all | 55 | 1545 | 458 | 0.533 (0.503-0.562) |
| all | 50 | 1661 | 476 | 0.538 (0.509-0.567) |
| all | 45 | 1819 | 508 | 0.530 (0.500-0.556) |
| all | 40 | 1997 | 538 | 0.534 (0.506-0.559) |
| all | 35 | 2187 | 560 | 0.536 (0.510-0.560) |
| all | 30 | 2386 | 589 | 0.526 (0.503-0.551) |
| all | 25 | 2420 | 623 | 0.566 (0.542-0.591) |
| all | 20 | 2483 | 686 | 0.632 (0.609-0.656) |
| all | 15 | 2553 | 756 | 0.717 (0.697-0.739) |
| all | 10 | 2679 | 882 | 0.809 (0.792-0.828) |
| all | 5 | 2804 | 1007 | 0.894 (0.880-0.907) |
| all | 0 | 2804 | 1007 | 0.986 (0.982-0.989) |
| reaches_20 | 20 | 2483 | 686 | 0.632 (0.609-0.656) |
| reaches_20 | 15 | 2483 | 686 | 0.700 (0.678-0.723) |
| reaches_20 | 10 | 2483 | 686 | 0.763 (0.742-0.785) |
| reaches_20 | 5 | 2483 | 686 | 0.845 (0.827-0.863) |
| reaches_20 | 0 | 2483 | 686 | 0.979 (0.974-0.984) |
| reaches_30 | 30 | 2386 | 589 | 0.526 (0.503-0.551) |
| reaches_30 | 25 | 2386 | 589 | 0.553 (0.530-0.578) |
| reaches_30 | 20 | 2386 | 589 | 0.595 (0.572-0.619) |
| reaches_30 | 15 | 2386 | 589 | 0.654 (0.631-0.678) |
| reaches_30 | 10 | 2386 | 589 | 0.725 (0.702-0.747) |
| reaches_30 | 5 | 2386 | 589 | 0.821 (0.801-0.841) |
| reaches_30 | 0 | 2386 | 589 | 0.977 (0.971-0.982) |
| reaches_40 | 40 | 1997 | 538 | 0.534 (0.506-0.559) |
| reaches_40 | 35 | 1997 | 538 | 0.565 (0.538-0.590) |
| reaches_40 | 30 | 1997 | 538 | 0.591 (0.565-0.617) |
| reaches_40 | 25 | 1997 | 538 | 0.630 (0.606-0.655) |
| reaches_40 | 20 | 1997 | 538 | 0.689 (0.666-0.713) |
| reaches_40 | 15 | 1997 | 538 | 0.750 (0.726-0.773) |
| reaches_40 | 10 | 1997 | 538 | 0.762 (0.738-0.786) |
| reaches_40 | 5 | 1997 | 538 | 0.825 (0.803-0.845) |
| reaches_40 | 0 | 1997 | 538 | 0.976 (0.970-0.982) |
| reaches_60 | 60 | 1433 | 433 | 0.540 (0.510-0.571) |
| reaches_60 | 55 | 1433 | 433 | 0.550 (0.520-0.580) |
| reaches_60 | 50 | 1433 | 433 | 0.582 (0.552-0.613) |
| reaches_60 | 45 | 1433 | 433 | 0.603 (0.572-0.632) |
| reaches_60 | 40 | 1433 | 433 | 0.652 (0.624-0.683) |
| reaches_60 | 35 | 1433 | 433 | 0.707 (0.679-0.737) |
| reaches_60 | 30 | 1433 | 433 | 0.718 (0.689-0.748) |
| reaches_60 | 25 | 1433 | 433 | 0.724 (0.696-0.750) |
| reaches_60 | 20 | 1433 | 433 | 0.738 (0.713-0.766) |
| reaches_60 | 15 | 1433 | 433 | 0.761 (0.734-0.787) |
| reaches_60 | 10 | 1433 | 433 | 0.763 (0.735-0.790) |
| reaches_60 | 5 | 1433 | 433 | 0.821 (0.797-0.845) |
| reaches_60 | 0 | 1433 | 433 | 0.976 (0.969-0.983) |


### MOVER (SIS)

| Sample | Bin, min | N cases | N event cases | AUROC (95% CI) |
|---|---|---|---|---|
| all | 60 | 1374 | 670 | 0.534 (0.503-0.562) |
| all | 55 | 1473 | 701 | 0.530 (0.500-0.558) |
| all | 50 | 1590 | 732 | 0.534 (0.504-0.561) |
| all | 45 | 1696 | 768 | 0.527 (0.499-0.553) |
| all | 40 | 1821 | 810 | 0.540 (0.514-0.564) |
| all | 35 | 2001 | 883 | 0.553 (0.528-0.577) |
| all | 30 | 2173 | 941 | 0.568 (0.544-0.591) |
| all | 25 | 2241 | 1009 | 0.605 (0.581-0.628) |
| all | 20 | 2315 | 1083 | 0.668 (0.646-0.687) |
| all | 15 | 2419 | 1187 | 0.744 (0.724-0.761) |
| all | 10 | 2528 | 1296 | 0.818 (0.802-0.834) |
| all | 5 | 2641 | 1409 | 0.878 (0.865-0.890) |
| all | 0 | 2641 | 1409 | 0.973 (0.968-0.977) |
| reaches_20 | 20 | 2315 | 1083 | 0.668 (0.646-0.687) |
| reaches_20 | 15 | 2315 | 1083 | 0.729 (0.709-0.748) |
| reaches_20 | 10 | 2315 | 1083 | 0.790 (0.771-0.808) |
| reaches_20 | 5 | 2315 | 1083 | 0.845 (0.829-0.860) |
| reaches_20 | 0 | 2315 | 1083 | 0.965 (0.958-0.971) |
| reaches_30 | 30 | 2173 | 941 | 0.568 (0.544-0.591) |
| reaches_30 | 25 | 2173 | 941 | 0.591 (0.566-0.615) |
| reaches_30 | 20 | 2173 | 941 | 0.636 (0.612-0.657) |
| reaches_30 | 15 | 2173 | 941 | 0.694 (0.671-0.714) |
| reaches_30 | 10 | 2173 | 941 | 0.762 (0.741-0.781) |
| reaches_30 | 5 | 2173 | 941 | 0.831 (0.814-0.847) |
| reaches_30 | 0 | 2173 | 941 | 0.964 (0.958-0.971) |
| reaches_40 | 40 | 1821 | 810 | 0.540 (0.514-0.564) |
| reaches_40 | 35 | 1821 | 810 | 0.565 (0.539-0.589) |
| reaches_40 | 30 | 1821 | 810 | 0.606 (0.581-0.630) |
| reaches_40 | 25 | 1821 | 810 | 0.640 (0.615-0.664) |
| reaches_40 | 20 | 1821 | 810 | 0.700 (0.675-0.723) |
| reaches_40 | 15 | 1821 | 810 | 0.744 (0.722-0.766) |
| reaches_40 | 10 | 1821 | 810 | 0.782 (0.761-0.803) |
| reaches_40 | 5 | 1821 | 810 | 0.837 (0.818-0.855) |
| reaches_40 | 0 | 1821 | 810 | 0.965 (0.958-0.972) |
| reaches_60 | 60 | 1374 | 670 | 0.534 (0.503-0.562) |
| reaches_60 | 55 | 1374 | 670 | 0.546 (0.515-0.576) |
| reaches_60 | 50 | 1374 | 670 | 0.579 (0.548-0.608) |
| reaches_60 | 45 | 1374 | 670 | 0.606 (0.576-0.634) |
| reaches_60 | 40 | 1374 | 670 | 0.646 (0.618-0.672) |
| reaches_60 | 35 | 1374 | 670 | 0.663 (0.636-0.689) |
| reaches_60 | 30 | 1374 | 670 | 0.677 (0.651-0.704) |
| reaches_60 | 25 | 1374 | 670 | 0.680 (0.652-0.707) |
| reaches_60 | 20 | 1374 | 670 | 0.713 (0.688-0.739) |
| reaches_60 | 15 | 1374 | 670 | 0.744 (0.719-0.769) |
| reaches_60 | 10 | 1374 | 670 | 0.786 (0.762-0.809) |
| reaches_60 | 5 | 1374 | 670 | 0.840 (0.820-0.860) |
| reaches_60 | 0 | 1374 | 670 | 0.965 (0.956-0.974) |


## 3. Are short and long run-ups the same cases?

Short is under 40 minutes of observable run-up, long is at or above it. |SMD| above 0.1 is flagged. For an event case the run-up *is* the time to onset, so a short run-up means an early-onset event; this table says whether those events are otherwise different.

| cohort_label | variable | n_long | n_short | long | short | smd |
|---|---|---|---|---|---|---|
| MOVER (EPIC) test | surgery_min, mean | 421 | 365 | 410.1 | 335 | 0.394 |
| MOVER (EPIC) test | episode_nadir_map, mean | 421 | 365 | 55.19 | 54.37 | 0.114 |
| MOVER (EPIC) test | asa = 2.0, proportion | 421 | 365 | 0.055 | 0.082 | -0.109 |
| MOVER (EPIC) test | asa = 4.0, proportion | 421 | 365 | 0.306 | 0.247 | 0.134 |
| MOVER (EPIC) test | ane_type = General, proportion | 421 | 365 | 0.936 | 0.967 | -0.145 |
| MOVER (EPIC) test | procedure_group = orthopedic, proportion | 421 | 365 | 0.114 | 0.162 | -0.138 |
| MOVER (EPIC) test | procedure_group = vascular_cardiac, proportion | 421 | 365 | 0.183 | 0.09 | 0.269 |
| VitalDB | surgery_min, mean | 530 | 477 | 242 | 182.8 | 0.515 |
| VitalDB | episode_nadir_map, mean | 530 | 477 | 58.32 | 57.77 | 0.115 |
| VitalDB | episode_duration_min, mean | 530 | 477 | 5.392 | 6.155 | -0.175 |
| VitalDB | asa = 1.0, proportion | 530 | 477 | 0.198 | 0.126 | 0.196 |
| VitalDB | asa = 2.0, proportion | 530 | 477 | 0.598 | 0.648 | -0.103 |
| VitalDB | procedure_group = abdominal, proportion | 530 | 477 | 0.657 | 0.528 | 0.261 |
| VitalDB | procedure_group = gyn_uro, proportion | 530 | 477 | 0.07 | 0.036 | 0.153 |
| VitalDB | procedure_group = other, proportion | 530 | 477 | 0.117 | 0.157 | -0.117 |
| VitalDB | procedure_group = thoracic, proportion | 530 | 477 | 0.134 | 0.268 | -0.335 |
| MOVER (SIS) | surgery_min, mean | 797 | 612 | 315 | 244.7 | 0.428 |
| MOVER (SIS) | episode_nadir_map, mean | 797 | 612 | 56.42 | 55.18 | 0.177 |
| MOVER (SIS) | episode_duration_min, mean | 797 | 612 | 5.794 | 6.444 | -0.116 |
| MOVER (SIS) | procedure_group = thoracic, proportion | 797 | 612 | 0.152 | 0.114 | 0.11 |


Unflagged variables are in `a7_balance_short_vs_long.csv`.

## 4. A model for the long run-up

Logistic regression for P(run-up >= 40 min) among event cases, fitted twice: on patient and event characteristics alone, and again adding operation length. Significant terms in the first model mean the long subset is a different set of patients, not only a set of longer operations.

| cohort_label | model | n | n_long | term | odds_ratio | or_ci_lo | or_ci_hi | p_value | pseudo_r2 |
|---|---|---|---|---|---|---|---|---|---|
| MOVER (EPIC) test | patient and event characteristics | 663 | 360 | procedure_group_vascular_cardiac | 2.237 | 1.219 | 4.105 | 0.0093 | 0.0293 |
| MOVER (EPIC) test | plus operation length | 663 | 360 | surgery_min | 1.002 | 1.001 | 1.003 | 0 | 0.0551 |
| VitalDB | patient and event characteristics | 980 | 516 | episode_duration_min | 0.9571 | 0.9269 | 0.9884 | 0.0075 | 0.0461 |
| VitalDB | patient and event characteristics | 980 | 516 | asa_2.0 | 0.6683 | 0.4546 | 0.9823 | 0.0403 | 0.0461 |
| VitalDB | patient and event characteristics | 980 | 516 | procedure_group_other | 0.5535 | 0.375 | 0.8168 | 0.0029 | 0.0461 |
| VitalDB | patient and event characteristics | 980 | 516 | procedure_group_thoracic | 0.3678 | 0.261 | 0.5183 | 0 | 0.0461 |
| VitalDB | plus operation length | 980 | 516 | episode_nadir_map | 1.03 | 1.001 | 1.061 | 0.0454 | 0.0942 |
| VitalDB | plus operation length | 980 | 516 | episode_duration_min | 0.9504 | 0.9192 | 0.9827 | 0.0029 | 0.0942 |
| VitalDB | plus operation length | 980 | 516 | surgery_min | 1.005 | 1.004 | 1.007 | 0 | 0.0942 |
| VitalDB | plus operation length | 980 | 516 | asa_2.0 | 0.6357 | 0.427 | 0.9465 | 0.0257 | 0.0942 |
| VitalDB | plus operation length | 980 | 516 | asa_3.0 | 0.6231 | 0.3887 | 0.9991 | 0.0496 | 0.0942 |
| VitalDB | plus operation length | 980 | 516 | asa_4.0 | 0.1776 | 0.0447 | 0.7065 | 0.0142 | 0.0942 |
| VitalDB | plus operation length | 980 | 516 | procedure_group_gyn_uro | 2.114 | 1.098 | 4.07 | 0.0251 | 0.0942 |
| VitalDB | plus operation length | 980 | 516 | procedure_group_thoracic | 0.4503 | 0.3145 | 0.6446 | 0 | 0.0942 |
| MOVER (SIS) | patient and event characteristics | 1392 | 788 | age | 0.9935 | 0.9872 | 0.9998 | 0.0425 | 0.0164 |
| MOVER (SIS) | patient and event characteristics | 1392 | 788 | episode_nadir_map | 1.026 | 1.01 | 1.042 | 0.0013 | 0.0164 |
| MOVER (SIS) | patient and event characteristics | 1392 | 788 | procedure_group_thoracic | 1.424 | 1.002 | 2.024 | 0.0487 | 0.0164 |
| MOVER (SIS) | plus operation length | 1392 | 788 | age | 0.9924 | 0.9861 | 0.9989 | 0.0214 | 0.049 |
| MOVER (SIS) | plus operation length | 1392 | 788 | episode_nadir_map | 1.027 | 1.011 | 1.043 | 0.0012 | 0.049 |
| MOVER (SIS) | plus operation length | 1392 | 788 | surgery_min | 1.003 | 1.002 | 1.004 | 0 | 0.049 |


Every term, significant or not, is in `a7_logistic_long_runup.csv`.

