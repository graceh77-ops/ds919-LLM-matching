# Current Experiment Configuration

## Status and scope

This document records the current implementation and configuration. Existing
results below are historical 2024-only runs using the former ten-field schema.
The active code schema now targets 2016-2024, but pooled analysis is pending
annual layout verification, code harmonization, and new eleven-field LLM
weight elicitation. The scope is the CDC Natality singleton cohort described in the
[maternal smoking analysis protocol](../../cdc%20natality/docs/protocal_maternal_smoking_dataset.md).

## Frozen shared configuration

| Component | Current configuration |
|---|---|
| Default experiment input | `cdc natality/data/processed/pooled_2016_2024/analysis_cohort_singletons.csv`; the file will exist after annual extraction, combination, and cohort preparation |
| Eligible cohort | 2016-2024 singleton births (`DPLURAL = 1`) with known smoking treatment, valid birth weight, flag-aware complete cases on the ten Natality covariates, and a valid birth year; annual layouts have been reviewed, while value-code harmonization and full-file extraction validation remain pending |
| Treatment | `CIG_REC = Y` versus `CIG_REC = N` |
| Outcome | Birth weight, grams (`DBWT`) |
| Estimand | ATT for treated births in each eligible cohort partition |
| Covariates | `MAGER`, `MRACEHISP`, `MEDUC`, `CIG0_R`, `PRIORLIVE`, `PRIORDEAD`, `BMI_R`, `RF_PDIAB`, `RF_PHYPE`, `SEX`, `birth_year` |
| Encoding | Matching methods fit numeric means/scales and categorical-contrast means on the 1% test sample; five categorical fields use fixed levels and full-rank orthonormal Helmert contrasts; three binary fields use one contrast each; 31 columns total. |
| Matching covariance | Full sample covariance (`ddof = 1`) estimated from encoded 1% test records once per split and reused by generalized Mahalanobis matching methods in that split |
| Eigenvalue floor | `1e-8` times the largest covariance eigenvalue; floor every lower eigenvalue at that threshold before inverse-square-root construction |
| Generalized Mahalanobis | `d_V(x_i,x_j) = sqrt((x_i-x_j)' S^(-1/2) V S^(-1/2)(x_i-x_j))`; identity method uses `V = I` |
| Field-weight mapping | Rescale eleven nonnegative field scores to mean 1, then repeat each field score on all columns from that field; column-normalized allocation is a separately labeled sensitivity method |
| LLM weights | Prior ten-field weights are historical and cannot be loaded for the new schema. Elicit a new outcome-blind eleven-field vector and pass it explicitly with `--weights-json`; the same vector applies across all splits. |
| PCA comparator | Z-standardize all 31 encoded columns using pooled 1% test covariates (`ddof = 0`); fit PCA there; retain the minimum component count reaching 90% cumulative explained variance; use ordinary Mahalanobis distance from retained score covariance, with the `1e-8` relative eigenvalue floor and no additional explained-variance weighting |
| Match rule | 1:1 nearest neighbor, with replacement, no caliper; ties within the coded tolerance resolve to the smallest source `record_number` |
| Split | Treatment-by-year-stratified random 99% reference / 1% test, without replacement within each stratum; use the same split for methods in a repetition |
| Primary reference estimator | AIPW-ATT in the 99% reference cohort: unpenalized logistic propensity model and control-only OLS outcome model, each using the shared encoded covariates; propensity clipping at `1e-6` and `1 - 1e-6` for finite odds weights |
| Reference sensitivities | IPW-ATT (normalized odds-weighted control mean) and outcome-regression ATT; report separately without averaging |
| Matching comparators | Identity-matrix generalized Mahalanobis, PSM, PCA Mahalanobis, and LLM-weighted matching use only 1% test-sample covariates and treatment to fit matching preprocessing, distances, and propensity scores; matching is within the 1% test cohort |
| Matching balance | Numeric and binary source-covariate SMDs; per-level proportion SMDs and maximum absolute level SMD for each categorical covariate; no encoded Helmert column is counted as a separate covariate |
| Evaluation | Report each test-sample ATT and its error relative to reference-cohort AIPW, plus the IPW and outcome-regression reference sensitivities, uncertainty, overlap, balance, weights, ESS, and matching diagnostics |

Repeated splits draw from the same source cohort. They are within-cohort
resampling, not independent validation or external replication.

## Preprocessing memory behavior

`fit_natality_transform()` now fits field means, scales, and the 31-column
sample covariance in 100,000-row batches. It combines batch covariance moments
with online updates, so it does not allocate the full cohort's encoded matrix.
The transformation and covariance definitions are unchanged. The input
DataFrame is still held in memory, and the experiment currently creates
reference and test subsets from it; this change reduces preprocessing's
temporary encoded-matrix memory but does not yet make the complete experiment
out-of-core. The reference propensity and AIPW calculations already process
their model and diagnostic calculations in batches.

## Method status

- **AIPW-ATT:** primary pseudo-reference estimator. Its propensity and control
  outcome models use a reference-fitted 31-column representation. AIPW diagnostics include propensity overlap, weighted SMD,
  odds-weight distribution and maximum, clipping count, effective sample size,
  and a robust influence-function standard error with a 95% Wald interval.
- **IPW-ATT and outcome-regression ATT:** separate reference sensitivity
  estimates; do not average them with AIPW.
- **LLM field weighting:** Existing manual-chat and DeepSeek weights are
  historical ten-field vectors. A new outcome-blind eleven-field vector must
  be elicited for this schema and supplied explicitly; no weight file is
  silently selected as the default.
- **Identity generalized Mahalanobis:** matching comparator evaluated within
  the 1% test cohort, on the same footing as PSM and LLM-weighted matching.
- **PSM:** The unpenalized logistic model uses the 31 encoded covariates and is
  fitted on 1% test-sample treatment and covariates. Its logit scores are used
  to match treated and controls within that same test sample under the shared
  1:1 replacement/no-caliper rule.
- **PCA Mahalanobis:** uses test-only standardized 31-column features, the 90%
  cumulative explained-variance retention rule, and ordinary Mahalanobis
  distance on retained PC scores. It is included as a comparator.
- **Genetic matching:** not included in the current comparison; its detailed
  specification has not been finalized.

## Historical run settings and outputs

All existing results listed below used the former ten-field/23-column design,
predate birth-year adjustment, and must be treated as historical analyses.
They should not be compared directly with results under the new schema. The
historical pre-refactor matching runs used reference-fitted matching
preprocessing and reference-fitted PSM; they predate the test-only matching
data boundary above and should be treated as historical, not results under
the current configuration. Under the revised design, the full cohort has been
run with one split (seed `20261022`, dated `20261023`) and two splits (seed
`20261022`, dated `20261024`), both using a 1% test fraction and the
outcome-blind manual-chat weights. These are exploratory comparisons, not a
final repeated-split evaluation. The manual-chat outputs are in
`cdc natality/results/matching results/1-split 20261023/` and
`cdc natality/results/matching results/2-split 20261024/`. A paired two-split DeepSeek API
run used the same seed (`20261022`) and 1% test fraction; its outputs are in
`cdc natality/results/matching results/2-split 20261024 (2)/`. This run recalculated all
methods on the same partitions, and its conventional comparator results match
the manual-chat run. This default records the project’s chosen standard input 
and does not imply that the two-split results establish DeepSeek as superior. 
The earlier development pilot used a 10,000-row random subset and a 20% test 
fraction. The final repetition count and seed plan remain open and must be 
recorded before the next comparison. The first AIPW implementation validation 
also used the existing 10,000-row pilot mode, one split, seed `20261022`, and 
20% test fraction; its outputs are `cdc natality/results/pilot runs/aipw_reference_validation.csv`
and `cdc natality/results/pilot runs/aipw_reference_validation_summary.csv`.

The PCA implementation validation used a 10,000-row random subset, one split,
seed `20261023`, a 20% test fraction, and the outcome-blind manual-chat weights
for the weighted comparison methods. It retained 17 PCs explaining
`0.912918` cumulative variance. The PCA row reported a test ATT of
`-153.16` grams (control-clustered SE `130.63` grams); these are development
pilot outputs, not study estimates. Detailed rows, method summary, and the
23-row encoded-column source map are in `cdc natality/results/pilot runs/`:
`pca_validation_20261023.csv`,
`pca_validation_20261023_summary.csv`, and
`pca_validation_20261023_feature_map.csv`.

New pooled-year experiment runs write to a new dated folder under
`cdc natality/results/matching results_2016-2024/`, named `{repeats}-split YYYYMMDD` (for example,
`20-split 20261024`). The folder contains `complete_information.csv` (one row
per method and split), `summary.csv` (aggregated by method), and
`complete_information_feature_map.csv`. A numbered suffix is added if the
same split-count/date folder already exists. Explicit `--output` and
`--summary-output` paths override this default.

The matching output table contains one row per method and split, including
method-level test-sample estimates, diagnostics, and source-covariate balance.
The summary table aggregates these measures by method. The feature map maps
every encoded column to its source covariate. PCA rows also record the
retained component count and cumulative variance explained.

## Matching and reference data boundary

For each split, matching preprocessing, the Mahalanobis covariance, the PSM
propensity model, and match selection use only treatment and covariates from
the 1% test sample. The 99% reference sample is used only by the AIPW, IPW, and
outcome-regression reference estimators. Birth-weight values in the test
sample are read after match selection to calculate the matched ATT, uncertainty,
and comparison metrics; they do not enter preprocessing, propensity fitting,
distances, or match selection. This allows the matching procedure to operate
as if no reference sample or causal-effect benchmark were available, while the
research evaluation retains the separate 99% pseudo-reference estimator.

The data frames passed to the current functions also contain the outcome, so
the separation is enforced by code usage rather than by all function
signatures. A stronger function-boundary refactor remains possible.

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
2. Decide whether to implement the function-boundary refactor before running
   further comparisons.
3. Specify genetic matching only if it is brought into scope.
