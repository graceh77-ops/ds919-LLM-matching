"""Recreate and export a saved streamed reference/test split."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_matching_experiment import _make_streamed_split


def export_saved_split(metadata_path: Path, output_dir: Path) -> None:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("repeats") != 1 or len(metadata.get("split_seeds", [])) != 1:
        raise ValueError("This exporter expects metadata for exactly one saved split.")
    if metadata.get("pilot_rows") is not None:
        raise ValueError("Pilot runs do not represent the full cohort split.")

    input_path = Path(metadata["input"])
    split_seed = int(metadata["split_seeds"][0])
    test_fraction = float(metadata["test_fraction_within_treatment_by_year_strata"])
    output_dir.mkdir(parents=True, exist_ok=True)
    reference_path = output_dir / "reference_99pct.csv"
    test_path = output_dir / "test_1pct.csv"
    manifest_path = output_dir / "split_manifest.json"
    existing = [p for p in (reference_path, test_path, manifest_path) if p.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite existing split exports: {existing[0]}")

    test, reference_batches, reference_counts = _make_streamed_split(
        input_path, test_fraction, split_seed
    )
    test.to_csv(test_path, index=False)
    reference_rows_written = 0
    first_reference_chunk = True
    try:
        for batch in reference_batches():
            batch.to_csv(
                reference_path,
                mode="w" if first_reference_chunk else "a",
                header=first_reference_chunk,
                index=False,
            )
            first_reference_chunk = False
            reference_rows_written += len(batch)
    except Exception:
        test_path.unlink(missing_ok=True)
        reference_path.unlink(missing_ok=True)
        raise

    if reference_rows_written != reference_counts["rows"]:
        test_path.unlink(missing_ok=True)
        reference_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Wrote {reference_rows_written:,} reference rows; expected "
            f"{reference_counts['rows']:,}."
        )

    manifest = {
        "source_run_metadata": str(metadata_path.resolve()),
        "input": str(input_path.resolve()),
        "split_seed": split_seed,
        "test_fraction_within_treatment_by_year_strata": test_fraction,
        "split_design": "within-cohort treatment-by-year-stratified resampling",
        "selection_reproduced_with": "run_matching_experiment._make_streamed_split",
        "reference_file": reference_path.name,
        "test_file": test_path.name,
        "reference_rows": reference_rows_written,
        "reference_treated": reference_counts["treated"],
        "reference_controls": reference_counts["controls"],
        "test_rows": len(test),
        "test_treated": int(test["treatment_binary"].sum()),
        "test_controls": int((test["treatment_binary"] == 0).sum()),
        "columns": list(test.columns),
        "note": "Files contain analysis-cohort records and are ignored by Git under data/.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    export_saved_split(args.metadata, args.output_dir)


if __name__ == "__main__":
    main()
