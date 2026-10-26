# Full Data Quality Summary

## Input and output

- Input file: `data\processed\pooled_2016_2024\extracted_natality.csv`
- Primary analysis cohort (singleton births): `data\processed\pooled_2016_2024\analysis_cohort_singletons.csv`
- Sensitivity cohort (all eligible births): `data\processed\pooled_2016_2024\analysis_cohort_all_births.csv`
- Input rows: 33,589,282
- All-births eligible rows before covariate filtering: 33,409,947
- Singleton primary eligible rows before covariate filtering (`DPLURAL = 1`): 32,321,844
- Eligible non-singleton births excluded from primary cohort: 1,088,103
- All-births records meeting the flag-aware covariate rule: 31,958,803
- All-births records excluded for incomplete/unknown covariates or non-reporting flags: 1,451,144
- Singleton records meeting the flag-aware covariate rule: 30,924,495
- Singleton records excluded by the flag-aware covariate rule: 1,397,349
- Final all-births sensitivity file rows: 31,958,803
- Final singleton primary file rows: 30,924,495

## Treatment values in the input

- `N`: 31,726,001
- `U`: 151,570
- `Y`: 1,711,711

## Exclusions

- Unknown or invalid treatment only: 149,331
- Missing or invalid birth weight only: 27,765
- Both treatment and birth weight invalid or missing: 2,239
- `DBWT` equal to the missing code `9999`: 30,004
- `DBWT` outside 227-8,165 grams, blank, or non-integer: 0

## Analysis cohort

- `CIG_REC = Y` (treatment_binary = 1): 1,710,154
- `CIG_REC = N` (treatment_binary = 0): 31,699,793
- Flag-aware complete-case all-births `Y`: 1,643,356
- Flag-aware complete-case all-births `N`: 30,315,447
- Flag-aware complete-case all-births excluded `Y`: 66,798
- Flag-aware complete-case all-births excluded `N`: 1,384,346
- Flag-aware complete-case singleton `Y`: 1,590,168
- Flag-aware complete-case singleton `N`: 29,334,327
- Flag-aware complete-case singleton excluded `Y`: 64,284
- Flag-aware complete-case singleton excluded `N`: 1,333,065
- Final all-births eligible records by birth year and treatment:
- 2016: `CIG_REC = Y` 271,237; `CIG_REC = N` 3,472,092
- 2017: `CIG_REC = Y` 254,474; `CIG_REC = N` 3,423,468
- 2018: `CIG_REC = Y` 236,254; `CIG_REC = N` 3,388,178
- 2019: `CIG_REC = Y` 213,734; `CIG_REC = N` 3,362,867
- 2020: `CIG_REC = Y` 192,391; `CIG_REC = N` 3,272,890
- 2021: `CIG_REC = Y` 161,759; `CIG_REC = N` 3,344,478
- 2022: `CIG_REC = Y` 128,441; `CIG_REC = N` 3,371,209
- 2023: `CIG_REC = Y` 102,712; `CIG_REC = N` 3,321,037
- 2024: `CIG_REC = Y` 82,354; `CIG_REC = N` 3,359,228
- Birth weight unit: grams
- Valid birth weight minimum: 227
- Valid birth weight maximum: 8165

The analysis cohort files apply the flag-aware complete-case rule for all
primary covariates, including birth year in the supported 2016-2024 range.
Values must use recognized, non-unknown codes; reporting
flags `F_MHISP`, `F_MEDUC`, `F_CIGS_0`, `F_M_HT`, `F_RF_PDIAB`, and
`F_RF_PHYPER` must equal `1`. `F_PWGT` is retained as a source-data audit
field but is not an eligibility requirement because the selected covariate is
the valid `BMI_R` recode, not `PWgt_R`. CDC-imputed age, race, and sex values remain
eligible; their imputation flags are retained for audit. Gestational age is not
part of this primary eligibility rule.
