import csv
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Change this filename if your full extraction has a different name.
INPUT_CSV = PROJECT_ROOT / "data" / "processed" / "2024" / "extracted_natality.csv"

OUTPUT_CSV = (
    PROJECT_ROOT / "data" / "processed" / "2024" / "analysis_cohort_singletons.csv"
)
SENSITIVITY_OUTPUT_CSV = (
    PROJECT_ROOT / "data" / "processed" / "2024" / "analysis_cohort_all_births.csv"
)
SUMMARY_MD = PROJECT_ROOT / "results" / "full_data_qc_summary.md"

TREATMENT_COLUMN = "CIG_REC"
OUTCOME_COLUMN = "DBWT"
DPLURAL_COLUMN = "DPLURAL"
MISSING_OUTCOME_CODE = 9999


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_CSV}\n"
            "Update INPUT_CSV to the filename of your full extracted dataset."
        )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    SENSITIVITY_OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)

    input_rows = 0
    treatment_values = Counter()
    included_treatment_values = Counter()
    excluded_treatment_only = 0
    excluded_outcome_only = 0
    excluded_both = 0
    dbwt_9999_count = 0
    invalid_dbwt_count = 0
    valid_birthweights = []
    eligible_singletons = 0
    excluded_non_singleton = 0

    with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)

        if reader.fieldnames is None:
            raise ValueError("The input CSV has no header row.")

        required_columns = {TREATMENT_COLUMN, OUTCOME_COLUMN, DPLURAL_COLUMN}
        missing_columns = required_columns - set(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                f"Required columns not found: {sorted(missing_columns)}\n"
                f"Available columns: {reader.fieldnames}"
            )

        output_columns = list(reader.fieldnames)
        for column in ("treatment_binary", "birthweight_g"):
            if column not in output_columns:
                output_columns.append(column)

        with OUTPUT_CSV.open("w", encoding="utf-8", newline="") as target, \
                SENSITIVITY_OUTPUT_CSV.open("w", encoding="utf-8", newline="") as sensitivity_target:
            writer = csv.DictWriter(target, fieldnames=output_columns)
            sensitivity_writer = csv.DictWriter(
                sensitivity_target, fieldnames=output_columns
            )
            writer.writeheader()
            sensitivity_writer.writeheader()

            for row in reader:
                input_rows += 1

                treatment = (row.get(TREATMENT_COLUMN) or "").strip().upper()
                treatment_values[treatment] += 1
                treatment_valid = treatment in {"Y", "N"}

                outcome_text = (row.get(OUTCOME_COLUMN) or "").strip()
                try:
                    birthweight = int(outcome_text)
                    outcome_valid = birthweight != MISSING_OUTCOME_CODE
                    if birthweight == MISSING_OUTCOME_CODE:
                        dbwt_9999_count += 1
                except ValueError:
                    birthweight = None
                    outcome_valid = False
                    invalid_dbwt_count += 1

                if not treatment_valid and not outcome_valid:
                    excluded_both += 1
                    continue
                if not treatment_valid:
                    excluded_treatment_only += 1
                    continue
                if not outcome_valid:
                    excluded_outcome_only += 1
                    continue

                row["treatment_binary"] = "1" if treatment == "Y" else "0"
                row["birthweight_g"] = str(birthweight)
                sensitivity_writer.writerow(row)
                if (row.get(DPLURAL_COLUMN) or "").strip() == "1":
                    writer.writerow(row)
                    eligible_singletons += 1
                else:
                    excluded_non_singleton += 1

                included_treatment_values[treatment] += 1
                valid_birthweights.append(birthweight)

    included_rows = sum(included_treatment_values.values())

    if valid_birthweights:
        min_birthweight = min(valid_birthweights)
        max_birthweight = max(valid_birthweights)
    else:
        min_birthweight = "N/A"
        max_birthweight = "N/A"

    summary = f"""# Full Data Quality Summary

## Input and output

- Input file: `{INPUT_CSV.relative_to(PROJECT_ROOT)}`
- Primary analysis cohort (singleton births): `{OUTPUT_CSV.relative_to(PROJECT_ROOT)}`
- Sensitivity cohort (all eligible births): `{SENSITIVITY_OUTPUT_CSV.relative_to(PROJECT_ROOT)}`
- Input rows: {input_rows:,}
- All-births cohort rows: {included_rows:,}
- Singleton primary cohort rows (`DPLURAL = 1`): {eligible_singletons:,}
- Eligible non-singleton births excluded from primary cohort: {excluded_non_singleton:,}

## Treatment values in the input

{format_counts(treatment_values)}

## Exclusions

- Unknown or invalid treatment only: {excluded_treatment_only:,}
- Missing or invalid birth weight only: {excluded_outcome_only:,}
- Both treatment and birth weight invalid or missing: {excluded_both:,}
- `DBWT` equal to the missing code `9999`: {dbwt_9999_count:,}
- Blank or non-integer `DBWT`: {invalid_dbwt_count:,}

## Analysis cohort

- `CIG_REC = Y` (treatment_binary = 1): {included_treatment_values["Y"]:,}
- `CIG_REC = N` (treatment_binary = 0): {included_treatment_values["N"]:,}
- Birth weight unit: grams
- Valid birth weight minimum: {min_birthweight}
- Valid birth weight maximum: {max_birthweight}

Covariate values were retained as extracted. No complete-case filtering or
covariate recoding was performed in this step.
"""

    SUMMARY_MD.write_text(summary, encoding="utf-8")

    print(f"Input rows: {input_rows:,}")
    print(f"All-births cohort rows: {included_rows:,}")
    print(f"Singleton primary cohort rows: {eligible_singletons:,}")
    print(f"Analysis cohort: {OUTPUT_CSV}")
    print(f"QC summary: {SUMMARY_MD}")


def format_counts(counts):
    if not counts:
        return "- No values found."

    return "\n".join(
        f"- `{value or '[blank]'}`: {count:,}"
        for value, count in sorted(counts.items())
    )


if __name__ == "__main__":
    main()
