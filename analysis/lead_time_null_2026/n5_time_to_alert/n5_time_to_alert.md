# N5 - replacement estimands for the median alert lead time

## 1. Fixed-horizon detection rate

Among event cases observed for at least X minutes before onset, the share whose first alert came at least X minutes before onset. Numerator and denominator move together, so a cohort watched for longer cannot inflate it.

|                                              |     5 |    10 |    15 |    20 |    30 |    45 |    60 |
|:---------------------------------------------|------:|------:|------:|------:|------:|------:|------:|
| ('ITE Transformer', 'MOVER (EPIC) test')     | 0.733 | 0.69  | 0.646 | 0.605 | 0.512 | 0.339 | 0.17  |
| ('ITE Transformer', 'MOVER (SIS)')           | 0.594 | 0.547 | 0.504 | 0.469 | 0.377 | 0.247 | 0.125 |
| ('ITE Transformer', 'VitalDB')               | 0.638 | 0.56  | 0.509 | 0.463 | 0.39  | 0.261 | 0.154 |
| ('LSTM', 'MOVER (EPIC) test')                | 0.721 | 0.663 | 0.635 | 0.597 | 0.49  | 0.331 | 0.109 |
| ('LSTM', 'MOVER (SIS)')                      | 0.453 | 0.392 | 0.346 | 0.319 | 0.253 | 0.167 | 0.047 |
| ('LSTM', 'VitalDB')                          | 0.343 | 0.278 | 0.265 | 0.223 | 0.173 | 0.102 | 0.03  |
| ('Logistic regression', 'MOVER (EPIC) test') | 0.726 | 0.692 | 0.658 | 0.63  | 0.547 | 0.401 | 0.122 |
| ('Logistic regression', 'MOVER (SIS)')       | 0.664 | 0.611 | 0.573 | 0.546 | 0.474 | 0.353 | 0.093 |
| ('Logistic regression', 'VitalDB')           | 0.338 | 0.307 | 0.303 | 0.274 | 0.233 | 0.137 | 0.026 |
| ('Random forest', 'MOVER (EPIC) test')       | 0.709 | 0.674 | 0.638 | 0.611 | 0.506 | 0.393 | 0.138 |
| ('Random forest', 'MOVER (SIS)')             | 0.736 | 0.674 | 0.64  | 0.6   | 0.526 | 0.403 | 0.114 |
| ('Random forest', 'VitalDB')                 | 0.589 | 0.559 | 0.559 | 0.53  | 0.478 | 0.347 | 0.103 |
| ('XGBoost', 'MOVER (EPIC) test')             | 0.688 | 0.651 | 0.615 | 0.575 | 0.484 | 0.367 | 0.119 |
| ('XGBoost', 'MOVER (SIS)')                   | 0.656 | 0.597 | 0.565 | 0.52  | 0.46  | 0.326 | 0.08  |
| ('XGBoost', 'VitalDB')                       | 0.502 | 0.47  | 0.453 | 0.425 | 0.366 | 0.237 | 0.054 |

## 2. Median lead on the fully observed cases, and time to first alert

The window is a constant in the first column rather than a covariate. `Unalerted by` is the Kaplan-Meier survival at that elapsed monitoring minute, with each case censored at the end of its own window. The censoring is **not** independent of the event: a short run-up is an early-onset event, not a case watched briefly by accident.

| Model | Cohort | Fully observed n | Detected | Median lead, min (95% CI) | Unalerted by min 1 | Unalerted by min 10 | Unalerted by min 30 |
|---|---|---|---|---|---|---|---|
| ITE Transformer | MOVER (EPIC) test | 311 | 0.441 | 47 (33–59) | 0.468 | 0.318 | 0.288 |
| ITE Transformer | VitalDB | 429 | 0.247 | 60 (60–60) | 0.540 | 0.353 | 0.343 |
| ITE Transformer | MOVER (SIS) | 665 | 0.304 | 57 (51–59) | 0.692 | 0.414 | 0.386 |
| LSTM | MOVER (EPIC) test | 311 | 0.598 | 40 (34–46) | 0.772 | 0.379 | 0.284 |
| LSTM | VitalDB | 429 | 0.200 | 33 (21–45) | 0.913 | 0.617 | 0.541 |
| LSTM | MOVER (SIS) | 665 | 0.433 | 28 (22–33) | 0.862 | 0.656 | 0.551 |
| XGBoost | MOVER (EPIC) test | 311 | 0.846 | 40 (34–44) | 0.812 | 0.549 | 0.332 |
| XGBoost | VitalDB | 429 | 0.762 | 33 (30–36) | 0.938 | 0.698 | 0.437 |
| XGBoost | MOVER (SIS) | 665 | 0.854 | 37 (34–41) | 0.881 | 0.626 | 0.350 |
| Random forest | MOVER (EPIC) test | 311 | 0.894 | 41 (35–45) | 0.817 | 0.540 | 0.301 |
| Random forest | VitalDB | 429 | 0.851 | 40 (36–44) | 0.899 | 0.590 | 0.313 |
| Random forest | MOVER (SIS) | 665 | 0.910 | 42 (39–45) | 0.834 | 0.547 | 0.291 |
| Logistic regression | MOVER (EPIC) test | 311 | 0.852 | 42 (36–45) | 0.774 | 0.490 | 0.284 |
| Logistic regression | VitalDB | 429 | 0.490 | 31 (26–37) | 0.964 | 0.795 | 0.608 |
| Logistic regression | MOVER (SIS) | 665 | 0.857 | 40 (37–43) | 0.879 | 0.615 | 0.348 |

