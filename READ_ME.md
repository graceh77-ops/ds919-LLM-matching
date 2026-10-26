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
- [ACIC 2016 application](acic2016/README.md) contains the ACIC benchmark data
  and its current data-layout notes. Its analysis implementation is still to
  be developed.
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
2016-2024 birth year as an LLM-weighted covariate. Raw public-use files for all
nine years are present, and each year has a CDC User Guide-reviewed layout
JSON. All nine annual extractions have completed, yielding 33,589,282 records;
each record passed the configured fixed-width length check. `F_PWGT` is
retained for audit but is not an eligibility requirement because the analysis
uses the `BMI_R` recode. The annual files have been combined and the pooled
singleton analysis cohort contains 30,924,495 births (1,590,168 exposed and
29,334,327 unexposed). The application is not a general-purpose
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

## ACIC 2016 application

The ACIC application is being prepared as a separate benchmark for the
matching-method study. The full data archive is stored under
`acic2016/data/raw/`; its extracted layout has `x.csv` and setup folders 1–77
directly under `acic2016/data/raw/full_data/`. Each setup folder contains 100
replication files. ACIC-specific matching code and experiment documentation
have not yet been added. See the [ACIC application README](acic2016/README.md)
for the data format, reference estimand, and citation details.
