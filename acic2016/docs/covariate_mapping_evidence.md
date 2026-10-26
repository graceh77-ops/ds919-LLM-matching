# ACIC 2016 Covariate Mapping Evidence

## Conclusion

The 58 proposed labels are plausible as an **order-based mapping** from the
ACIC package's ordered CPP variable list, and the observed field types support
some of them. They are not all independently verified: the package manual
does not provide an explicit `x_i`-to-CPP-name crosswalk. Treat the full
mapping as provisional until an authoritative crosswalk or source-data schema
is found. This document assesses label plausibility; it does not establish
that each field is an appropriate adjustment covariate for a causal analysis.

The package describes 4,802 de-identified records with 58 covariates, drawn
from possible confounders, instruments, and unrelated variables in a
hypothetical twin study of birthweight and IQ. It does not identify which
variables play which causal roles. The package's ordered name list is the
basis for the proposed labels below. [Package reference manual](https://mrcieu.r-universe.dev/aciccomp2016/doc/manual.html)

## Evidence limits and independent checks

The ACIC 2017 competition paper independently names eight positions:
`x_1` mother's age, `x_3` cigarettes per day, `x_10` endocrine conditions,
`x_14` nervous-system conditions, `x_15` obstetric complications, `x_21`
birthplace, `x_24` race, and `x_43` child bilirubin. This corroborates the
semantic identities for those positions, but the 2017 analysis uses a selected
and recoded subset; it does not verify every 2016 field's units or coding.
For example, local `x_10`, `x_14`, and `x_15` are counts, while the 2017 paper
describes binary indicators; local `x_24` has five categories while the 2017
description uses a binary race variable. These differences may reflect
recoding/selection and should not be silently treated as identical encodings.
[Dorie et al. (2019)](https://arxiv.org/abs/1905.09515)

The local shared `x.csv` has 4,802 rows and 58 columns. Its observed categorical
fields are `x_2` (A-F), `x_21` (A-P), and `x_24` (A-E); this is consistent with
the ordered labels marital status, birthplace, and race. The observed 0/1
numeric fields are `x_17`, `x_22`, `x_38`, `x_51`, and `x_54`. These types are
useful consistency checks, not proof of names or code meanings. Category
letters and binary values have no documented reference labels in the package
material reviewed.

The numerical ranges below were inspected in the local shared covariate file.
They are broad plausibility checks only. Numeric storage does not imply a
continuous scale: some fields may be counts, ordinal codes, or transformed
scores. In particular, `family_income` (`x_19`) and `socio_eco` (`x_23`) need
their original definitions and units before interpreting their scale;
`bottle_feed_days` (`x_41`) and `breast_feed_days` (`x_42`) have observed
maximum 8 despite the proposed “days” labels; and `gest_delivery` (`x_58`)
spans 21-50 but its unit is undocumented.

## Field-by-field audit

“Anchored” means the semantic position is independently named in the cited
ACIC paper, with the recoding caveat above. “Order-inferred” means the label
comes from pairing the position with the package manual's ordered list. A
plausible range/type does not promote an order-inferred label to confirmed.

| Field | Proposed label | Evidence status | Local type/range check and interpretation |
|---|---|---|---|
| `x_1` | Mother's age | Anchored | Numeric, 14-48; plausible age range. |
| `x_2` | Mother's marital status | Order-inferred | Categorical A-F; type is plausible, category meanings unknown. |
| `x_3` | Mother's cigarettes per day | Anchored | Numeric, 0-60; plausible, but fractional values occur and exact unit/transform is unverified. |
| `x_4` | Mother's years of smoking | Order-inferred | Numeric, 0-35; plausible duration/count. |
| `x_5` | Mother's height | Order-inferred | Numeric, 40-78; plausible in a common height unit, but unit is not documented. |
| `x_6` | Mother's pre-pregnancy weight | Order-inferred | Numeric, 71-289; plausible in a common weight unit, but unit is not documented. |
| `x_7` | Mother's cardiovascular-condition count | Order-inferred | Numeric, 0-5; count-like range. |
| `x_8` | Mother's pulmonary-condition count | Order-inferred | Numeric, 0-4; count-like range. |
| `x_9` | Mother's hematological-condition count | Order-inferred | Numeric, 0-5; count-like range. |
| `x_10` | Mother's endocrine-condition count | Anchored | Numeric, 0-8; count-like locally; 2017 paper's binary coding is not the same encoding. |
| `x_11` | Mother's venereal-condition count | Order-inferred | Numeric, 0-3; count-like range. The source spelling is “veneral”; this note uses the conventional spelling. |
| `x_12` | Mother's urinary-condition count | Order-inferred | Numeric, 0-8; count-like range. |
| `x_13` | Mother's gynecological-condition count | Order-inferred | Numeric, 0-5; count-like range. |
| `x_14` | Mother's neurological-condition count | Anchored | Numeric, 0-5; count-like locally; 2017 paper's binary coding differs. |
| `x_15` | Mother's obstetric-complication count | Anchored | Numeric, 0-6; count-like locally; 2017 paper's binary coding differs. |
| `x_16` | Mother's infectious-disease count | Order-inferred | Numeric, 0-2; count-like range. |
| `x_17` | Mother's work status | Order-inferred | Binary 0/1, consistent with an indicator; which value means which status is unknown. |
| `x_18` | Mother's years of education | Order-inferred | Numeric, 0-18; plausible, but exact coding/units should be confirmed. |
| `x_19` | Family income | Order-inferred | Numeric, 0-105; scale is unclear and may be coded/ordinal rather than currency units. |
| `x_20` | Housing density | Order-inferred | Numeric, 2-70; plausible as a density measure, but definition and unit are unknown. |
| `x_21` | Mother's birthplace | Anchored | Categorical A-P; semantic identity and categorical type align; category meanings unknown. |
| `x_22` | Consanguinity | Order-inferred | Binary 0/1, consistent with an indicator; code meanings are unknown. |
| `x_23` | Socioeconomic measure | Order-inferred | Numeric, 0-95; definition and scale are unclear; avoid treating as an interval measure without evidence. |
| `x_24` | Mother's race | Anchored | Categorical A-E locally; 2017 binary race coding is a different representation. |
| `x_25` | Mother's age at menarche | Order-inferred | Numeric, 7-19; plausible age range. |
| `x_26` | Mother's diastolic blood pressure | Order-inferred | Numeric, 12-124; plausible measurement range, units not documented. |
| `x_27` | Mother's own birth weight | Order-inferred | Numeric, 88-284; plausible in a common birth-weight unit, but unit is unverified. |
| `x_28` | Father's age | Order-inferred | Numeric, 14-66; plausible age range. |
| `x_29` | Father's years of education | Order-inferred | Numeric, 0-18; plausible, but exact coding is unverified. |
| `x_30` | Number of premature births | Order-inferred | Numeric, 0-7; count-like range; definition of “premature” is not supplied. |
| `x_31` | Number of abortions | Order-inferred | Numeric, 0-7; count-like range. |
| `x_32` | Number of prior pregnancies | Order-inferred | Numeric, 0-4; count-like range. |
| `x_33` | Number of stillbirths | Order-inferred | Numeric, 0-7; count-like range. |
| `x_34` | Child's Bayley mental score | Order-inferred | Numeric, 7-99; plausible score range, assessment timing/version unknown. |
| `x_35` | Child's Bayley motor score | Order-inferred | Numeric, 7-43; plausible score range, assessment timing/version unknown. |
| `x_36` | Placental weight | Order-inferred | Numeric, 150-940; plausible measurement, unit unverified. |
| `x_37` | Umbilical-cord length | Order-inferred | Numeric, 1-98; plausible measurement, unit unverified. |
| `x_38` | Child's sex | Order-inferred | Binary 0/1, consistent with a two-level field; code meanings are unknown. |
| `x_39` | APGAR total at one minute | Order-inferred | Numeric, 0-10; matches the usual total-score range, but original scoring details are not provided here. |
| `x_40` | APGAR total at five minutes | Order-inferred | Numeric, 1-10; matches a plausible total-score range. |
| `x_41` | Bottle-feeding duration | Order-inferred | Numeric, 0-8; conflicts with a literal “days” interpretation unless transformed, capped, or coarsened. |
| `x_42` | Breastfeeding duration | Order-inferred | Numeric, 0-8; same unit/coding concern as `x_41`. |
| `x_43` | Child bilirubin | Anchored | Numeric, 0-25; semantic identity corroborated, measurement unit/timing unverified. |
| `x_44` | Child hematocrit | Order-inferred | Numeric, 13-85; plausible percentage-like range, but unit/timing unverified. |
| `x_45` | Child hemoglobin | Order-inferred | Numeric, 4-27; plausible measurement range, but unit/timing unverified. |
| `x_46` | Child neurological-abnormality count | Order-inferred | Numeric, 0-8; count-like range. |
| `x_47` | Child central-nervous-system-condition count | Order-inferred | Numeric, 0-2; count-like range. |
| `x_48` | Child musculoskeletal-condition count | Order-inferred | Numeric, 0-3; count-like range. |
| `x_49` | Child respiratory-abnormality count | Order-inferred | Numeric, 0-8; count-like range. |
| `x_50` | Child cardiovascular-abnormality count | Order-inferred | Numeric, 0-3; count-like range. |
| `x_51` | Child liver-abnormality field | Order-inferred | Binary 0/1 although proposed name says “number”; likely an indicator or a count restricted to 0/1. |
| `x_52` | Child hematological-condition count | Order-inferred | Numeric, 0-3; count-like range. |
| `x_53` | Child infection count | Order-inferred | Numeric, 0-3; count-like range. |
| `x_54` | Child syndrome field | Order-inferred | Binary 0/1 although proposed name says “number”; likely an indicator or a count restricted to 0/1. |
| `x_55` | Child endocrine-disorder count | Order-inferred | Numeric, 0-2; count-like range. |
| `x_56` | Number of procedures involving child | Order-inferred | Numeric, 0-8; count-like range. |
| `x_57` | Child head size at one year | Order-inferred | Numeric, 34-51; plausible measurement, but unit and exact age window are unverified. |
| `x_58` | Gestational/delivery measure | Order-inferred | Numeric, 21-50; plausible gestational-age-like range, but the proposed name itself is ambiguous and unit is unknown. |

## Whether the fields make sense for LLM matching

As a **benchmark input inventory**, the 58-field set is coherent: it combines
maternal and parental characteristics, pregnancy history, delivery/newborn
measures, child health/development measures, and possible non-confounders.
That is consistent with the package's description of a deliberately mixed
simulation covariate set. As a clinical adjustment set for a birthweight
effect, it is not automatically coherent. Variables measured during delivery
or after birth (for example placental weight, APGAR, feeding, child lab values,
and one-year measures) may be downstream of exposure and/or outcome, so their
inclusion could create mediator or collider adjustment. Their exact causal
roles vary by target question and simulation setting.

For this ACIC benchmark, retain the prespecified 58 fields when comparing
matching methods so the methods see the same inputs. In the LLM prompt and
reported results, call the labels **provisional**, do not invent category
meanings or units, and do not describe the scores as clinical confounder
importance. If the scientific goal changes to estimating a real-world causal
effect, first obtain a verified codebook and define a pretreatment adjustment
set for that estimand.

## What would resolve the remaining uncertainty

1. Find the original CPP input schema or an explicit crosswalk linking each
   package column to the source variable and codebook definition.
2. Confirm units, transformations, category labels, missing-value conventions,
   and assessment timing for each field.
3. Compare the 2016 file construction with the 2017 paper's selected/re-coded
   variables before treating those coding schemes as interchangeable.
4. Update the field dictionary only when the evidence supports the change;
   preserve an audit trail of the source and mapping decision.

See also the [provisional field dictionary](llm_matching/field_dictionary.md)
and [analysis protocol](analysis_protocol.md).
