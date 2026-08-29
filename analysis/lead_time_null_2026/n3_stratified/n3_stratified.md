# N3 — median lead inside quintiles of observed window length

Stratifying takes the ratio out of the argument. Inside a quintile the observed window is nearly constant, so the median **absolute lead in minutes** is directly comparable, and the question is whether minutes of warning depend on how long the patient happened to be watched.

## Headline

Median lead rises from the shortest to the longest quintile in **15 of 15** cells, by **+26 to +54 minutes**. The reported median lead is not a constant amount of warning that happens to be measured in a window; it moves with the window.

0 of 15 cells are censored at the 60-minute alert-window cap and are flagged in the gradient table.

## Transformer, all three cohorts

| Cohort | Quintile | n | Window, min (median) | Median lead, min (95% CI) | Median ratio (95% CI) |
|---|---|---|---|---|---|
| MOVER (EPIC) test | 1 | 139 | 10 | 9 (8–9) | 0.88 (0.85–0.89) |
| MOVER (EPIC) test | 2 | 111 | 19 | 18 (17–18) | 0.94 (0.94–0.95) |
| MOVER (EPIC) test | 3 | 121 | 33 | 31 (29–32) | 0.97 (0.96–0.97) |
| MOVER (EPIC) test | 4 | 240 | 60 | 46 (44–50) | 0.98 (0.96–0.98) |
| VitalDB | 1 | 143 | 7 | 5 (5–6) | 0.83 (0.83–0.83) |
| VitalDB | 2 | 140 | 12 | 10 (10–11) | 0.91 (0.90–0.91) |
| VitalDB | 3 | 132 | 20 | 19 (18–20) | 0.94 (0.94–0.95) |
| VitalDB | 4 | 134 | 40 | 38 (37–40) | 0.97 (0.97–0.97) |
| VitalDB | 5 | 135 | 60 | 59 (57–60) | 0.98 (0.98–1.00) |
| MOVER (SIS) | 1 | 199 | 8 | 6 (5–6) | 0.80 (0.80–0.82) |
| MOVER (SIS) | 2 | 179 | 17 | 14 (13–15) | 0.86 (0.84–0.91) |
| MOVER (SIS) | 3 | 186 | 29 | 27 (26–28) | 0.94 (0.93–0.96) |
| MOVER (SIS) | 4 | 362 | 60 | 46 (43–49) | 0.95 (0.93–0.97) |


## Gradient across all fifteen cells

`Lead min per window min` is the change in median lead divided by the change in median window between the lowest and highest quintile. A value near 1 means an extra minute of observation buys an extra minute of reported lead.

| Model | Cohort | Bands | Window Q1→Q5, min | Lead Q1→Q5, min | Gradient, min | Lead min per window min | Censored |
|---|---|---|---|---|---|---|---|
| ITE Transformer | MOVER (EPIC) test | 4 | 10 → 60 | 9 → 46 | +37 | 0.74 |  |
| ITE Transformer | VitalDB | 5 | 7 → 60 | 5 → 59 | +54 | 1.02 |  |
| ITE Transformer | MOVER (SIS) | 4 | 8 → 60 | 6 → 46 | +40 | 0.77 |  |
| LSTM | MOVER (EPIC) test | 4 | 10 → 60 | 6 → 44 | +38 | 0.77 |  |
| LSTM | VitalDB | 5 | 6 → 60 | 3 → 34 | +31 | 0.57 |  |
| LSTM | MOVER (SIS) | 4 | 9 → 60 | 5 → 31 | +26 | 0.51 |  |
| XGBoost | MOVER (EPIC) test | 3 | 12 → 60 | 8 → 38 | +30 | 0.62 |  |
| XGBoost | VitalDB | 3 | 9 → 60 | 3 → 30 | +27 | 0.53 |  |
| XGBoost | MOVER (SIS) | 3 | 12 → 60 | 5 → 36 | +31 | 0.65 |  |
| Random forest | MOVER (EPIC) test | 3 | 13 → 60 | 8 → 38 | +30 | 0.64 |  |
| Random forest | VitalDB | 3 | 9 → 60 | 3 → 34 | +31 | 0.61 |  |
| Random forest | MOVER (SIS) | 3 | 12 → 60 | 6 → 40 | +34 | 0.71 |  |
| Logistic regression | MOVER (EPIC) test | 3 | 11 → 60 | 8 → 40 | +32 | 0.65 |  |
| Logistic regression | VitalDB | 3 | 10 → 60 | 3 → 28 | +26 | 0.51 |  |
| Logistic regression | MOVER (SIS) | 3 | 12 → 60 | 5 → 38 | +33 | 0.69 |  |


## Method

Quintile cut points are computed within cell, because the cohorts' window-length distributions differ too much for a pooled cut to be meaningful. Where the window is censored at the 60-minute cap the upper quintiles collapse; `pd.qcut` drops the duplicate edges and the realised band count is reported rather than assumed. Cells with fewer than 3 distinct edges are flagged as censored. Every median carries a 2,000-replicate cluster bootstrap, clustering on patient for MOVER (EPIC) and VitalDB and on case for MOVER (SIS); one weight matrix is drawn per cell and reused across bands, so band-to-band differences are paired.
