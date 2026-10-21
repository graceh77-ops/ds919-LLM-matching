# Full Data Quality Summary

## Input and output

- Input file: `data\processed\2024\extracted_natality.csv`
- Primary analysis cohort (singleton births): `data\processed\2024\analysis_cohort_singletons.csv`
- Sensitivity cohort (all eligible births): `data\processed\2024\analysis_cohort_all_births.csv`
- Input rows: 3,638,436
- All-births cohort rows: 3,617,844
- Singleton primary cohort rows (`DPLURAL = 1`): 3,506,582
- Eligible non-singleton births excluded from primary cohort: 111,262

## Treatment values in the input

- `N`: 3,534,051
- `U`: 17,729
- `Y`: 86,656

## Exclusions

- Unknown or invalid treatment only: 17,486
- Missing or invalid birth weight only: 2,863
- Both treatment and birth weight invalid or missing: 243
- `DBWT` equal to the missing code `9999`: 3,106
- Blank or non-integer `DBWT`: 0

## Analysis cohort

- `CIG_REC = Y` (treatment_binary = 1): 86,575
- `CIG_REC = N` (treatment_binary = 0): 3,531,269
- Birth weight unit: grams
- Valid birth weight minimum: 227
- Valid birth weight maximum: 8160

Covariate values were retained as extracted. No complete-case filtering or
covariate recoding was performed in this step.
