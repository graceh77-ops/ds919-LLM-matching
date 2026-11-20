"""Run the ACIC replication-level train/validation/test weight search."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from coordinate_search import coordinate_search

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACIC_SOURCE = PROJECT_ROOT / "acic2016" / "src"
if str(ACIC_SOURCE) not in sys.path:
    sys.path.insert(0, str(ACIC_SOURCE))

from load_acic_replication import encode_covariates  # noqa: E402
from run_matching_experiment import (  # noqa: E402
    _balance_metrics,
    _mahalanobis_coordinates,
    _matching_indices,
)

DEFAULT_CONFIG = PROJECT_ROOT / "acic2016_weight_search" / "config" / "experiment.json"
REPLICATION_PATTERN = re.compile(r"^zymu_(\d+)\.csv$")
OUTCOME_COLUMNS = ("z", "y0", "y1")


@dataclass(frozen=True)
class ReplicationOutcome:
    setting: int
    filename: str
    treatment: np.ndarray
    observed: np.ndarray
    realized_satt: float


def resolve_path(value: str | Path, config_path: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (config_path.resolve().parent.parent / path).resolve()


def parse_settings(value: str) -> list[int]:
    if value.strip().lower() == "all":
        return list(range(1, 78))
    selected: list[int] = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" in item:
            start, end = (int(part) for part in item.split("-", 1))
            if end < start:
                raise ValueError(f"Invalid setting range: {item}")
            selected.extend(range(start, end + 1))
        else:
            selected.append(int(item))
    if not selected or len(selected) != len(set(selected)):
        raise ValueError("Settings must be a nonempty unique list")
    if min(selected) < 1 or max(selected) > 77:
        raise ValueError("ACIC settings must be between 1 and 77")
    return selected


def list_files(data_dir: Path, setting: int, expected_count: int) -> list[str]:
    folder = data_dir / str(setting)
    if not folder.is_dir():
        raise FileNotFoundError(f"ACIC setting folder not found: {folder}")
    files = [
        path.name for path in folder.iterdir()
        if path.is_file() and REPLICATION_PATTERN.fullmatch(path.name)
    ]
    files.sort(key=lambda name: int(REPLICATION_PATTERN.fullmatch(name).group(1)))
    if len(files) != expected_count:
        raise ValueError(
            f"Expected {expected_count} replications in setting {setting}; found {len(files)}"
        )
    return files


def build_split(
    files_by_setting: Mapping[int, Sequence[str]],
    settings: Sequence[int],
    split_config: Mapping,
    seed: int,
) -> tuple[dict[tuple[int, str], str], list[dict[str, object]]]:
    fractions = [
        float(split_config["train_fraction"]),
        float(split_config["validation_fraction"]),
        float(split_config["test_fraction"]),
    ]
    if any(fraction <= 0 for fraction in fractions) or not math.isclose(sum(fractions), 1.0):
        raise ValueError("Train, validation, and test fractions must be positive and sum to 1")

    forced: dict[int, set[str]] = {}
    for entry in split_config.get("force_training", []):
        forced[int(entry["setting"])] = set(entry["replications"])

    rng = np.random.default_rng(seed)
    assignments: dict[tuple[int, str], str] = {}
    rows: list[dict[str, object]] = []
    for setting in settings:
        files = list(files_by_setting[setting])
        n = len(files)
        n_train = int(round(n * fractions[0]))
        n_validation = int(round(n * fractions[1]))
        n_test = n - n_train - n_validation
        forced_files = forced.get(setting, set())
        unknown = forced_files - set(files)
        if unknown:
            raise ValueError(
                f"Forced training files not found in setting {setting}: {sorted(unknown)}"
            )
        if len(forced_files) > n_train:
            raise ValueError(f"Too many forced training files for setting {setting}")

        remaining = [filename for filename in files if filename not in forced_files]
        permutation = rng.permutation(len(remaining))
        shuffled = [remaining[index] for index in permutation]
        train_needed = n_train - len(forced_files)
        train_files = forced_files | set(shuffled[:train_needed])
        validation_files = set(shuffled[train_needed:train_needed + n_validation])
        test_files = set(shuffled[train_needed + n_validation:])
        if len(test_files) != n_test:
            raise RuntimeError(f"Split allocation failed for setting {setting}")

        for filename in files:
            if filename in train_files:
                split = "train"
            elif filename in validation_files:
                split = "validation"
            else:
                split = "test"
            assignments[(setting, filename)] = split
            rows.append({"setting": setting, "replication": filename, "split": split})
    return assignments, rows


def load_reference_covariates(data_dir: Path):
    path = data_dir / "x.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Shared ACIC covariates not found: {path}")
    covariates = pd.read_csv(path)
    encoded, feature_map = encode_covariates(covariates)
    return covariates, encoded, feature_map, list(covariates.columns)


def load_outcome(data_dir: Path, setting: int, filename: str) -> ReplicationOutcome:
    path = data_dir / str(setting) / filename
    frame = pd.read_csv(path, usecols=list(OUTCOME_COLUMNS))
    if len(frame) != 4802:
        raise ValueError(f"Expected 4802 rows in {path}; found {len(frame)}")
    numeric = frame.loc[:, list(OUTCOME_COLUMNS)].apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError(f"Non-finite treatment/outcome values in {path}")
    treatment = values[:, 0]
    if not np.isin(treatment, [0, 1]).all():
        raise ValueError(f"Treatment must be binary in {path}")
    treatment = treatment.astype(np.int8)
    treated = treatment == 1
    if not treated.any() or treated.all():
        raise ValueError(f"Both treatment groups must be present in {path}")
    y0, y1 = values[:, 1], values[:, 2]
    observed = np.where(treated, y1, y0)
    realized_satt = float(np.mean(y1[treated] - y0[treated]))
    return ReplicationOutcome(setting, filename, treatment, observed, realized_satt)


def field_column_weights(feature_map, encoded_columns, field_weights):
    source = feature_map.set_index("encoded_column")["source_field"]
    expanded = np.asarray(
        [field_weights[source[column]] for column in encoded_columns], dtype=np.float64
    )
    expanded /= expanded.mean()
    return expanded


def evaluate_weights(
    outcomes: Sequence[ReplicationOutcome],
    covariates: pd.DataFrame,
    features: np.ndarray,
    feature_map,
    fields: Sequence[str],
    weights: Mapping[str, float],
    *,
    diagnostics: bool = False,
) -> tuple[float, list[dict[str, object]]]:
    columns = list(feature_map["encoded_column"])
    column_weights = field_column_weights(feature_map, columns, weights)
    coordinates = _mahalanobis_coordinates(features, column_weights)
    squared_errors = []
    records: list[dict[str, object]] = []
    for item in outcomes:
        treated, controls, distances = _matching_indices(coordinates, item.treatment)
        estimate = float(np.mean(item.observed[treated] - item.observed[controls]))
        error = estimate - item.realized_satt
        squared_errors.append(error * error)
        record: dict[str, object] = {
            "setting": item.setting,
            "replication": item.filename,
            "matched_att": estimate,
            "realized_satt": item.realized_satt,
            "error": error,
            "rmse_contribution": error * error,
            "mean_match_distance": float(np.mean(distances)),
        }
        if diagnostics:
            balance = _balance_metrics(
                covariates,
                item.treatment,
                treated_indices=treated,
                control_indices=controls,
                prefix="after",
            )
            record["max_abs_smd_after"] = balance["max_abs_smd_after"]
        records.append(record)
    rmse = math.sqrt(float(np.mean(squared_errors)))
    return rmse, records


def load_llm_weights(path: Path, fields: Sequence[str]) -> dict[str, float]:
    with path.open("r", encoding="utf-8-sig") as stream:
        raw = json.load(stream)
    if not isinstance(raw, dict) or set(raw) != set(fields):
        raise ValueError(f"LLM weights must include exactly the 58 source fields: {list(fields)}")
    weights = {field: float(raw[field]) for field in fields}
    if not np.isfinite(list(weights.values())).all() or min(weights.values()) <= 0:
        raise ValueError("LLM starting weights must be finite and positive")
    return weights


def write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write to {path.name}")
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args, remaining = parser.parse_known_args()
    config_path = args.config.resolve()
    with config_path.open("r", encoding="utf-8-sig") as stream:
        config = json.load(stream)
    experiment = config.get("experiment", {})
    search = config["search"]
    split_config = config["split"]
    outputs = config["outputs"]
    data_dir_default = resolve_path(config["data_dir"], config_path)
    output_default = resolve_path(outputs.get("experiment_directory", "results/full_experiment"), config_path)
    llm_default = resolve_path(search["llm_weights"], config_path)
    initializations = search.get("initializations", ["identity", "llm"])
    starts_default = (
        "both" if set(initializations) == {"identity", "llm"} else initializations[0]
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=config_path)
    parser.add_argument("--data-dir", type=Path, default=data_dir_default)
    parser.add_argument("--settings", default=experiment.get("settings", "all"))
    parser.add_argument("--seed", type=int, default=split_config.get("seed", 919))
    parser.add_argument("--starts", choices=("identity", "llm", "both"), default=starts_default)
    parser.add_argument("--max-sweeps", type=int, default=experiment.get("max_sweeps", 5))
    parser.add_argument("--field-set", default=search.get("field_set", "all"))
    parser.add_argument(
        "--multipliers", type=float, nargs="+",
        default=search.get("candidate_multipliers", [0.1, 0.5, 1, 2, 10]),
    )
    parser.add_argument("--output-dir", type=Path, default=output_default)
    parser.add_argument("--llm-weights", type=Path, default=llm_default)
    args = parser.parse_args(remaining, namespace=argparse.Namespace(**vars(args)))

    if args.max_sweeps < 1:
        raise SystemExit("--max-sweeps must be at least 1")
    settings = parse_settings(args.settings)
    expected = int(config.get("data", {}).get("replications_per_setting", 100))
    files_by_setting = {
        setting: list_files(args.data_dir, setting, expected) for setting in settings
    }
    assignment, split_rows = build_split(files_by_setting, settings, split_config, args.seed)

    covariates, encoded, feature_map, fields = load_reference_covariates(args.data_dir)
    requested_fields = args.field_set
    fields_to_search = (
        fields if requested_fields.lower() == "all"
        else [field.strip() for field in requested_fields.split(",") if field.strip()]
    )
    unknown = set(fields_to_search) - set(fields)
    if unknown:
        raise ValueError(f"Unknown source fields: {sorted(unknown)}")
    if not fields_to_search or len(fields_to_search) != len(set(fields_to_search)):
        raise ValueError("The searched field set must be nonempty and unique")
    features = encoded.to_numpy(dtype=np.float64)

    by_split: dict[str, list[ReplicationOutcome]] = {name: [] for name in ("train", "validation")}
    for setting in settings:
        for filename in files_by_setting[setting]:
            split_name = assignment[(setting, filename)]
            if split_name in by_split:
                by_split[split_name].append(load_outcome(args.data_dir, setting, filename))
    train = by_split["train"]
    validation = by_split["validation"]
    train_validation = train + validation

    starts = []
    if args.starts in {"identity", "both"}:
        starts.append(("identity", {field: 1.0 for field in fields}))
    if args.starts in {"llm", "both"}:
        starts.append(("llm", load_llm_weights(args.llm_weights, fields)))
    multipliers = [float(value) for value in args.multipliers]
    if any(value <= 0 for value in multipliers) or 1.0 not in multipliers:
        raise ValueError("Candidate multipliers must be positive and include 1")

    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    write_csv(output_dir / "split_manifest.csv", split_rows)

    history: list[dict[str, object]] = []
    validation_rows: list[dict[str, object]] = []
    checkpoint_weights: dict[str, dict[str, dict[str, float]]] = {}
    selection_rows: list[dict[str, object]] = []
    final_weights: dict[str, dict[str, float]] = {}
    starting_weights = {name: dict(weights) for name, weights in starts}
    test_rows: list[dict[str, object]] = []
    timings: dict[str, float] = {}

    for start_name, initial_weights in starts:
        def train_score(candidate: dict[str, float]) -> float:
            return evaluate_weights(
                train, covariates, features, feature_map, fields, candidate
            )[0]

        checkpoints: list[tuple[int, dict[str, float], float]] = []
        checkpoint_weights[start_name] = {}

        def record_checkpoint(sweep: int, weights: dict[str, float], train_rmse: float) -> None:
            validation_rmse, _ = evaluate_weights(
                validation, covariates, features, feature_map, fields, weights
            )
            checkpoints.append((sweep, dict(weights), validation_rmse))
            checkpoint_weights[start_name][str(sweep)] = dict(weights)
            validation_rows.append({
                "start": start_name,
                "sweep": sweep,
                "training_rmse": train_rmse,
                "validation_rmse": validation_rmse,
            })

        started = time.perf_counter()
        _, _, search_history = coordinate_search(
            initial_weights,
            fields_to_search,
            multipliers,
            train_score,
            args.max_sweeps,
            start_name=start_name,
            on_sweep=record_checkpoint,
        )
        timings[f"{start_name}_training_search_seconds"] = time.perf_counter() - started
        history.extend(search_history)
        selected_sweep, _, selected_validation_rmse = min(
            checkpoints, key=lambda item: (item[2], item[0])
        )
        selection_rows.append({
            "start": start_name,
            "selected_sweeps": selected_sweep,
            "validation_rmse": selected_validation_rmse,
        })

        if selected_sweep == 0:
            refit_weights = dict(initial_weights)
        else:
            def refit_score(candidate: dict[str, float]) -> float:
                return evaluate_weights(
                    train_validation, covariates, features, feature_map, fields, candidate
                )[0]

            refit_weights, _, refit_history = coordinate_search(
                initial_weights,
                fields_to_search,
                multipliers,
                refit_score,
                selected_sweep,
                start_name=f"{start_name}_refit",
            )
            history.extend(refit_history)
        final_weights[start_name] = refit_weights

    # Test outcomes are loaded only after both search procedures and sweep selection are frozen.
    test_outcomes = [
        load_outcome(args.data_dir, setting, filename)
        for setting in settings
        for filename in files_by_setting[setting]
        if assignment[(setting, filename)] == "test"
    ]
    test_summary_rows: list[dict[str, object]] = []
    test_models: dict[str, dict[str, float]] = {}
    for start_name in final_weights:
        test_models[f"{start_name}_baseline"] = starting_weights[start_name]
        if final_weights[start_name] != starting_weights[start_name]:
            test_models[f"{start_name}_searched"] = final_weights[start_name]
    for model_name, weights in test_models.items():
        started = time.perf_counter()
        test_rmse, rows = evaluate_weights(
            test_outcomes,
            covariates,
            features,
            feature_map,
            fields,
            weights,
            diagnostics=True,
        )
        timings[f"{model_name}_test_evaluation_seconds"] = time.perf_counter() - started
        test_rows.extend({"model": model_name, **row} for row in rows)
        test_summary_rows.append({
            "model": model_name,
            "scope": "overall",
            "setting": "all",
            "test_rmse": test_rmse,
            "mean_abs_error": float(np.mean([abs(row["error"]) for row in rows])),
            "mean_max_abs_smd_after": float(np.mean([row["max_abs_smd_after"] for row in rows])),
        })
        for setting in settings:
            setting_rows = [row for row in rows if row["setting"] == setting]
            test_summary_rows.append({
                "model": model_name,
                "scope": "setting",
                "setting": setting,
                "test_rmse": math.sqrt(float(np.mean([row["error"] ** 2 for row in setting_rows]))),
                "mean_abs_error": float(np.mean([abs(row["error"]) for row in setting_rows])),
                "mean_max_abs_smd_after": float(np.mean([row["max_abs_smd_after"] for row in setting_rows])),
            })

    write_csv(output_dir / "search_history.csv", history)
    write_csv(output_dir / "validation_sweep_metrics.csv", validation_rows)
    write_csv(output_dir / "selected_sweeps.csv", selection_rows)
    write_csv(output_dir / "test_replication_metrics.csv", test_rows)
    write_csv(output_dir / "test_summary.csv", test_summary_rows)
    with (output_dir / "final_weights.json").open("w", encoding="utf-8") as stream:
        json.dump(final_weights, stream, indent=2)
        stream.write("\n")
    with (output_dir / "starting_weights.json").open("w", encoding="utf-8") as stream:
        json.dump(starting_weights, stream, indent=2)
        stream.write("\n")
    with (output_dir / "validation_checkpoint_weights.json").open("w", encoding="utf-8") as stream:
        json.dump(checkpoint_weights, stream, indent=2)
        stream.write("\n")
    metadata = {
        "status": "completed",
        "seed": args.seed,
        "settings": settings,
        "replications_per_setting": expected,
        "split_counts": {
            name: sum(row["split"] == name for row in split_rows)
            for name in ("train", "validation", "test")
        },
        "forced_training_files": split_config.get("force_training", []),
        "searched_fields": fields_to_search,
        "starts": list(final_weights),
        "multipliers": multipliers,
        "maximum_sweeps": args.max_sweeps,
        "test_models": list(test_models),
        "timings_seconds": timings,
        "output_dir": str(output_dir),
    }
    with (output_dir / "run_metadata.json").open("w", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2)
        stream.write("\n")
    print(f"Experiment outputs: {output_dir}", flush=True)
    for row in test_summary_rows:
        if row["scope"] == "overall":
            print(f"{row['model']} test RMSE: {row['test_rmse']:.6f}", flush=True)


if __name__ == "__main__":
    main()
