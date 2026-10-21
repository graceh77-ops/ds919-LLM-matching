# Targeted Covariate Inventory: 2024 Natality

## Purpose

This is a targeted inventory of 2024 Natality fields that may be relevant
to the study of maternal smoking during pregnancy and birth weight.

It records what the User Guide says about the fields. It does not establish
that a field is a confounder or should be used in matching.

## Source

CDC/NCHS, User Guide to the 2024 Natality Public Use File  
https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality/UserGuide2024.pdf

Record positions below refer to positions in the 2024 fixed-width record.
Positions and coding may differ in other years.

## Maternal and family characteristics

| Field | Position | What it measures | Timing or review note |
|---|---:|---|---|
| MAGER | 75–76 | Mother's age in years | Baseline candidate; check age grouping and imputation |
| MRACEHISP | 117 | Mother's race/Hispanic-origin recode | Social-context measure; do not treat as a biological cause |
| DMAR | 120 | Mother's marital status | Recorded for the birth; timing before pregnancy is unclear |
| MAR_IMP | 121 | Marital-status imputation flag | Data-quality check, not a covariate by itself |
| MEDUC | 124 | Mother's education | Candidate; inspect unknown values |
| F_MEDUC | 126 | Reporting flag for mother's education | Use to check whether the item was reported |
| FAGECOMB | 147–148 | Father's age | Family-context candidate; check missingness |
| FRACEHISP | 162 | Father's race/Hispanic-origin recode | Family-context candidate; check missingness |
| FEDUC | 163 | Father's education | Family-context candidate; check reporting flag |
| F_FEDUC | 165 | Reporting flag for father's education | Use to check whether the item was reported |

## Prior smoking, body size, and pregnancy history

| Field | Position | What it measures | Timing or review note |
|---|---:|---|---|
| CIG0_R | 261 | Cigarette use before pregnancy, recoded | Prior behavior; keep separate from the treatment |
| F_CIGS_0 | 265 | Reporting flag for cigarettes before pregnancy | Check before interpreting blank or missing values |
| M_Ht_In | 280–281 | Mother's height in inches | Candidate; overlaps with BMI-related information |
| F_M_HT | 282 | Reporting flag for mother's height | Data-quality check |
| BMI | 283–286 | Mother's body mass index | Candidate; review how it is derived |
| BMI_R | 287 | Body-mass-index category | Alternative representation to BMI; do not include both by default |
| PWgt_R | 292–294 | Mother's pre-pregnancy weight recode | Overlaps with BMI and height |
| F_PWGT | 295 | Reporting flag for pre-pregnancy weight | Data-quality check |
| PRIORLIVE | 171–172 | Previous live births now living | Prior pregnancy history |
| PRIORDEAD | 173–174 | Previous live births now dead | Prior pregnancy history |
| LBO_REC | 179 | Live-birth-order recode | Alternative summary of birth history; overlaps with prior-birth counts |
| RF_PDIAB | 313 | Pre-pregnancy diabetes | Pre-pregnancy health candidate |
| RF_PHYPE | 315 | Pre-pregnancy hypertension | Pre-pregnancy health candidate |
| RF_PPTERM | 318 | Previous preterm birth | Prior pregnancy history |
| RF_CESAR | 331 | Previous cesarean delivery | Prior pregnancy history |

## Pregnancy-course fields to review separately

These fields are measured during pregnancy or at delivery. They may be affected by treatment or may lie on a pathway from smoking to birth weight.

| Field | Position | What it measures | Initial handling |
|---|---:|---|---|
| PRECARE5 | 227 | Month prenatal care began, recoded | Review separately; measured during pregnancy |
| PREVIS_REC | 242–243 | Number of prenatal visits, recoded | Review separately; measured during pregnancy |
| WIC | 251 | WIC participation | Review timing and meaning before using |
| RF_GDIAB | 314 | Gestational diabetes | Possible post-treatment variable |
| RF_GHYPE | 316 | Gestational hypertension | Possible post-treatment variable |
| COMBGEST | 490–491 | Combined gestational age in weeks | Possible mediator for birth weight |
| WTGAIN_REC | 306 | Weight gain during pregnancy, recoded | Possible post-treatment variable |
| DMETH_REC | 408 | Delivery method recode | Measured at delivery; do not use as a default baseline covariate |
| PAY_REC | 436 | Payment source for delivery, recoded | Measured at delivery; review timing and proxy role |

## Birth and infant fields

| Field | Position | What it measures | Initial role |
|---|---:|---|---|
| DPLURAL | 454 | Single, twin, triplet, or higher-order birth | Candidate; strong birth-weight predictor |
| SEX | 475 | Infant sex | Outcome-prediction candidate; not automatically a confounder |
| DBWT | 504–507 | Edited birth weight in grams | Outcome, not a covariate |

## Treatment and outcome cross-reference

The treatment fields are documented in `data_dictionary.md`:

- `CIG_1`, `CIG_2`, `CIG_3`: cigarettes smoked daily in each trimester
- `CIG1_R`, `CIG2_R`, `CIG3_R`: trimester-specific recodes
- `CIG_REC`: cigarette recode
- `F_CIGS_1`, `F_CIGS_2`, `F_CIGS_3`, `F_TOBACO`: reporting flags

The outcome is `DBWT`, birth weight in grams.

## Data-quality notes

- Check each field's reporting flag where one is provided.
- Do not treat unknown or not-stated codes as ordinary numeric values.
- The User Guide notes that blank values can indicate that an item was not on the certificate in a non-reporting area.
- Keep this inventory separate from the final candidate covariate set.
- Do not assign numeric LLM weights until the candidate set and causal roles have been reviewed.