# Current Experiment Configuration

## Status and scope

This document records the current implementation and configuration. Historical
matching outputs are preserved. The new AIPW implementation has been checked
with the development pilot recorded below; no new full-cohort AIPW comparison
has been run.
The scope is the 2024 CDC Natality singleton cohort described in the
[maternal smoking analysis protocol](../maternal_smoking_birthweight/analysis_protocol.md).

## Frozen shared configuration

| Component | Current configuration |
|---|---|
| Eligible cohort | 2024 singleton births (`DPLURAL = 1`) with known smoking treatment, valid birth weight, and flag-aware complete cases on the ten prespecified covariates |
| Treatment | `CIG_REC = Y` versus `CIG_REC = N` |
| Outcome | Birth weight, grams (`DBWT`) |
| Estimand | ATT for treated births in each eligible cohort partition |
| Covariates | `MAGER`, `MRACEHISP`, `MEDUC`, `CIG0_R`, `PRIORLIVE`, `PRIORDEAD`, `BMI_R`, `RF_PDIAB`, `RF_PHYPE`, `SEX` |
| Encoding | Three numeric fields standardized using reference-sample mean and population SD (`ddof = 0`); four categorical fields mapped to fixed recognized levels and full-rank orthonormal Helmert contrasts; three binary fields represented by one contrast column each; 23 encoded columns total |
| Covariance | Full sample covariance (`ddof = 1`) estimated from encoded reference records once per split and reused by generalized Mahalanobis methods in that split |
| Eigenvalue floor | `1e-8` times the largest covariance eigenvalue; floor every lower eigenvalue at that threshold before inverse-square-root construction |
| Generalized Mahalanobis | `d_V(x_i,x_j) = sqrt((x_i-x_j)' S^(-1/2) V S^(-1/2)(x_i-x_j))`; identity method uses `V = I` |
| Field-weight mapping | Rescale ten nonnegative field scores to mean 1, then repeat each field score on all columns from that field; column-normalized allocation is a separately labeled sensitivity method |
| Match rule | 1:1 nearest neighbor, with replacement, no caliper; ties within the coded tolerance resolve to the smallest source `record_number` |
| Split | Treatment-stratified random 99% reference / 1% test, without replacement within each treatment stratum; use the same split for methods in a repetition |
| Primary reference estimator | AIPW-ATT in the 99% reference cohort: unpenalized logistic propensity model and control-only OLS outcome model, each using the shared encoded covariates; propensity clipping at `1e-6` and `1 - 1e-6` for finite odds weights |
| Reference sensitivities | IPW-ATT (normalized odds-weighted control mean) and outcome-regression ATT; report separately without averaging |
| Matching comparators | Identity-matrix generalized Mahalanobis, PSM, and LLM-weighted matching are each applied to the 1% test cohort under the shared matching rules |
| Evaluation | Report each test-sample ATT and its error relative to reference-cohort AIPW, plus the IPW and outcome-regression reference sensitivities, uncertainty, overlap, balance, weights, ESS, and matching diagnostics |

Repeated splits draw from the same source cohort. They are within-cohort
resampling, not independent validation or external replication.

## Method status

- **AIPW-ATT:** primary pseudo-reference estimator. Its propensity and control
  outcome models use the same reference-fitted 23-column representation as the
  matching methods. AIPW diagnostics include propensity overlap, weighted SMD,
  odds-weight distribution and maximum, clipping count, effective sample size,
  and a robust influence-function standard error with a 95% Wald interval.
- **IPW-ATT and outcome-regression ATT:** separate reference sensitivity
  estimates; do not average them with AIPW.
- **LLM field weighting:** Outcome-blind manual-chat weights and DeepSeek API  
  weights have been generated and recorded separately.
- **Identity generalized Mahalanobis:** matching comparator evaluated within
  the 1% test cohort, on the same footing as PSM and LLM-weighted matching.
- **PSM:** The unpenalized logistic model uses the same 23 encoded covariates, 
  is fitted on reference records, and is applied to test rows for logit-score 
  matching under the shared 1:1 replacement/no-caliper rule.
- **PCA and genetic matching:** not included in the frozen current comparison;
  their detailed specifications have not been finalized.

## Historical run settings and outputs

The recorded historical run setting is seed `20261022` with one split. The
full-cohort comparison used the 1% test fraction. The earlier development
pilot used a 10,000-row random subset and a 20% test fraction. The final repetition count and seed plan remain open and must be recorded before
the next comparison. The first AIPW implementation validation also used the
existing 10,000-row pilot mode, one split, seed `20261022`, and 20% test
fraction; its outputs are `results/pilot runs/aipw_reference_validation.csv`
and `results/pilot runs/aipw_reference_validation_summary.csv`. This is a
development validation, not a full-cohort estimate or final comparison.

The matching output tables retain method-level test-sample estimates
and diagnostics. 

## Leakage boundary and refactor review

Split assignment and reference-fitted preprocessing use treatment and
covariates; the propensity model uses treatment and encoded covariates.
Birth-weight values are consumed after matching to calculate ATT and related
metrics. The existing functions receive data frames that also contain the
outcome, so this separation is enforced by current code usage rather than by
their function signatures.

The preprocessing and matching path can be refactored to accept covariates,
treatment, and record identifiers separately from outcomes, then attach
outcomes only after match indices are fixed. This appears feasible without
changing numerical behavior if row order, dtypes, contrast coding, reference
fit parameters, covariance/eigenvalue operations, distance calculations,
nearest-neighbor tie handling, and outcome-index alignment are preserved.
That refactor has not been performed or numerically verified. Treat it as a
proposed code-quality safeguard, not as a current pipeline property.

## Decisions still open

1. Choose and record the number of within-cohort splits and seed procedure for
   the next comparison.
2. Review whether to implement the function-boundary refactor before running
   further comparisons.
3. Specify PCA and genetic matching only if they are brought into scope.
