# Extraction Specification

## Source and format

- Dataset: 2024 CDC Natality Public Use File, U.S. data
- Source document: User Guide to the 2024 Natality Public Use File
- Record format: Fixed-width text
- Expected record length: 1,345 characters
- Position convention: 1-based and inclusive, following the User Guide
- Extraction rule: Preserve field values as raw strings in the initial extract.
- Missing-value rule: Do not recode unknown, not-stated, or blank values at this stage.

## Field map

| Field | Position | Width | Description | Analysis role | Notes |
|---|---:|---:|---|---|---|
| `MAGER` | 75–76 | 2 | Mother's age in single years | Potential baseline covariate | Review unknown and imputed-age information |
| `MRACEHISP` | 117 | 1 | Mother's race and Hispanic-origin recode | Potential baseline covariate or proxy | Code `8` means origin unknown or not stated |
| `DMAR` | 120 | 1 | Mother's marital status | Sensitivity candidate | Timing may not represent status before smoking exposure |
| `MEDUC` | 124 | 1 | Mother's education | Potential baseline covariate | Code `9` means unknown |
| `PRIORLIVE` | 171–172 | 2 | Prior births now living | Potential baseline covariate | Code `99` means unknown or not stated |
| `PRIORDEAD` | 173–174 | 2 | Prior births now dead | Potential baseline covariate | Code `99` means unknown or not stated |
| `CIG1_R` | 262 | 1 | Cigarettes in first trimester, recoded | Treatment audit field | Codes `0`–`5`; `6` means unknown or not stated |
| `CIG2_R` | 263 | 1 | Cigarettes in second trimester, recoded | Treatment audit field | Codes `0`–`5`; `6` means unknown or not stated |
| `CIG3_R` | 264 | 1 | Cigarettes in third trimester, recoded | Treatment audit field | Codes `0`–`5`; `6` means unknown or not stated |
| `F_CIGS_1` | 266 | 1 | Reporting flag for first-trimester smoking | Data-quality audit field | `0` non-reporting; `1` reporting |
| `F_CIGS_2` | 267 | 1 | Reporting flag for second-trimester smoking | Data-quality audit field | `0` non-reporting; `1` reporting |
| `F_CIGS_3` | 268 | 1 | Reporting flag for third-trimester smoking | Data-quality audit field | `0` non-reporting; `1` reporting |
| `CIG_REC` | 269 | 1 | Cigarette-smoking recode | Primary treatment field | `Y` yes; `N` no; `U` unknown or not stated |
| `BMI_R` | 287 | 1 | Maternal BMI recode | Potential baseline covariate | Code `9` means unknown or not stated |
| `PWgt_R` | 292–294 | 3 | Pre-pregnancy weight recode | Potential baseline covariate | Code `999` means unknown or not stated |
| `F_PWGT` | 295 | 1 | Reporting flag for pre-pregnancy weight | Data-quality audit field | `0` non-reporting; `1` reporting |
| `DPLURAL` | 454 | 1 | Plurality recode | Eligibility and sample-description field | `1` single; `2` twin; `3` triplet; `4` quadruplet or higher |
| `DBWT` | 504–507 | 4 | Birth weight in grams | Primary continuous outcome candidate | `9999` means not stated |
| `BWTR12` | 509–510 | 2 | Birth-weight recode with 12 categories | Categorical outcome candidate | Code `12` means not stated |
| `BWTR4` | 511 | 1 | Birth-weight recode with 4 categories | Categorical outcome candidate | Code `4` means unknown or not stated |

## Initial extraction plan

- Extract all fields in the field map for the first 1,000 records.
- Keep all extracted values as strings.
- Do not include reporting flags as matching covariates.
- Use `CIG_REC` as the primary treatment field for initial data checks.
- Retain `CIG1_R`, `CIG2_R`, and `CIG3_R` to audit the treatment classification.
- Retain `DBWT`, `BWTR12`, and `BWTR4` so the continuous and categorical outcome options can be reviewed.
- Treat the covariate roles as provisional until the causal diagram and analysis protocol are finalized.