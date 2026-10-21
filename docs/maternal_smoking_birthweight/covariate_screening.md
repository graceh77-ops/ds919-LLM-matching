# Covariate Screening

## Purpose

This document screens variables listed in
[`covariate_inventory.md`](covariate_inventory.md)
for their possible roles in estimating the effect of maternal smoking
during pregnancy on birth weight.

These classifications are provisional. They must be reviewed against
the study's causal diagram and variable timing before analysis.

## Provisional screening

| Variable | Timing | Possible relation to treatment | Possible relation to outcome | Provisional role | Decision |
|---|---|---|---|---|---|
| `MAGER` | Before pregnancy | May be related to smoking during pregnancy | May be related to birth weight | Potential confounder | Primary candidate |
| `MRACEHISP` | Before pregnancy | May reflect social and structural factors related to smoking | May reflect factors related to birth weight | Potential confounder or proxy | Primary candidate; interpret cautiously |
| `MEDUC` | Usually established before pregnancy | May be related to smoking | May be related to birth weight through social conditions | Potential confounder or proxy | Primary candidate |
| `DMAR` | At birth; timing may not match pregnancy start | May be related to smoking and social conditions | May be related to birth weight through social conditions | Potential confounder or proxy | Candidate; check timing and missingness |
| `PRIORLIVE`, `PRIORDEAD` | Before current birth | May relate to smoking patterns and pregnancy history | May relate to birth weight through maternal and pregnancy history | Potential confounder or prognostic variable | Primary candidates |
| `BMI`, `PWgt_R` | Intended to represent pre-pregnancy body size | May relate to smoking | May relate to birth weight | Potential confounder | Candidate; verify definition and missingness |
| `PRECARE`, `PREVIS` | During pregnancy | Timing relative to smoking exposure is unclear | May relate to birth outcomes | Possible post-treatment variable | Keep out of primary set until timing is clarified |
| `WIC`, `PAY_REC` | During pregnancy or at delivery | May be related to smoking and social conditions; timing may be unclear | May be related to birth weight through access to resources | Possible proxy or post-treatment variable | Sensitivity analysis candidate |
| `RF_GDIAB`, `RF_GHYPE`, `WTGAIN_REC` | During pregnancy | Could occur after smoking exposure begins | May affect birth weight | Possible mediator or post-treatment variable | Exclude from primary set for now |
| `COMBGEST` | Measured at birth | Smoking may affect gestational duration | Gestational duration affects birth weight | Possible mediator | Exclude from primary set |
| `DMETH_REC` | At delivery | Could be affected by pregnancy complications | May be related to birth outcomes | Post-treatment variable | Exclude from primary set |
| `SEX`, `DPLURAL` | Recorded at birth; established earlier in pregnancy | Relation to smoking needs review | Related to expected birth weight | Prognostic variables; causal role needs review | Consider in a secondary specification |

## Questions to resolve

- Which variables plausibly precede the smoking exposure?
- Which variables could be affected by smoking during pregnancy?
- Which variables could be common causes of smoking and birth weight?
- Which variables are included in the primary matching set, sensitivity set, or excluded?
- What is the reason for each decision?
