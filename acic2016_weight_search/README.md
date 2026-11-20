# ACIC 2016 Weight Search

This folder contains a separate implementation for learning matching weights
on ACIC 2016 simulation replications. It is isolated from the existing ACIC
benchmark runner and its results.

The experiment will use the existing ACIC input data at
`../acic2016/data/raw/full_data/`; raw data will not be copied into this
folder or committed to Git. The current benchmark code remains unchanged.

## Contents

- `config/experiment.json`: pilot defaults and the proposed full split.
- `docs/experiment_design.md`: concise decisions and evaluation boundaries.
- `src/coordinate_search.py`: reusable one-coordinate-at-a-time optimizer.
- `src/run_pilot.py`: configurable ACIC pilot runner.
- `jobs/pilot.sge`: SCC batch-job wrapper.
- `results/` and `logs/`: generated results and scheduler logs.

The pilot defaults to setting 1, replications 1-5, all 58 source fields, both
identity and LLM starting vectors, and one coordinate-search sweep. These
replications are development/training data and must not be assigned to the final
test set.

Run from this directory. The data path, settings, replication IDs, field set,
starting vectors, candidate multipliers, sweep count, and output path can all be
overridden from the command line:

```bash
python src/run_pilot.py --data-dir ../acic2016/data/raw/full_data \
  --settings 1 --replications 1-5 --starts both \
  --multipliers 0.1 0.5 1 2 10 --max-sweeps 1
```

For SCC, submit the batch wrapper with the same overrides:

```bash
qsub jobs/pilot.sge
# Or override selected defaults:
qsub jobs/pilot.sge --data-dir /path/to/full_data \
  --settings 1 --replications 1-5 --starts both \
  --multipliers 0.1 0.5 1 2 10 --max-sweeps 1
```

This runner accepts the ACIC directory layout. A different dataset format needs
its own data adapter and a valid reference-effect field; the search algorithm
itself is reusable.

