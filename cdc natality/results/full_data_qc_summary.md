# Full Data Quality Summary

> Historical 2024 QC generated under the previous eligibility rule, which
> required `F_PWGT = 1`. The current rule no longer requires `F_PWGT`; the
> counts below have not been regenerated and must not be presented as current
> eligible-cohort counts.

## Input and output

- Input file: `data\processed\2024\extracted_natality.csv`
- Primary analysis cohort (singleton births): `data\processed\2024\analysis_cohort_singletons.csv`
- Sensitivity cohort (all eligible births): `data\processed\2024\analysis_cohort_all_births.csv`
- Input rows: 3,638,436
- All-births eligible rows before covariate filtering: 3,617,844
- Singleton primary eligible rows before covariate filtering (`DPLURAL = 1`): 3,506,582
- Eligible non-singleton births excluded from primary cohort: 111,262
- All-births records meeting the flag-aware covariate rule: 3,441,582
- All-births records excluded for incomplete/unknown covariates or non-reporting flags: 176,262
- Singleton records meeting the flag-aware covariate rule: 3,336,235
- Singleton records excluded by the flag-aware covariate rule: 170,347
- Final all-births sensitivity file rows: 3,441,582
- Final singleton primary file rows: 3,336,235

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
- Flag-aware complete-case all-births `Y`: 82,354
- Flag-aware complete-case all-births `N`: 3,359,228
- Flag-aware complete-case all-births excluded `Y`: 4,221
- Flag-aware complete-case all-births excluded `N`: 172,041
- Flag-aware complete-case singleton `Y`: 79,378
- Flag-aware complete-case singleton `N`: 3,256,857
- Flag-aware complete-case singleton excluded `Y`: 4,048
- Flag-aware complete-case singleton excluded `N`: 166,299
- Birth weight unit: grams
- Valid birth weight minimum: 227
- Valid birth weight maximum: 8160

The analysis cohort files apply the flag-aware complete-case rule for all
primary covariates. Values must use recognized, non-unknown codes; reporting
flags `F_MHISP`, `F_MEDUC`, `F_CIGS_0`, `F_M_HT`, `F_PWGT`, `F_RF_PDIAB`, and
`F_RF_PHYPER` must equal `1`. CDC-imputed age, race, and sex values remain
eligible; their imputation flags are retained for audit. Gestational age is not
part of this primary eligibility rule.
