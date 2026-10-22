# Covariate Review: 2024 Natality

This document holds the candidate list, field inventory, and causal
screening for the study of maternal smoking during pregnancy and birth weight.
The selected primary set is recorded below; unknown-code and missing-data
handling remain to be specified. Variable roles are study judgments, not CDC
classifications.

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
| `RF_PDIAB` | 313 | Pre-pregnancy diabetes | Pre-pregnancy health | Primary candidate; Y/N/U coding; check reporting flag |
| `RF_PHYPE` | 315 | Pre-pregnancy hypertension | Pre-pregnancy health | Primary candidate; Y/N/U coding; check reporting flag |
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
| `COMBGEST` / `GESTREC10` | 490-491 / 492-493 | Gestational age | Possible mediator between smoking and birth weight |
| `DMETH_REC` | 408 | Delivery method recode | At delivery; may be affected by pregnancy complications |

## Population variable to handle separately

| Field | Position | Measure | Review question |
|---|---:|---|---|
| `DPLURAL` | 454 | Plurality | Primary cohort is singleton births; consider all-births cohort as a sensitivity analysis |

## Agreed primary set and planned sensitivity variables

The primary set below reflects the current study decision.

| Proposed role | Fields | Rationale / handling |
|---|---|---|
| Primary set | `MAGER`, `MRACEHISP`, `MEDUC` | Maternal age and social-context measures may relate to both smoking and birth weight. Treat race/Hispanic-origin as social context, not biology. |
| Primary set | `CIG0_R` | Pre-pregnancy smoking is a strong baseline predictor of smoking during pregnancy and may affect birthweight of child; CDC categories are 0 (nonsmoker), 1-5 (intensity groups), and 6 (unknown/not stated). |
| Primary set | `PRIORLIVE`, `PRIORDEAD` | Prior birth history precedes the index birth and may relate to both smoking patterns and birth outcomes. |
| Primary set | `BMI_R` | CDC's BMI measure represents pre-pregnancy BMI; use the recoded form available in this extract. Do not include `PWgt_R` alongside it in the primary set. |
| Primary set | `RF_PDIAB`, `RF_PHYPE` | Pre-pregnancy diabetes and hypertension are baseline health characteristics; use reporting flags for data-quality review, not as matching variables. |
| Primary prognostic covariate | `SEX` | Include infant sex to balance this strong birth-weight predictor; treat it as prognostic, not an established confounder. |
| Sensitivity alternative | `CIG_0` instead of `CIG0_R` | Compare the more detailed daily count with the recode; do not enter both together. |
| Sensitivity alternative | `PWgt_R` instead of `BMI_R` | Compare pre-pregnancy weight with BMI; do not enter both together by default. |
| Sensitivity addition | `DMAR` | Add only as a sensitivity check because it is recorded at birth and may not represent marital status before pregnancy. |
| Sensitivity only | `COMBGEST` | Add gestational length in a separately labeled sensitivity analysis because it may mediate part of smoking's effect on birth weight. Conditioning on this possible mediator changes the estimand; do not call the result a direct effect without additional mediation assumptions. Retain imputation/source flags for review. `GESTREC10` is available as a coarser alternative. |
| All-births sensitivity | `DPLURAL` | The primary cohort is all singletons, so plurality is constant there. Consider plurality in the all-births sensitivity analysis; it is not part of the singleton primary set. |

### Other candidates not currently included

`RF_PPTERM` and `RF_CESAR` are plausible prior-pregnancy history measures but
are not included in the current extraction. They can be revisited after the
first covariate missingness and balance summaries.

Gestational length is not a baseline confounder for this question. Its
sensitivity-only role is intentional because it may lie on the pathway from
pregnancy smoking to birth weight. Retain the imputation and source flags to
describe how the gestational estimate was constructed.

## Covariate handling decisions and remaining questions

- Keep the primary representation choices explicit: `CIG0_R` over `CIG_0`,
  `BMI_R` over `PWgt_R` or `M_Ht_In`, and `PRIORLIVE` plus `PRIORDEAD` instead
  of `LBO_REC`.
- For matching, treat `MEDUC` as a categorical variable grouped into four
  levels: codes `1-2`, `3-4`, `5-6`, and `7-8`. Do not encode these groups as
  numeric scores in the primary representation.
- Use `CIG0_R` as a categorical pre-pregnancy smoking measure. Keep code `0`
  as nonsmoker; group codes `1-2` as light smoking (1-10 cigarettes/day), code
  `3` as moderate smoking (11-20 cigarettes/day), and codes `4-5` as heavy
  smoking (21+ cigarettes/day). Do not treat the grouped categories as equally
  spaced numeric values.
- Recommended first-pass matching representation and scaling:
  - Treat `MRACEHISP`, grouped `MEDUC`, grouped `CIG0_R`, and `BMI_R` as
    categorical blocks, not numeric scores. Encode `RF_PDIAB`, `RF_PHYPE`, and
    `SEX` as binary indicators.
  - Treat `MAGER`, `PRIORLIVE`, and `PRIORDEAD` as numeric in the first pass.
    Center and divide by the standard deviation calculated from the 99%
    reference portion of each split; apply those same values to the 1% test
    portion. Keep prior-birth counts on their original count scale initially;
    consider a nonlinear or grouped version only as a documented sensitivity
    if diagnostics show the linear count distance is unsuitable.
  - Use full-rank orthonormal Helmert contrasts with `k-1` columns for each
    categorical field. Use the fixed recognized category levels for every
    split. The 7-level `MRACEHISP`, four-level grouped `MEDUC`, four-level
    grouped `CIG0_R`, and six-level `BMI_R` produce 6, 3, 3, and 5 columns,
    respectively. Encode binary `RF_PDIAB`, `RF_PHYPE`, and `SEX` as one
    contrast column each. Together with one column each for standardized
    `MAGER`, `PRIORLIVE`, and `PRIORDEAD`, the design has 23 encoded columns.
  - For the full-covariance generalized Mahalanobis distance, estimate the
    covariance matrix `S` from the 99% reference portion after applying the
    fixed encoding and preprocessing. Use the same `S` and preprocessing for
    every method in that split, including the 1% test portion. Standardize
    numeric fields using reference-sample means and standard deviations; center
    categorical contrasts using reference-sample means. Do not standardize
    categorical contrast columns separately.
  - Ask the LLM for one nonnegative weight per original field and rescale those
    10 weights to have mean 1. Construct diagonal `V` by repeating each field's
    weight across all encoded columns derived from that field. Thus, the
    equal-weight reference uses `V = I` in the 23-column encoded design, while
    the LLM method uses the repeated field weights. This primary allocation
    follows the full-covariance formula; fields encoded with more columns may
    consequently have more effective influence.
  - As a weight-allocation sensitivity analysis, divide each field's weight by
    the number of encoded columns in its block before filling the corresponding
    diagonal entries of `V`. Keep the encoding, preprocessing, and `S` fixed
    between the primary and sensitivity allocations. Check `S` for numerical
    singularity; if regularization is needed, prespecify it and apply the same
    rule to all methods within each split. All transformations and covariance
    estimation are outcome-blind.
- Decide whether to add `DMAR` or other optional candidates in a sensitivity
  analysis after reviewing timing and missingness.
- Exclude reporting flags from matching; use them to interpret item reporting.
- Missing-data rule selected: use flag-aware complete cases for both singleton
  primary and all-births sensitivity cohorts. Require recognized values for
  all primary covariates and reporting flags `F_MHISP`, `F_MEDUC`, `F_CIGS_0`,
  `F_M_HT`, `F_PWGT`, `F_RF_PDIAB`, and `F_RF_PHYPER` equal to `1`. Retain
  CDC-imputed age, race, and sex values and report their imputation flags.
