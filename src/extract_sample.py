import csv
from pathlib import Path

source_path = Path(
    "data/raw/2024/Nat2024us/Nat2024PublicUS.c20250512.r20250708.txt"
)
output_path = Path(
    "data/processed/2024/sample_extract_1000.csv"
)

expected_record_length = 1345
sample_size = 1000

# Positions are 1-based and inclusive, as listed in the CDC User Guide.
# Python slices start at 0 and exclude the end position.
fields = {
    "MAGER": (75, 76),
    "MRACEHISP": (117, 117),
    "DMAR": (120, 120),
    "MEDUC": (124, 124),
    "PRIORLIVE": (171, 172),
    "PRIORDEAD": (173, 174),
    "CIG_0": (253, 254),
    "CIG0_R": (261, 261),
    "CIG1_R": (262, 262),
    "CIG2_R": (263, 263),
    "CIG3_R": (264, 264),
    "F_CIGS_0": (265, 265),
    "F_CIGS_1": (266, 266),
    "F_CIGS_2": (267, 267),
    "F_CIGS_3": (268, 268),
    "CIG_REC": (269, 269),
    "BMI_R": (287, 287),
    "PWgt_R": (292, 294),
    "F_PWGT": (295, 295),
    "DPLURAL": (454, 454),
    "DBWT": (504, 507),
    "BWTR12": (509, 510),
    "BWTR4": (511, 511),
}

if not source_path.exists():
    raise FileNotFoundError(f"Data file not found: {source_path}")

output_path.parent.mkdir(parents=True, exist_ok=True)

fieldnames = ["record_number", *fields.keys()]
records_written = 0

with source_path.open("r", encoding="latin-1", newline="") as source:
    with output_path.open(
        "w", encoding="utf-8", newline=""
    ) as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for record_number, line in enumerate(source, start=1):
            if records_written >= sample_size:
                break

            record = line.rstrip("\r\n")

            if len(record) != expected_record_length:
                raise ValueError(
                    f"Record {record_number} has length {len(record)}; "
                    f"expected {expected_record_length}"
                )

            row = {"record_number": record_number}

            for field, (start, end) in fields.items():
                row[field] = record[start - 1 : end]

            writer.writerow(row)
            records_written += 1

print(f"Records written: {records_written}")
print(f"Output file: {output_path}")