import argparse
import csv
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "2024" / "extracted_natality.csv"

TREATMENT_COLUMN = "CIG_REC"
OUTCOME_COLUMN = "DBWT"
DPLURAL_COLUMN = "DPLURAL"
MISSING_OUTCOME_CODE = 9999
MIN_VALID_BIRTHWEIGHT_G = 227
MAX_VALID_BIRTHWEIGHT_G = 8165

# Values must be recognized, and these item-level reporting flags must confirm
# that the source item was reported. Imputation flags for age, race, and sex do
# not disqualify otherwise usable values.
PRIMARY_COVARIATE_VALIDATORS = {
    "birth_year": lambda value: value.isdigit() and 2016 <= int(value) <= 2024,
    "MAGER": lambda value: value.isdigit() and 12 <= int(value) <= 50,
    "MRACEHISP": lambda value: value in {"1", "2", "3", "4", "5", "6", "7"},
    "MEDUC": lambda value: value in {"1", "2", "3", "4", "5", "6", "7", "8"},
    "CIG0_R": lambda value: value in {"0", "1", "2", "3", "4", "5"},
    "PRIORLIVE": lambda value: value.isdigit() and 0 <= int(value) <= 30,
    "PRIORDEAD": lambda value: value.isdigit() and 0 <= int(value) <= 30,
    "BMI_R": lambda value: value in {"1", "2", "3", "4", "5", "6"},
    "RF_PDIAB": lambda value: value in {"Y", "N"},
    "RF_PHYPE": lambda value: value in {"Y", "N"},
    "SEX": lambda value: value in {"M", "F"},
}
REQUIRED_REPORTING_FLAGS = (
    "F_MHISP",
    "F_MEDUC",
    "F_CIGS_0",
    "F_M_HT",
    "F_RF_PDIAB",
    "F_RF_PHYPER",
)


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare a harmonized Natality analysis cohort.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--all-births-output", type=Path)
    parser.add_argument("--summary", type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    input_csv = args.input.resolve()
    output_csv = args.output or input_csv.with_name("analysis_cohort_singletons.csv")
    sensitivity_output_csv = args.all_births_output or input_csv.with_name(
        "analysis_cohort_all_births.csv"
    )
    summary_md = args.summary or PROJECT_ROOT / "results" / (
        "full_data_qc_summary.md" if input_csv == DEFAULT_INPUT.resolve()
        else f"full_data_qc_summary_{input_csv.parent.name}.md"
    )

    if not input_csv.exists():
        raise FileNotFoundError(
            f"Input file not found: {input_csv}\n"
            "Run src/total_extraction.py with a verified layout or provide --input."
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    sensitivity_output_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_md.parent.mkdir(parents=True, exist_ok=True)

    input_rows = 0
    treatment_values = Counter()
    included_treatment_values = Counter()
    excluded_treatment_only = 0
    excluded_outcome_only = 0
    excluded_both = 0
    dbwt_9999_count = 0
    invalid_dbwt_count = 0
    min_birthweight = None
    max_birthweight = None
    eligible_singletons = 0
    excluded_non_singleton = 0
    complete_case_rows = 0
    excluded_covariate_rows = 0
    complete_case_treatment_values = Counter()
    incomplete_case_treatment_values = Counter()
    singleton_complete_case_treatment_values = Counter()
    singleton_incomplete_case_treatment_values = Counter()
    final_by_year_treatment = Counter()

    with input_csv.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)

        if reader.fieldnames is None:
            raise ValueError("The input CSV has no header row.")

        required_columns = (
            {TREATMENT_COLUMN, OUTCOME_COLUMN, DPLURAL_COLUMN}
            | set(PRIMARY_COVARIATE_VALIDATORS)
            | set(REQUIRED_REPORTING_FLAGS)
        )
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

        with output_csv.open("w", encoding="utf-8", newline="") as target, \
                sensitivity_output_csv.open("w", encoding="utf-8", newline="") as sensitivity_target:
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
                    if birthweight == MISSING_OUTCOME_CODE:
                        outcome_valid = False
                        dbwt_9999_count += 1
                    elif MIN_VALID_BIRTHWEIGHT_G <= birthweight <= MAX_VALID_BIRTHWEIGHT_G:
                        outcome_valid = True
                    else:
                        outcome_valid = False
                        invalid_dbwt_count += 1
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
                covariates_valid = all(
                    validator((row.get(field) or "").strip().upper())
                    for field, validator in PRIMARY_COVARIATE_VALIDATORS.items()
                )
                flags_reported = all(
                    (row.get(flag) or "").strip() == "1"
                    for flag in REQUIRED_REPORTING_FLAGS
                )
                complete_case = covariates_valid and flags_reported
                is_singleton = (row.get(DPLURAL_COLUMN) or "").strip() == "1"
                if complete_case:
                    complete_case_rows += 1
                    complete_case_treatment_values[treatment] += 1
                    if is_singleton:
                        singleton_complete_case_treatment_values[treatment] += 1
                else:
                    excluded_covariate_rows += 1
                    incomplete_case_treatment_values[treatment] += 1
                    if is_singleton:
                        singleton_incomplete_case_treatment_values[treatment] += 1

                # Apply the same covariate rule to primary and sensitivity
                # populations so estimates use comparable eligibility rules.
                if is_singleton:
                    eligible_singletons += 1
                else:
                    excluded_non_singleton += 1

                if complete_case:
                    sensitivity_writer.writerow(row)
                    year = (row.get("birth_year") or "unknown").strip()
                    final_by_year_treatment[(year, treatment)] += 1
                    if (row.get(DPLURAL_COLUMN) or "").strip() == "1":
                        writer.writerow(row)

                included_treatment_values[treatment] += 1
                min_birthweight = (
                    birthweight if min_birthweight is None
                    else min(min_birthweight, birthweight)
                )
                max_birthweight = (
                    birthweight if max_birthweight is None
                    else max(max_birthweight, birthweight)
                )

    included_rows = sum(included_treatment_values.values())

    if min_birthweight is None:
        min_birthweight = "N/A"
        max_birthweight = "N/A"

    year_breakdown = "\n".join(
        f"- {year}: `CIG_REC = Y` {final_by_year_treatment[(year, 'Y')]:,}; "
        f"`CIG_REC = N` {final_by_year_treatment[(year, 'N')]:,}"
        for year in sorted({key[0] for key in final_by_year_treatment})
    ) or "- No year field was supplied."

    summary = f"""# Full Data Quality Summary

## Input and output

- Input file: `{display_path(input_csv)}`
- Primary analysis cohort (singleton births): `{display_path(output_csv)}`
- Sensitivity cohort (all eligible births): `{display_path(sensitivity_output_csv)}`
- Input rows: {input_rows:,}
- All-births eligible rows before covariate filtering: {included_rows:,}
- Singleton primary eligible rows before covariate filtering (`DPLURAL = 1`): {eligible_singletons:,}
- Eligible non-singleton births excluded from primary cohort: {excluded_non_singleton:,}
- All-births records meeting the flag-aware covariate rule: {complete_case_rows:,}
- All-births records excluded for incomplete/unknown covariates or non-reporting flags: {excluded_covariate_rows:,}
- Singleton records meeting the flag-aware covariate rule: {sum(singleton_complete_case_treatment_values.values()):,}
- Singleton records excluded by the flag-aware covariate rule: {sum(singleton_incomplete_case_treatment_values.values()):,}
- Final all-births sensitivity file rows: {complete_case_rows:,}
- Final singleton primary file rows: {sum(singleton_complete_case_treatment_values.values()):,}

## Treatment values in the input

{format_counts(treatment_values)}

## Exclusions

- Unknown or invalid treatment only: {excluded_treatment_only:,}
- Missing or invalid birth weight only: {excluded_outcome_only:,}
- Both treatment and birth weight invalid or missing: {excluded_both:,}
- `DBWT` equal to the missing code `9999`: {dbwt_9999_count:,}
- `DBWT` outside 227-8,165 grams, blank, or non-integer: {invalid_dbwt_count:,}

## Analysis cohort

- `CIG_REC = Y` (treatment_binary = 1): {included_treatment_values["Y"]:,}
- `CIG_REC = N` (treatment_binary = 0): {included_treatment_values["N"]:,}
- Flag-aware complete-case all-births `Y`: {complete_case_treatment_values["Y"]:,}
- Flag-aware complete-case all-births `N`: {complete_case_treatment_values["N"]:,}
- Flag-aware complete-case all-births excluded `Y`: {incomplete_case_treatment_values["Y"]:,}
- Flag-aware complete-case all-births excluded `N`: {incomplete_case_treatment_values["N"]:,}
- Flag-aware complete-case singleton `Y`: {singleton_complete_case_treatment_values["Y"]:,}
- Flag-aware complete-case singleton `N`: {singleton_complete_case_treatment_values["N"]:,}
- Flag-aware complete-case singleton excluded `Y`: {singleton_incomplete_case_treatment_values["Y"]:,}
- Flag-aware complete-case singleton excluded `N`: {singleton_incomplete_case_treatment_values["N"]:,}
- Final all-births eligible records by birth year and treatment:
{year_breakdown}
- Birth weight unit: grams
- Valid birth weight minimum: {min_birthweight}
- Valid birth weight maximum: {max_birthweight}

The analysis cohort files apply the flag-aware complete-case rule for all
primary covariates, including birth year in the supported 2016-2024 range.
Values must use recognized, non-unknown codes; reporting
flags `F_MHISP`, `F_MEDUC`, `F_CIGS_0`, `F_M_HT`, `F_RF_PDIAB`, and
`F_RF_PHYPER` must equal `1`. `F_PWGT` is retained as a source-data audit
field but is not an eligibility requirement because the selected covariate is
the valid `BMI_R` recode, not `PWgt_R`. CDC-imputed age, race, and sex values remain
eligible; their imputation flags are retained for audit. Gestational age is not
part of this primary eligibility rule.
"""

    summary_md.write_text(summary, encoding="utf-8")

    print(f"Input rows: {input_rows:,}")
    print(f"All-births cohort rows: {included_rows:,}")
    print(f"Singleton primary cohort rows: {eligible_singletons:,}")
    print(f"Analysis cohort: {output_csv}")
    print(f"QC summary: {summary_md}")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path.resolve())


def format_counts(counts):
    if not counts:
        return "- No values found."

    return "\n".join(
        f"- `{value or '[blank]'}`: {count:,}"
        for value, count in sorted(counts.items())
    )


if __name__ == "__main__":
    main()
