# ACIC 2016 Weight Search

This folder contains a separate implementation for learning matching weights
on ACIC 2016 simulation replications. It is isolated from the existing ACIC
benchmark runner and its results.

The pilot and full runner read ACIC input data from `data/raw/full_data/`.
Keep raw data out of Git; the `data/` folder is ignored. The current benchmark
code remains unchanged.

## Contents

- `config/experiment.json`: pilot defaults and the proposed full split.
- `docs/experiment_design.md`: concise decisions and evaluation boundaries.
- `src/coordinate_search.py`: reusable one-coordinate-at-a-time optimizer.
- `src/run_pilot.py`: configurable ACIC pilot runner (accepts partial data).
- `src/run_experiment.py`: replication split, search, validation selection, and test runner.
- `jobs/pilot.sge`: SCC batch-job wrapper.
- `jobs/experiment.sge`: SCC wrapper for the full experiment.
- `results/` and `logs/`: generated results and scheduler logs.

The pilot defaults to setting 1, the first five loader-sorted replication files,
all 58 source fields, both
identity and LLM starting vectors, and one coordinate-search sweep. These
replications are development/training data and must not be assigned to the final
test set.

Run from this directory. The data path, settings, replication IDs, field set,
starting vectors, candidate multipliers, sweep count, and output path can all be
overridden from the command line:

```bash
python src/run_pilot.py --data-dir data/raw/full_data \
  --settings 1 --replications first:5 --starts both \
  --multipliers 0.1 0.5 1 2 10 --max-sweeps 1
```

For SCC, submit the batch wrapper with the same overrides:

```bash
qsub jobs/pilot.sge
# Or override selected defaults:
qsub jobs/pilot.sge --data-dir /path/to/full_data \
  --settings 1 --replications first:5 --starts both \
  --multipliers 0.1 0.5 1 2 10 --max-sweeps 1
```

This runner accepts the ACIC directory layout. A different dataset format needs
its own data adapter and a valid reference-effect field; the search algorithm
itself is reusable.

## Full experiment

The full runner expects all 100 replications for each selected setting under
`data/raw/full_data/`. It creates a seeded 60/20/20 split within each setting, keeping the
five pilot replications in training. It searches on all training replications,
selects the best checkpoint (initial, after sweep one, or after sweep two) on
validation, then evaluates the frozen weights once on test. It does not refit
on train plus validation.
Test summaries include the original identity and LLM starting weights alongside
their searched versions, plus the existing propensity-score logit and PCA
Mahalanobis baselines, so all methods use the same held-out replications.

From this directory on SCC:

```bash
qsub jobs/experiment.sge
```

Defaults are all 77 settings, both identity and LLM starts, seed 919, up to two
sweeps, and four worker processes to score the five multiplier candidates for
each covariate in parallel. Override them as needed, for example:

```bash
qsub jobs/experiment.sge --settings 1-10 --starts identity --max-sweeps 2
```

To include an estimated propensity-score logit as a 59th search dimension, pass
`--include-propensity-score`. The score is fit separately within each ACIC
replication from its treatment assignments and the 79 encoded covariates; ACIC
files do not supply a propensity score. The identity start gives the added
dimension weight 1. The LLM start appends the same default weight (override with
`--propensity-score-start-weight`). A pooled augmented covariance transform is
fit from training replications only and reused for validation and test. This is
a separate run; it does not change a job that was already submitted.

For example, use a distinct results directory when submitting the
propensity-augmented version:

```bash
qsub jobs/experiment.sge --include-propensity-score \
  --output-dir results/full_experiment_with_propensity_score
```

The job script requests four cores and 120 hours. The runner writes an atomic
`checkpoint.json` after each completed covariate and test model. If the job is
interrupted, submit again with the same output directory and `--resume` to
continue from the last checkpoint. Use a new output directory for each fresh run:

```bash
qsub jobs/experiment.sge --output-dir results/full_experiment_checkpointed
qsub jobs/experiment.sge --output-dir results/full_experiment_checkpointed --resume
```

