# Data Reference: 2024 Natality

## Source and local files

- Dataset: 2024 CDC/NCHS Natality Public Use File, U.S. data.
- Source: [User Guide to the 2024 Natality Public Use File](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality/UserGuide2024.pdf).
- Download date: 2026-10-20.
- Raw fixed-width file: `Nat2024PublicUS.c20250512.r20250708.txt`, stored under
  `data/raw/2024/Nat2024us/` and excluded from Git.
- The raw file contains 3,638,436 records. Every inspected record was 1,345
  characters; the User Guide lists 1,330 characters. The file was not edited.
- Initial raw-file inspection is documented in `src/inspect_natality.py`.

## Record and extraction conventions

- Positions below are 1-based and inclusive, following the User Guide.
- `src/total_extraction.py` extracts the listed fields from the fixed-width
  records into `data/processed/2024/extracted_natality.csv`.
- Initial extraction preserves values as strings and does not recode blanks,
  unknown values, or not-stated values.
- Reporting flags are retained for data-quality review and are not matching
  covariates.

## Extracted field map

| Field | Position | Analysis role / coding note |
|---|---:|---|
| `MAGER` | 75-76 | Mother's age in single years; review imputation/unknown values |
| `MRACEHISP` | 117 | Mother's race/Hispanic-origin recode; 8 unknown/not stated |
| `DMAR` | 120 | Mother's marital status |
| `MEDUC` | 124 | Mother's education; 9 unknown |
| `PRIORLIVE` | 171-172 | Prior births now living; 99 unknown/not stated |
| `PRIORDEAD` | 173-174 | Prior births now dead; 99 unknown/not stated |
| `CIG_0` | 253-254 | Cigarettes/day before pregnancy; 98 means 98+, 99 unknown/not stated |
| `CIG0_R` | 261 | Pre-pregnancy smoking recode; 0 nonsmoker, 1-5 categories, 6 unknown/not stated |
| `CIG1_R` | 262 | First-trimester smoking recode; 0-5 categories, 6 unknown/not stated |
| `CIG2_R` | 263 | Second-trimester smoking recode; same scheme as `CIG1_R` |
| `CIG3_R` | 264 | Third-trimester smoking recode; same scheme as `CIG1_R` |
| `F_CIGS_0` | 265 | Reporting flag for pre-pregnancy smoking |
| `F_CIGS_1` | 266 | Reporting flag for first-trimester smoking |
| `F_CIGS_2` | 267 | Reporting flag for second-trimester smoking |
| `F_CIGS_3` | 268 | Reporting flag for third-trimester smoking |
| `CIG_REC` | 269 | Pregnancy smoking recode: Y yes, N no, U unknown/not stated |
| `BMI_R` | 287 | Maternal BMI category; 9 unknown/not stated |
| `PWgt_R` | 292-294 | Pre-pregnancy weight recode; 999 unknown/not stated |
| `F_PWGT` | 295 | Reporting flag for pre-pregnancy weight |
| `DPLURAL` | 454 | Plurality: 1 single, 2 twin, 3 triplet, 4 quadruplet or higher |
| `DBWT` | 504-507 | Edited birth weight in grams; 9999 not stated; User Guide range 227-8165 |
| `BWTR12` | 509-510 | Birth-weight recode, 12 categories; 12 not stated |
| `BWTR4` | 511 | Birth-weight recode, 4 categories; 4 unknown/not stated |

## Treatment and outcome definitions

- Primary treatment: `CIG_REC`; `Y` is treated, `N` is comparison, and `U` is
  unknown and excluded. Trimester-specific smoking recodes are retained to
  describe and audit the classification.
- Primary outcome: `DBWT`, birth weight in grams. Exclude 9999 and unavailable
  or invalid values. `BWTR12` and `BWTR4` are categorical alternatives, not
  matching covariates.
- The current cohort definitions and QC counts are in
  [`analysis_protocol.md`](analysis_protocol.md) and
  [`../../results/full_data_qc_summary.md`](../../results/full_data_qc_summary.md).

