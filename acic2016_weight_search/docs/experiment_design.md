# Experiment Design Decisions

This short note records the current pilot and the proposed evaluation split.
Do not use held-out test outcomes or potential outcomes to make design choices.

## Current choices

- One global field-weight vector across settings; all 58 source fields.
- Coordinate-wise search, with separate identity and LLM starting vectors.
- Candidate multipliers: `0.1, 0.5, 1, 2, 10`. They include no change, half/double,
  and one-tenth/tenfold changes around the current value. They are a coarse,
  symmetric-on-log-scale starting grid, not a claim that the optimum lies there.
- Pilot: setting 1, first five replications in the ACIC loader's numeric filename
  order, one sweep, timing/code check only: `zymu_13.csv`, `zymu_336720322.csv`,
  `zymu_336720327.csv`, `zymu_336720328.csv`, and `zymu_336720331.csv`.
- Full split: seeded 60/20/20 by replication within every setting. The five
  pilot replications are forced into training. The current seed is 919.
- Objective: RMSE of matched ATT against realized SATT, aggregated across the
  training replications.

## Evaluation boundary

The pilot uses its five replications only for search execution and timing; it has
no validation or test estimate. In the full experiment, all training
replications select weights and validation replications select a checkpoint
for each starting vector from sweep 0, 1, or 2. The selected training
checkpoint is evaluated on test once; there is no train-plus-validation refit.
Report test RMSE overall and by setting, with balance and matching diagnostics.
The five multiplier candidates for a covariate are scored in parallel within
one SCC job; covariate updates and sweeps remain sequential.

