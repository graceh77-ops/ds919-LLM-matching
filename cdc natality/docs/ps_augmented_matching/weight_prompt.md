# Standalone weight prompt for propensity-score-augmented matching

Copy only the text between the delimiters into an isolated LLM session.

---

Assign a relative matching-priority score to each of the twelve fields listed
below. Base each score only on the study definitions and method description
here. Do not use prior weight sets, empirical results, or outside data.

**Treatment:** Maternal smoking during pregnancy, defined as `CIG_REC = Y`; the
comparison group is `CIG_REC = N`.

**Outcome:** Infant birth weight in grams (`DBWT`).

**Matching representation:** Estimate the propensity probability from
treatment and the encoded covariates. Append that probability as one additional
coordinate after the original encoded covariate columns. Keep the original
encoded covariate values in the matching representation; do not residualize
them. Assign a score to the propensity-probability coordinate as well as to
each source covariate field. A field's score will be applied to every encoded
column derived from that field.

**Covariates:**

- `MAGER`: Mother's age in years.
- `MRACEHISP`: Mother's race and Hispanic-origin recode; a social-context
  measure that may relate to exposure and outcome through structural and social
  factors, not a biological cause.
- `MEDUC`: Mother's education; generally established before pregnancy.
- `CIG0_R`: Mother's cigarette use before pregnancy.
- `PRIORLIVE`: Number of the mother's previous live births now living.
- `PRIORDEAD`: Number of the mother's previous live births now dead.
- `BMI_R`: Mother's recoded pre-pregnancy body mass index.
- `RF_PDIAB`: Whether the mother had pre-pregnancy diabetes.
- `RF_PHYPE`: Whether the mother had pre-pregnancy hypertension.
- `SEX`: Infant sex; a strong prognostic covariate for birth weight, but not
  an established cause of maternal smoking during pregnancy.
- `birth_year`: Calendar year of birth, from 2016 through 2024.
- `PROPENSITY_SCORE`: Estimated probability that the birth is in the
  maternal-smoking treatment group, conditional on the prespecified encoded
  covariates. This is a derived matching coordinate, not a source covariate.

Return one integer score from 0 to 10 for each field. A score of 0 means lowest
relative priority; 10 means highest. Scores are relative and do not need to sum
to 1.

Return a JSON object with exactly these twelve keys and numeric integer values.
Do not include prose, comments, or additional keys.

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
