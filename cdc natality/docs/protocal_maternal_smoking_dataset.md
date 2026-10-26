# Analysis Protocol

## Research question

Among U.S. singleton live births in the 2016-2024 Natality files, what is the
effect of maternal smoking during pregnancy on birth weight?

## Target population

- Primary analysis population: records from 2016-2024 with `DPLURAL = 1` (singleton births),
  known treatment status, and a valid birth weight.
- Sensitivity population: records with known treatment status and a valid birth
  weight, regardless of plurality. This is the all-births cohort.
- The 2024 User Guide defines `DPLURAL = 1` as single birth. The full-data QC
  found 3,506,582 records in the primary cohort and 3,617,844 in the all-births
  sensitivity cohort before covariate missingness is considered.

## Cohort construction

- Start from annual extracted U.S. Natality records for 2016-2024, with one
  record per birth. Each annual layout JSON has been reviewed against its CDC
  User Guide. Shared analysis codes have been reviewed; complete full-file
  extraction validation before pooling. `F_PWGT` is retained for audit but is
  not an eligibility requirement because the selected covariate is `BMI_R`,
  not pre-pregnancy weight. All nine raw annual files are present locally.
- Exclude records with unknown or invalid treatment status (`CIG_REC` other
  than `Y` or `N`). Do not classify unknown status as unexposed.
- Exclude records with unavailable or invalid birth weight. `DBWT = 9999` is
  the not-stated code; retain edited birth weights only from 227 through 8,165
  grams. Blank, non-integer, and out-of-range values are invalid.
- For the primary cohort, additionally retain only `DPLURAL = 1`. Keep
  multiple births in the all-births sensitivity cohort.
- Apply the flag-aware complete-case rule to both the singleton primary cohort
  and all-births sensitivity cohort: retain records only when every primary
  covariate has a recognized, non-unknown value and the reporting flags
  `F_MHISP`, `F_MEDUC`, `F_CIGS_0`, `F_M_HT`, `F_RF_PDIAB`, and
  `F_RF_PHYPER` equal `1`.
- Do not exclude records solely because age, race, or sex was CDC-imputed;
  retain those values and report their imputation flags. Gestational-age
  variables and flags do not determine primary cohort eligibility.
- The existing 2024 missingness audit reports counts from the previous
  flag-aware definition, which required `F_PWGT = 1`. Those counts are
  historical and do not describe the updated eligibility rule; regenerate the
  cohort and QC summaries before reporting current eligible counts.
- The cohort counts above are pre-covariate counts. The corresponding file
  paths and QC details are in [`../results/full_data_qc_summary.md`](../results/full_data_qc_summary.md).

## Treatment

- Treatment: `CIG_REC = Y` (any reported cigarette smoking during pregnancy);
  comparison group: `CIG_REC = N` (no reported cigarette smoking during
  pregnancy).
- Use the CDC-provided pregnancy smoking classification (`CIG_REC`) as-is for
  the first analysis.
- Retain trimester-specific smoking variables to describe the exposure and
  check the classification.
- Do not treat unknown or unreported smoking status as nonsmoking.


## Outcome

- Birth weight in grams (`DBWT`).
- Follow the User Guide's rules for unknown or invalid values.
- Report the number of records excluded because birth weight is unavailable.

## Target causal effect

- Primary estimand: ATT among treated births that can be matched to comparable
  nonsmoking births.
- Interpret this as the effect for the matched smoking group, not automatically
  for every birth or every pregnant person.
- Report how many treated records were not matched.

## Initial matching setup

- Start with 1:1 nearest-neighbor matching with replacement and no caliper.
- Use the same ratio, replacement rule, and no-caliper rule across all
  compared methods; the distance definition is method-specific.
- With replacement, a nonsmoking birth may serve as a match for multiple
  treated births. Report the number of unique controls used and the distribution
  of control reuse.
- With no caliper, treated-birth retention will generally be 100% when at least
  one eligible control is available. Therefore, assess match quality with
  covariate balance, overlap, and the distribution of matched distances, not
  retention alone. A caliper can be evaluated later as a sensitivity analysis.
- Use repeated treatment-by-year-stratified 99% reference / 1% test splits,
  sampling without replacement within each treatment and birth-year stratum.
  The same split is used for all methods in each repetition. These are
  within-cohort resamples, not independent validation sets.
- The primary reference-cohort estimator for the repeated 99% / 1%
  comparison is AIPW-ATT, using a reference-fitted propensity model and a
  control-only outcome model on the shared encoded covariates. IPW-ATT and
  outcome-regression ATT are reported separately as reference sensitivities.
  Estimator formulas, model specifications, diagnostics, and evaluation
  metrics are specified in the
  [LLM matching protocol](../../docs/llm_matching/protocol_LLM_matching.md).
- Include an initial propensity-score comparator: fit an unpenalized logistic
  treatment model using only treatment and covariates from the 1% test portion,
  then match those test births on the fitted logit propensity score. Do not use
  test outcomes to fit the model or select matches.
  Model and matching details are specified in the
  [LLM matching protocol](../../docs/llm_matching/protocol_LLM_matching.md).
- Include PCA Mahalanobis matching as a comparator: use the fixed 31 encoded
  covariate columns, standardize them on the pooled 1% test cohort, retain the
  minimum number of principal components reaching 90% cumulative explained
  variance, and match by ordinary Mahalanobis distance on the retained scores.
  Fit all PCA parameters on test covariates only and do not add another
  explained-variance weight to the distance.
- For every matching method, report signed SMDs for numeric and binary source
  covariates and proportion SMDs for every level of each categorical source
  covariate, with the maximum absolute level SMD per categorical covariate.
  Do not interpret encoded contrast columns as separate covariates. The run
  writes a machine-readable encoded-column-to-source-covariate map.

## Covariates

- Primary set: `MAGER`, `MRACEHISP`, `MEDUC`, `CIG0_R`,
  `PRIORLIVE`, `PRIORDEAD`, `BMI_R`, `RF_PDIAB`, `RF_PHYPE`, and `SEX`.
- Include `birth_year` (2016-2024) as the eleventh, categorical adjustment
  field in the pooled-year analysis and include it in every AIPW and matching
  method. It represents study period and may capture secular differences; it
  is not a maternal characteristic. The current 2024-only data layout can
  exercise only the 2024 level, so it does not validate pooled-year behavior.
- Treat `SEX` as a prognostic covariate for birth weight, not as an established
  confounder.
- Include `COMBGEST` only in a separately labeled sensitivity analysis because
  gestational length may mediate the effect of smoking; use `GESTREC10` as a
  coarser alternative if needed. Conditioning on gestational length changes
  the estimand and does not by itself identify a direct effect.
- See [`covariate_review.md`](covariate_review.md) for rationales and
  alternatives under consideration.
- Do not use variables that may occur after smoking exposure begins in the
  primary matching set unless the causal diagram and timing review support it.
- Report missingness for each selected covariate and the number of records
  removed by the missing-data rule.

## Covariate encoding and generalized Mahalanobis distance

- Use fixed full-rank orthonormal Helmert contrasts with `k-1` columns for
  categorical fields: 6 for `MRACEHISP`, 3 for grouped `MEDUC`, 3 for grouped
  `CIG0_R`, and 5 for `BMI_R`. Encode `RF_PDIAB`, `RF_PHYPE`, and `SEX` as one
  binary contrast column each. With one column each for standardized `MAGER`,
  `PRIORLIVE`, and `PRIORDEAD`, plus eight contrasts for the nine birth-year
  levels, the design has 31 columns.

  | Original field | Encoding | Encoded columns | Count |
  |---|---|---|---:|
  | `MAGER` | Standardized numeric | `MAGER` | 1 |
  | `MRACEHISP` | Seven recognized levels, Helmert contrasts | `MRACEHISP_helmert_1` through `MRACEHISP_helmert_6` | 6 |
  | `MEDUC` | Four grouped levels, Helmert contrasts | `MEDUC_helmert_1` through `MEDUC_helmert_3` | 3 |
  | `CIG0_R` | Four grouped levels, Helmert contrasts | `CIG0_R_helmert_1` through `CIG0_R_helmert_3` | 3 |
  | `PRIORLIVE` | Standardized numeric | `PRIORLIVE` | 1 |
  | `PRIORDEAD` | Standardized numeric | `PRIORDEAD` | 1 |
  | `BMI_R` | Six recognized levels, Helmert contrasts | `BMI_R_helmert_1` through `BMI_R_helmert_5` | 5 |
  | `RF_PDIAB` | Binary contrast | `RF_PDIAB_contrast` | 1 |
  | `RF_PHYPE` | Binary contrast | `RF_PHYPE_contrast` | 1 |
  | `SEX` | Binary contrast | `SEX_contrast` | 1 |
  | `birth_year` | Nine levels (2016-2024), Helmert contrasts | `birth_year_helmert_1` through `birth_year_helmert_8` | 8 |

  The grouped `CIG0_R` levels are nonsmoker (0), light (codes 1-2), moderate
  (code 3), and heavy (codes 4-5), as specified in
  [`covariate_review.md`](covariate_review.md). This table also defines the
  field-to-column mapping used to construct `V`.
- Within each split, fit matching-side numeric means and standard deviations
  and categorical-contrast means using only the 1% test portion. Apply this
  test-fitted encoding and scaling consistently across all matching
  comparators in that split. Use the population standard deviation (`ddof = 0`)
  for numeric scaling and do not standardize categorical contrast columns
  separately. Keep this separate from the reference-fitted representation
  used for AIPW, IPW, and outcome-regression reference calculations.
- Estimate the full covariance matrix `S` from the preprocessed 1% test
  portion using the sample covariance (`ddof = 1`) and keep it fixed across
  generalized Mahalanobis methods in that split. For the inverse square root, floor eigenvalues below
  `1e-8` times the largest eigenvalue to that threshold. Apply this same rule
  across methods and do not select its parameter based on test outcomes.
- Use the full-covariance generalized Mahalanobis distance
  `d_V(x_i, x_j) = sqrt((x_i-x_j)' S^(-1/2) V S^(-1/2) (x_i-x_j))`.
- Obtain one nonnegative LLM weight for each of the 11 original fields and
  rescale those weights to have mean 1. Construct diagonal `V` by repeating
  each field's weight across every encoded column derived from that field.
  The year field receives one LLM score, repeated across its eight encoded
  contrasts by the primary mapping; the column-normalized sensitivity divides
  the field score by the number of columns in its block. The identity-matrix
  matching baseline uses `V = I` over the 31 encoded
  columns.
  This primary mapping preserves the stated formula but may give fields with
  more encoded columns greater effective influence.
- As a sensitivity analysis, divide each field's weight by the number of
  encoded columns in its block before assigning the corresponding diagonal
  entries of `V`. Keep encoding, preprocessing, and `S` unchanged for this
  comparison.
- For PCA matching, z-standardize each of the 31 encoded columns using the
  pooled 1% test cohort's column means and population standard deviations
  (`ddof = 0`); use scale 1 for a constant encoded column. Fit PCA by SVD on
  this standardized test matrix, retaining the smallest component count whose
  cumulative explained-variance ratio is at least 0.90. Compute ordinary
  Mahalanobis distance using the retained PC-score covariance (with the same
  relative `1e-8` eigenvalue floor for numerical stability). Do not multiply
  the PC scores or distances by a further explained-variance weight.
- For distance ties within `1e-12 * max(1, distance)`, select the eligible
  control with the smallest source `record_number`. Allow control reuse and
  apply no caliper in the initial 1:1 nearest-neighbor analysis.

## Identification assumptions and diagnostics

- No unmeasured confounding after adjustment for the selected covariates.
- Overlap: comparable treated and control records exist across covariate
  patterns.
- Consistency: treatment and outcome are defined clearly enough for the
  comparison.
- Check covariate balance and overlap after matching.
- Treat these assumptions as limitations; they cannot all be verified from
  balance statistics alone.

## Decisions still to confirm

- Confirm how gestational length will be used and reported in sensitivity analysis.
