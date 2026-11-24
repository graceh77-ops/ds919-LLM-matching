# CDC Natality Application

This folder contains the current dataset-specific implementation of the
LLM-assisted matching project: CDC Natality data on maternal smoking during
pregnancy and infant birth weight.

## Scope and status

The active design targets 2016-2024 singleton births and includes `birth_year`
as an eleventh categorical, LLM-weighted field. Raw public-use files for all
nine years are present under `data/raw/<year>/`. A separate fixed-width layout
JSON has been prepared for each year from 2016 through 2024 and checked against
the corresponding CDC User Guide. Shared code meanings are documented.
`F_PWGT` is retained for audit but is not an eligibility requirement because
the analysis uses `BMI_R`. All nine annual extractions are complete
(33,589,282 records); every source record passed the configured record-length
check. The pooled singleton analysis cohort contains 30,924,495 births
(1,590,168 exposed and 29,334,327 unexposed). Existing experiment outputs use the earlier
2024-only, ten-field design and are historical. The current AIPW and matching
models are Natality-specific and do not automatically generalize to a
different dataset.

## Contents

- `config/natality_layouts/`: verified year-specific fixed-width layouts.
- `src/`: Natality extraction, cohort preparation, and matching programs.
- `docs/`: cohort, variable, data, and multi-year protocols.
- `data/raw/` and `data/processed/`: local inputs and derived data; ignored by
  Git.
- `results/`: QC summaries and experiment outputs.

New pooled-year matching runs and their LLM weight records are written to
`results/matching results_2016-2024/`. Earlier 2024-only experiment results in
`results/matching results/` are retained as historical outputs.

The streamed entropy-balancing ATT sensitivity check is documented in
[`docs/entropy_balancing_protocol.md`](docs/entropy_balancing_protocol.md).
Its implementation is `src/run_entropy_balancing_validation.py`; results are
written under `results/entropy-balancing/`.

The propensity-score-augmented representation keeps the original encoded
covariates and appends the fitted treatment probability as one additional
coordinate; it does not use covariate residuals. Its optional comparators are
identity Mahalanobis, LLM-weighted generalized Mahalanobis, and PCA Mahalanobis.
They are implemented under `src/ps_augmented_matching/` and documented in
[`docs/ps_augmented_matching/protocol.md`](docs/ps_augmented_matching/protocol.md).
Enable them with `--include-ps-covariate`; new outputs are saved under
`results/ps_augmented_matching/`. All use test-cohort covariates and treatment
for matching-side fitting. Obtain a fresh 12-score set, including a
propensity-probability weight, using
[`docs/ps_augmented_matching/deepseek_api_setup.md`](docs/ps_augmented_matching/deepseek_api_setup.md).
The old `--include-ps-residual` option remains a command-line alias but runs
the new augmented-covariate design.

The shared LLM workflow and its current Natality implementation notes are in
the repository-level [`docs/llm_matching/`](../docs/llm_matching/protocol_LLM_matching.md).

## Run the programs

From the repository root, enter this directory first:

```powershell
Set-Location "cdc natality"
```

The completed annual outputs are in
`data/processed/pooled_2016_2024/annual/<year>/extracted_natality.csv`. To
repeat the extraction without overwriting earlier year-specific outputs, use:

```powershell
foreach ($year in 2016..2024) {
    $output = "data/processed/pooled_2016_2024/annual/$year/extracted_natality.csv"
    python src/total_extraction.py --year $year --output $output
    if ($LASTEXITCODE -ne 0) { break }
}
```

The nine extracted files have matching 43-column headers. They have been
combined and the singleton/all-births cohorts prepared. The current QC report is
[`results/full_data_qc_summary_pooled_2016_2024.md`](results/full_data_qc_summary_pooled_2016_2024.md).
To repeat the workflow, use the commands in
[`docs/multi_year_data_pipeline.md`](docs/multi_year_data_pipeline.md).

For an experiment, pass the prepared singleton cohort using `--input` and set
the required split count and seed. Standard pooled-year runs use an
eleven-field weight file. Runs with `--include-ps-covariate` require a fresh
twelve-score file that also includes `PROPENSITY_SCORE`; see the dedicated
elicitation instructions above. Use `--no-llm-weights` for conventional
comparators when no LLM weights are being evaluated. Prior ten-field weight
files cannot be used with the pooled-year schema. See the experiment
configuration and multi-year pipeline documentation before running pooled-
year comparisons.

The experiment runner streams the cohort CSV in batches, retains only each
split's test rows for matching, and streams reference rows through the AIPW
calculations. This reduces RAM use substantially, while adding repeated disk
reads during propensity-model fitting. The test cohort and PCA/matching
workspaces still use RAM, so check available memory before a full run. Reference
weight and propensity quantiles are estimated from a bounded random sample;
their sample sizes and approximate status are recorded in the detailed output.

## Coordinate and grid search pilot

The pilot samples 30,000 singleton births, splits them 60/20/20 by
treatment-by-year strata, and runs coordinate search from identity and current
PS-augmented LLM weights. Its restricted five-level grid varies
`CIG0_R`, `MAGER`, and `PROPENSITY_SCORE` around the LLM vector (125 candidates;
other weights stay fixed). AIPW is the tuning reference, not known causal
truth. Pilot test results are for code/timing checks, not study conclusions.

From this directory on SCC, after creating `logs/`, submit:

```bash
qsub jobs/weight_search_pilot.sge --algorithms both --pilot-rows 30000 \
  --weights-json results/ps_augmented_matching/deepseek_api/20261102T060435Z/weights.json \
  --grid-fields CIG0_R MAGER PROPENSITY_SCORE --max-sweeps 1 \
  --multipliers 0.1 0.5 1 2 10
```

Use `--algorithms coordinate` or `--algorithms grid` to run one search alone.
Each run writes a timestamped directory under
`results/weight_search_pilots/`; the coordinate history, grid candidates,
validation scores, selected weights, test estimates, and run metadata are
separate files there.

### Sharded full-vector grid benchmark

`src/prepare_weight_grid_pilot.py`, `src/run_weight_grid_shard.py`, and
`src/merge_weight_grid_shards.py` implement a disjoint prefix-sharded grid.
Preparation writes one shared 60/20/20 pilot split. Each shard scores its
assigned full-vector multiplier combinations on train and validation. The
merge step refuses to evaluate test until every shard has completed, then
evaluates the global validation winner once. With 12 weight dimensions and five
multipliers, the complete grid has 244,140,625 candidates; benchmark a shard
before deciding whether the full search fits the available compute budget.

After pulling the code on SCC, submit preparation from this directory:

```bash
mkdir -p logs
qsub jobs/weight_grid_prepare.sge \
  --pilot-rows 30000 --seed 919 \
  --weights-json results/ps_augmented_matching/deepseek_api/20261102T060435Z/weights.json \
  --output-dir results/weight_search_pilots/grid12d_benchmark_20261124
```

After preparation finishes, benchmark shard 0 (25 candidates):

```bash
qsub -t 1-1 jobs/weight_grid_shard.sge \
  --prepared-dir results/weight_search_pilots/grid12d_benchmark_20261124 \
  --prefix-dimensions 10
```

Read `shards/prefix10_shard00000000/shard_summary.json` for candidate timing
and validation scores. A full-array plan should be chosen only after using that
measurement to estimate runtime and storage.

Python dependencies are listed in the repository-root `requirements.txt`.
Install them from the repository root with:

```powershell
python -m pip install -r requirements.txt
```
