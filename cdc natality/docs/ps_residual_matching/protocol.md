# Probability Propensity Score Plus Covariate Residual Matching

## Status

Proposed method; implementation and experiment results are pending. This is a
separate comparison method and does not replace the existing propensity-score
logit comparator or other matching methods.

## Proposed construction

For each treatment-stratified split, fit the existing logistic propensity
model using only the 1% test cohort's treatment and encoded covariates. Let
`p(X) = P(A = 1 | X)` be the fitted probability. For each of the 31 encoded
covariate columns, fit an ordinary least-squares regression with an intercept
on `p(X)` in the pooled test cohort. Form a 32-column matching representation
from the probability score and the 31 residual columns, then use the existing
1:1 nearest-neighbor matching with replacement and no caliper, subject to
final review of the distance and covariance details.

All fitting and matching must remain outcome-blind. Birth weight is used only
after matches are selected to calculate ATT and its uncertainty. The same
test-cohort split, cohort coding, and fixed feature schema should be used as
the other test-only comparators.

## Feasibility and caveats

A read-only diagnostic on a reconstructed 2016-2024 test cohort found that the
probability-score-plus-residual representation had full numerical rank
(32/32), covariance condition number about 854, and correlation-scaled
condition number about 30. These values suggest the covariance is usable for
that reconstructed cohort. The reconstruction's pre-match maximum absolute
SMD (7.129) did not exactly match the saved run (6.987), because the original
split seed was not recorded. Therefore these diagnostics are preliminary and
must not be presented as an exact reanalysis of the saved run.

Using the logistic model's linear predictor (logit score) instead of the
probability is unsuitable for this construction: the logit is a linear
combination of the encoded covariates, making the combined score-plus-residual
matrix rank-deficient (31/32 in the diagnostic). Eigenvalue flooring would
not remove that underlying redundancy.

OLS residualization makes residual columns linearly uncorrelated with the
probability score in the cohort used to fit the regressions. It does not imply
independence or guarantee improved causal balance. Adding the score and
residuals defines a different distance geometry, so assess post-match balance,
overlap, reuse, distance conditioning, and ATT uncertainty before drawing
conclusions. Record the split seed to make the diagnostics reproducible.

## Result files

Store outputs from this method only under
`results/ps_residual_matching/<run-id>/`. Preserve existing experiment output
folders. Include the run configuration and split seed with the method results.
