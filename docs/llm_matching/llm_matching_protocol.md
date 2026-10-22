# LLM Matching Evaluation Protocol

## Objective and scope

Evaluate whether LLM-assisted covariate weighting improves matching quality
and treatment-effect estimation compared with conventional matching methods.
The current application is the 2024 CDC Natality study of maternal smoking
during pregnancy and birth weight. Study-specific cohort and variable
definitions are maintained in the
[Natality analysis protocol](../maternal_smoking_birthweight/analysis_protocol.md).
ACIC 2016 is a possible future benchmark, outside the current scope.

## Research question

Does LLM-generated covariate weighting improve matching performance compared with conventional matching approaches on the Natality application?

## Repeated 99% / 1% reference comparison

For each of `R` repeated, outcome-blind, treatment-stratified random splits:

1. Assign 99% of eligible singleton births to a reference sample and 1% to a
   test sample, preserving treatment strata in the split.
2. Apply identity-matrix generalized Mahalanobis matching, using the fixed
   study-specific distance specification, to the 99% reference sample to
   estimate the reference ATT.
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

The number of repetitions `R` and random seed strategy are not yet finalized.
Specify and document them before comparing final results. The reference
estimator and primary matching settings are defined in the Natality analysis
protocol.

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
  with identity weight matrix (`V = I`) after the study-specific covariate
  coding and scaling.
- **PCA-based matching:** match in the retained principal-component space.
  Document preprocessing, component-retention rule, and distance measure.

### Additional comparators

- **Propensity-score matching:** estimate treatment propensity from the
  covariates and apply a fixed matching rule.
- **Genetic matching:** use a genetic-matching procedure to select distance weights and apply the generalized Mahalanobis distance metric.

The analysis protocol specifies the primary matching algorithm, distance,
covariate preprocessing, scaling, tie handling, and reference estimator.
Specify settings needed by each additional comparator before final comparisons.
Keep shared settings fixed across methods wherever possible so the comparison
isolates the weighting approach.

## Evaluation and reporting

For every method and split, report:

- Absolute standardized mean differences before and after matching.
- Treatment-group overlap or covariate-space matchability.
- Number and proportion of treated births retained or matched.
- Sensitivity of balance and retention to prespecified matching settings and
  covariate weights.

Report ATT uncertainty alongside the reference-error metrics defined above.
Do not describe reference error as error against the true causal effect. Do
not interpret improved balance alone as proof of improved effect estimation.

## Reproducibility

Document the cohort definition, variable coding, covariate set, split
assignments or seed procedure, LLM prompts and settings, returned weights,
matching specifications, reference estimator, and metric calculations before
the final method comparison. Preserve enough outputs to reproduce each
method's estimate and diagnostic for each split.
