# Propensity Score and Covariate-Residual Matching Comparators

## Comparison design

The optional `--include-ps-residual` runner option adds three methods to the
existing comparison run. All three use the same test-only representation,
matching cohort, and 1:1 nearest-neighbor matching with replacement and no
caliper:

1. `identity_ps_residual_generalized_mahalanobis`: identity `V` in the
   full-covariance Mahalanobis distance.
2. `llm_weighted_ps_residual_generalized_mahalanobis`: the LLM field weights
   in `V`, mapped to encoded covariate residual columns.
3. `pca_ps_residual_mahalanobis`: ordinary Mahalanobis matching on the retained
   principal component scores after test-only standardization and PCA; retain
   the minimum number of PCs reaching 90% cumulative variance.

The existing methods on the original encoded covariates also run in the same
experiment, so these variants can be compared with the original identity,
LLM-weighted, PCA, and propensity-logit methods on identical splits.
For the original covariate-only LLM methods in this run, the eleven covariate
scores are renormalized over those fields; `PROPENSITY_SCORE` applies only to
the PS-residual LLM comparator.

## Shared probability-score/residual representation

For each split, fit the existing unpenalized logistic propensity model using
only treatment and the 31 encoded covariate columns in the pooled 1% test
cohort. Calculate the fitted probability `p(X) = P(A = 1 | X)`, not the logit.
For each encoded covariate column, fit an ordinary least-squares regression
with an intercept on `p(X)` in the pooled test cohort. The common 32-column
representation is the centered probability and the 31 OLS residual columns.

No outcomes or reference-cohort records enter propensity fitting,
residualization, covariance estimation, PCA, distances, or match selection.
Birth weight is used only after matching to calculate ATT and its
control-clustered standard error. The 99% reference-cohort AIPW estimate stays
a separate benchmark for comparison error.

### LLM weight mapping

The LLM prompt supplies scores for the eleven source fields and a twelfth
score for the derived propensity-probability coordinate. The implementation
normalizes all twelve scores to mean 1, applies `PROPENSITY_SCORE` to the
probability coordinate, and repeats each covariate score across that field's
encoded residual columns. The identity comparator uses weight 1 on every
coordinate; PCA does not use LLM weights. This mapping is recorded in the
PS-residual feature map and run metadata. Obtain a fresh elicitation with the
[PS-residual weight prompt](weight_prompt.md), saved separately using the
[DeepSeek setup](deepseek_api_setup.md). Earlier eleven-field weights do not
provide a propensity-score weight and are not accepted for this comparison.

For the two generalized Mahalanobis variants, estimate the full covariance
matrix of the 32-column representation from the test cohort, floor covariance
eigenvalues at `largest_eigenvalue * 1e-8`, and whiten the coordinates. The
LLM-weighted version then scales the whitened coordinates by the square root
of their diagonal weights, implementing
`(x_i - x_j)^T S^(-1/2) V S^(-1/2) (x_i - x_j)`.

For PCA, standardize the 32 representation columns using test-cohort means
and scales, fit PCA on the pooled test cohort, retain the minimum number of
components reaching 90% cumulative explained variance, and use ordinary
Mahalanobis distance on those retained scores without additional
explained-variance weighting.

## Diagnostics and output

The detailed result rows include test ATT, clustered SE, control reuse,
distance quantiles, and original-covariate pre/post-match balance summaries.
PS-residual methods also report the fitted probability range and standard
deviation, covariance rank, dimension, eigenvalue range, condition numbers
before and after flooring, number of floored eigenvalues, and maximum
absolute linear correlation between probability and residuals. PCA rows
include retained component count and cumulative variance. Summary output
aggregates these diagnostics across splits.

Each run folder includes the original feature map, a PS-residual feature map,
and `run_metadata.json` containing the input, split seeds, weights, and method
settings. Default outputs are written under
`results/ps_residual_matching/<split-count>-split <date>/`. Existing result
folders are not overwritten by default.

## Feasibility and interpretation

A prior read-only diagnostic on a reconstructed 2016-2024 test cohort found
full numerical rank (32/32), covariance condition number about 854, and
correlation-scaled condition number about 30 for the probability-plus-residual
representation. The reconstructed pre-match maximum absolute SMD (7.129) did
not exactly match the saved run (6.987), because that original run's seed was
not recorded. Treat those values as preliminary, not as a reanalysis of the
saved run. New runs record their seeds for reproducibility.

Using the propensity logit with the residuals is not part of this method: the
logit is a linear combination of encoded covariates, so the joint
score-plus-residual representation is rank-deficient. OLS residualization
guarantees only linear sample orthogonality to the fitted probability; it
does not imply independence or guarantee improved causal balance. Repeated
splits are within-cohort resampling, not independent validation.

## Run

From the `cdc natality/` directory, provide the same input, base seed, split
count, test fraction, and 12-score PS-residual LLM weight file:

```powershell
python src/run_matching_experiment.py `
  --input data/processed/pooled_2016_2024/analysis_cohort_singletons.csv `
  --repeats 1 `
  --seed <same-base-seed> `
  --test-fraction 0.01 `
  --weights-json <path-to-12-score-ps-residual-weights.json> `
  --include-ps-residual
```

This runs the three PS-residual variants alongside the existing comparators
on the same split(s). Use the same base seed to reproduce an earlier split
only if that seed is known; older outputs without saved seed metadata may not
be exactly reproducible.
