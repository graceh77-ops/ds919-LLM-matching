# ACIC 2016 Field Dictionary for Weight Elicitation

The ACIC 2016 package documents 58 de-identified fields from the
Collaborative Perinatal Project (CPP). **The package manual does not publish an
explicit one-to-one crosswalk from each `x_i` to an original CPP name.** The
table below provisionally pairs `x_i` with the `i`th name in the manual's
ordered original-variable list. Several positions are independently
corroborated by an ACIC challenge description (including `x_1` mother's age,
`x_3` cigarettes per day, `x_10` endocrine conditions, `x_14` neurological
conditions, `x_15` obstetric complications, `x_21` birthplace, `x_24` race,
and `x_43` child bilirubin), but this does not verify every mapping. Treat
other row-level labels as provisional pending confirmation from the original
data construction code or an explicit crosswalk.

See the [covariate mapping evidence audit](../covariate_mapping_evidence.md)
for field-by-field plausibility checks, type/range caveats, and the distinction
between independently corroborated anchors and order-inferred labels.

The ACIC file uses `x_1` through `x_58`; the three categorical fields are
`x_2`, `x_21`, and `x_24`. The five fields observed as 0/1 in this shared
covariate file are `x_17`, `x_22`, `x_38`, `x_51`, and `x_54`.

The source documentation describes the data as de-identified variables
representing possible confounders, instruments, and uncorrelated variables in
a hypothetical twin study of birthweight and IQ. It does not identify which
fields are confounders or instruments, provide category labels for A/B/etc.,
or provide complete units and code meanings for every field. The descriptions
below therefore expand the source names without claiming undocumented causal
roles or code values.

| ACIC field | Original CPP field | Type in the shared file | Plain-language description |
|---|---|---|---|
| `x_1` | `mom_age` | Numeric | Mother's age |
| `x_2` | `mar_status` | Categorical, A-F | Mother's marital status; category labels are not supplied |
| `x_3` | `mom_cigs_per_day` | Numeric | Mother's cigarettes smoked per day |
| `x_4` | `mom_years_smoked` | Numeric | Mother's years of smoking |
| `x_5` | `mom_height` | Numeric | Mother's height |
| `x_6` | `mom_weight_prior` | Numeric | Mother's weight before the pregnancy |
| `x_7` | `mom_num_cardio_cond` | Numeric | Count of mother's cardiovascular conditions |
| `x_8` | `mom_num_pulm_cond` | Numeric | Count of mother's pulmonary conditions |
| `x_9` | `mom_num_hema_cond` | Numeric | Count of mother's hematological conditions |
| `x_10` | `mom_num_endocrine_cond` | Numeric | Count of mother's endocrine conditions |
| `x_11` | `mom_num_veneral_cond` | Numeric | Count of mother's venereal conditions |
| `x_12` | `mom_num_urin_cond` | Numeric | Count of mother's urinary conditions |
| `x_13` | `mom_num_gyne_cond` | Numeric | Count of mother's gynecological conditions |
| `x_14` | `mom_num_neur_cond` | Numeric | Count of mother's neurological conditions |
| `x_15` | `mom_num_obst_compl` | Numeric | Count of mother's obstetric complications |
| `x_16` | `mom_num_infect_dis` | Numeric | Count of mother's infectious diseases |
| `x_17` | `mom_work_status` | Binary, 0/1 | Mother's work-status indicator; code meanings are not supplied |
| `x_18` | `mom_years_educ` | Numeric | Mother's years of education |
| `x_19` | `family_income` | Numeric | Family income |
| `x_20` | `housing_density` | Numeric | Housing density |
| `x_21` | `mom_birth_place` | Categorical, A-P | Mother's birthplace; category labels are not supplied |
| `x_22` | `consanguinity` | Binary, 0/1 | Consanguinity indicator; code meanings are not supplied |
| `x_23` | `socio_eco` | Numeric | Socioeconomic measure; detailed definition is not supplied |
| `x_24` | `mom_race` | Categorical, A-E | Mother's race; category labels are not supplied |
| `x_25` | `age_menarche` | Numeric | Mother's age at menarche |
| `x_26` | `dias_blood_pres` | Numeric | Mother's diastolic blood pressure |
| `x_27` | `mom_weight_birth` | Numeric | Mother's own birth weight |
| `x_28` | `dad_age` | Numeric | Father's age |
| `x_29` | `dad_years_educ` | Numeric | Father's years of education |
| `x_30` | `num_premes` | Numeric | Number of premature births; exact coding is not supplied |
| `x_31` | `num_abortions` | Numeric | Number of abortions |
| `x_32` | `num_prior_pregs` | Numeric | Number of prior pregnancies |
| `x_33` | `num_stillbirths` | Numeric | Number of stillbirths |
| `x_34` | `bayley_mental` | Numeric | Child's Bayley mental score |
| `x_35` | `bayley_motor` | Numeric | Child's Bayley motor score |
| `x_36` | `placental_weight` | Numeric | Placental weight |
| `x_37` | `cord_length` | Numeric | Umbilical cord length |
| `x_38` | `sex` | Binary, 0/1 | Child's sex; code meanings are not supplied |
| `x_39` | `apgar_1m_total` | Numeric | Child's total APGAR score at one minute |
| `x_40` | `apgar_5m_total` | Numeric | Child's total APGAR score at five minutes |
| `x_41` | `bottle_feed_days` | Numeric | Days of bottle feeding |
| `x_42` | `breast_feed_days` | Numeric | Days of breastfeeding |
| `x_43` | `child_bilirubin` | Numeric | Child's bilirubin measure |
| `x_44` | `child_hematocrit` | Numeric | Child's hematocrit measure |
| `x_45` | `child_hemoglobin` | Numeric | Child's hemoglobin measure |
| `x_46` | `child_num_neur_abn` | Numeric | Count of child's neurological abnormalities |
| `x_47` | `child_num_cns_cond` | Numeric | Count of child's central nervous system conditions |
| `x_48` | `child_num_muscoskel` | Numeric | Count of child's musculoskeletal conditions |
| `x_49` | `child_num_resp_abn` | Numeric | Count of child's respiratory abnormalities |
| `x_50` | `child_num_cardio_abn` | Numeric | Count of child's cardiovascular abnormalities |
| `x_51` | `child_num_liver_abn` | Binary, 0/1 | Child liver-abnormality field; stored as 0/1 in this file |
| `x_52` | `child_num_hemo_cond` | Numeric | Count of child's hematological conditions |
| `x_53` | `child_num_infect` | Numeric | Count of child's infections |
| `x_54` | `child_num_synd` | Binary, 0/1 | Child syndrome field; stored as 0/1 in this file |
| `x_55` | `child_num_endo_dis` | Numeric | Count of child's endocrine disorders |
| `x_56` | `child_num_proc` | Numeric | Count of procedures involving the child |
| `x_57` | `head_size_1yr` | Numeric | Child's head size at one year |
| `x_58` | `gest_delivery` | Numeric | Gestational/delivery measure; exact unit is not supplied |

This provisional mapping is for naming and describing fields. It does not assert that every
field is a valid pretreatment confounder for every simulation setting. Several
fields describe child or delivery characteristics and may be post-treatment
in a real birthweight study. The current ACIC protocol retains all 58 input
fields for benchmark comparability; interpret LLM weights as a prior over this
benchmark's named input fields, not as a clinical causal adjustment set.

## Sources

- [ACIC 2016 package reference manual, Input Data for the 2016 ACIC Competition](https://mrcieu.r-universe.dev/aciccomp2016/doc/manual.html)
- [ACIC 2016 data README](https://github.com/BiomedSciAI/causallib/blob/master/causallib/datasets/data/acic_challenge_2016/README.md)
- [Dorie et al. (2019), competition paper](https://doi.org/10.1214/18-STS667)
