# Research Plan

## 1. Working research question
How does LLM-based covariate weighting for matching compare with conventional matching
when estimating the effect of maternal smoking during pregnancy on birth weight?

## 2. Data
- Source: CDC Natality public-use data
- Years: 2024
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
- `9999` is not stated; unavailable or invalid values are excluded.

## 5. Covariates
- Selected primary set: `MAGER`, `MRACEHISP`, `MEDUC`, `CIG0_R`, `PRIORLIVE`,
  `PRIORDEAD`, `BMI_R`, `RF_PDIAB`, `RF_PHYPE`, and `SEX`.
- See [`covariate_review.md`](covariate_review.md) for rationale and planned
  sensitivity variables.
- Variables that may occur after treatment or lie on the pathway to birth weight: review before including

## 6. Matching comparison
- Conventional matching method: TBD
- LLM-based matching method: LLM proposes or assigns covariate relevance/weights; exact procedure TBD
- Keep the eligible sample and preprocessing consistent across methods where possible

## 7. Evaluation
- Covariate balance: TBD
- Overlap and number of matched records: TBD
- Estimated treatment effect: report for each method
- Ground truth: not known from the observed Natality data alone
- Use a benchmark with known or constructed ground truth if evaluating estimation accuracy

## 8. Open decisions
- Final covariate missing-data rule: TBD
- Confirm whether the primary estimand is the matched-sample ATT: TBD
- Matching and evaluation details: TBD
