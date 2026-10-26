# Standalone manual-chat weight prompt

Copy only the text between the delimiters into a new, isolated LLM session.

---

Assign a relative matching-priority score to each of the eleven fields listed below for this study. Base each score only on the definitions provided here.

**Treatment:** Maternal smoking during pregnancy, defined as `CIG_REC = Y`; the comparison group is `CIG_REC = N`.

**Outcome:** Infant birth weight in grams (`DBWT`).

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
- `birth_year`: Calendar year of the birth, from 2016 through 2024. Year may capture secular changes in smoking patterns, population composition, clinical care, and data collection. It is a study-period adjustment variable, not a characteristic caused by an individual mother's smoking.

Return one **integer score from 0 to 10** for each field. A score of 0 means lowest relative priority for matching; 10 means highest relative priority. Scores are relative and do not need to sum to 1.

The `birth_year` field will be represented in the analysis by eight categorical contrasts for the nine calendar years. Give one field-level score for `birth_year`; the matching implementation will apply that score to each encoded year contrast in the primary field-to-column mapping.

Return a JSON object with exactly these eleven keys and numeric values. Do not include prose, comments, or additional keys.

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
  "birth_year": 0
}
```

---
