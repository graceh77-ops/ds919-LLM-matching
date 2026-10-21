# Covariate Review: 2024 Natality

This document holds the candidate list, field inventory, and provisional
causal screening for the study of maternal smoking during pregnancy and birth
weight. The roles below are working judgments, not CDC classifications or a
final adjustment set. Review them against the estimand before matching. 
Do not assign LLM weights until the primary set is settled.

Field positions refer to the 2024 fixed-width record. See
[`data_reference.md`](data_reference.md) for source and extraction details.

## Candidate variables

| Field | Position | What it measures | Timing and rationale | Provisional handling |
|---|---:|---|---|---|
| `MAGER` | 75-76 | Mother's age in years | Pre-pregnancy; may relate to smoking and birth weight | Primary candidate; review age coding and imputation |
| `MRACEHISP` | 117 | Mother's race/Hispanic-origin recode | Social-context measure; may proxy structural factors related to exposure and outcome | Primary candidate; do not interpret as a biological cause; code 8 is unknown/not stated |
| `DMAR` | 120 | Mother's marital status | Recorded for the birth; timing relative to pregnancy start is unclear | Candidate; timing and missingness review |
| `MEDUC` | 124 | Mother's education | Usually established before pregnancy; may relate to smoking and social conditions affecting birth weight | Primary candidate; code 9 is unknown |
| `CIG0_R` | 261 | Pre-pregnancy cigarette use recode | Prior behavior likely predicts smoking during pregnancy | Candidate baseline smoking history; keep distinct from treatment |
| `CIG_0` | 253-254 | Cigarettes smoked daily before pregnancy | More detail on prior smoking intensity | Alternative for sensitivity analysis; do not include with `CIG0_R` by default; 98 means 98+, 99 unknown/not stated |
| `F_CIGS_0` | 265 | Reporting flag for pre-pregnancy smoking | Data-quality indicator | Audit only; exclude from matching |
| `BMI`, `BMI_R` | 283-287 | Maternal BMI and category | Intended baseline body-size measure; BMI is derived | Choose continuous BMI or category, not both; review unknown codes |
| `PWgt_R` | 292-294 | Pre-pregnancy weight recode | Baseline body size; overlaps with BMI and height | Alternative body-size measure; 999 unknown/not stated |
| `M_Ht_In` | 280-281 | Mother's height in inches | Baseline body size; overlaps with BMI | Alternative; check reporting flag `F_M_HT` (282) |
| `PRIORLIVE`, `PRIORDEAD` | 171-174 | Prior births now living / dead | Pregnancy history before the current birth | Primary candidates; review unknown code 99 |
| `LBO_REC` | 179 | Live-birth order recode | Alternative summary of birth history | Choose instead of overlapping prior-birth counts unless justified |
| `RF_PDIAB` | 313 | Pre-pregnancy diabetes | Pre-pregnancy health | Candidate; check reporting and unknown values |
| `RF_PHYPE` | 315 | Pre-pregnancy hypertension | Pre-pregnancy health | Candidate; check reporting and unknown values |
| `RF_PPTERM` | 318 | Previous preterm birth | Prior pregnancy history | Candidate; check reporting and unknown values |
| `RF_CESAR` | 331 | Previous cesarean delivery | Prior pregnancy history | Candidate; check reporting and unknown values |
| `FAGECOMB`, `FRACEHISP`, `FEDUC` | 147-148, 162-163 | Father's age, race/Hispanic origin, and education | Family-context measures; often more missing | Optional candidates; assess missingness and added information; `F_FEDUC` (165) is a reporting flag |

## Keep out of the primary set pending timing review

These measures occur during pregnancy or at delivery and could be affected by
smoking, mediate its effect, or reflect care decisions.

| Field | Position | Measure | Provisional concern |
|---|---:|---|---|
| `PRECARE5` | 227 | Month prenatal care began, recoded | During pregnancy; timing unclear |
| `PREVIS_REC` | 242-243 | Prenatal visits, recoded | During pregnancy; may reflect care and pregnancy course |
| `WIC` | 251 | WIC participation | Timing and meaning before exposure need review |
| `PAY_REC` | 436 | Payment source for delivery | Recorded at delivery; proxy/timing concerns |
| `RF_GDIAB`, `RF_GHYPE` | 314, 316 | Gestational diabetes / hypertension | Possible post-treatment variables |
| `WTGAIN_REC` | 306 | Pregnancy weight gain recode | Possible post-treatment variable |
| `COMBGEST` / `GESTREC10` | 490-491 / varies | Gestational age | Possible mediator between smoking and birth weight |
| `DMETH_REC` | 408 | Delivery method recode | At delivery; may be affected by pregnancy complications |

## Prognostic or population variables to decide separately

| Field | Position | Measure | Review question |
|---|---:|---|---|
| `DPLURAL` | 454 | Plurality | Primary cohort is singleton births; consider all-births cohort as a sensitivity analysis |
| `SEX` | 475 | Infant sex | Strongly predicts birth weight, but is not automatically a confounder; decide whether to use in a secondary specification |

## Decisions to make before matching

- Mark each candidate as primary, sensitivity-only, or excluded, with a short
  rationale.
- Resolve overlapping representations: `BMI`/`BMI_R`/`PWgt_R`/`M_Ht_In`,
  and `LBO_REC` versus `PRIORLIVE` plus `PRIORDEAD`.
- Decide whether to include pre-pregnancy smoking history and family-context
  variables after checking their coding and missingness.
- Exclude reporting flags from matching; use them to interpret item reporting.
- Specify unknown-code and missing-data handling for the selected variables.
