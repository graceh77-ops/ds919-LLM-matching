# CDC Natality Application

This folder contains the current dataset-specific implementation of the
LLM-assisted matching project: CDC Natality data on maternal smoking during
pregnancy and infant birth weight.

## Scope and status

The active design targets 2016-2024 singleton births and includes `birth_year`
as an eleventh categorical, LLM-weighted field. The extraction code supports a
shared annual schema, but only the 2024 fixed-width layout has been verified.
Each additional year needs a reviewed layout and documented code
harmonization before extraction. Existing experiment outputs use the earlier
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

The shared LLM workflow and its current Natality implementation notes are in
the repository-level [`docs/llm_matching/`](../docs/llm_matching/protocol_LLM_matching.md).

## Run the programs

From the repository root, enter this directory first:

```powershell
Set-Location "cdc natality"
```

Then run annual extraction and cohort preparation:

```powershell
python src/total_extraction.py
python src/prepare_analysis_data.py
```

For an experiment, pass the prepared singleton cohort using `--input` and set
the required split count and seed. A matching run also requires an
eleven-field weight file via `--weights-json`; use `--no-llm-weights` to run
conventional comparators before a new outcome-blind weight vector is ready.
Prior ten-field weight files cannot be used with the pooled-year schema. See
the experiment configuration and multi-year pipeline documentation before
running pooled-year comparisons.

Python dependencies are listed in the repository-root `requirements.txt`.
Install them from the repository root with:

```powershell
python -m pip install -r requirements.txt
```
