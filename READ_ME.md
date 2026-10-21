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
estimand will be specified in the analysis protocol before the final 
evaluation.

## Evaluation Approach

The evaluation will compare the LLM-assisted method with one or more
conventional matching baselines.

For the Natality case study, the evaluation may include:

- Covariate balance before and after matching, including standardized mean
  differences.
- Overlap between treatment and comparison groups.
- Number and proportion of treated records retained or matched.
- Estimated treatment effect and its uncertainty.
- Sensitivity of results to matching and covariate-weight choices.

The Natality data do not provide a known true causal effect. Therefore, metrics
such as mean squared error (MSE) against the true effect cannot be calculated
from this real-data case study alone. Claims about causal effect-estimation
accuracy require an evaluation dataset with a known ground truth.

## Real-Data Case Study

The case study uses the 2024 CDC Natality Public Use File.

- **Treatment:** `CIG_REC`
  - `Y`: reported cigarette smoking during pregnancy
  - `N`: no reported cigarette smoking during pregnancy
  - `U`: unknown treatment status
- **Outcome:** `DBWT`
  - Birth weight in grams
  - `9999`: not-stated code
- **Candidate covariates:** documented in `docs/`

Records with unknown treatment status or missing birth weight are excluded from
the primary analysis cohort. Their counts are recorded in the data-quality
summary. Candidate covariates and their missing values are handled according
to the analysis protocol.

## Data

The fixed-width source file is stored locally at:

```text
data/raw/2024/Nat2024us/Nat2024PublicUS.c20250512.r20250708.txt