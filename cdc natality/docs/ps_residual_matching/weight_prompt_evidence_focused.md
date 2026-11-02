# Evidence-focused prompt for PS-residual matching weights

This is an alternative, outcome-blind prompt for a separate DeepSeek elicitation.
It adapts the evidence-focused framing of the referenced Lasso prompt while
keeping the score direction compatible with the matching implementation:
higher values give a coordinate more influence in the distance. The API script
accepts this file through `--prompt`; use `--schema ps-residual`.

Copy only the text between the delimiters into a separate, isolated LLM session
or pass this file to the DeepSeek extraction script.

---

We are studying births in the CDC Natality data from 2016 through 2024. The
treatment is maternal smoking during pregnancy (`CIG_REC = Y`); the comparison
group is births with `CIG_REC = N`. The outcome is infant birth weight in grams
(`DBWT`).

Assign each field a matching-priority weight from 0 to 10 based only on the
definitions and study context below. A higher value gives that field more
influence in matching. Give higher priority to pre-treatment factors with a
strong rationale for being related to both maternal smoking and birth weight.
Strong prognostic relevance to birth weight alone is not sufficient to justify
a high confounding-control priority. Use established evidence or a strong
causal rationale; do not speculate. Do not assume every field is equally
important. Give lower scores where the rationale for controlling confounding
is weak, and reserve the highest scores for fields with the strongest rationale.
Scores are relative and need not sum to any value.

Fields:

- `MAGER`: Mother's age in years; a pre-pregnancy characteristic.
- `MRACEHISP`: Mother's race and Hispanic-origin recode; a social-context
  measure that may relate to exposure and outcome through structural and social
  factors, not a biological cause.
- `MEDUC`: Mother's education; generally established before pregnancy.
- `CIG0_R`: Mother's cigarette-use category before pregnancy; prior smoking
  behavior.
- `PRIORLIVE`: Number of the mother's previous live births now living; prior
  pregnancy history.
- `PRIORDEAD`: Number of the mother's previous live births now dead; prior
  pregnancy history.
- `BMI_R`: Mother's recoded pre-pregnancy body mass index category; a baseline
  health characteristic.
- `RF_PDIAB`: Whether the mother had pre-pregnancy diabetes; a baseline health
  characteristic.
- `RF_PHYPE`: Whether the mother had pre-pregnancy hypertension; a baseline
  health characteristic.
- `SEX`: Infant sex; may strongly predict birth weight but is not an established
  cause of maternal smoking during pregnancy.
- `birth_year`: Calendar year of birth, 2016 through 2024; captures changes in
  population composition and measurement over time.
- `PROPENSITY_SCORE`: Estimated probability that a birth is in the maternal-
  smoking treatment group, conditional on the prespecified encoded
  covariates. This is a derived matching coordinate, not a source covariate.

Return one integer weight from 0 to 10 for each of the twelve fields. A score
of 0 means lowest relative matching priority; 10 means highest. Do not use
empirical outcome results, matching results, prior weight sets, or information
outside this prompt.

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
