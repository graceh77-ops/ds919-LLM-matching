# Standalone manual-chat weight prompt

Copy only the text between the delimiters into a new, isolated LLM session.

---

Assign a relative matching-priority score to each of the ten covariates listed below for this study. Base each score only on the definitions provided here.

**Treatment:** Maternal smoking during pregnancy, defined as `CIG_REC = Y`; the comparison group is `CIG_REC = N`.

**Outcome:** Infant birth weight in grams (`DBWT`).

**Covariates:**

- `MAGER`: Mother's age in years; a pre-pregnancy characteristic that may relate to smoking during pregnancy and birth weight.
- `MRACEHISP`: Mother's race and Hispanic-origin recode; a social-context measure that may relate to exposure and outcome through structural and social factors, not a biological cause.
- `MEDUC`: Mother's education; generally established before pregnancy and may relate to smoking and social conditions affecting birth weight.
- `CIG0_R`: Mother's cigarette use before pregnancy; prior smoking behavior may predict smoking during pregnancy and may relate to birth weight.
- `PRIORLIVE`: Number of the mother's previous live births now living; prior pregnancy history.
- `PRIORDEAD`: Number of the mother's previous live births now dead; prior pregnancy history.
- `BMI_R`: Mother's recoded pre-pregnancy body mass index; a baseline body-size measure.
- `RF_PDIAB`: Whether the mother had pre-pregnancy diabetes; a baseline health characteristic.
- `RF_PHYPE`: Whether the mother had pre-pregnancy hypertension; a baseline health characteristic.
- `SEX`: Infant sex; a strong prognostic covariate for birth weight, but not an established confounder in this study.

Return one **integer score from 0 to 10** for each covariate. A score of 0 means lowest relative priority for matching; 10 means highest relative priority. Scores are relative and do not need to sum to 1.

Return a JSON object with exactly these ten keys and numeric values. Do not include prose, comments, or additional keys.

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
  "SEX": 0
}
```

---
