# LLM Matching Evaluation Protocol

## Objective and current scope

Evaluate whether LLM-assisted covariate weighting improves matching quality and 
treatment-effect estimation compared with conventional matching methods.

The current empirical application is the 2024 CDC Natality Public Use File,
focused on maternal smoking during pregnancy and birth weight among singleton
births. ACIC 2016 is a possible future known-ground-truth benchmark; it is
outside the current scope and will be discussed further before any work begins 
on it.

## Research question

Does LLM-generated covariate weighting improve matching performance compared with conventional matching approaches on the Natality application?

## Natality study design

### Treatment, outcome, and estimand

- **Treatment:** `CIG_REC = Y` (reported cigarette smoking during pregnancy).
- **Comparison:** `CIG_REC = N` (no reported smoking during pregnancy).
  Unknown treatment status is excluded, not classified as nonsmoking.
- **Outcome:** `DBWT`, birth weight in grams; not-stated or invalid values are
  excluded.
- **Proposed estimand:** ATT among treated births that can be matched to
  comparable nonsmoking births. Report treated births that are not matched.

The cohort and primary covariate eligibility rules are documented in the
[maternal smoking analysis protocol](../maternal_smoking_birthweight/analysis_protocol.md).
The current primary population is singleton births. Use the same eligible
cohort and covariate handling for every method and every split.

### Repeated 99% / 1% reference comparison

For each of `R` repeated, outcome-blind, treatment-stratified random splits:

1. Assign 99% of eligible singleton births to a reference sample and 1% to a
   test sample, preserving treatment strata in the split.
2. Apply a conventional matching estimator, specified before final evaluation,
   to the 99% reference sample to estimate the reference ATT.
3. Apply each candidate method separately to the same 1% test sample and
   estimate its test-sample ATT using the fixed treatment, outcome, covariates,
   estimand, eligibility rules, and matching rules.
4. Record the test ATT, reference ATT, their difference, diagnostics, and
   retained-treated count for every method and split.

For method `m` and split `r`, define reference error as:

`Error_(m,r) = ATT_test_(m,r) - ATT_reference_r`

Report mean squared reference error and RMSE across the `R` splits. Lower
values indicate closer agreement with the conventional reference estimator.
This is a **pseudo-ground-truth** comparison, not evaluation against the true
causal effect. The reference estimate can be biased or retain residual
confounding; therefore, the results show agreement with the chosen reference
procedure and do not establish causal accuracy.

The 2024 cohort has about 80,000 treated singleton births before matching, so
a 1% test sample contains about 800 treated births before matching and may
contain fewer after matching. Test-sample estimates may consequently be noisy.
The later plan is to consider adding 2023, 2022, and earlier Natality years to
increase sample size and improve the stability of the reference comparison.
The present work remains 2024 only. Before pooling years, harmonize variables
and eligibility rules and document how calendar year affects the target
population and analysis.

The number of repetitions `R`, random seed strategy, reference estimator, and
matching specifications are not yet finalized. Specify and document them
before comparing final results.

## Staged LLM workflow

Apply the same covariate-weighting task and Natality design in three stages:

1. **Manual chat-interface matching:** first obtain covariate priorities or
   weights through a chat interface, without using an API.
2. **DeepSeek API:** next implement the same weighting task through DeepSeek.
3. **Advanced API:** then use the more advanced API/model to be identified
   after discussion with the professor.

For every stage, give the LLM only the pre-specified covariate names,
definitions, coding, research question, and relevant pre-treatment rationale
needed to assign weights. Do not provide outcome values. The LLM assigns
covariate priorities or weights.

Request structured output that can be checked and applied reproducibly. Record
the interface or model and version, exact prompt, settings, date, returned
weights, any retries, and any manual changes. Use the resulting weights
consistently across repeated splits for that stage; do not tune weights against
test outcomes.

## Methods to compare

All methods use the same cohort, treatment, outcome, covariates, estimand, and
split assignments.

### LLM method

Apply LLM-assigned covariate weights using generalized Mahalanobis matching.
The LLM provides the weights only; preprocessing and matching rules are
specified outside the LLM.

### Primary conventional comparisons

- **Identity-matrix unweighted matching:** generalized Mahalanobis distance
  with identity weight matrix (`W = I`) after covariate coding and scaling.
- **PCA-based matching:** match in the retained principal-component space.
  Document preprocessing, component-retention rule, and distance measure.

### Additional comparators

- **Propensity-score matching:** estimate treatment propensity from the
  covariates and apply a fixed matching rule.
- **Genetic matching:** use a genetic-matching procedure to select distance weights and apply the generalized Mahalanobis distance metric.

Specify the matching algorithm, distance calculation, covariate preprocessing
and scaling, caliper, replacement rule, tie handling, and conventional
reference estimator before final comparisons. Keep these settings fixed across
methods whenever possible so the comparison isolates the weighting approach.

## Evaluation and reporting

For every method and split, report:

- Reference ATT, test-sample ATT, reference error, and uncertainty for the
  estimated ATT.
- Absolute standardized mean differences before and after matching.
- Treatment-group overlap or covariate-space matchability.
- Number and proportion of treated births retained or matched.
- Sensitivity of balance, retention, ATT, and reference error to prespecified
  matching settings and covariate weights.

Report mean squared reference error and RMSE across repeated splits as measures
of agreement with the conventional reference estimator. Do not describe them
as error against the true causal effect. Do not interpret improved balance
alone as proof of improved effect estimation.

## Possible future benchmark

ACIC 2016 may be considered later as a separate known-ground-truth benchmark.
It is not part of the current Natality procedure, and performance on it would
not directly establish the true effect of maternal smoking. Confirm whether to
include it with the professor before starting that work.

## Reproducibility

Document the cohort definition, variable coding, covariate set, split
assignments or seed procedure, LLM prompts and settings, returned weights,
matching specifications, reference estimator, and metric calculations before
the final method comparison. Preserve enough outputs to reproduce each
method's estimate and diagnostic for each split.
