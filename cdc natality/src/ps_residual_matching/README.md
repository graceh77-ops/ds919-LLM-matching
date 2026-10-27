# PS Residual Matching Implementation

This package builds the shared 32-column representation for three matching
comparators: identity Mahalanobis, LLM-weighted generalized Mahalanobis, and
PCA Mahalanobis. They are wired into the shared experiment runner and enabled
with `--include-ps-residual`.

`coordinates.py` accepts only encoded covariates and fitted propensity
coefficients, so it cannot access birth weight. It returns the centered
probability-plus-residual representation, covariance whitening transform,
and diagnostics. The runner fits the propensity model on test-cohort
treatment and covariates and uses the shared outcome estimator only after
match selection. The LLM prompt provides a score for the propensity
probability coordinate and each of the eleven covariate fields. The score for
each field is repeated over its encoded residual columns; the propensity score
receives its own elicited weight.

See [`../../docs/ps_residual_matching/protocol.md`](../../docs/ps_residual_matching/protocol.md) for the method specification and run command.
