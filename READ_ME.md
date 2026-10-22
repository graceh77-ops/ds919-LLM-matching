# Evaluating LLM-Assisted Matching

## Project Overview

This project evaluates whether an LLM-assisted matching approach can improve
causal matching in observational data.

The method under study uses an LLM to assess the relative importance of
pre-specified covariates and inform the matching process. Its performance will
be compared with conventional matching approaches. Maternal smoking during
pregnancy and infant birth weight in the 2024 CDC Natality Public Use File serve
as the real-data case study.

The primary goal is to evaluate the matching method, not to establish that
maternal smoking causes a particular change in birth weight.

## Main Research Question

How does LLM-assisted covariate prioritization or weighting affect matching
quality and causal effect estimates compared with conventional matching
approaches?

The exact LLM role, matching algorithm, comparison methods, and target
estimand will be specified in the llm_matching_protocol before the final
evaluation.


## Evaluation

### Primary comparison: pseudo-ground-truth reference error

For the Natality case study, we will evaluate whether matching methods applied to a held-out sample reproduce a pre-specified reference effect estimate from a larger sample.

For each of R repeated, outcome-blind, treatment-stratified random splits, we will use 99% of the eligible singleton cohort as the reference sample and 1% as the test sample. A pre-specified conventional estimator will produce the reference ATT in the 99% sample. Each candidate method will estimate the ATT in the 1% test sample using the same treatment definition, outcome, covariates, estimand, and eligibility rules.

For method m, the reference-relative mean squared error will be:

MSE_m = (1 / R) * sum_r (ATT_test,m,r - ATT_reference,r)^2

We will also report the root mean squared error (RMSE) in grams. Lower values indicate closer agreement with the reference estimate across repeated splits.

This is a pseudo-ground-truth evaluation, not an evaluation against the known true causal effect. The reference estimate may retain residual confounding, and the MSE measures agreement with that reference estimator. The reference estimator will be specified before comparing methods; if propensity-score matching is used as the reference, the results will be interpreted as agreement with that approach.

### Supporting diagnostics

For each method, we will report:

- Covariate balance before and after matching, including standardized mean differences (SMDs).
- Propensity-score overlap or covariate-space matchability, as appropriate to the method.
- Number and proportion of treated births retained or matched.
- Estimated ATT in grams and its uncertainty.
- Sensitivity of balance, retention, and ATT estimates to matching and covariate-weight choices.

## Real-Data Case Study

The case study uses the 2024 CDC Natality Public Use File.

- **Treatment:** `CIG_REC`
  - `Y`: reported cigarette smoking during pregnancy
  - `N`: no reported cigarette smoking during pregnancy
  - `U`: unknown treatment status
- **Outcome:** `DBWT`
  - Birth weight in grams
  - `9999`: not-stated code
- **Candidate covariates:** documented in
  [`docs/maternal_smoking_birthweight/covariate_review.md']

Records with unknown treatment status or missing birth weight are excluded
from the primary analysis cohort. Their counts are recorded in the
data-quality summary. Candidate covariates and their missing values are
handled according to the analysis protocol.

## Data

The fixed-width source file is stored locally at:

```text
data/raw/2024/Nat2024us/Nat2024PublicUS.c20250512.r20250708.txt
```

## Documentation

- [`docs/llm_matching/`](docs/llm_matching/) contains the general LLM matching
  evaluation protocol.
- [`docs/maternal_smoking_birthweight/`](docs/maternal_smoking_birthweight/)
  contains the Natality case-study plan, analysis protocol, extraction details,
  data dictionary, and covariate review.
