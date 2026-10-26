# Entropy-Balancing Reference Sensitivity

## Purpose

This sensitivity analysis compares the reference-cohort ATT from AIPW with an
ATT using entropy-balancing weights on the same 99% reference cohort from split
1 of the 2016–2024 singleton analysis cohort. Entropy balancing is a separate
adjustment estimator, not an independent ground truth. Agreement is a
robustness check under a different adjustment procedure.

## Estimator and calibration

The treated births in the reference cohort define the target covariate means.
For controls, entropy weights use exponential tilting,

\[
w_i = n_1\frac{\exp(\lambda^T x_i)}{\sum_{j:A_j=0}\exp(\lambda^T x_j)},
\]

where `n_1` is the number of treated reference births. The target means are
computed exactly over all treated reference births. To bound memory and avoid
repeated scans of the multi-gigabyte input, the dual optimization estimates
`lambda` from a uniform sample of 500,000 reference controls. It uses covariates
only. The resulting weights are then applied to every reference control in a
streaming pass; the program reports the full-reference balance gaps and
computes the entropy ATT from all reference outcomes after the weights are
fixed. This is a sample-calibrated approximation, not an exact full-control
entropy-balancing solution.

The fixed Natality transform in `src/matching_distance.py` supplies the
encoded columns for the prespecified fields. Numeric scaling and categorical
contrast centering are fitted on the reference cohort. The transform is shared
with the AIPW analysis. Matching covariance and LLM weights do not determine
the entropy weights. Birth weight is not used to fit `lambda`.

## Memory and runtime

The script streams the input CSV in batches. It holds the small test cohort, a
500,000-row control calibration sample, and bounded diagnostic samples in
memory; it never constructs a full reference DataFrame or full reference design
matrix. The split reconstruction and shared preprocessing still require
several sequential scans of the large CSV. Memory is bounded, but runtime can
still be substantial and depends on disk speed, batch size, and optimizer
iterations.

## Diagnostics and interpretation

The output reports the entropy ATT, its difference from the saved AIPW ATT in
grams and AIPW standard-error units, the AIPW confidence interval, optimizer
convergence, full-reference maximum absolute encoded mean gap, and weight
concentration diagnostics including effective sample size and maximum weight.
Weight quantiles are estimated from a bounded sample and marked approximate;
total weight, effective sample size, extrema, ATT, and balance gaps are
calculated over all reference controls.

Treat balance and convergence as gates for interpretation. Large full-reference
gaps show that the sample-calibrated weights did not adequately balance the
reference cohort, even if the optimizer converged on its sample. Highly
concentrated weights also weaken the estimate. Similar AIPW and entropy
estimates support robustness to these two adjustment strategies on this
reference cohort; they do not establish the true causal effect. Both methods
use the same observed births and measured covariates and can share bias from
unmeasured confounding, selection, limited overlap, or omitted model structure.

## Reproduction

From the `cdc natality/` directory, run:

```powershell
python src/run_entropy_balancing_validation.py
```

Defaults reconstruct split 1 with seed `20261026`, verify the saved test
treated count, and compare with the AIPW result at
`results/matching results_2016-2024/1-split 20261026/`. The program refuses to
overwrite an existing output directory. It writes `summary.csv` and
`record.json` under `results/entropy-balancing/1-split 20261026/`.
