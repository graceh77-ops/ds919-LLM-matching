# ACIC 2016 Analysis Protocol

## Evaluation design

- Analyze all 77 settings and 100 replications per setting, treating each
  4,802-unit replication as a separate evaluation cohort.
- Match treated and control units within each complete replication; do not use
  a 99/1 reference/test split.
- Use realized SATT, `mean(y1 - y0)` among treated units, as the primary
  reference. Report the expected contrast, `mean(mu1 - mu0)` among treated,
  separately as a secondary reference.
- Keep outcomes out of covariate preprocessing, weight assignment, and match
  selection. Use `z` only where a method requires treatment labels. Use
  outcomes after matching to estimate ATT and compare it with the reference.

## Covariates and reporting

Use all 58 fields in `x.csv`. Encode `x_2` (A–F), `x_21` (A–P), and `x_24`
(A–E) as categorical using fixed one-hot columns, dropping level A. Keep the
other 55 fields numeric, including the five binary fields. This yields 79
encoded columns; retain a map from each encoded column to its source field.
Apply this schema across replications. Prespecify scaling, matching ratio,
replacement, caliper, and other method settings before experiments; exclude
outcomes from all preprocessing.

Report each method's matched ATT, error from realized SATT, uncertainty
interval, treated/control counts, control reuse, and covariate balance. Summarize
results by setting and across all replications.
