# LLM-Assisted Matching

This repository develops and documents a workflow for comparing LLM-assigned
covariate weights with conventional matching methods. Each dataset application
needs its own definitions, eligibility rules, harmonization, covariates, and
analysis configuration.

## Repository structure

- [`docs/llm_matching/`](docs/llm_matching/protocol_LLM_matching.md) contains
  the current matching and LLM weight-extraction protocols. Some documents
  describe the current Natality implementation and are identified as such;
  their study-specific choices are not universal defaults.
- [CDC Natality application](cdc%20natality/README.md) contains its source
  layouts, extraction and
  analysis code, study documentation, local data folders, and results.
- `requirements.txt` at the repository root lists the Python dependencies
  used by the current application.

For a future, unrelated dataset, create a separate application folder with its
own extraction or import code, harmonized schema, treatment and outcome
definitions, covariates, matching configuration, and documentation. Reuse
shared matching utilities only after their assumptions have been separated
from Natality-specific fields and verified for the new dataset. Do not reuse
Natality's 31-column encoding, smoking weights, cohort filters, or AIPW
specification automatically.

## Current application: CDC Natality

The active application studies maternal smoking during pregnancy and infant
birth weight in U.S. singleton births. The analysis design now includes
2016-2024 birth year as an LLM-weighted covariate. Raw public-use files for
2023 and 2024 are present, but only the 2024 data layout is verified so far.
The 2023 layout and each additional annual layout and its codes must be
reviewed before pooled analysis. The application is not a general-purpose
importer or matching engine for arbitrary datasets.

Start with:

- [Natality analysis protocol](cdc%20natality/docs/protocal_maternal_smoking_dataset.md)
- [Natality data reference](cdc%20natality/docs/data_reference.md)
- [Multi-year Natality pipeline](cdc%20natality/docs/multi_year_data_pipeline.md)
- [Current matching protocol](docs/llm_matching/protocol_LLM_matching.md)
- [Current experiment configuration](docs/llm_matching/current_experiment_configuration.md)

To work with the Natality application, change to its folder before running its
scripts:

```powershell
Set-Location "cdc natality"
python src/total_extraction.py
python src/prepare_analysis_data.py
```

The extraction command uses the local 2024 raw file by default. Raw and
processed data are ignored by Git and must remain local; commit code,
configuration, and documentation only when appropriate.
