# Data Dictionary: 2024 Natality

Source: CDC User Guide to the 2024 Natality Public Use File
Guide: https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality/UserGuide2024.pdf

## Scope
This document currently defines the treatment and outcome variables.
Definitions and field positions for candidate covariates are documented in
[`covariate_inventory.md`](covariate_inventory.md) and
[`extraction_spec.md`](extraction_spec.md). The final analysis data
dictionary will be updated after the covariate set and recoding rules are
finalized.


| Role | Field | Record positions | Meaning and values |
|---|---|---:|---|
# Treatment Data: Cigarette Smoking
| Candidate treatment | CIG_1 | 255–256 | Cigarettes smoked daily in the 1st trimester. 00–97 = number daily; 98 = 98 or more; 99 = unknown or not stated. |
| Candidate treatment | CIG_2 | 257–258 | Cigarettes smoked daily in the 2nd trimester. Same value scheme as CIG_1. |
| Candidate treatment | CIG_3 | 259–260 | Cigarettes smoked daily in the 3rd trimester. Same value scheme as CIG_1. |
| Candidate treatment | CIG1_R | 262 | 1st-trimester recode: 0 = nonsmoker; 1–5 = smoking categories; 6 = unknown or not stated. |
| Candidate treatment | CIG2_R | 263 | 2nd-trimester recode. Same category scheme as CIG1_R. |
| Candidate treatment | CIG3_R | 264 | 3rd-trimester recode. Same category scheme as CIG1_R. |
| Candidate treatment | CIG_REC | 269 | Cigarette recode: Y = yes; N = no; U = unknown or not stated. |
| Reporting flag | F_CIGS_1 | 266 | Whether 1st-trimester smoking is reported: 0 = non-reporting; 1 = reporting. |
| Reporting flag | F_CIGS_2 | 267 | Whether 2nd-trimester smoking is reported: 0 = non-reporting; 1 = reporting. |
| Reporting flag | F_CIGS_3 | 268 | Whether 3rd-trimester smoking is reported: 0 = non-reporting; 1 = reporting. |
| Reporting flag | F_TOBACO | 270 | Reporting flag for tobacco use: 0 = non-reporting; 1 = reporting. |

# Outcome Data: Birth weight
| Outcome | DBWT | 504–507 | Edited birth weight in grams: 0227–8165 = grams; 9999 = not stated. |
| Outcome | BWTR12 | 509-510 | Birth Weight Recode 12 categories: 01 = 0227-0499 grams; 02 = 0500-0999 grams; 03 = 1000-1499 grams; 04 = 1500-1999 grams; 05 = 2000-2499 grams; 06 = 2500-2999 grams; 07 = 3000-3499 grams; 08 = 3500-3999 grams; 09 = 4000-4499 grams; 10 = 4500-4999 grams; 11 = 5000-8165 grams; 12 = Not Stated. |
| Outcome | BWTR4 | Birth Weight Recode 4 categories: 1 = 0227-1499 grams; 2 = 1500-2499 grams; 3 = 2500-8165 grams; 4 = Unknown or not stated. |

## Provisional definitions

- Treatment: maternal smoking during any trimester; exact coding rule is not finalized.
- Outcome: birth weight in grams.
- Unknown, not stated, and non-reporting values must be handled explicitly.
- Covariates: TBD.
- Study population and estimand: TBD.
