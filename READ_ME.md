# Evaluating LLM-Assisted Matching

## Project overview

This project evaluates whether LLM-assisted covariate weight decisions improves
matching quality and treatment-effect estimation compared with conventional
matching methods. The current application is maternal smoking during pregnancy
and infant birth weight using the 2024 CDC Natality Public Use File.

The project evaluates matching procedures. It does not aim to establish a
definitive causal effect of maternal smoking on birth weight.

## Research question

Does LLM-generated covariate weighting improve matching performance compared 
with conventional approaches?

## Current evaluation plan (Pseudo-ground truth construction)

The current study will use the eligible 2024 singleton-birth Natality cohort.
For each of `R` repeated, outcome-blind, treatment-stratified random splits,
use 99% of the eligible cohort as the reference sample and 1% as the test
sample. A conventional estimator, to be specified before the final comparison,
will estimate the reference ATT in the 99% sample. Each matching method will
estimate the ATT in the 1% test sample using the same treatment, outcome,
covariates, eligibility rules, and estimand.

For method `m` and split `r`, compare its test-sample estimate with the
reference estimate:

`Reference error_(m,r) = ATT_test_(m,r) - ATT_reference_r`

Report the mean squared reference error and its square root (RMSE) across the
`R` splits. These quantify agreement with the selected conventional reference
procedure; they are **not** error against a known true causal effect. The
reference may itself retain bias or residual confounding. Also report balance,
overlap, treated-birth retention, and ATT uncertainty so the reference error
is interpreted alongside matching diagnostics.

The 2024 cohort currently contains about 80,000 treated singleton births
before matching. A 1% test split therefore has only about 800 treated births
before matching, and fewer may be retained. This may make test estimates
variable. Later, the study may add 2023, 2022, and other years to increase the
available sample. Any multi-year analysis will require harmonized fields and a
documented decision about year effects and the target population. The current
stage is 2024 only.

## LLM workflow

Apply the same Natality cohort, split design, covariates, estimand, and
matching rules through three stages:

1. **Manual chat-interface matching:** obtain covariate priorities or weights
   through a chat interface without using an API.
2. **DeepSeek API:** implement the same LLM weighting task using DeepSeek.
3. **Advanced API:** repeat the task with the more advanced API/model to be
   selected after discussion.

At every stage, provide covariate names, definitions, coding, and relevant
pre-treatment rationale. Do not provide outcome values when obtaining LLM
weights. The LLM supplies covariate weights only; it does not choose the
cohort, outcome, estimand, split, or matching algorithm. Save the model or
interface, prompt, settings, returned structured weights, and any retries.

## Matching methods

Compare the LLM-weighted method with:

- Identity-matrix unweighted generalized Mahalanobis matching.
- PCA-based matching.
- Propensity-score matching.
- Genetic matching.

The matching algorithm, distance calculation, preprocessing and scaling,
caliper, replacement rule, and conventional reference estimator remain to be
specified before the final comparison. Apply the same rules to all methods
where applicable.

## Data and study variables

- **Treatment:** `CIG_REC`; `Y` means reported smoking during pregnancy and
  `N` means no reported smoking. Unknown status is excluded.
- **Outcome:** `DBWT`, birth weight in grams. The not-stated code `9999` is
  excluded.
- **Primary covariates and eligibility:** see
  [`docs/maternal_smoking_birthweight/analysis_protocol.md`](docs/maternal_smoking_birthweight/analysis_protocol.md)
  and the [covariate review](docs/maternal_smoking_birthweight/covariate_review.md).
- **Primary cohort:** eligible singleton births under the documented
  flag-aware complete-case rule.
- **Proposed estimand:** ATT for treated births that can be matched to
  comparable nonsmoking births; report unmatched treated births.

ACIC 2016 is a possible known-ground-truth benchmark, but it is not part of the
current Natality study. Discuss with the professor before adding it.

## Documentation and data

- [`docs/llm_matching/`](docs/llm_matching/) contains the general evaluation
  protocol.
- [`docs/maternal_smoking_birthweight/`](docs/maternal_smoking_birthweight/)
  contains the Natality case-study protocol and data documentation.
- The fixed-width 2024 source file is stored locally at
  `data/raw/2024/Nat2024us/Nat2024PublicUS.c20250512.r20250708.txt`.
- Raw and processed data are local project inputs and must not be committed to
  Git.
