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
- For each 99% reference sample, use the equal-weight identity-matrix
  generalized Mahalanobis method with 1:1 nearest-neighbor matching,
  replacement, and no caliper to estimate the reference ATT.
- Treat this as a pseudo-ground-truth reference, not the known true causal
  effect. Compare each method's 1% test-sample ATT with the reference ATT from
  the corresponding split.

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
- Specify the exact distance implementation, including categorical contrast
  coding and block normalization.
