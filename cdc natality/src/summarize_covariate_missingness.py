import csv
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = (
    PROJECT_ROOT / "data" / "processed" / "2024" / "extracted_natality.csv"
)
OUTPUT_MD = PROJECT_ROOT / "results" / "primary_covariate_missingness.md"

TREATMENT_COLUMN = "CIG_REC"
PRIMARY_FIELDS = {
    "MAGER": (lambda value: value.isdigit() and 12 <= int(value) <= 50,
              "Valid age codes 12-50; 12 represents 10-12 years"),
    "MRACEHISP": (lambda value: value in {"1", "2", "3", "4", "5", "6", "7"},
                  "Code 8 is unknown or not stated"),
    "MEDUC": (lambda value: value in {"1", "2", "3", "4", "5", "6", "7", "8"},
              "Code 9 is unknown or not stated"),
    "CIG0_R": (lambda value: value in {"0", "1", "2", "3", "4", "5"},
               "Code 6 is unknown or not stated"),
    "PRIORLIVE": (lambda value: value.isdigit() and 0 <= int(value) <= 30,
                  "Code 99 is unknown or not stated"),
    "PRIORDEAD": (lambda value: value.isdigit() and 0 <= int(value) <= 30,
                  "Code 99 is unknown or not stated"),
    "BMI_R": (lambda value: value in {"1", "2", "3", "4", "5", "6"},
              "Code 9 is unknown or not stated"),
    "RF_PDIAB": (lambda value: value in {"Y", "N"},
                 "U or blank is unknown/not stated"),
    "RF_PHYPE": (lambda value: value in {"Y", "N"},
                 "U or blank is unknown/not stated"),
    "SEX": (lambda value: value in {"M", "F"},
            "Blank or other value is unknown/unexpected"),
}
UNKNOWN_CODES = {
    "MRACEHISP": "8",
    "MEDUC": "9",
    "CIG0_R": "6",
    "PRIORLIVE": "99",
    "PRIORDEAD": "99",
    "BMI_R": "9",
    "RF_PDIAB": "U",
    "RF_PHYPE": "U",
}

AUDIT_FIELDS = (
    "MAGE_IMPFLG",
    "MAGE_REPFLG",
    "MRACEIMP",
    "F_MHISP",
    "F_MEDUC",
    "F_M_HT",
    "F_PWGT",
    "F_CIGS_0",
    "F_RF_PDIAB",
    "F_RF_PHYPER",
    "IMP_SEX",
)
GESTATION_FIELDS = ("COMBGEST", "GESTREC10")
GESTATION_FLAGS = ("COMPGST_IMP", "OBGEST_FLG")
FLAG_CROSS_TABS = {
    "MAGER": ("MAGE_IMPFLG", "MAGE_REPFLG"),
    "MRACEHISP": ("MRACEIMP", "F_MHISP"),
    "MEDUC": ("F_MEDUC",),
    "CIG0_R": ("F_CIGS_0",),
    # F_M_HT is BMI_R's reporting flag; F_PWGT is kept as a descriptive
    # cross-check for PWgt_R, not as an eligibility requirement.
    "BMI_R": ("F_M_HT", "F_PWGT"),
    "RF_PDIAB": ("F_RF_PDIAB",),
    "RF_PHYPE": ("F_RF_PHYPER",),
    "SEX": ("IMP_SEX",),
}
REQUIRED_REPORTING_FLAGS = {
    "F_MHISP",
    "F_MEDUC",
    "F_CIGS_0",
    "F_M_HT",
    "F_RF_PDIAB",
    "F_RF_PHYPER",
}


def normalize(value):
    return (value or "").strip().upper()


def status(value, valid_function, unknown_code):
    if not value:
        return "blank"
    if value == unknown_code:
        return "unknown code"
    if valid_function(value):
        return "observed"
    return "unexpected code"


def count_table(counter):
    if not counter:
        return "- No values found."
    return "\n".join(
        f"- `{value or '[blank]'}`: {count:,}"
        for value, count in sorted(counter.items())
    )


def main():
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Analysis cohort not found: {INPUT_CSV}")

    status_counts = {field: Counter() for field in PRIMARY_FIELDS}
    value_counts = {field: Counter() for field in PRIMARY_FIELDS}
    audit_counts = {field: Counter() for field in AUDIT_FIELDS}
    flag_cross_tabs = {
        (field, flag): Counter()
        for field, flags in FLAG_CROSS_TABS.items()
        for flag in flags
    }
    gestation_counts = {field: Counter() for field in GESTATION_FIELDS}
    gestation_flag_counts = {field: Counter() for field in GESTATION_FLAGS}
    complete_by_treatment = Counter()
    missing_by_treatment = Counter()
    reported_complete_by_treatment = Counter()
    reported_missing_by_treatment = Counter()
    total_rows = 0

    with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        required = set(PRIMARY_FIELDS) | {TREATMENT_COLUMN} | set(AUDIT_FIELDS)
        required |= set(GESTATION_FIELDS) | set(GESTATION_FLAGS)
        required |= {"DBWT", "DPLURAL"}
        missing_columns = required - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

        for row in reader:
            treatment = normalize(row.get(TREATMENT_COLUMN))
            outcome = normalize(row.get("DBWT"))
            try:
                outcome_valid = int(outcome) != 9999
            except ValueError:
                outcome_valid = False
            if treatment not in {"Y", "N"} or not outcome_valid:
                continue
            if normalize(row.get("DPLURAL")) != "1":
                continue

            total_rows += 1
            complete_case = True

            for field, (valid_function, _) in PRIMARY_FIELDS.items():
                value = normalize(row.get(field))
                value_counts[field][value] += 1
                value_status = status(value, valid_function, UNKNOWN_CODES.get(field))
                status_counts[field][value_status] += 1
                if value_status != "observed":
                    complete_case = False

            for field in AUDIT_FIELDS:
                flag_value = normalize(row.get(field))
                audit_counts[field][flag_value] += 1
            for field, flags in FLAG_CROSS_TABS.items():
                value = normalize(row.get(field))
                value_status = status(
                    value,
                    PRIMARY_FIELDS[field][0],
                    UNKNOWN_CODES.get(field),
                )
                for flag in flags:
                    flag_value = normalize(row.get(flag))
                    flag_cross_tabs[(field, flag)][(value_status, flag_value)] += 1
            for field in GESTATION_FIELDS:
                gestation_counts[field][normalize(row.get(field))] += 1
            for field in GESTATION_FLAGS:
                gestation_flag_counts[field][normalize(row.get(field))] += 1

            if complete_case:
                complete_by_treatment[treatment] += 1
            else:
                missing_by_treatment[treatment] += 1

            all_reporting_flags_present = all(
                normalize(row.get(flag)) == "1"
                for flag in REQUIRED_REPORTING_FLAGS
            )
            if complete_case and all_reporting_flags_present:
                reported_complete_by_treatment[treatment] += 1
            else:
                reported_missing_by_treatment[treatment] += 1

    complete_cases = sum(complete_by_treatment.values())
    reported_complete_cases = sum(reported_complete_by_treatment.values())
    removed = total_rows - complete_cases
    rows = [
        "# Primary Covariate Missingness Review",
        "",
        "## Scope",
        "",
        f"- Input: `{INPUT_CSV.relative_to(PROJECT_ROOT)}`",
        f"- Singleton analysis cohort rows before covariate handling: {total_rows:,}",
        f"- Proposed primary covariates assessed: {', '.join(f'`{field}`' for field in PRIMARY_FIELDS)}",
        "- This report profiles unknown codes, blanks, and unexpected values. It does not apply a missing-data rule or alter the cohort.",
        "",
        "## Primary covariate value status",
        "",
        "Unknown/not-stated codes and blank values are shown separately. Reporting and imputation flags are descriptive audits; their values are not automatically treated as missing covariates.",
        "",
        "| Field | Observed | Unknown code | Blank | Unexpected code | Coding note |",
        "|---|---:|---:|---:|---:|---|",
    ]

    for field, (_, note) in PRIMARY_FIELDS.items():
        counts = status_counts[field]
        rows.append(
            f"| `{field}` | {counts['observed']:,} | {counts['unknown code']:,} "
            f"| {counts['blank']:,} | {counts['unexpected code']:,} | {note} |"
        )

    rows.extend(["", "## Observed value distributions", ""])
    for field, counts in value_counts.items():
        rows.extend([f"### `{field}`", "", count_table(counts), ""])

    rows.extend([
        "## Reporting and imputation flag distributions",
        "",
        "Flags are reported as coded in the cohort. For reporting flags, `0` means non-reporting and `1` means reporting where defined by the User Guide. Age/race/sex imputation flags describe processing, not missing covariate values.",
        "",
    ])
    for field, counts in audit_counts.items():
        rows.extend([f"### `{field}`", "", count_table(counts), ""])

    rows.extend([
        "## Covariate-by-flag cross-checks",
        "",
        "These tables check whether a selected covariate value appears alongside a non-reporting or imputation flag. The flag-aware scenario requires the selected item to be reported where a reporting flag applies, including Hispanic origin, education, pre-pregnancy smoking, maternal height for BMI_R, diabetes, and hypertension. F_PWGT is shown as an audit cross-check for the separate PWgt_R field and is not an eligibility requirement. Imputation flags are reviewed but do not by themselves make a value missing.",
        "",
    ])
    for (field, flag), counts in flag_cross_tabs.items():
        flag_values = sorted({flag_value for _, flag_value in counts})
        rows.extend([
            f"### `{field}` by `{flag}`",
            "",
            "| Covariate status | " + " | ".join(f"`{v or '[blank]'}`" for v in flag_values) + " |",
            "|---|" + "---:|" * len(flag_values),
        ])
        for value_status in ("observed", "unknown code", "blank", "unexpected code"):
            rows.append(
                f"| {value_status} | "
                + " | ".join(f"{counts[(value_status, flag_value)]:,}" for flag_value in flag_values)
                + " |"
            )
        rows.append("")

    rows.extend([
        "## Gestational-age sensitivity-variable profile",
        "",
        "Gestational age is not part of the proposed primary set. `COMBGEST` is detailed weeks; `GESTREC10` is the coarser 10-category recode. Their flags describe imputation/source and should be reviewed before the sensitivity analysis.",
        "",
    ])
    for field, counts in gestation_counts.items():
        rows.extend([f"### `{field}`", "", count_table(counts), ""])
    for field, counts in gestation_flag_counts.items():
        rows.extend([f"### `{field}`", "", count_table(counts), ""])

    rows.extend([
        "## Complete-case scenarios",
        "",
        "These are descriptive scenarios: retain a record only when every proposed primary covariate has an observed, recognized value. The flag-aware scenario also requires a reporting flag for fields where CDC supplies one. CDC-imputed ages, races, and sex remain observed values in these counts; their imputation flags are reported separately.",
        "",
        f"- Complete cases: {complete_cases:,} ({complete_cases / total_rows:.2%})",
        f"- Records excluded by this strict rule: {removed:,} ({removed / total_rows:.2%})",
        f"- Complete cases when required reporting flags must also equal `1`: {reported_complete_cases:,} ({reported_complete_cases / total_rows:.2%})",
        f"- Records excluded by the flag-aware scenario: {total_rows - reported_complete_cases:,} ({(total_rows - reported_complete_cases) / total_rows:.2%})",
        "",
        "| Treatment | Code-based complete | Code-based excluded | Flag-aware complete | Flag-aware excluded |",
        "|---|---:|---:|---:|---:|",
    ])
    for treatment in ("Y", "N"):
        rows.append(
            f"| `{treatment}` | {complete_by_treatment[treatment]:,} "
            f"| {missing_by_treatment[treatment]:,} "
            f"| {reported_complete_by_treatment[treatment]:,} "
            f"| {reported_missing_by_treatment[treatment]:,} |"
        )
    rows.extend([
        "",
        "## Interpretation and next decision",
        "",
        "The flag-aware complete-case rule was selected for the primary analysis cohort and applied in `prepare_analysis_data.py`. The code-based complete-case count is shown as an eligibility comparison only. Reporting flags are eligibility checks, not matching covariates; CDC-imputed age, race, and sex values remain eligible and their imputation flags are retained for audit.",
        "",
    ])

    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text("\n".join(rows), encoding="utf-8")
    print(f"Cohort rows: {total_rows:,}")
    print(f"Strict complete cases: {complete_cases:,}")
    print(f"Strict complete-case exclusions: {removed:,}")
    print(f"Report: {OUTPUT_MD}")


if __name__ == "__main__":
    main()
