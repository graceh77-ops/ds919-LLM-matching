# LLM Matching Evaluation Protocol

## Objective

Evaluate whether LLM-assisted covariate prioritization improves matching
quality and treatment effect estimation compared with conventional matching
approaches.

The 2024 CDC Natality Public Use File is the real-data application. It does not
provide a known true causal effect, so it cannot by itself establish which
method has the most accurate effect estimate.

## Research Question

Does LLM-generated covariate prioritization or weighting improve matching
performance compared with conventional matching approaches?

## Data Roles

### Real-data application

Use the 2024 CDC Natality Public Use File to compare matching behavior in a
large observational dataset. Assess covariate balance, overlap, the proportion
of treated records retained, and the estimated effect with its uncertainty.

Do not use MSE against a true effect for this dataset because the true causal
effect is unknown.

### Known-ground-truth benchmark

Use a benchmark with known treatment effects to assess effect-estimation error.
ACIC 2016 is a candidate: its challenge data include real covariates and
simulated treatment and potential-outcome information. Its scenarios differ
from the Natality application, so benchmark performance should not be
interpreted as direct evidence about the true effect of maternal smoking.
The original challenge focused on SATT estimation. 

## Proposed Estimand

For the Natality application, the proposed primary estimand is the ATT: the
average treatment effect among births with `CIG_REC = Y`.

For each known-ground-truth benchmark sample, evaluate the estimator against
the corresponding sample-level treatment effect (SATT). Confirm the estimand
and its exact implementation before running the final comparison.

## Methods to Compare

1. **Unweighted matching:** Apply the selected matching algorithm with equal
   covariate weights.
2. **Conventional propensity-score matching:** Estimate propensity scores
   using a pre-specified conventional model, then apply the selected matching
   rule.
3. **LLM-weighted matching:** Ask the LLM to assign importance weights to the
   pre-specified covariates, then apply the same matching algorithm and rules
   used for the unweighted method.

Keep the matching algorithm, caliper or distance rule, replacement rule, and
cohort fixed across methods whenever possible. This helps isolate the
contribution of LLM-generated weights.

## LLM Procedure

Provide the LLM with the covariate names, definitions, coding, and relevant
pre-treatment rationale. Do not provide outcome values when requesting
covariate weights. Record the model, prompt, settings, returned weights, and
any retries. Require a structured output that can be checked and reproduced.

## Evaluation Metrics

### Known-ground-truth benchmark

- **Primary metric:** MSE between the estimated effect and the known target
  effect, reported across benchmark samples or scenarios.
- **Matching diagnostics:** Absolute standardized mean differences,
  proportion of treated records matched, and overlap.

### Natality application

- Absolute standardized mean differences after matching.
- Treatment-group overlap.
- Number and proportion of treated records retained.
- Estimated ATT and its uncertainty.
- Sensitivity to covariate weights and matching specifications.

Do not interpret a smaller balance metric alone as proof of more accurate causal
effect estimation.

## Reproducibility

Keep the cohort definition, covariate set, prompts, LLM settings, matching
rules, and metric calculations documented before comparing final results.