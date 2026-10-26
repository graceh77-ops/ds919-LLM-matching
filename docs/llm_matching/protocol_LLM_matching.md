# LLM Matching Evaluation Protocol

## Objective and scope

Evaluate whether LLM-assisted covariate weighting improves matching quality
and treatment-effect estimation compared with conventional matching methods.
This document records the current **CDC Natality implementation** as a worked
application of the workflow. Its estimator, split, encoding, covariate, and
matching choices are study-specific. A different dataset needs its own
protocol and configuration; do not assume these specifications transfer
without review. Study-specific cohort and variable definitions are maintained
in the [Natality analysis protocol](../../cdc%20natality/docs/maternal_smoking_birthweight/protocal_maternal_smoking_dataset.md).
ACIC 2016 remains a possible future benchmark, outside the current scope.

## Research question

Does LLM-generated covariate weighting improve matching performance compared with conventional matching approaches on the Natality application?

## Repeated 99% / 1% reference comparison

For each of `R` repeated, treatment-stratified random splits:

1. Assign 99% of eligible singleton births to a reference sample and 1% to a
   test sample, preserving treatment strata in the split. Use NumPy's seeded
   `default_rng` generator (PCG64); within each treatment group, round the 1%
   test count to the nearest integer (half-up) and sample without replacement.
2. Fit the reference-cohort propensity and control outcome models using a
   reference-fitted representation of the shared 23 encoded covariates.
   Calculate AIPW-ATT as the primary reference estimate and calculate IPW-ATT
   and outcome-regression ATT as separate reference sensitivities.
3. Fit matching-side preprocessing and any treatment model using only the 1%
   test sample's covariates and treatment. Apply each candidate method to that
   same test sample and estimate its test-sample ATT.
4. Record each method's test ATT, the AIPW/IPW/outcome-regression reference
   estimates, diagnostics, and retained-treated count for every split.

### Reference estimator specifications

Let `A` indicate maternal smoking, `Y` be birth weight in grams, `e(X)` be the
reference-fitted propensity score, and `m0(X)` be reference-fitted expected
birth weight among nonsmokers. The primary AIPW estimate is:

`ATT_AIPW = sum[A_i (Y_i - m0(X_i))] / n1 - sum[(1-A_i) w_i (Y_i - m0(X_i))] / n1`

where `w_i = e(X_i) / (1 - e(X_i))` for controls and `n1` is the number of
treated reference records. Propensity scores used to form odds weights are
clipped to `[1e-6, 1 - 1e-6]` for numerical stability; raw scores are retained
for overlap diagnostics. The propensity model is unpenalized logistic
regression fitted on reference treatment and the shared encoded covariates.
The control outcome model is unpenalized ordinary least squares for birth
weight on an intercept and the same encoded covariates, fitted only among
reference controls using incremental QR in memory-bounded chunks. This is a
parametric, in-sample nuisance-model specification; no test outcomes are used.

The IPW-ATT sensitivity estimate is the treated reference mean minus the
propensity-odds-weighted control reference mean, normalized by the sum of
control odds weights. The outcome-regression ATT sensitivity is the mean
treated reference residual `Y - m0(X)`. None of the reference estimates is labeled as ground truth.

For AIPW, report a robust influence-function standard error and a 95% Wald
interval, along with propensity overlap, pre- and post-weighting SMDs, odds
weight quantiles and maximum, the count affected by propensity clipping, and
effective sample size `ESS = (sum w)^2 / sum(w^2)`. The weighted-control SMD
uses odds weights normalized to sum to one for balance calculations.

For test method `m` and split `r`, define error relative to the
reference-cohort AIPW estimate as:

`Error_AIPW_(m,r) = ATT_test_(m,r) - ATT_AIPW_reference_r`

Report mean squared error and RMSE relative to the reference-cohort AIPW
estimate across the `R` splits. Lower values indicate closer agreement with
that estimate, not greater accuracy relative to the unknown true causal
effect. Differences between the reference and test cohorts may contribute to
this error. The AIPW reference may itself be biased or retain residual
confounding. This remains a **pseudo-reference comparison**, not evaluation
against the true causal effect.

These repeated splits are **within-cohort resampling**: every split is drawn
from the same eligible 2024 cohort, and records may appear in the test sample
in one split and the reference sample in another. They are not independent
validation cohorts or independent replications. Summaries across splits
describe sensitivity to the random partition of this cohort; they do not
provide external validation or make the source births independent across
repetitions.

The 2024 cohort has about 80,000 treated singleton births before matching, so
a 1% test sample contains about 800 treated births before matching and may
contain fewer after matching. Test-sample estimates may consequently be noisy.
The later plan is to consider adding 2023, 2022, and earlier Natality years to
increase sample size and improve the stability of the reference comparison.
The present work remains 2024 only. Before pooling years, harmonize variables
and eligibility rules and document how calendar year affects the target
population and analysis.

The historical runs used one split and seed `20261022`. A final repetition
count and seed procedure have not been selected. Record and freeze them before
the next comparison; do not treat the historical one-split results as repeated
validation. See the [current experiment configuration](current_experiment_configuration.md)
for the recorded historical settings and decisions still open.

## Staged LLM workflow

Apply the same covariate-weighting task and Natality design in three stages:

1. **Manual chat-interface matching:** obtain covariate priorities in a new,
   isolated session using the
   [outcome-blind manual-chat protocol](weight%20extraction%20protocol/manual_chat_weight_protocol.md)
   and [standalone prompt](weight%20extraction%20protocol/llm_prompt_covariate_weights.md).
   Preserve the recorded weights as a separate method input for comparison.
2. **DeepSeek API:** apply the same weighting task through the separate
   implementation in [`cdc natality/src/get_deepseek_weights.py`](../../cdc%20natality/src/get_deepseek_weights.py).
   Preserve its exact prompt, settings, returned weights, and API response in
   the timestamped run record; the currently selected outcome-blind DeepSeek
   weights are the default input for matching runs. The manual-chat weights
   remain available by passing their JSON path with `--weights-json`.
3. **Advanced API:** then use the more advanced API/model(to be identified).

For every stage, give the LLM only the pre-specified covariate names,
definitions, coding, research question, and relevant pre-treatment rationale
needed to assign weights. Do not provide outcome values. The LLM assigns
covariate weights.

Request structured output that can be checked and applied reproducibly. Record
the interface or model and version, exact prompt, settings, date, returned
weights, any retries, and any manual changes. Use the resulting weights
consistently across repeated splits for that stage; do not tune weights against
test outcomes. Selecting DeepSeek as the current default is an operational
project choice; it does not establish that DeepSeek weights perform better.

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
  coding and scaling. Estimate its ATT in the test cohort.
- **PCA Mahalanobis matching:** use the existing 23 encoded columns and fixed
  category schema. For each split, standardize these columns using means and
  population standard deviations from the pooled 1% test cohort, then fit PCA
  on that cohort only. Retain the smallest number of components reaching 90%
  cumulative explained variance. Match using ordinary Mahalanobis distance
  computed from the covariance of the retained PC scores, without multiplying
  distances by another explained-variance weight. Apply the shared 1:1
  nearest-neighbor, replacement, no-caliper rule. Do not use outcomes in
  standardization, PCA, or matching.

### Additional comparators

- **Propensity-score matching:** fit an unpenalized logistic regression for
  treatment using the 23 encoded covariates, preprocessing, treatment, and
  records in the 1% test sample in each split. Match those same test records on
  their fitted logit propensity scores using 1:1 nearest-neighbor matching
  with replacement and no caliper. Resolve ties by the smallest source record
  number.
- **Genetic matching:** use a genetic-matching procedure to select distance weights and apply the generalized Mahalanobis distance metric.


## Evaluation and reporting

For every matching method and split, report:

- ATT, control-clustered standard error, matched-control reuse, median and
  90th-percentile matching distance, and balance before and after matching.
- For balance, report signed SMDs for each numeric and binary source
  covariate. For each categorical source covariate, report proportion SMDs for
  every fixed-schema level and its maximum absolute level SMD. Do not count
  encoded Helmert columns as separate covariates. Give each encoded column's
  source covariate in the feature-map output.
- Treatment-group overlap or covariate-space matchability.
- Number and proportion of treated births retained or matched.
- Sensitivity of balance and retention to prespecified matching settings and
  covariate weights.
- Reference-cohort AIPW-ATT, its influence-function standard error and 95%
  interval, IPW-ATT, and outcome-regression ATT as separately named estimates.
- Test-sample ATT for each matching comparator, including identity-matrix
  generalized Mahalanobis, PSM, and the LLM-weighted methods.
- Reference AIPW propensity-score quantiles and overlap, weighted SMDs, odds
  weight quantiles and maximum, clipping count, and effective sample size.

Report ATT uncertainty alongside the reference-error metrics defined above.
For the initial matched ATT, estimate uncertainty with a control-clustered
standard error to account for reuse of the same control for multiple treated
records.
Do not describe reference error as error against the true causal effect. Do
not interpret improved balance alone as proof of improved effect estimation.

## Reproducibility

Document the cohort definition, variable coding, covariate set, split
assignments or seed procedure, LLM prompts and settings, returned weights,
matching specifications, reference estimator, and metric calculations before
the final method comparison. Preserve enough outputs to reproduce each
method's estimate and diagnostic for each split. By default, each run's
detailed results, method summary, and encoded-column feature map are saved in
a new dated `{repeats}-split YYYYMMDD` folder under
`cdc natality/results/matching results/`;
see the [current experiment configuration](current_experiment_configuration.md)
for the file naming convention and recorded runs.
