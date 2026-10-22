# Current Experiment Configuration

## Status and scope

This document records the existing implementation and the configuration to
hold fixed for the next comparison. It does not authorize or report a new run.
No matching results have been changed or regenerated as part of this record.
The scope is the 2024 CDC Natality singleton cohort described in the
[maternal smoking analysis protocol](../maternal_smoking_birthweight/analysis_protocol.md).

## Frozen shared configuration

| Component | Current configuration |
|---|---|
| Eligible cohort | 2024 singleton births (`DPLURAL = 1`) with known smoking treatment, valid birth weight, and flag-aware complete cases on the ten prespecified covariates |
| Treatment | `CIG_REC = Y` versus `CIG_REC = N` |
| Outcome | Birth weight, grams (`DBWT`) |
| Estimand | ATT for treated births matched to nonsmoking controls |
| Covariates | `MAGER`, `MRACEHISP`, `MEDUC`, `CIG0_R`, `PRIORLIVE`, `PRIORDEAD`, `BMI_R`, `RF_PDIAB`, `RF_PHYPE`, `SEX` |
| Encoding | Three numeric fields standardized using reference-sample mean and population SD (`ddof = 0`); four categorical fields mapped to fixed recognized levels and full-rank orthonormal Helmert contrasts; three binary fields represented by one contrast column each; 23 encoded columns total |
| Covariance | Full sample covariance (`ddof = 1`) estimated from encoded reference records once per split and reused by generalized Mahalanobis methods in that split |
| Eigenvalue floor | `1e-8` times the largest covariance eigenvalue; floor every lower eigenvalue at that threshold before inverse-square-root construction |
| Generalized Mahalanobis | `d_V(x_i,x_j) = sqrt((x_i-x_j)' S^(-1/2) V S^(-1/2)(x_i-x_j))`; identity method uses `V = I` |
| Field-weight mapping | Rescale ten nonnegative field scores to mean 1, then repeat each field score on all columns from that field; column-normalized allocation is a separately labeled sensitivity method |
| Match rule | 1:1 nearest neighbor, with replacement, no caliper; ties within the coded tolerance resolve to the smallest source `record_number` |
| Split | Treatment-stratified random 99% reference / 1% test, without replacement within each treatment stratum; use the same split for methods in a repetition |
| Evaluation | Match reference identity method to form the pseudo-reference ATT; apply each comparator within the test cohort; report ATT, reference error, clustered uncertainty, balance, and control reuse |

Repeated splits draw from the same source cohort. They are within-cohort
resampling, not independent validation or external replication.

## Method status

- **Identity generalized Mahalanobis:** reference estimator and primary
  conventional comparator under the shared configuration.
- **LLM field weighting:** existing manual weights remain exploratory because
  their elicitation occurred in a context where pilot metrics were present.
  Regenerate and freeze outcome-blind weights in a separate session using the
  [manual-chat protocol](manual_chat_weight_protocol.md) before evaluating
  that new weight set. Keep its results separate from exploratory results.
- **PSM:** the comparator family was identified earlier, but its detailed
  implementation was finalized on 2026-10-22 after reviewing the first
  full-cohort identity/LLM comparison and before the PSM run. Exact time was
  not recorded. The unpenalized logistic model uses the same 23 encoded
  covariates, is fitted on reference records, and is applied to test rows for
  logit-score matching under the shared 1:1 replacement/no-caliper rule. This
  is a later refinement and exploratory comparator for this phase. Hold its
  current specification fixed.
- **PCA and genetic matching:** not included in the frozen current comparison;
  their detailed specifications have not been finalized.

## Historical run settings and outputs

The recorded historical run setting is seed `20261022` with one split. The
full-cohort comparison used the 1% test fraction. The earlier development
pilot used a 10,000-row random subset and a 20% test fraction. These are
historical exploratory settings, not a selected final repetition plan. The
final repetition count and seed plan remain open and must be recorded before
the next comparison.

Existing output files are retained as historical results, including the
`full_cohort_manual_chat_*` outputs and pilot outputs under
`results/manual llm matching/`. Do not overwrite or combine them with results
from the outcome-blind weight set.

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

1. Regenerate and document the independent outcome-blind manual weights.
2. Choose and record the number of within-cohort splits and seed procedure for
   the next comparison.
3. Review whether to implement the function-boundary refactor before running
   further comparisons.
4. Specify PCA and genetic matching only if they are brought into scope.
