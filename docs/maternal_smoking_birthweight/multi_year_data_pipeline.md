# Multi-year Natality Data Pipeline

## Purpose and status

The scripts use a shared annual extraction schema so verified CDC Natality
layouts can feed the same cohort-preparation and matching programs. The current
repository contains a layout verified for **2024 only**. Layouts for 2023,
2022, 2010, and any other year must be checked against that year's CDC User
Guide before extraction. Year-agnostic means the analysis code can consume the
shared schema; it does not mean annual source files have the same field
positions, code definitions, or reporting flags.

## Shared extraction schema

Each annual extraction contains:

- `schema_version`: currently `natality_core_v1`;
- `birth_year`: the file's birth year;
- `record_number`: a year-prefixed unique integer ID, used for stable record
  identification and match tie-breaking;
- `source_record_number`: the original row number within that year's file;
- the canonical project field names used by cohort preparation, including
  treatment, outcome, plurality, the ten covariates, and reporting flags.

Initial extraction keeps field values as strings. A layout may optionally
define `value_maps` for code changes verified in the relevant User Guide. Keep
such recodes explicit and documented; do not map unknown or unavailable codes
to a valid analysis category. The raw source file remains unchanged.

The year-prefixed ID is `year * 100,000,000 + source row number`. The original
within-file row number is also preserved in `source_record_number`.

## Prepare an annual layout

Create `config/natality_layouts/<year>.json` using the structure in
[`config/natality_layouts/2024.json`](../../config/natality_layouts/2024.json).
Verify the file encoding, record length, every 1-based inclusive position,
variable definitions, code sets, and reporting-flag meanings against that
year's official User Guide. The `fields` keys are canonical project names;
their values are source positions for that year. If codes differ, document
and add explicit `value_maps` only after reviewing the source definitions.

For a year whose variables or reporting rules cannot be mapped to the current
schema without changing their meaning, stop and review the cohort rules. Do
not fill unavailable fields with fabricated values or silently drop the
corresponding eligibility check.

## Workflow

1. Extract each year using its verified layout. For example, after creating
   and reviewing the 2023 layout:

   ```powershell
   python src/total_extraction.py --year 2023 `
     --layout config/natality_layouts/2023.json `
     --input data/raw/2023/<official-file-name>.txt `
     --output data/processed/2023/extracted_natality.csv
   ```

   The 2024 defaults still point to the existing 2024 file and output path.

2. Combine the annual extractions. The combiner checks identical column
   schemas and distinct year labels:

   ```powershell
   python src/combine_natality_years.py `
     --inputs data/processed/2022/extracted_natality.csv `
             data/processed/2023/extracted_natality.csv `
             data/processed/2024/extracted_natality.csv `
     --output data/processed/pooled_2022_2024/extracted_natality.csv
   ```

3. Prepare the pooled analysis cohort and year-by-treatment QC summary:

   ```powershell
   python src/prepare_analysis_data.py `
     --input data/processed/pooled_2022_2024/extracted_natality.csv
   ```

   The singleton and all-births analysis files are written beside the input;
   the QC report is written under `results/`.

4. Run the existing experiment against the prepared singleton file by passing
   its path to `src/run_matching_experiment.py --input ...`. The matching and
   AIPW implementations require the same canonical covariate and derived
   treatment/outcome fields as the 2024 cohort.

## Methodological decision before pooled-year results

`birth_year` is retained in annual and pooled files for audit and reporting,
but the current matching and reference models use the existing ten
prespecified covariates and do **not** adjust for birth year. A pooled analysis
may therefore mix year-specific treatment and birth-weight patterns. Before
using pooled results as substantive comparisons, decide and document whether
year should enter AIPW and matching, whether splits should be stratified by
year as well as treatment, and whether effects should also be reported by
year. Adding year to model covariates changes the frozen ten-field/23-column
specification and requires updated encoding, model, PCA, and LLM-weight
protocol decisions.

Until those decisions and annual code harmonization are reviewed, the
2024-only experiment remains the current analysis. Raw and processed datasets
are local inputs and must not be committed to Git.
