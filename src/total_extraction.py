"""Extract a CDC Natality fixed-width file using a verified year layout.

Each layout JSON maps canonical project field names to that year's 1-based,
inclusive positions in the source record. Only the 2024 layout is currently
provided; add a reviewed layout after checking the corresponding CDC User Guide.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_YEAR = 2024


def load_layout(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as source:
        layout = json.load(source)
    for key in ("year", "expected_record_length", "encoding", "fields"):
        if key not in layout:
            raise ValueError(f"Layout {path} is missing required key {key!r}.")
    fields = layout["fields"]
    if not isinstance(fields, dict) or not fields:
        raise ValueError("Layout 'fields' must be a non-empty object.")
    for name, positions in fields.items():
        if (
            not isinstance(positions, list)
            or len(positions) != 2
            or not all(isinstance(value, int) for value in positions)
            or positions[0] < 1
            or positions[1] < positions[0]
        ):
            raise ValueError(
                f"Invalid 1-based inclusive positions for {name!r}: {positions!r}"
            )
    return layout


def extract_file(source_path: Path, output_path: Path, layout: dict[str, Any]) -> int:
    if not source_path.exists():
        raise FileNotFoundError(f"Natality source file not found: {source_path}")

    year = int(layout["year"])
    expected_length = int(layout["expected_record_length"])
    fields: dict[str, list[int]] = layout["fields"]
    value_maps: dict[str, dict[str, str]] = layout.get("value_maps", {})
    if expected_length < max(end for _, end in fields.values()):
        raise ValueError("A configured field extends beyond the expected record length.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "schema_version", "birth_year", "record_number", "source_record_number", *fields
    ]
    records_written = 0
    with source_path.open("r", encoding=layout["encoding"], newline="") as source:
        with output_path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for source_record_number, line in enumerate(source, start=1):
                record = line.rstrip("\r\n")
                if len(record) != expected_length:
                    raise ValueError(
                        f"Record {source_record_number} has length {len(record)}; "
                        f"layout for {year} expects {expected_length}."
                    )

                # Keep a wide range for the within-file row number so annual
                # IDs stay distinct when years are pooled.
                record_id = year * 100_000_000 + source_record_number
                row: dict[str, Any] = {
                    "schema_version": "natality_core_v1",
                    "birth_year": year,
                    "record_number": record_id,
                    "source_record_number": source_record_number,
                }
                for field, (start, end) in fields.items():
                    value = record[start - 1 : end]
                    value_map = value_maps.get(field, {})
                    row[field] = value_map.get(value.strip(), value)
                writer.writerow(row)
                records_written += 1
    return records_written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument(
        "--input",
        type=Path,
        help="Raw fixed-width input file. Defaults to data/raw/<year>/.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Extracted CSV path. Defaults to data/processed/<year>/extracted_natality.csv.",
    )
    parser.add_argument(
        "--layout",
        type=Path,
        help="Verified layout JSON. Defaults to config/natality_layouts/<year>.json.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    layout_path = args.layout or PROJECT_ROOT / "config" / "natality_layouts" / f"{args.year}.json"
    layout = load_layout(layout_path)
    if int(layout["year"]) != args.year:
        raise ValueError(
            f"Requested year {args.year} does not match layout year {layout['year']}."
        )
    source_path = args.input or PROJECT_ROOT / layout.get(
        "default_input",
        f"data/raw/{args.year}/Nat{args.year}us/Nat{args.year}PublicUS.txt",
    )
    output_path = args.output or PROJECT_ROOT / layout.get(
        "default_output", f"data/processed/{args.year}/extracted_natality.csv"
    )
    count = extract_file(source_path, output_path, layout)
    print(f"Year: {args.year}")
    print(f"Records written: {count:,}")
    print(f"Output file: {output_path}")


if __name__ == "__main__":
    main()
