"""Combine extracted annual files that use the project's common field schema."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


REQUIRED_COLUMNS = {"schema_version", "birth_year", "record_number"}
SUPPORTED_SCHEMA_VERSION = "natality_core_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inputs", type=Path, nargs="+", required=True,
        help="Annual extracted_natality.csv files, one per year.",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def combine(inputs: list[Path], output: Path) -> int:
    if len(inputs) < 2:
        raise ValueError("Provide at least two annual extraction files to combine.")
    headers: list[str] | None = None
    years: set[str] = set()
    record_count = 0
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8", newline="") as target:
        writer: csv.DictWriter | None = None
        for input_path in inputs:
            if not input_path.exists():
                raise FileNotFoundError(f"Annual extraction not found: {input_path}")
            with input_path.open("r", encoding="utf-8-sig", newline="") as source:
                reader = csv.DictReader(source)
                if reader.fieldnames is None:
                    raise ValueError(f"No header row in {input_path}")
                current_header = reader.fieldnames
                if not REQUIRED_COLUMNS.issubset(current_header):
                    raise ValueError(
                        f"{input_path} must include {sorted(REQUIRED_COLUMNS)}."
                    )
                if headers is None:
                    headers = current_header
                    writer = csv.DictWriter(target, fieldnames=headers)
                    writer.writeheader()
                elif current_header != headers:
                    missing = sorted(set(headers) - set(current_header))
                    extra = sorted(set(current_header) - set(headers))
                    raise ValueError(
                        f"Schema mismatch in {input_path}; missing={missing}, extra={extra}."
                    )

                for row in reader:
                    year = (row.get("birth_year") or "").strip()
                    if not year.isdigit() or len(year) != 4:
                        raise ValueError(f"Invalid birth_year {year!r} in {input_path}.")
                    if row.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
                        raise ValueError(
                            f"Unsupported schema_version {row.get('schema_version')!r} "
                            f"in {input_path}. Expected {SUPPORTED_SCHEMA_VERSION!r}."
                        )
                    years.add(year)
                    if writer is None:
                        raise RuntimeError("Output writer was not initialized.")
                    writer.writerow(row)
                    record_count += 1

    if len(years) != len(inputs):
        raise ValueError(
            "Each input must represent a distinct year; found years "
            f"{sorted(years)} for {len(inputs)} files."
        )
    print(f"Years combined: {', '.join(sorted(years))}")
    print(f"Records written: {record_count:,}")
    print(f"Output file: {output}")
    return record_count


def main() -> None:
    args = parse_args()
    combine(args.inputs, args.output)


if __name__ == "__main__":
    main()
