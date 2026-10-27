# ACIC 2016 Application

This folder prepares the ACIC 2016 semi-synthetic benchmark for a separate
evaluation of the project's matching methods. The replication loader and
single-replication runner are available. The runner currently compares
identity generalized Mahalanobis, propensity score matching, and PCA
Mahalanobis; optional LLM field weights can be provided as JSON.

The planned evaluation is summarized in the
[analysis protocol](docs/analysis_protocol.md).
The ACIC field descriptions and outcome-blind LLM elicitation procedure are in
the [field dictionary](docs/llm_matching/field_dictionary.md),
[standalone prompt](docs/llm_matching/weight_prompt.md), and
[weight protocol](docs/llm_matching/weight_protocol.md).

To inspect one replication from the repository root:

```powershell
python acic2016/src/load_acic_replication.py --setting 1 --replication zymu_13.csv
```

To run the matching pilot on that replication:

```powershell
python acic2016/src/run_matching_experiment.py --setting 1 --replication zymu_13.csv
```

The runner writes method diagnostics, the replication references, and the
encoded-column feature map to a new numbered pilot folder
(`pilot_runN_YYYYMMDDTHHMMSSZ`) under `acic2016/results/`. It does not
overwrite an existing run. A one-replication pilot is not evidence of
performance across the benchmark; the full evaluation covers 77 settings and
100 replications per setting.

## Data layout

The full archive and extracted data are stored locally under `data/raw/`:

```text
data/raw/
├── data_cf_all.tar.gz
└── full_data/
    ├── x.csv
    ├── 1/
    │   └── zymu_*.csv
    ├── ...
    └── 77/
        └── zymu_*.csv
```

The extracted folder contains all 77 simulation settings, with 100 replication
files per setting. `x.csv` contains the shared covariates. Each `zymu_*.csv`
contains treatment assignment (`z`), noisy potential outcomes (`y0`, `y1`), and
expected potential outcomes (`mu0`, `mu1`). The observed outcome is
`z * y1 + (1 - z) * y0`.

The full archive includes the 20 settings used in the competition's
do-it-yourself track as well as the other 57 settings. Duplicate standalone
`zy_1.csv`–`zy_20.csv` files were removed after their treatment and observed
outcomes were matched to the corresponding archive replications. The archive
and extracted data are ignored by Git; do not commit raw or processed data.

## Reference effect

The competition target is the sample average treatment effect on the treated
(SATT):

```text
mean(y1 - y0 among rows where z = 1)
```

This realized SATT is the primary reference when evaluating estimates against
the known simulation outcomes. The expected contrast
`mean(mu1 - mu0 among rows where z = 1)` may be reported separately as a
secondary reference; it is not the same quantity as the realized SATT.

## Citation

For academic use, cite the competition paper:

> Dorie, V., Hill, J., Shalit, U., Scott, M., and Cervone, D. (2019).
> “Automated versus Do-It-Yourself Methods for Causal Inference: Lessons
> Learned from a Data Analysis Competition.” *Statistical Science*, 34(1),
> 43–68. <https://doi.org/10.1214/18-STS667>.

Also cite the [ACIC 2016 competition description](https://jenniferhill7.wixsite.com/acic-2016/competition)
and the [CATENets ACIC 2016 loader](https://github.com/AliciaCurth/CATENets/blob/main/catenets/datasets/dataset_acic2016.py)
when describing the full potential-outcome archive and its file organization.
