# PS Residual Matching Implementation

This folder is reserved for the separate probability-propensity-score plus
covariate-residual matching implementation. The method has not yet been
implemented. Its current proposed specification and preliminary feasibility
diagnostics are in [`../../docs/ps_residual_matching/protocol.md`](../../docs/ps_residual_matching/protocol.md).

Keep the existing runner and matching methods unchanged while implementing
this as a separate comparator. Use only test-cohort treatment and covariates
to fit the propensity model and residual regressions; do not use birth weight
until after match selection.
