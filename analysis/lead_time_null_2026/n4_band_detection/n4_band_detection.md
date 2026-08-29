# N4 - detection rate by band of observed pre-onset window

Bands are quantiles of the observed window over **all** event cases, so the detection rate has every event case of that window length in its denominator. N3's bands are cut on the detected subset instead, which is correct for a statistic computed on detected cases and wrong for this one, so the median leads below are close to N3's without being identical.

## Detection rate, lowest to highest band

| Model | Cohort | Event cases | Bands | Overall | Lowest band | Highest band | Gradient (95% CI) |
|---|---|---|---|---|---|---|---|
| ITE Transformer | MOVER (EPIC) test | 786 | 4 | 0.777 | 1.000 | 0.444 | -0.556 (-0.612–-0.502) |
| ITE Transformer | VitalDB | 1007 | 3 | 0.679 | 1.000 | 0.462 | -0.538 (-0.579–-0.500) |
| ITE Transformer | MOVER (SIS) | 1409 | 3 | 0.657 | 0.986 | 0.432 | -0.554 (-0.590–-0.517) |
| LSTM | MOVER (EPIC) test | 786 | 4 | 0.807 | 0.931 | 0.601 | -0.330 (-0.395–-0.264) |
| LSTM | VitalDB | 1007 | 3 | 0.492 | 0.814 | 0.303 | -0.510 (-0.577–-0.447) |
| LSTM | MOVER (SIS) | 1409 | 3 | 0.551 | 0.683 | 0.470 | -0.213 (-0.276–-0.148) |
| XGBoost | MOVER (EPIC) test | 786 | 4 | 0.810 | 0.692 | 0.847 | +0.155 (+0.075–+0.235) |
| XGBoost | VitalDB | 1007 | 3 | 0.694 | 0.539 | 0.762 | +0.222 (+0.149–+0.300) |
| XGBoost | MOVER (SIS) | 1409 | 3 | 0.790 | 0.624 | 0.843 | +0.220 (+0.160–+0.277) |
| Random forest | MOVER (EPIC) test | 786 | 4 | 0.828 | 0.673 | 0.895 | +0.222 (+0.141–+0.304) |
| Random forest | VitalDB | 1007 | 3 | 0.803 | 0.686 | 0.853 | +0.167 (+0.099–+0.236) |
| Random forest | MOVER (SIS) | 1409 | 3 | 0.849 | 0.700 | 0.896 | +0.196 (+0.139–+0.253) |
| Logistic regression | MOVER (EPIC) test | 786 | 4 | 0.837 | 0.748 | 0.853 | +0.105 (+0.029–+0.181) |
| Logistic regression | VitalDB | 1007 | 3 | 0.461 | 0.348 | 0.497 | +0.149 (+0.071–+0.222) |
| Logistic regression | MOVER (SIS) | 1409 | 3 | 0.790 | 0.620 | 0.853 | +0.233 (+0.171–+0.291) |


## Every band

| Model | Cohort | Band | Event cases | Detected | Window median, min | Detection rate (95% CI) | Median lead, min (95% CI) |
|---|---|---|---|---|---|---|---|
| ITE Transformer | MOVER (EPIC) test | 1 | 159 | 159 | 11 | 1.000 (1.000–1.000) | 9 (8–10) |
| ITE Transformer | MOVER (EPIC) test | 2 | 164 | 164 | 23 | 1.000 (1.000–1.000) | 22 (20–24) |
| ITE Transformer | MOVER (EPIC) test | 3 | 150 | 149 | 44 | 0.993 (0.979–1.000) | 42 (40–43) |
| ITE Transformer | MOVER (EPIC) test | 4 | 313 | 139 | 60 | 0.444 (0.388–0.498) | 54 (33–58) |
| ITE Transformer | VitalDB | 1 | 204 | 204 | 8 | 1.000 (1.000–1.000) | 6 (6–7) |
| ITE Transformer | VitalDB | 2 | 203 | 203 | 18 | 1.000 (1.000–1.000) | 16 (14–17) |
| ITE Transformer | VitalDB | 3 | 600 | 277 | 60 | 0.462 (0.421–0.500) | 44 (42–46) |
| ITE Transformer | MOVER (SIS) | 1 | 287 | 283 | 10 | 0.986 (0.971–0.997) | 7 (7–8) |
| ITE Transformer | MOVER (SIS) | 2 | 285 | 281 | 25 | 0.986 (0.971–0.997) | 23 (22–24) |
| ITE Transformer | MOVER (SIS) | 3 | 837 | 362 | 60 | 0.432 (0.398–0.465) | 46 (43–49) |
| LSTM | MOVER (EPIC) test | 1 | 159 | 148 | 11 | 0.931 (0.889–0.970) | 7 (6–8) |
| LSTM | MOVER (EPIC) test | 2 | 164 | 157 | 23 | 0.957 (0.925–0.987) | 20 (18–21) |
| LSTM | MOVER (EPIC) test | 3 | 150 | 141 | 44 | 0.940 (0.897–0.974) | 39 (37–41) |
| LSTM | MOVER (EPIC) test | 4 | 313 | 188 | 60 | 0.601 (0.545–0.652) | 40 (34–46) |
| LSTM | VitalDB | 1 | 204 | 166 | 8 | 0.814 (0.760–0.868) | 3 (3–4) |
| LSTM | VitalDB | 2 | 203 | 147 | 18 | 0.724 (0.660–0.783) | 10 (9–12) |
| LSTM | VitalDB | 3 | 600 | 182 | 60 | 0.303 (0.268–0.340) | 32 (28–34) |
| LSTM | MOVER (SIS) | 1 | 287 | 196 | 10 | 0.683 (0.628–0.738) | 6 (5–6) |
| LSTM | MOVER (SIS) | 2 | 285 | 188 | 25 | 0.660 (0.604–0.714) | 18 (16–21) |
| LSTM | MOVER (SIS) | 3 | 837 | 393 | 60 | 0.470 (0.437–0.504) | 33 (29–36) |
| XGBoost | MOVER (EPIC) test | 1 | 159 | 110 | 11 | 0.692 (0.619–0.760) | 7 (5–9) |
| XGBoost | MOVER (EPIC) test | 2 | 164 | 132 | 23 | 0.805 (0.743–0.865) | 17 (16–19) |
| XGBoost | MOVER (EPIC) test | 3 | 150 | 130 | 44 | 0.867 (0.806–0.918) | 32 (28–36) |
| XGBoost | MOVER (EPIC) test | 4 | 313 | 265 | 60 | 0.847 (0.806–0.885) | 40 (34–44) |
| XGBoost | VitalDB | 1 | 204 | 110 | 8 | 0.539 (0.471–0.606) | 3 (2–3) |
| XGBoost | VitalDB | 2 | 203 | 132 | 18 | 0.650 (0.587–0.718) | 7 (5–9) |
| XGBoost | VitalDB | 3 | 600 | 457 | 60 | 0.762 (0.728–0.794) | 26 (23–30) |
| XGBoost | MOVER (SIS) | 1 | 287 | 179 | 10 | 0.624 (0.570–0.678) | 5 (4–5) |
| XGBoost | MOVER (SIS) | 2 | 285 | 228 | 25 | 0.800 (0.753–0.844) | 14 (13–16) |
| XGBoost | MOVER (SIS) | 3 | 837 | 706 | 60 | 0.843 (0.819–0.866) | 35 (33–37) |
| Random forest | MOVER (EPIC) test | 1 | 159 | 107 | 11 | 0.673 (0.596–0.746) | 6 (5–8) |
| Random forest | MOVER (EPIC) test | 2 | 164 | 135 | 23 | 0.823 (0.762–0.880) | 17 (15–18) |
| Random forest | MOVER (EPIC) test | 3 | 150 | 129 | 44 | 0.860 (0.800–0.914) | 30 (27–34) |
| Random forest | MOVER (EPIC) test | 4 | 313 | 280 | 60 | 0.895 (0.861–0.928) | 41 (35–45) |
| Random forest | VitalDB | 1 | 204 | 140 | 8 | 0.686 (0.626–0.747) | 3 (2–3) |
| Random forest | VitalDB | 2 | 203 | 157 | 18 | 0.773 (0.711–0.831) | 7 (6–10) |
| Random forest | VitalDB | 3 | 600 | 512 | 60 | 0.853 (0.825–0.882) | 32 (30–35) |
| Random forest | MOVER (SIS) | 1 | 287 | 201 | 10 | 0.700 (0.646–0.752) | 5 (5–6) |
| Random forest | MOVER (SIS) | 2 | 285 | 245 | 25 | 0.860 (0.819–0.899) | 16 (14–17) |
| Random forest | MOVER (SIS) | 3 | 837 | 750 | 60 | 0.896 (0.875–0.916) | 38 (36–41) |
| Logistic regression | MOVER (EPIC) test | 1 | 159 | 119 | 11 | 0.748 (0.678–0.814) | 7 (6–9) |
| Logistic regression | MOVER (EPIC) test | 2 | 164 | 138 | 23 | 0.841 (0.787–0.896) | 18 (17–20) |
| Logistic regression | MOVER (EPIC) test | 3 | 150 | 134 | 44 | 0.893 (0.843–0.940) | 36 (32–38) |
| Logistic regression | MOVER (EPIC) test | 4 | 313 | 267 | 60 | 0.853 (0.812–0.892) | 42 (36–46) |
| Logistic regression | VitalDB | 1 | 204 | 71 | 8 | 0.348 (0.283–0.412) | 3 (2–3) |
| Logistic regression | VitalDB | 2 | 203 | 95 | 18 | 0.468 (0.404–0.539) | 7 (6–8) |
| Logistic regression | VitalDB | 3 | 600 | 298 | 60 | 0.497 (0.454–0.537) | 26 (22–30) |
| Logistic regression | MOVER (SIS) | 1 | 287 | 178 | 10 | 0.620 (0.566–0.676) | 5 (5–5) |
| Logistic regression | MOVER (SIS) | 2 | 285 | 221 | 25 | 0.775 (0.727–0.821) | 14 (12–16) |
| Logistic regression | MOVER (SIS) | 3 | 837 | 714 | 60 | 0.853 (0.829–0.876) | 36 (34–38) |

