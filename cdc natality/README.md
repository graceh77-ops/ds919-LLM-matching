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
check. Combining the extracts and preparing the pooled cohort remain. Existing experiment outputs use the earlier
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

The nine extracted files have matching 43-column headers. Combine them and prepare the pooled analysis
cohort using the commands in
[`docs/multi_year_data_pipeline.md`](docs/multi_year_data_pipeline.md).

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
