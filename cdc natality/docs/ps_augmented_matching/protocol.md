# Propensity-Score-Augmented Matching Comparators

## Comparison design

The optional `--include-ps-covariate` runner option adds three methods to the
existing comparison run. For each split, they use the original encoded
covariates with the fitted propensity probability appended as one additional
matching coordinate. Covariates are not residualized. All methods use the same
test-only cohort and existing 1:1 nearest-neighbor matching with replacement
and no caliper:

1. `identity_ps_augmented_generalized_mahalanobis`: identity diagonal `V` in
   the full-covariance Mahalanobis distance.
2. `llm_weighted_ps_augmented_generalized_mahalanobis`: the 12 elicited field
   scores mapped to the 31 encoded covariate columns and final propensity
   probability coordinate.
3. `pca_ps_augmented_mahalanobis`: standardize the augmented columns, fit
   test-only PCA, retain the minimum number of PCs reaching 90% cumulative
   explained variance, then use ordinary Mahalanobis distance on those scores.

The standard identity, LLM-weighted, PCA, and propensity-logit comparators also
run on the same splits. The original covariate-only LLM method continues to use
the eleven covariate weights renormalized over those fields. The 12-score
weight file is required for the three propensity-augmented comparators.

## Propensity-score-augmented representation

For each split, fit the existing unpenalized logistic propensity model using
only treatment and the 31 encoded covariate columns in the pooled 1% test
cohort. Calculate the fitted probability
`p(X) = P(A = 1 | X)`, not the logit. Center each encoded covariate column and
the fitted probability using test-cohort means, then append the centered
probability after the original encoded columns. The representation therefore
has 32 columns for the current schema.

No outcomes or reference-cohort records enter propensity fitting, covariance
estimation, PCA, distances, or match selection. Birth weight is used only after
matching to calculate ATT and its control-clustered standard error. The 99%
reference-cohort AIPW estimate remains a separate benchmark.

### LLM weight mapping

The prompt supplies scores for the eleven source covariates, `birth_year`, and
the derived `PROPENSITY_SCORE` coordinate. The implementation normalizes all
twelve scores to mean 1. Each covariate score is repeated over that field's
encoded columns; the propensity score weight is assigned to the final appended
probability coordinate. No field-level column-count normalization is applied.
The identity comparator uses weight 1 on every coordinate; PCA does not use
LLM weights. The mapping is recorded in the feature map and run metadata.
Use the [evidence-focused prompt](weight_prompt_evidence_focused.md) for the
new elicitation and the [DeepSeek setup](deepseek_api_setup.md) to save it
separately. The old `--include-ps-residual` CLI spelling remains an alias for
backward compatibility, but now invokes the propensity-score-augmented method.

For the two generalized Mahalanobis variants, estimate the full covariance
matrix of the 32-column augmented representation from the test cohort, floor
covariance eigenvalues at `largest_eigenvalue * 1e-8`, and whiten the
coordinates. The LLM-weighted version scales the whitened coordinates by the
square root of the diagonal field weights, implementing
`(x_i - x_j)^T S^(-1/2) V S^(-1/2) (x_i - x_j)`.

For PCA, standardize the 32 columns using test-cohort means and scales, fit PCA
on the pooled test cohort, retain the minimum number of components reaching
90% cumulative explained variance, and use ordinary Mahalanobis distance on
the retained scores without additional explained-variance weighting.

## Diagnostics and output

Detailed rows include test ATT, clustered SE, control reuse, distance
quantiles, and original-source-covariate pre/post-match balance. The augmented
methods report the fitted propensity-probability range and standard deviation,
covariance rank, dimension, eigenvalue range, condition numbers before and
after flooring, and the number of floored eigenvalues. PCA rows also report
retained component count and cumulative variance. Output includes the
propensity-augmented feature map and `run_metadata.json` with input, split
seeds, weights, and method settings.

New runs are written under
`results/ps_augmented_matching/<split-count>-split <date>/`. The prior
`results/ps_residual_matching/` folder and its outputs are historical and are
not overwritten.

## Interpretation and limitations

The propensity probability is estimated from the same covariates that are
already included in the representation. It therefore adds a nonlinear summary
of those covariates, not new information. Its added influence can change
distances, and its redundancy with the encoded covariates can make the
covariance less well-conditioned. The implementation records rank and
condition diagnostics and applies the existing eigenvalue floor; these
numerical safeguards do not guarantee improved balance or causal validity.
The propensity-score-only comparator remains distinct: it matches on the
probability alone, while these augmented methods include both the original
covariates and that probability.

Repeated splits are within-cohort resampling, not independent validation.

## Run

From the `cdc natality/` directory:

```powershell
python src/run_matching_experiment.py `
  --input data/processed/pooled_2016_2024/analysis_cohort_singletons.csv `
  --repeats 1 `
  --seed <base-seed> `
  --test-fraction 0.01 `
  --weights-json <path-to-12-score-weights.json> `
  --include-ps-covariate
```

This runs the three augmented variants alongside existing comparators on the
same split. Use a recorded seed to reproduce a prior split; older results
without saved seed metadata may not be exactly reproducible.
