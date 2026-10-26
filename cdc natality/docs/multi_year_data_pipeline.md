# Multi-year Natality Data Pipeline

## Purpose and status

The scripts use a shared annual extraction schema so verified CDC Natality
layouts can feed the same cohort-preparation and matching programs. Raw public-
use files for **2016 through 2024** are present under `data/raw/<year>/`.
Separate layout JSON files for each year are in `config/natality_layouts/` and
their field positions have been reviewed against the matching CDC User Guide.
Cross-year value-code harmonization and full-file extraction validation remain
before pooled analysis. Year-agnostic means the analysis code can consume the
shared schema; it does not mean annual source files have the same field
positions, code definitions, or reporting flags.

## Shared extraction schema

Download each annual Natality public-use file and its matching User Guide from
[CDC Vital Statistics Online](https://www.cdc.gov/NCHS/data_access/VitalStatsOnline.htm)
and the [CDC Natality documentation directory](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/DVS/natality/).
Place the unmodified annual files under `data/raw/<year>/`. Keep downloaded
archives and extracted fixed-width source files out of Git.

Each annual extraction contains:

- `schema_version`: currently `natality_core_v1`;
- `birth_year`: the file's birth year;
- `record_number`: a year-prefixed unique integer ID, used for stable record
  identification and match tie-breaking;
- `source_record_number`: the original row number within that year's file;
- the canonical project field names used by cohort preparation, including
  treatment, outcome, plurality, the ten clinical/demographic covariates,
  `birth_year`, and reporting flags.

Initial extraction keeps field values as strings. A layout may optionally
define `value_maps` for code changes verified in the relevant User Guide. Keep
such recodes explicit and documented; do not map unknown or unavailable codes
to a valid analysis category. The raw source file remains unchanged.

The year-prefixed ID is `year * 100,000,000 + source row number`. The original
within-file row number is also preserved in `source_record_number`.

## Prepare an annual layout

Each annual JSON uses the structure in
[`config/natality_layouts/2024.json`](../config/natality_layouts/2024.json),
with its own source-guide link, raw filename, output path, and source positions.
Each CDC guide lists a 1,330-character record layout. The first local record in
each raw file is 1,345 characters; each config records this observed length,
and the extractor checks all records against it. A full extraction has not yet
validated every line. The `fields` keys are canonical project names; their
values are that year's 1-based inclusive source positions. Cross-year code
definitions and reporting-flag behavior must still be checked before pooling;
document any confirmed changes using explicit `value_maps`.

For a year whose variables or reporting rules cannot be mapped to the current
schema without changing their meaning, stop and review the cohort rules. Do
not fill unavailable fields with fabricated values or silently drop the
corresponding eligibility check.

## Workflow

Run the following commands from the `cdc natality/` application directory. If
the terminal is at the repository root, first run `Set-Location "cdc natality"`.

1. Extract each year using its verified layout. Repeat this for every year
   from 2016 through 2024 after creating and reviewing that year's layout:

   ```powershell
   python src/total_extraction.py --year 2016 `
     --layout config/natality_layouts/2016.json `
     --input data/raw/2016/<official-file-name>.txt `
     --output data/processed/2016/extracted_natality.csv
   ```

   Each layout's default input points to the exact raw filename present under
   `data/raw/<year>/`; defaults can be overridden with `--input` and `--output`.

2. Combine the nine annual extractions. The combiner checks identical column
   schemas and distinct year labels:

   ```powershell
   python src/combine_natality_years.py `
     --inputs data/processed/2016/extracted_natality.csv `
             data/processed/2017/extracted_natality.csv `
             data/processed/2018/extracted_natality.csv `
             data/processed/2019/extracted_natality.csv `
             data/processed/2020/extracted_natality.csv `
             data/processed/2021/extracted_natality.csv `
             data/processed/2022/extracted_natality.csv `
             data/processed/2023/extracted_natality.csv `
             data/processed/2024/extracted_natality.csv `
     --output data/processed/pooled_2016_2024/extracted_natality.csv
   ```

3. Prepare the pooled analysis cohort and year-by-treatment QC summary:

   ```powershell
   python src/prepare_analysis_data.py `
     --input data/processed/pooled_2016_2024/extracted_natality.csv
   ```

   The singleton and all-births analysis files are written beside the input;
   the QC report is written under `results/`.

4. Run the existing experiment against the prepared singleton file by passing
   its path to `src/run_matching_experiment.py --input ...`. The matching and
   AIPW implementations require the same canonical covariate and derived
   treatment/outcome fields and `birth_year` field as the 2024 cohort.

## Pooled-year model decision

The pooled 2016-2024 design now includes `birth_year` as an eleventh
LLM-weighted field and as a covariate in AIPW and every matching comparator.
Encode the nine years categorically with eight fixed Helmert contrasts. The
LLM returns one field score for `birth_year`; the primary mapping repeats that
score over the eight encoded columns, with the existing column-normalized
field allocation as a sensitivity method. Split each treatment-by-year
stratum into the 99% reference and 1% test portions. Also report pooled
results and consider year-specific ATT summaries as a secondary description.

The code schema now supports years 2016-2024. Nine annual layout JSON files
have been prepared and their field positions reviewed against their
year-specific guides. Cross-year value-code harmonization and extraction of
the nine raw files remain before pooled estimates can be produced. Historical ten-field/23-column
results remain archived and are not directly comparable to the new
eleven-field/31-column design. Raw and processed datasets are local inputs and
must not be committed to Git.

New pooled-year matching runs and their new DeepSeek weight elicitation
records are saved under `results/matching results_2016-2024/`. Existing
2024-only files under `results/matching results/` remain historical and are
left in place.
