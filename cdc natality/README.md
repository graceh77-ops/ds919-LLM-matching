# CDC Natality Application

This folder contains the current dataset-specific implementation of the
LLM-assisted matching project: CDC Natality data on maternal smoking during
pregnancy and infant birth weight.

## Scope and status

The active analysis uses the 2024 singleton-birth cohort. The extraction code
supports a shared annual schema, but only the 2024 fixed-width layout has been
verified. A future year must have its own reviewed layout and documented code
harmonization before extraction. The current AIPW and matching models are
Natality-specific and do not automatically generalize to a different dataset.

## Contents

- `config/natality_layouts/`: verified year-specific fixed-width layouts.
- `src/`: Natality extraction, cohort preparation, and matching programs.
- `docs/maternal_smoking_birthweight/`: cohort, variable, and data protocols.
- `data/raw/` and `data/processed/`: local inputs and derived data; ignored by
  Git.
- `results/`: QC summaries and experiment outputs.

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
the required split count and seed. See the experiment configuration and
multi-year pipeline documentation before running pooled-year comparisons.

Python dependencies are listed in the repository-root `requirements.txt`.
Install them from the repository root with:

```powershell
python -m pip install -r requirements.txt
```
