# Standalone weight prompt for PS-residual matching

Copy only the text between the delimiters into a new, isolated LLM session.

---

Assign a relative matching-priority score to each of the twelve fields listed below. Base each score only on the study definitions and method description here. Do not use prior weight sets, empirical results, or outside data.

**Treatment:** Maternal smoking during pregnancy, defined as `CIG_REC = Y`; the comparison group is `CIG_REC = N`.

**Outcome:** Infant birth weight in grams (`DBWT`).

**Matching representation:** Estimate the propensity probability from treatment and the encoded covariates, then regress each encoded covariate column on that probability and use the resulting residual columns for matching. The matching representation contains the estimated propensity probability and the residualized covariate columns. Assign a score to the propensity-probability coordinate as well as to each covariate field. Each covariate field's score will be applied to its residual coordinate(s).

**Covariates:**

- `MAGER`: Mother's age in years.
- `MRACEHISP`: Mother's race and Hispanic-origin recode; a social-context measure that may relate to exposure and outcome through structural and social factors, not a biological cause.
- `MEDUC`: Mother's education; generally established before pregnancy.
- `CIG0_R`: Mother's cigarette use before pregnancy.
- `PRIORLIVE`: Number of the mother's previous live births now living.
- `PRIORDEAD`: Number of the mother's previous live births now dead.
- `BMI_R`: Mother's recoded pre-pregnancy body mass index.
- `RF_PDIAB`: Whether the mother had pre-pregnancy diabetes.
- `RF_PHYPE`: Whether the mother had pre-pregnancy hypertension.
- `SEX`: Infant sex.
- `birth_year`: Calendar year of birth, from 2016 through 2024.
- `PROPENSITY_SCORE`: Estimated probability that the birth is in the maternal-smoking treatment group, conditional on the prespecified encoded covariates. This is a derived matching coordinate, not an additional source covariate.

Return one **integer score from 0 to 10** for each of the eleven covariate fields and the propensity-score coordinate. A score of 0 means the coordinate receives zero weight; 10 means highest relative priority. Prioritize pre-treatment covariates that may help control confounding because they are plausibly related to both smoking and birth weight. Do not prioritize a variable solely because it predicts smoking or birth weight. Do not use outcome data or reference-estimate errors.

The implementation will normalize the twelve scores to mean 1. It will apply the propensity-score weight to the probability-score coordinate and each covariate field’s score to every residual column derived from that field. No field-level column-count normalization will be applied. `birth_year` is represented by eight categorical contrast columns.

Return a JSON object with exactly these twelve keys and numeric values. Do not include prose, comments, or additional keys.

```json
{
  "MAGER": 0,
  "MRACEHISP": 0,
  "MEDUC": 0,
  "CIG0_R": 0,
  "PRIORLIVE": 0,
  "PRIORDEAD": 0,
  "BMI_R": 0,
  "RF_PDIAB": 0,
  "RF_PHYPE": 0,
  "SEX": 0,
  "birth_year": 0,
  "PROPENSITY_SCORE": 0
}
```

---
