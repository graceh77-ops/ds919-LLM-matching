"""Development-only coordinate and restricted-grid search pilot for Natality."""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from matching_distance import (
    FIELD_ORDER,
    estimate_att,
    fit_natality_transform,
    nearest_neighbor_with_replacement,
)
from ps_augmented_matching.coordinates import build_representation
from run_matching_experiment import (
    DEFAULT_INPUT,
    PROPENSITY_SCORE_WEIGHT_FIELD,
    _covariate_field_weights,
    _covariate_balance_smds,
    _fit_propensity_model,
    _fit_reference_control_outcome,
    _load_streamed_pilot,
    _ps_augmented_diagonal_weights,
    _reference_aipw_estimates,
    _test_propensity_coordinates,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS = (
    PROJECT_DIR
    / "results"
    / "ps_augmented_matching"
    / "deepseek_api"
    / "20261102T060435Z"
    / "weights.json"
)
DEFAULT_OUTPUT_ROOT = PROJECT_DIR / "results" / "weight_search_pilots"
DEFAULT_MULTIPLIERS = (0.1, 0.5, 1.0, 2.0, 10.0)
DEFAULT_PS_GRID_FIELDS = ("CIG0_R", "MAGER", PROPENSITY_SCORE_WEIGHT_FIELD)
DEFAULT_COVARIATE_GRID_FIELDS = ("CIG0_R", "MAGER", "birth_year")


def _read_weights(path: Path) -> dict[str, float]:
    with path.open("r", encoding="utf-8-sig") as stream:
        values = json.load(stream)
    if not isinstance(values, dict):
        raise ValueError("Weight JSON must contain a JSON object keyed by field name.")
    expected = set(FIELD_ORDER)
    if PROPENSITY_SCORE_WEIGHT_FIELD in values:
        expected.add(PROPENSITY_SCORE_WEIGHT_FIELD)
    if set(values) != expected:
        raise ValueError(
            "Weight JSON must contain exactly the eleven Natality fields, "
            "optionally plus PROPENSITY_SCORE."
        )
    result = {str(key): float(value) for key, value in values.items()}
    if not np.isfinite(list(result.values())).all() or min(result.values()) <= 0:
        raise ValueError("Pilot search requires every starting weight to be positive.")
    return result


def _split_sample(
    sample: pd.DataFrame,
    seed: int,
    fractions: tuple[float, float, float] = (0.6, 0.2, 0.2),
) -> dict[str, pd.DataFrame]:
    if not math.isclose(sum(fractions), 1.0) or any(value <= 0 for value in fractions):
        raise ValueError("Split fractions must be positive and sum to one.")
    rng = np.random.default_rng(seed)
    indices: dict[str, list[int]] = {name: [] for name in ("train", "validation", "test")}
    for key, group in sample.groupby(
        ["treatment_binary", "birth_year"], sort=True, observed=True
    ):
        shuffled = rng.permutation(group.index.to_numpy(dtype=np.int64))
        n_train = int(round(len(shuffled) * fractions[0]))
        n_validation = int(round(len(shuffled) * fractions[1]))
        n_test = len(shuffled) - n_train - n_validation
        if min(n_train, n_validation, n_test) < 1:
            raise ValueError(
                f"Pilot sample is too small for treatment-by-year stratum {key}. "
                "Increase --pilot-rows."
            )
        indices["train"].extend(shuffled[:n_train].tolist())
        indices["validation"].extend(
            shuffled[n_train : n_train + n_validation].tolist()
        )
        indices["test"].extend(shuffled[n_train + n_validation :].tolist())
    return {
        name: sample.loc[sorted(rows)].reset_index(drop=True)
        for name, rows in indices.items()
    }


def _prepare_split(name: str, frame: pd.DataFrame, use_ps: bool) -> dict[str, Any]:
    transform = fit_natality_transform(frame)
    features = transform.transform(frame)
    propensity_coefficients = _fit_propensity_model(frame, transform)
    outcome_coefficients = _fit_reference_control_outcome(frame, transform)
    aipw = _reference_aipw_estimates(
        frame, transform, propensity_coefficients, outcome_coefficients
    )
    prepared: dict[str, Any] = {
        "name": name,
        "frame": frame,
        "transform": transform,
        "features": features,
        "propensity_coefficients": propensity_coefficients,
        "aipw": aipw,
        "treatment": frame["treatment_binary"].to_numpy(dtype=np.int8),
        "treated_mask": frame["treatment_binary"].to_numpy(dtype=np.int8) == 1,
        "aipw_att": float(aipw["reference_aipw_att_g"]),
    }
    if use_ps:
        representation, inverse_root, diagnostics = build_representation(
            features, propensity_coefficients
        )
        prepared["whitened_augmented"] = np.ascontiguousarray(
            representation @ inverse_root
        )
        prepared["ps_diagnostics"] = diagnostics
    return prepared


def _matching_result(
    prepared: Mapping[str, Any],
    weights: Mapping[str, float],
    *,
    include_diagnostics: bool = True,
) -> dict[str, float | int]:
    frame = prepared["frame"]
    transform = prepared["transform"]
    features = prepared["features"]
    treatment = prepared["treatment"]
    treated_mask = prepared["treated_mask"]
    controls = frame.loc[~treated_mask]
    treated = frame.loc[treated_mask]

    if PROPENSITY_SCORE_WEIGHT_FIELD in weights:
        diagonal_weights, _ = _ps_augmented_diagonal_weights(dict(weights), transform)
        coordinates = prepared["whitened_augmented"] * np.sqrt(diagonal_weights)[None, :]
    else:
        covariate_weights = _covariate_field_weights(dict(weights))
        diagonal_weights = transform.diagonal_field_weights(covariate_weights)
        coordinates = features @ transform.distance_factor(diagonal_weights)

    match = nearest_neighbor_with_replacement(
        coordinates[treated_mask],
        coordinates[~treated_mask],
        controls["record_number"].to_numpy(dtype=np.int64),
    )
    att = estimate_att(
        treated["birthweight_g"].to_numpy(dtype=np.float64),
        controls["birthweight_g"].to_numpy(dtype=np.float64),
        match,
    )
    result: dict[str, float | int] = {
        "matched_att_g": float(att),
        "aipw_att_g": float(prepared["aipw_att"]),
        "absolute_gap_vs_aipw_g": abs(float(att) - float(prepared["aipw_att"])),
        "treated_n": int(len(treated)),
        "unique_controls_n": int(np.unique(match.control_indices).size),
        "max_control_reuse": int(np.bincount(match.control_indices).max()),
    }
    if include_diagnostics:
        matched_controls = controls.iloc[match.control_indices]
        balance = _covariate_balance_smds(treated, matched_controls)
        result["max_abs_smd_after"] = float(balance["max_abs_smd"])
    return result


def _score(
    prepared: Mapping[str, Any], weights: Mapping[str, float]
) -> float:
    return float(
        _matching_result(prepared, weights, include_diagnostics=False)[
            "absolute_gap_vs_aipw_g"
        ]
    )


def _score_candidates(
    prepared: Mapping[str, Any],
    candidates: Sequence[dict[str, float]],
    workers: int,
) -> list[tuple[float, float]]:
    def evaluate(weights: dict[str, float]) -> tuple[float, float]:
        started = time.perf_counter()
        value = _score(prepared, weights)
        return value, time.perf_counter() - started

    if workers <= 1 or len(candidates) < 2:
        return [evaluate(candidate) for candidate in candidates]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(evaluate, candidates))


def _validation_checkpoint(
    prepared: Mapping[str, Any], weights: Mapping[str, float]
) -> float:
    return _score(prepared, weights)


def _coordinate_search(
    start_name: str,
    initial_weights: Mapping[str, float],
    fields: Sequence[str],
    multipliers: Sequence[float],
    train: Mapping[str, Any],
    validation: Mapping[str, Any],
    max_sweeps: int,
    workers: int,
) -> tuple[dict[str, float], list[dict[str, object]], list[dict[str, object]]]:
    current = dict(initial_weights)
    history: list[dict[str, object]] = []
    checkpoints: list[dict[str, object]] = []
    start_time = time.perf_counter()
    current_score = _score(train, current)
    history.append({
        "start": start_name,
        "sweep": 0,
        "field": "__initial__",
        "multiplier": 1.0,
        "candidate_weight": None,
        "training_gap_g": current_score,
        "accepted": True,
        "evaluation_seconds": time.perf_counter() - start_time,
    })
    checkpoints.append({
        "start": start_name,
        "sweep": 0,
        "training_gap_g": current_score,
        "validation_gap_g": _validation_checkpoint(validation, current),
        "weights": dict(current),
    })

    for sweep in range(1, max_sweeps + 1):
        any_update = False
        for field in fields:
            base = current[field]
            candidates = []
            candidate_values = []
            for multiplier in multipliers:
                candidate = dict(current)
                candidate[field] = base * multiplier
                candidates.append(candidate)
                candidate_values.append(candidate[field])
            candidate_scores = _score_candidates(train, candidates, workers)
            best_weight = base
            best_multiplier = 1.0
            best_score = current_score
            rows = []
            for multiplier, candidate_weight, (candidate_score, elapsed) in zip(
                multipliers, candidate_values, candidate_scores
            ):
                accepted = candidate_score < best_score
                if accepted:
                    best_weight = candidate_weight
                    best_multiplier = multiplier
                    best_score = candidate_score
                rows.append({
                    "start": start_name,
                    "sweep": sweep,
                    "field": field,
                    "multiplier": multiplier,
                    "candidate_weight": candidate_weight,
                    "training_gap_g": candidate_score,
                    "accepted": False,
                    "evaluation_seconds": elapsed,
                })
            for row in rows:
                row["accepted"] = (
                    row["multiplier"] == best_multiplier
                    and best_multiplier != 1.0
                )
            history.extend(rows)
            if best_multiplier != 1.0:
                current[field] = best_weight
                current_score = best_score
                any_update = True
            print(
                f"coordinate {start_name}: sweep {sweep}, {field}; "
                f"training AIPW gap={current_score:.4f} g",
                flush=True,
            )

        checkpoints.append({
            "start": start_name,
            "sweep": sweep,
            "training_gap_g": current_score,
            "validation_gap_g": _validation_checkpoint(validation, current),
            "weights": dict(current),
        })
        if not any_update:
            break

    selected = min(
        checkpoints,
        key=lambda row: (float(row["validation_gap_g"]), int(row["sweep"])),
    )
    return dict(selected["weights"]), history, checkpoints


def _grid_search(
    initial_weights: Mapping[str, float],
    fields: Sequence[str],
    multipliers: Sequence[float],
    train: Mapping[str, Any],
    validation: Mapping[str, Any],
    workers: int,
) -> tuple[dict[str, float], list[dict[str, object]]]:
    candidate_weights: list[dict[str, float]] = []
    combinations = list(itertools.product(multipliers, repeat=len(fields)))
    for combination in combinations:
        candidate = dict(initial_weights)
        for field, multiplier in zip(fields, combination):
            candidate[field] *= multiplier
        candidate_weights.append(candidate)

    train_scores = _score_candidates(train, candidate_weights, workers)
    validation_scores = _score_candidates(validation, candidate_weights, workers)
    rows = []
    for combination, weights, train_result, validation_result in zip(
        combinations, candidate_weights, train_scores, validation_scores
    ):
        rows.append({
            "start": "llm",
            "grid_fields": ",".join(fields),
            "multipliers": json.dumps(dict(zip(fields, combination)), sort_keys=True),
            "training_gap_g": train_result[0],
            "validation_gap_g": validation_result[0],
            "training_evaluation_seconds": train_result[1],
            "validation_evaluation_seconds": validation_result[1],
            "weights": json.dumps(weights, sort_keys=True),
        })
    selected = min(
        rows,
        key=lambda row: (
            float(row["validation_gap_g"]),
            float(row["training_gap_g"]),
            str(row["multipliers"]),
        ),
    )
    selected_weights = json.loads(str(selected["weights"]))
    return {str(field): float(value) for field, value in selected_weights.items()}, rows


def _evaluate_test_models(
    prepared: Mapping[str, Any],
    models: Mapping[str, Mapping[str, float]],
) -> list[dict[str, object]]:
    rows = []
    for model_name, weights in models.items():
        metrics = _matching_result(prepared, weights)
        rows.append({"model": model_name, "split": "test", **metrics})

    # Include a conventional propensity-logit matcher as a comparator.
    frame = prepared["frame"]
    treatment = prepared["treatment"]
    treated_mask = prepared["treated_mask"]
    controls = frame.loc[~treated_mask]
    treated = frame.loc[treated_mask]
    ps_coordinates = _test_propensity_coordinates(
        frame,
        prepared["transform"],
        prepared["propensity_coefficients"],
        test_features=prepared["features"],
    )
    match = nearest_neighbor_with_replacement(
        ps_coordinates[0], ps_coordinates[1], controls["record_number"].to_numpy()
    )
    att = estimate_att(
        treated["birthweight_g"].to_numpy(dtype=np.float64),
        controls["birthweight_g"].to_numpy(dtype=np.float64),
        match,
    )
    balance = _covariate_balance_smds(treated, controls.iloc[match.control_indices])
    rows.append({
        "model": "propensity_score_logit",
        "split": "test",
        "matched_att_g": float(att),
        "aipw_att_g": float(prepared["aipw_att"]),
        "absolute_gap_vs_aipw_g": abs(float(att) - float(prepared["aipw_att"])),
        "max_abs_smd_after": float(balance["max_abs_smd"]),
        "treated_n": int(len(treated)),
        "unique_controls_n": int(np.unique(match.control_indices).size),
        "max_control_reuse": int(np.bincount(match.control_indices).max()),
    })
    return rows


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise ValueError(f"No rows to write to {path.name}.")
    fieldnames = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--weights-json", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--pilot-rows", type=int, default=30_000)
    parser.add_argument("--seed", type=int, default=919)
    parser.add_argument(
        "--multipliers", type=float, nargs="+", default=list(DEFAULT_MULTIPLIERS)
    )
    parser.add_argument("--max-sweeps", type=int, default=1)
    parser.add_argument("--workers", type=int, default=max(1, int(os.environ.get("NSLOTS", "1"))))
    parser.add_argument(
        "--algorithms", choices=("both", "coordinate", "grid"), default="both"
    )
    parser.add_argument("--grid-fields", nargs="+", default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"Input cohort not found: {args.input}")
    if not args.weights_json.is_file():
        parser.error(f"LLM weights file not found: {args.weights_json}")
    if args.pilot_rows < 100:
        parser.error("--pilot-rows must be at least 100 for the stratified split.")
    if args.max_sweeps < 1 or args.workers < 1:
        parser.error("--max-sweeps and --workers must be positive.")
    if len(set(args.multipliers)) != len(args.multipliers) or any(
        value <= 0 for value in args.multipliers
    ) or 1.0 not in args.multipliers:
        parser.error("Multipliers must be unique, positive, and include 1.")

    llm_weights = _read_weights(args.weights_json)
    dimensions = [*FIELD_ORDER]
    use_ps = PROPENSITY_SCORE_WEIGHT_FIELD in llm_weights
    if use_ps:
        dimensions.append(PROPENSITY_SCORE_WEIGHT_FIELD)
    grid_fields = args.grid_fields or (
        DEFAULT_PS_GRID_FIELDS if use_ps else DEFAULT_COVARIATE_GRID_FIELDS
    )
    unknown = set(grid_fields) - set(dimensions)
    if unknown or not grid_fields or len(set(grid_fields)) != len(grid_fields):
        parser.error(f"Invalid --grid-fields: {sorted(unknown)}")
    grid_count = len(args.multipliers) ** len(grid_fields)

    output_dir = args.output_dir
    if output_dir is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_dir = DEFAULT_OUTPUT_ROOT / f"pilot_{timestamp}"
    elif not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    started = time.perf_counter()
    print(f"Sampling {args.pilot_rows:,} rows from {args.input}.", flush=True)
    sample = _load_streamed_pilot(args.input, args.pilot_rows, args.seed)
    splits = _split_sample(sample, args.seed)
    print(
        "Split sizes: "
        + ", ".join(f"{name}={len(frame):,}" for name, frame in splits.items()),
        flush=True,
    )
    prepared = {
        name: _prepare_split(name, frame, use_ps)
        for name, frame in splits.items()
    }
    identity = {field: 1.0 for field in dimensions}
    search_fields = tuple(dimensions)
    coordinate_history: list[dict[str, object]] = []
    validation_rows: list[dict[str, object]] = []
    selected_models: dict[str, dict[str, float]] = {}
    grid_rows: list[dict[str, object]] = []

    if args.algorithms in {"both", "coordinate"}:
        for start_name, start_weights in (("identity", identity), ("llm", llm_weights)):
            selected, history, checkpoints = _coordinate_search(
                start_name,
                start_weights,
                search_fields,
                args.multipliers,
                prepared["train"],
                prepared["validation"],
                args.max_sweeps,
                args.workers,
            )
            coordinate_history.extend(history)
            for row in checkpoints:
                validation_rows.append({
                    "algorithm": "coordinate",
                    "start": row["start"],
                    "sweep": row["sweep"],
                    "training_gap_g": row["training_gap_g"],
                    "validation_gap_g": row["validation_gap_g"],
                })
            selected_models[f"coordinate_{start_name}_selected"] = selected

    if args.algorithms in {"both", "grid"}:
        selected_grid, grid_rows = _grid_search(
            llm_weights,
            grid_fields,
            args.multipliers,
            prepared["train"],
            prepared["validation"],
            args.workers,
        )
        selected_models["grid_llm_selected"] = selected_grid
        for row in grid_rows:
            validation_rows.append({
                "algorithm": "restricted_grid",
                "start": row["start"],
                "sweep": "grid",
                "training_gap_g": row["training_gap_g"],
                "validation_gap_g": row["validation_gap_g"],
            })

    test_models = {
        "identity_ps_augmented" if use_ps else "identity": identity,
        "llm_ps_augmented" if use_ps else "llm": llm_weights,
        **selected_models,
    }
    # Add covariate-only versions when the selected LLM vector includes PS.
    if use_ps:
        test_models["identity_covariates_only"] = {
            field: 1.0 for field in FIELD_ORDER
        }
        test_models["llm_covariates_only"] = _covariate_field_weights(llm_weights)
    test_results = _evaluate_test_models(prepared["test"], test_models)

    if coordinate_history:
        _write_csv(output_dir / "coordinate_candidate_history.csv", coordinate_history)
    if validation_rows:
        _write_csv(output_dir / "validation_scores.csv", validation_rows)
    if grid_rows:
        _write_csv(output_dir / "grid_candidate_results.csv", grid_rows)
    _write_csv(output_dir / "test_results.csv", test_results)
    with (output_dir / "selected_weights.json").open("w", encoding="utf-8") as stream:
        json.dump(selected_models, stream, indent=2)
        stream.write("\n")
    metadata = {
        "status": "completed",
        "pilot_only": True,
        "purpose": "timing_and_code_check_not_study_inference",
        "input": str(args.input.resolve()),
        "weights_json": str(args.weights_json.resolve()),
        "pilot_rows": args.pilot_rows,
        "seed": args.seed,
        "split_fractions": {"train": 0.6, "validation": 0.2, "test": 0.2},
        "split_counts": {
            name: {
                "rows": int(len(frame)),
                "treated": int(frame["treatment_binary"].sum()),
                "controls": int((frame["treatment_binary"] == 0).sum()),
            }
            for name, frame in splits.items()
        },
        "weight_dimensions": dimensions,
        "weight_dimension_count": len(dimensions),
        "propensity_score_in_weight_vector": use_ps,
        "coordinate_search_fields": list(search_fields),
        "coordinate_starts": ["identity", "llm"] if args.algorithms != "grid" else [],
        "grid_fields": list(grid_fields) if args.algorithms != "coordinate" else [],
        "grid_candidate_count_per_start": grid_count,
        "grid_start": "llm",
        "multipliers": args.multipliers,
        "maximum_sweeps": args.max_sweeps,
        "workers": args.workers,
        "candidate_objective": "absolute difference between matched ATT and split-specific AIPW ATT",
        "aipw_interpretation": "estimated reference, not known causal ground truth",
        "matching": "1:1 nearest neighbor with replacement; no caliper",
        "elapsed_seconds": time.perf_counter() - started,
        "output_dir": str(output_dir.resolve()),
    }
    with (output_dir / "run_metadata.json").open("w", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2)
        stream.write("\n")
    print(f"Pilot outputs: {output_dir}", flush=True)
    print(f"Grid candidates: {grid_count}", flush=True)
    for row in test_results:
        print(
            f"{row['model']}: test ATT={row['matched_att_g']:.3f} g; "
            f"absolute AIPW gap={row['absolute_gap_vs_aipw_g']:.3f} g",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
