# Candidate Covariates: 2024 Natality

Source: CDC User Guide to the 2024 Natality Public Use File

These are candidates for review, not a finalized adjustment set.
The timing and causal role of each variable must be reviewed before matching.

## Candidate pool

| Variable | Initial role | Rationale | Caution |
|---|---|---|---|
| MAGER | Baseline candidate | Mother's age | Check age coding and imputation |
| MRACEHISP | Baseline social-context candidate | Mother's race and Hispanic origin | Treat as a social-context measure, not a biological cause |
| MEDUC | Baseline candidate | Mother's education | Categories; unknown values need handling |
| DMAR | Timing unclear | Mother's marital status | Recorded for the birth; may not reflect status before pregnancy |
| CIG0_R | Pre-pregnancy history | Cigarette use before pregnancy may relate to smoking during pregnancy | Keep distinct from the treatment definition |
| `CIG_0` | Alternative measure of baseline smoking history | Preserves more detail about pre-pregnancy smoking intensity | Retain for data checks and sensitivity analysis; do not include together with `CIG0_R` in the primary set |
| `F_CIGS_0` | Data-quality field | Indicates whether pre-pregnancy smoking was reported | Use to review reporting; exclude from matching |
| BMI or BMI_R | Baseline candidate | Mother's body mass index | Choose continuous or recoded form, not both |
| PWgt_R | Baseline candidate | Mother's pre-pregnancy weight | Overlaps with BMI and height |
| M_Ht_In | Baseline candidate | Mother's height | Overlaps with BMI |
| LBO_REC | Baseline history | Live-birth order | Overlaps with prior-birth variables |
| PRIORLIVE | Baseline history | Previous live births now living | Overlaps with live-birth order |
| PRIORDEAD | Baseline history | Previous live births now dead | Overlaps with live-birth order |
| RF_PDIAB | Pre-pregnancy health candidate | Pre-pregnancy diabetes | Check reporting flag and unknown values |
| RF_PHYPE | Pre-pregnancy health candidate | Pre-pregnancy hypertension | Check reporting flag and unknown values |
| RF_PPTERM | Prior pregnancy history | Previous preterm birth | Check reporting flag and unknown values |
| RF_CESAR | Prior pregnancy history | Previous cesarean delivery | Check reporting flag and unknown values |
| DPLURAL | Pregnancy characteristic | Single or multiple birth; strong birth-weight predictor | Confirm the intended study population |
| SEX | Outcome-prediction candidate | Infant sex predicts birth weight | Likely prognostic; not automatically a confounder |
| FAGECOMB | Family-context candidate | Father's age | Often missing; assess missingness first |
| FEDUC | Family-context candidate | Father's education | Check reporting flag and missingness |
| FRACEHISP | Family-context candidate | Father's race and Hispanic origin | Check missingness and whether it adds information |

## Hold out of the primary candidate set for now

These variables are recorded during or after pregnancy. They may be mediators, consequences of treatment, or variables affected by care decisions.

- PRECARE5: timing of prenatal care
- PREVIS_REC: number of prenatal visits
- WIC: WIC participation
- RF_GDIAB: gestational diabetes
- RF_GHYPE: gestational hypertension
- COMBGEST or GESTREC10: gestational age
- WTGAIN_REC: weight gain during pregnancy
- DMETH_REC: delivery method
- PAY_REC: payment source for delivery

## Notes

- This list is a candidate pool, not a recommendation to adjust for every variable.
- Do not include overlapping representations together without a reason. Examples: BMI with pre-pregnancy weight and height; live-birth order with both prior-birth counts.
- The timing categories are provisional causal judgments, not CDC classifications.
- Assign numeric LLM weights only after reviewing the causal roles and the study estimand.