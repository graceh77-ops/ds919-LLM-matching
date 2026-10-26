# ACIC 2016 Analysis Protocol

## Evaluation design

- The motivating scientific scenario is a hypothetical study of birthweight's
  effect on IQ. In ACIC, each replication supplies a simulated binary treatment
  `z`, continuous potential outcomes `y0` and `y1`, and expected outcomes
  `mu0` and `mu1`. Do not assign a clinical meaning or birthweight cutoff to
  `z = 1`; the available competition description does not define it.
- Analyze each of the 77 simulation settings and its 100 replications as a
  separate cohort of 4,802 units. Do not make a 99/1 reference/test split.
- Match treated and control units within each replication. The known potential
  outcomes are reserved for calculating reference effects and evaluating
  matched estimates; they must not enter preprocessing, weight assignment, or
  match selection. The current loader does read the outcome columns and
  calculates the reference effects before matching, but matching-coordinate
  construction and match selection use only covariates and treatment; outcome
  values enter the evaluator after matches have been selected.
- The primary reference is realized SATT,
  `mean(y1 - y0 | z = 1)`. Report the expected effect,
  `mean(mu1 - mu0 | z = 1)`, separately as a secondary reference.
- After matches are fixed, calculate matched ATT from the observed outcome
  `y = z*y1 + (1-z)*y0`. Compare it with realized SATT and label the difference
  as error relative to the known SATT, not as error against an estimated
  pseudo-ground-truth.

## Shared covariate representation

Use all 58 columns from `x.csv`, with no outcome or treatment columns included
as covariates. Apply one fixed schema in every replication:

- Encode `x_2` (levels A-F), `x_21` (A-P), and `x_24` (A-E) as one-hot
  indicators with A as the reference level.
- Keep the other 55 fields numeric on their original scales.
- This produces 79 encoded columns. Save a feature map from every encoded
  column to its source `x_` field. Balance summaries treat each source field as
  one covariate: numeric SMD for numeric fields and per-level proportion SMDs
  for categorical fields, summarized by the maximum absolute level SMD.

The feature encoding is fixed across replications. The proposed semantic
labels for `x_1` through `x_58` are provisional order-based mappings; see the
[mapping evidence audit](covariate_mapping_evidence.md). Keep the same input
fields for each matching comparator, and interpret LLM weights as priorities
assigned to the prompt's described fields, not verified clinical confounder
importance. Any method-specific
centering, scaling, covariance, PCA, or propensity model is fitted separately
within the current replication using only its covariates and treatment.

## Matching configuration

Use 1:1 nearest-neighbor matching with replacement and no caliper for all
matching comparators. Match each treated unit to the closest control within
the same replication. Resolve exact distance ties by original row order.

- **Identity generalized Mahalanobis:** use the full sample covariance of the
  79 encoded columns and the generalized Mahalanobis formula with `V = I`.
- **LLM-weighted generalized Mahalanobis:** use the same covariance and
  formula, with one nonnegative LLM weight per original source field. Map a
  field's weight to all encoded columns derived from that field. Normalize the
  expanded diagonal matrix to mean weight 1; weights do not need to sum to 1.
  A column-normalized allocation may be reported only as a separately named
  sensitivity analysis.
- **PCA Mahalanobis:** standardize the 79 columns using the current
  replication's pooled covariates (`ddof = 0`), fit PCA on those covariates,
  and retain the fewest components explaining at least 90% of total variance.
  Use ordinary Mahalanobis distance on retained PC scores, with no additional
  explained-variance weighting.
- **PSM:** fit an unpenalized logistic regression of `z` on the same 79 encoded
  covariates within the replication. Match on the estimated propensity-score
  logit using the shared nearest-neighbor rule. Standardize columns internally
  for numerical optimization; with an unpenalized linear logit and intercept,
  this is a reparameterization of the same model. Record a fitting failure
  rather than silently changing the model specification.

For covariance-based distances, estimate covariance with `ddof = 1`. Floor
eigenvalues at `1e-8` times the largest eigenvalue before inverse-square-root
construction. Apply the same rule to retained PCA score covariance. Report the
number of retained PCs and cumulative explained variance for PCA.

LLM field weights come from a separately recorded DeepSeek elicitation. The
current prompt gives provisional field descriptions but omits most encoding
details, category code meanings, and measurement units. Report the elicitation
as description-based weighting with provisional labels; do not imply that the
mapping or the weights represent validated clinical importance.

## Outcomes and reporting

For every method and replication, report matched ATT, difference from realized
SATT, difference from expected SATT, uncertainty estimate, treated count,
unique controls, maximum control reuse, distance summaries where applicable,
and pre/post-match covariate balance. Report reference SATTs once per
replication rather than repeating them as if they were separate method
estimates. Aggregate results by method within each setting and across all 77
settings; retain per-replication results for analysis. Treat the 7,700
replications as simulation replications, not independent real-world cohorts.
For matched ATT uncertainty, use a control-clustered standard error of paired
treated-minus-matched-control differences, clustering on matched control ID to
account for control reuse. Report it as a matching-estimator uncertainty
diagnostic; the known SATT comparison remains the primary accuracy measure.

## Implementation status

`src/load_acic_replication.py` loads one replication, creates the fixed encoded
covariate matrix and feature map, derives observed outcomes, and calculates
realized and expected SATT. `src/run_matching_experiment.py` implements
identity generalized Mahalanobis, PSM, and PCA Mahalanobis matching, with
optional LLM field weights supplied as JSON. An initial one-replication pilot
ran on setting 1, `zymu_13.csv`, without LLM weights. The latest DeepSeek
vector is saved at
`results/llm_weights/deepseek_api/20261026T234904Z/weights.json` and is the
planned vector for the next pilot. The full 7,700-replication evaluation and
the LLM-weighted pilot have not been run.
