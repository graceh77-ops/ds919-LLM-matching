# Research Plan

## 1. Working research question
How does LLM-based covariate weighting for matching compare with conventional matching
when estimating the effect of maternal smoking during pregnancy on birth weight?

## 2. Data
- Source: CDC Natality public-use data
- Target years: 2016-2024. All nine raw public-use files are present and each
  year has a guide-reviewed layout JSON. Shared analysis codes have been
  reviewed; all nine annual extractions are complete (33,589,282 records), and
  the pooled singleton cohort contains 30,924,495 births. `F_PWGT` is retained
  for audit but is
  not an eligibility requirement because the analysis uses `BMI_R`, not
  pre-pregnancy weight.
- Unit of observation: one live-birth record
- Study population: singleton live births for the primary analysis; all births
  with known treatment and valid birth weight for sensitivity analysis

## 3. Treatment
- Concept: maternal cigarette smoking during pregnancy
- Working definition: `CIG_REC = Y` vs. `CIG_REC = N`
- Unknown treatment status (`U`) is excluded, not classified as nonsmoking.

## 4. Outcome
- Concept: birth weight
- Measurement: edited birth weight in grams (`DBWT`)
- Retain `DBWT` values from 227 to 8,165 grams; `9999` is not stated, and
  blank, non-integer, or out-of-range values are excluded.

## 5. Covariates
- Selected primary set: `MAGER`, `MRACEHISP`, `MEDUC`, `CIG0_R`, `PRIORLIVE`,
  `PRIORDEAD`, `BMI_R`, `RF_PDIAB`, `RF_PHYPE`, and `SEX`.
- For the pooled-year design, include `birth_year` as an eleventh categorical
  covariate and obtain an outcome-blind LLM weight for it.
- See [`covariate_review.md`](covariate_review.md) for rationale and planned
  sensitivity variables.
- Variables that may occur after treatment or lie on the pathway to birth weight: review before including

## 6. Matching comparison
- Conventional comparators: identity-matrix generalized Mahalanobis, PSM, and
  PCA Mahalanobis.
- LLM-based method: generalized Mahalanobis matching using the 11
  outcome-blind field weights, with the specified repeated-column mapping.
- Use the treatment-by-year-stratified 99% reference / 1% test design and
  keep preprocessing, cohort, and covariate coding consistent across methods.

## 7. Evaluation
- Covariate balance: TBD
- Overlap and number of matched records: TBD
- Estimated treatment effect: report for each method
- Ground truth: not known from the observed Natality data alone
- Use a benchmark with known or constructed ground truth if evaluating estimation accuracy

## 8. Implementation status
- The detailed cohort and estimator specifications are in
  [`protocal_maternal_smoking_dataset.md`](protocal_maternal_smoking_dataset.md).
- Annual layouts and shared code definitions for 2016-2024 have been reviewed.
  Annual extraction completed with fixed-width validation for all source
  records; pooling and cohort preparation are complete. Historical 2024
  results use the prior ten-field design.
