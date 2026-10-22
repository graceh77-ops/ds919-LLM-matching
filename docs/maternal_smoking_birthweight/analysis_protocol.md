# Analysis Protocol

## Research question

Among 2024 U.S. live births represented in the Natality file, what is the
effect of maternal smoking during pregnancy on birth weight?

## Target population

- Primary analysis population: records with `DPLURAL = 1` (singleton births),
  known treatment status, and a valid birth weight.
- Sensitivity population: records with known treatment status and a valid birth
  weight, regardless of plurality. This is the all-births cohort.
- The 2024 User Guide defines `DPLURAL = 1` as single birth. The full-data QC
  found 3,506,582 records in the primary cohort and 3,617,844 in the all-births
  sensitivity cohort before covariate missingness is considered.

## Cohort construction

- Start from the extracted 2024 U.S. Natality records, with one record per
  birth.
- Exclude records with unknown or invalid treatment status (`CIG_REC` other
  than `Y` or `N`). Do not classify unknown status as unexposed.
- Exclude records with unavailable or invalid birth weight. `DBWT = 9999` is
  the not-stated code; blank or non-integer values are invalid. The User Guide
  lists edited birth weights from 227 through 8,165 grams.
- For the primary cohort, additionally retain only `DPLURAL = 1`. Keep
  multiple births in the all-births sensitivity cohort.
- Apply the flag-aware complete-case rule to both the singleton primary cohort
  and all-births sensitivity cohort: retain records only when every primary
  covariate has a recognized, non-unknown value and the reporting flags
  `F_MHISP`, `F_MEDUC`, `F_CIGS_0`, `F_M_HT`, `F_PWGT`, `F_RF_PDIAB`, and
  `F_RF_PHYPER` equal `1`.
- Do not exclude records solely because age, race, or sex was CDC-imputed;
  retain those values and report their imputation flags. Gestational-age
  variables and flags do not determine primary cohort eligibility.
- The flag-aware rule retained 3,336,235 of 3,506,582 singleton records
  (95.14%) in the covariate missingness audit. The code-based complete-case
  rule without reporting-flag requirements retained 3,344,587 (95.38%) and is
  reported as an eligibility comparison only; the primary cohort uses the
  flag-aware rule.
- The cohort counts above are pre-covariate counts. The corresponding file
  paths and QC details are in [`../../results/full_data_qc_summary.md`](../../results/full_data_qc_summary.md).

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
- The conventional reference is equal-weight identity-matrix generalized
  Mahalanobis matching under these same settings. The repeated 99% / 1%
  comparison and evaluation metrics are specified in the
  [LLM matching protocol](../llm_matching/llm_matching_protocol.md).

## Covariates

- Primary set: `MAGER`, `MRACEHISP`, `MEDUC`, `CIG0_R`,
  `PRIORLIVE`, `PRIORDEAD`, `BMI_R`, `RF_PDIAB`, `RF_PHYPE`, and `SEX`.
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
  `PRIORLIVE`, and `PRIORDEAD`, the design has 23 columns.

  | Original field | Encoding | Columns (`q_j`) |
  |---|---|---:|
  | `MAGER` | Standardized numeric | 1 |
  | `MRACEHISP` | Seven recognized levels, Helmert contrasts | 6 |
  | `MEDUC` | Four grouped levels (1-2, 3-4, 5-6, 7-8), Helmert contrasts | 3 |
  | `CIG0_R` | Four grouped levels, Helmert contrasts | 3 |
  | `PRIORLIVE` | Standardized numeric | 1 |
  | `PRIORDEAD` | Standardized numeric | 1 |
  | `BMI_R` | Six recognized levels, Helmert contrasts | 5 |
  | `RF_PDIAB` | Binary contrast | 1 |
  | `RF_PHYPE` | Binary contrast | 1 |
  | `SEX` | Binary contrast | 1 |

  The grouped `CIG0_R` levels are nonsmoker (0), light (codes 1-2), moderate
  (code 3), and heavy (codes 4-5), as specified in
  [`covariate_review.md`](covariate_review.md). This table also defines the
  field-to-column mapping used to construct `V`.
- Within each split, calculate numeric means and standard deviations and
  categorical-contrast means from the 99% reference portion. Use these same
  preprocessing values and encoded columns for the reference and 1% test
  estimates across all methods. Do not standardize categorical contrast
  columns separately.
- Estimate the full covariance matrix `S` from the preprocessed 99% reference
  portion and keep it fixed across methods in that split. If `S` is numerically
  singular or ill-conditioned, apply one prespecified regularization rule
  consistently across methods. Record the rule and its parameter before
  comparing methods; do not choose them based on the 1% test outcomes.
- Use the full-covariance generalized Mahalanobis distance
  `d_V(x_i, x_j) = sqrt((x_i-x_j)' S^(-1/2) V S^(-1/2) (x_i-x_j))`.
- Obtain one nonnegative LLM weight for each of the 10 original fields and
  rescale those weights to have mean 1. Construct diagonal `V` by repeating
  each field's weight across every encoded column derived from that field.
  The identity-matrix reference uses `V = I` over the 23 encoded columns.
  This primary mapping preserves the stated formula but may give fields with
  more encoded columns greater effective influence.
- As a sensitivity analysis, divide each field's weight by the number of
  encoded columns in its block before assigning the corresponding diagonal
  entries of `V`. Keep encoding, preprocessing, and `S` unchanged for this
  comparison.

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
