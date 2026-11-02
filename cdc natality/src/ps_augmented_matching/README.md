# Propensity-Score-Augmented Matching Implementation

This package builds a test-only 32-column representation from the existing
31 encoded covariate columns and one appended test-only fitted propensity
probability. It retains the covariates and does not construct residuals.

`coordinates.py` receives encoded covariates and fitted logistic coefficients,
not birth weight. It returns the centered augmented representation, covariance
whitening transform, and numerical diagnostics. The runner uses the shared
outcome estimator only after match selection. For LLM-weighted matching, each
field weight is repeated over that field's encoded columns and the
`PROPENSITY_SCORE` weight is assigned to the final probability coordinate.

See [`../../docs/ps_augmented_matching/protocol.md`](../../docs/ps_augmented_matching/protocol.md)
for the method specification and run command.
