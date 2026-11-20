"""Run a configurable ACIC coordinate-search timing and code pilot."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from coordinate_search import coordinate_search


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACIC_SOURCE = PROJECT_ROOT / "acic2016" / "src"
if str(ACIC_SOURCE) not in sys.path:
    sys.path.insert(0, str(ACIC_SOURCE))

from load_acic_replication import load_replication  # noqa: E402
from run_matching_experiment import (  # noqa: E402
    _mahalanobis_coordinates,
    _matching_indices,
)


DEFAULT_DATA_DIR = PROJECT_ROOT / "acic2016" / "data" / "raw" / "full_data"
DEFAULT_LLM_WEIGHTS = (
    PROJECT_ROOT
    / "acic2016"
    / "results"
    / "llm_weights"
    / "deepseek_api"
    / "20261026T234904Z"
    / "weights.json"
)
DEFAULT_MULTIPLIERS = (0.1, 0.5, 1.0, 2.0, 10.0)
DEFAULT_CONFIG = PROJECT_ROOT / "acic2016_weight_search" / "config" / "experiment.json"
REPLICATION_PATTERN = re.compile(r"^zymu_(\d+)\.csv$")


def read_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as stream:
        config = json.load(stream)
    if not isinstance(config, dict):
        raise ValueError("Experiment config must contain a JSON object")
    return config


def resolve_config_path(value: str | Path, config_path: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (config_path.resolve().parent.parent / path).resolve()


def parse_integer_selection(value: str) -> list[int]:
    """Parse comma-separated integers/ranges such as ``1-5,9,12-14``."""
    selected: list[int] = []
    for piece in value.split(","):
        piece = piece.strip()
        if not piece:
            continue
        if "-" in piece:
            left, right = piece.split("-", 1)
            start, end = int(left), int(right)
            if end < start:
                raise argparse.ArgumentTypeError(f"Invalid range: {piece}")
            selected.extend(range(start, end + 1))
        else:
            selected.append(int(piece))
    if not selected or len(selected) != len(set(selected)):
        raise argparse.ArgumentTypeError("Selection must be nonempty and unique")
    return selected


def resolve_replication_files(value: str, setting: int, data_dir: Path) -> list[str]:
    """Resolve explicit numeric IDs or the first N files in loader order."""
    normalized = value.strip().lower()
    if normalized.startswith("first:"):
        count = int(normalized.split(":", 1)[1])
        setting_dir = Path(data_dir) / str(setting)
        if not setting_dir.is_dir():
            raise FileNotFoundError(f"ACIC setting folder not found: {setting_dir}")
        available = [
            path.name for path in setting_dir.iterdir()
            if path.is_file() and REPLICATION_PATTERN.fullmatch(path.name)
        ]
        available.sort(
            key=lambda name: int(REPLICATION_PATTERN.fullmatch(name).group(1))
        )
        if count < 1 or count > len(available):
            raise ValueError(
                f"Requested first {count} replications for setting {setting}, "
                f"which has {len(available)} files"
            )
        return available[:count]
    numbers = parse_integer_selection(value)
    return [f"zymu_{number}.csv" for number in numbers]


def load_field_weights(path: Path, fields: Sequence[str]) -> dict[str, float]:
    with path.open("r", encoding="utf-8-sig") as stream:
        raw = json.load(stream)
    if not isinstance(raw, dict) or set(raw) != set(fields):
        raise ValueError(f"Weight file must contain exactly these fields: {list(fields)}")
    weights = {field: float(raw[field]) for field in fields}
    if not np.isfinite(list(weights.values())).all() or min(weights.values()) <= 0:
        raise ValueError("Starting LLM weights must be finite and positive")
    return weights


def encoded_column_weights(feature_map, encoded_columns, field_weights):
    source_for_column = feature_map.set_index("encoded_column")["source_field"]
    missing = set(source_for_column.unique()) - set(field_weights)
    if missing:
        raise ValueError(f"Missing field weights for: {sorted(missing)}")
    expanded = np.asarray(
        [field_weights[source_for_column[column]] for column in encoded_columns],
        dtype=np.float64,
    )
    expanded /= expanded.mean()
    return expanded


def evaluate_weights(datasets, fields, weights, *, keep_rows=False):
    first = datasets[0]
    features = first.encoded_covariates.to_numpy(dtype=np.float64)
    if list(first.covariates.columns) != list(fields):
        raise ValueError("Dataset source fields changed unexpectedly")
    column_weights = encoded_column_weights(
        first.feature_map,
        list(first.encoded_covariates.columns),
        weights,
    )
    coordinates = _mahalanobis_coordinates(features, column_weights)
    errors = []
    rows = []
    for data in datasets:
        treatment = data.treatment.to_numpy(dtype=np.int8)
        treated, matched_controls, _ = _matching_indices(coordinates, treatment)
        observed = data.observed_outcome.to_numpy(dtype=np.float64)
        matched_att = float(np.mean(observed[treated] - observed[matched_controls]))
        error = matched_att - float(data.realized_satt)
        errors.append(error)
        rows.append({
            "setting": int(data.setting),
            "replication": data.replication_file,
            "matched_att": matched_att,
            "realized_satt": float(data.realized_satt),
            "error_vs_realized_satt": error,
        })
    rmse = math.sqrt(float(np.mean(np.square(errors))))
    return (rmse, rows) if keep_rows else rmse


def parse_args() -> argparse.Namespace:
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    config_args, _ = config_parser.parse_known_args()
    config_path = config_args.config.resolve()
    config = read_config(config_path)
    data_default = resolve_config_path(config.get("data_dir", DEFAULT_DATA_DIR), config_path)
    pilot = config.get("pilot", {})
    search = config.get("search", {})
    output = config.get("outputs", {}).get("directory", "results/pilot_runs")
    settings_default = ",".join(str(value) for value in pilot.get("settings", [1]))
    pilot_replications = pilot.get("replications", "first:5")
    replications_default = (
        pilot_replications
        if isinstance(pilot_replications, str)
        else ",".join(str(value) for value in pilot_replications)
    )
    initializations = search.get("initializations", ["identity", "llm"])
    starts_default = "both" if set(initializations) == {"identity", "llm"} else initializations[0]
    output_default = resolve_config_path(output, config_path)
    llm_default = resolve_config_path(search.get("llm_weights", DEFAULT_LLM_WEIGHTS), config_path)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=config_path)
    parser.add_argument("--data-dir", type=Path, default=data_default)
    parser.add_argument("--settings", default=settings_default, help="ACIC settings, e.g. 1 or 1-77")
    parser.add_argument(
        "--replications", default=replications_default,
        help="Use first:N for the first N loader-sorted files, or specify IDs such as 13,336720322",
    )
    parser.add_argument(
        "--field-set", default=search.get("field_set", "all"),
        help="all or a comma-separated subset such as x_1,x_3,x_24",
    )
    parser.add_argument(
        "--starts", choices=("identity", "llm", "both"), default=starts_default
    )
    parser.add_argument("--llm-weights", type=Path, default=llm_default)
    parser.add_argument(
        "--multipliers", type=float, nargs="+",
        default=search.get("candidate_multipliers", list(DEFAULT_MULTIPLIERS)),
        help="Positive relative weight factors; must include 1",
    )
    parser.add_argument("--max-sweeps", type=int, default=search.get("max_sweeps", 1))
    parser.add_argument("--output-dir", type=Path, default=output_default)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = parse_integer_selection(args.settings)
    fields_requested = None if args.field_set.lower() == "all" else [
        field.strip() for field in args.field_set.split(",") if field.strip()
    ]
    factors = [float(value) for value in args.multipliers]
    if any(value <= 0 for value in factors) or 1.0 not in factors:
        raise SystemExit("--multipliers must be positive and include 1")
    if args.max_sweeps < 1:
        raise SystemExit("--max-sweeps must be at least 1")

    datasets = []
    replication_files_by_setting = {}
    for setting in settings:
        replication_files = resolve_replication_files(
            args.replications, setting, args.data_dir
        )
        replication_files_by_setting[str(setting)] = replication_files
        for replication_file in replication_files:
            datasets.append(load_replication(
                setting,
                replication_file,
                args.data_dir,
            ))
    if not datasets:
        raise SystemExit("No replications were selected")

    source_fields = list(datasets[0].covariates.columns)
    if fields_requested is None:
        searched_fields = source_fields
    else:
        unknown = set(fields_requested) - set(source_fields)
        if unknown:
            raise SystemExit(f"Unknown source fields: {sorted(unknown)}")
        searched_fields = fields_requested

    if args.starts in {"identity", "both"}:
        identity = {field: 1.0 for field in source_fields}
        starting_vectors = [("identity", identity)]
    else:
        starting_vectors = []
    if args.starts in {"llm", "both"}:
        llm = load_field_weights(args.llm_weights, source_fields)
        starting_vectors.append(("llm", llm))

    output_dir = args.output_dir
    if output_dir is None or output_dir == resolve_config_path(
        read_config(args.config).get("outputs", {}).get("directory", "results/pilot_runs"),
        args.config,
    ):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = output_dir / f"pilot_{timestamp}"
    elif not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    search_history = []
    best_weight_records = {}
    final_replication_rows = []
    evaluation_count = 0
    all_search_start = time.perf_counter()

    for start_name, initial_weights in starting_vectors:
        def score(candidate_weights: Mapping[str, float]) -> float:
            nonlocal evaluation_count
            evaluation_count += 1
            return evaluate_weights(datasets, source_fields, candidate_weights)

        best_weights, best_rmse, history = coordinate_search(
            initial_weights,
            searched_fields,
            factors,
            score,
            args.max_sweeps,
            start_name=start_name,
        )
        search_history.extend(history)
        _, rows = evaluate_weights(
            datasets, source_fields, best_weights, keep_rows=True
        )
        final_replication_rows.extend({"start": start_name, **row} for row in rows)
        best_weight_records[start_name] = {
            "weights": best_weights,
            "training_rmse": best_rmse,
        }
        print(f"Finished {start_name} start: RMSE={best_rmse:.6f}", flush=True)

    elapsed = time.perf_counter() - all_search_start
    with (output_dir / "candidate_history.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(search_history[0]))
        writer.writeheader()
        writer.writerows(search_history)
    with (output_dir / "best_weights.json").open("w", encoding="utf-8") as stream:
        json.dump(best_weight_records, stream, indent=2)
        stream.write("\n")
    with (output_dir / "pilot_replication_metrics.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(final_replication_rows[0]))
        writer.writeheader()
        writer.writerows(final_replication_rows)

    evaluation_seconds = [float(row["evaluation_seconds"]) for row in search_history if row["field"] != "__initial__"]
    metadata = {
        "purpose": "timing_and_code_check_only",
        "status": "completed",
        "config": str(args.config.resolve()),
        "data_dir": str(args.data_dir.resolve()),
        "settings": settings,
        "replication_files_by_setting": replication_files_by_setting,
        "searched_fields": searched_fields,
        "starts": [name for name, _ in starting_vectors],
        "multipliers": factors,
        "max_sweeps": args.max_sweeps,
        "candidate_evaluations": evaluation_count,
        "elapsed_seconds": elapsed,
        "mean_candidate_evaluation_seconds": float(np.mean(evaluation_seconds)) if evaluation_seconds else None,
        "p95_candidate_evaluation_seconds": float(np.quantile(evaluation_seconds, 0.95)) if evaluation_seconds else None,
        "held_out_evaluation_performed": False,
        "output_dir": str(output_dir),
    }
    with (output_dir / "run_metadata.json").open("w", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2)
        stream.write("\n")
    print(f"Pilot outputs: {output_dir}", flush=True)
    print(f"Candidate evaluations: {evaluation_count}; elapsed: {elapsed:.1f} seconds", flush=True)


if __name__ == "__main__":
    main()
