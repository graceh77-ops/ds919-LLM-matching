"""Run repeated reference/test matching comparisons on the singleton cohort."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from matching_distance import (
    FIELD_ORDER,
    estimate_att,
    fit_natality_transform,
    nearest_neighbor_with_replacement,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "2024" / "analysis_cohort_singletons.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "results" / "matching_experiment.csv"
DEFAULT_SUMMARY_OUTPUT = PROJECT_ROOT / "results" / "matching_experiment_summary.csv"
DEFAULT_TEST_FRACTION = 0.01

INPUT_COLUMNS = [
    "record_number",
    "treatment_binary",
    "birthweight_g",
    *FIELD_ORDER,
]
INPUT_DTYPES = {
    "record_number": "int32",
    "treatment_binary": "int8",
    "birthweight_g": "int16",
    "MAGER": "int8",
    "MRACEHISP": "int8",
    "MEDUC": "int8",
    "CIG0_R": "int8",
    "PRIORLIVE": "int8",
    "PRIORDEAD": "int8",
    "BMI_R": "int8",
    "RF_PDIAB": "category",
    "RF_PHYPE": "category",
    "SEX": "category",
}


def _stratified_split(
    treatment: np.ndarray,
    test_fraction: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Split each treatment group, rounding the test count to nearest integer."""
    test_parts: list[np.ndarray] = []
    reference_parts: list[np.ndarray] = []
    for treatment_value in (0, 1):
        group = np.flatnonzero(treatment == treatment_value)
        if len(group) < 2:
            raise ValueError(
                f"Treatment group {treatment_value} has fewer than two records."
            )
        shuffled = rng.permutation(group)
        test_count = max(1, int(np.floor(len(group) * test_fraction + 0.5)))
        if test_count >= len(group):
            raise ValueError("The test fraction leaves no reference records in a stratum.")
        test_parts.append(shuffled[:test_count])
        reference_parts.append(shuffled[test_count:])

    test_indices = np.sort(np.concatenate(test_parts))
    reference_indices = np.sort(np.concatenate(reference_parts))
    return reference_indices, test_indices


def _match_one_method(
    reference: pd.DataFrame,
    test: pd.DataFrame,
    transform: Any,
    diagonal_weights: np.ndarray,
    method_name: str,
    split_number: int,
    reference_att: float | None = None,
    reference_att_se: float | None = None,
) -> dict[str, Any]:
    """Estimate ATT in reference and test portions using one fixed distance."""
    reference_treated = reference.loc[reference["treatment_binary"] == 1]
    reference_controls = reference.loc[reference["treatment_binary"] == 0]
    test_treated = test.loc[test["treatment_binary"] == 1]
    test_controls = test.loc[test["treatment_binary"] == 0]
    if reference_treated.empty or reference_controls.empty:
        raise ValueError("Reference portion must contain treated and control records.")
    if test_treated.empty or test_controls.empty:
        raise ValueError("Test portion must contain treated and control records.")

    factor = transform.distance_factor(diagonal_weights)

    reference_unique_controls: int | None = None
    reference_max_reuse: int | None = None
    if reference_att is None:
        reference_control_coordinates = transform.transform(reference_controls) @ factor
        reference_treated_coordinates = transform.transform(reference_treated) @ factor
        reference_match = nearest_neighbor_with_replacement(
            reference_treated_coordinates,
            reference_control_coordinates,
            reference_controls["record_number"].to_numpy(),
        )
        reference_treated_outcomes = reference_treated["birthweight_g"].to_numpy(dtype=np.float64)
        reference_control_outcomes = reference_controls["birthweight_g"].to_numpy(dtype=np.float64)
        reference_att = estimate_att(
            reference_treated_outcomes,
            reference_control_outcomes,
            reference_match,
        )
        reference_differences = reference_treated_outcomes - reference_control_outcomes[
            reference_match.control_indices
        ]
        reference_att_se = _cluster_robust_se(
            reference_differences, reference_match.control_indices
        )
        reference_unique_controls = int(np.unique(reference_match.control_indices).size)
        reference_max_reuse = int(np.bincount(reference_match.control_indices).max())

    test_control_features = transform.transform(test_controls)
    test_treated_features = transform.transform(test_treated)
    test_control_coordinates = test_control_features @ factor
    test_treated_coordinates = test_treated_features @ factor
    test_match = nearest_neighbor_with_replacement(
        test_treated_coordinates,
        test_control_coordinates,
        test_controls["record_number"].to_numpy(),
    )
    test_treated_outcomes = test_treated["birthweight_g"].to_numpy(dtype=np.float64)
    test_control_outcomes = test_controls["birthweight_g"].to_numpy(dtype=np.float64)
    test_att = estimate_att(test_treated_outcomes, test_control_outcomes, test_match)
    differences = test_treated_outcomes - test_control_outcomes[test_match.control_indices]
    test_se = _cluster_robust_se(differences, test_match.control_indices)
    test_reuse_counts = np.bincount(test_match.control_indices)
    smd_before = _absolute_smds(test_treated_features, test_control_features)
    smd_after = _absolute_smds(
        test_treated_features,
        test_control_features[test_match.control_indices],
    )

    result = {
        "split": split_number,
        "method": method_name,
        "reference_att_g": reference_att,
        "reference_att_cluster_se_g": reference_att_se,
        "test_att_g": test_att,
        "reference_error_g": test_att - reference_att,
        "test_att_cluster_se_g": test_se,
        "reference_treated_n": int(len(reference_treated)),
        "test_treated_n": int(len(test_treated)),
        "reference_unique_controls_n": reference_unique_controls,
        "reference_max_control_reuse": reference_max_reuse,
        "test_unique_controls_n": int(np.unique(test_match.control_indices).size),
        "test_max_control_reuse": int(test_reuse_counts.max()),
        "test_distance_median": float(np.median(test_match.distances)),
        "test_distance_p90": float(np.quantile(test_match.distances, 0.90)),
        "max_abs_smd_before": float(np.max(smd_before)),
        "max_abs_smd_after": float(np.max(smd_after)),
    }
    for feature, before, after in zip(transform.feature_names, smd_before, smd_after):
        result[f"smd_before_{feature}"] = float(before)
        result[f"smd_after_{feature}"] = float(after)
    return result


def _absolute_smds(treated: np.ndarray, controls: np.ndarray) -> np.ndarray:
    """Compute absolute pooled-SD standardized differences by encoded feature."""
    if treated.ndim != 2 or controls.ndim != 2 or treated.shape[1] != controls.shape[1]:
        raise ValueError("SMD inputs must be two-dimensional with equal feature counts.")
    mean_difference = treated.mean(axis=0) - controls.mean(axis=0)
    if len(treated) > 1 and len(controls) > 1:
        treated_variance = treated.var(axis=0, ddof=1)
        control_variance = controls.var(axis=0, ddof=1)
        pooled_sd = np.sqrt((treated_variance + control_variance) / 2.0)
    else:
        pooled_sd = np.zeros(treated.shape[1], dtype=np.float64)
    smd = np.zeros_like(mean_difference, dtype=np.float64)
    positive_scale = pooled_sd > 0
    smd[positive_scale] = mean_difference[positive_scale] / pooled_sd[positive_scale]
    zero_scale_difference = (~positive_scale) & (mean_difference != 0)
    smd[zero_scale_difference] = np.inf
    return np.abs(smd)


def _cluster_robust_se(differences: np.ndarray, matched_control_indices: np.ndarray) -> float:
    """Compute a control-clustered SE for paired differences with reused controls."""
    count = len(differences)
    _, cluster_index = np.unique(matched_control_indices, return_inverse=True)
    clusters = int(cluster_index.max()) + 1
    if count < 2 or clusters < 2:
        return float("nan")
    centered = differences - differences.mean()
    cluster_sums = np.bincount(cluster_index, weights=centered)
    variance = (clusters / (clusters - 1)) * np.square(cluster_sums).sum() / (count**2)
    return float(np.sqrt(max(variance, 0.0)))


def _load_weights(path: Path) -> dict[str, float]:
    with path.open("r", encoding="utf-8") as source:
        weights = json.load(source)
    if not isinstance(weights, dict):
        raise ValueError("The weight JSON must be an object of field names to weights.")
    return {str(field): float(weight) for field, weight in weights.items()}


def run_experiment(
    input_path: Path,
    output_path: Path,
    summary_path: Path,
    repeats: int,
    seed: int,
    test_fraction: float = DEFAULT_TEST_FRACTION,
    pilot_rows: int | None = None,
    weights: dict[str, float] | None = None,
    overwrite: bool = False,
) -> None:
    if repeats < 1:
        raise ValueError("repeats must be at least 1.")
    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between 0 and 1.")
    if pilot_rows is not None and pilot_rows < 2:
        raise ValueError("pilot_rows must be at least 2.")
    if not input_path.exists():
        raise FileNotFoundError(f"Analysis cohort not found: {input_path}")
    existing_outputs = [path for path in (output_path, summary_path) if path.exists()]
    if existing_outputs and not overwrite:
        raise FileExistsError(
            f"Output already exists: {existing_outputs[0]}. Choose another path or pass --overwrite."
        )

    data = pd.read_csv(
        input_path,
        usecols=INPUT_COLUMNS,
        dtype=INPUT_DTYPES,
        low_memory=False,
    )
    treatment = data["treatment_binary"].to_numpy(dtype=np.int8)
    if not np.isin(treatment, (0, 1)).all():
        raise ValueError("treatment_binary must contain only 0 and 1.")
    rng = np.random.default_rng(seed)
    if pilot_rows is not None:
        if pilot_rows > len(data):
            raise ValueError(f"pilot_rows ({pilot_rows}) exceeds cohort size ({len(data)}).")
        pilot_indices = np.sort(rng.choice(len(data), size=pilot_rows, replace=False))
        data = data.iloc[pilot_indices].reset_index(drop=True)
        treatment = data["treatment_binary"].to_numpy(dtype=np.int8)
    result_rows: list[dict[str, Any]] = []

    for split_number in range(1, repeats + 1):
        reference_indices, test_indices = _stratified_split(
            treatment, test_fraction, rng
        )
        reference = data.iloc[reference_indices]
        test = data.iloc[test_indices]
        transform = fit_natality_transform(reference)
        identity_weights = transform.diagonal_field_weights()

        identity = _match_one_method(
            reference,
            test,
            transform,
            identity_weights,
            "identity_generalized_mahalanobis",
            split_number,
        )
        identity["pilot_rows"] = pilot_rows
        identity["test_fraction"] = test_fraction
        result_rows.append(identity)

        if weights is not None:
            llm_weights = transform.diagonal_field_weights(weights)
            llm = _match_one_method(
                reference,
                test,
                transform,
                llm_weights,
                "llm_weighted_generalized_mahalanobis",
                split_number,
                reference_att=identity["reference_att_g"],
                reference_att_se=identity["reference_att_cluster_se_g"],
            )
            llm["pilot_rows"] = pilot_rows
            llm["test_fraction"] = test_fraction
            result_rows.append(llm)

            sensitivity_weights = transform.column_normalized_field_weights(weights)
            sensitivity = _match_one_method(
                reference,
                test,
                transform,
                sensitivity_weights,
                "llm_column_normalized_sensitivity",
                split_number,
                reference_att=identity["reference_att_g"],
                reference_att_se=identity["reference_att_cluster_se_g"],
            )
            sensitivity["pilot_rows"] = pilot_rows
            sensitivity["test_fraction"] = test_fraction
            result_rows.append(sensitivity)

        print(f"Completed split {split_number} of {repeats}.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(result_rows[0]))
        writer.writeheader()
        writer.writerows(result_rows)
    print(f"Wrote matching results to {output_path}")

    results = pd.DataFrame(result_rows)
    results["squared_reference_error_g2"] = results["reference_error_g"] ** 2
    summary = results.groupby("method", as_index=False).agg(
        splits=("split", "count"),
        reference_error_mse_g2=("squared_reference_error_g2", "mean"),
        mean_test_att_g=("test_att_g", "mean"),
        mean_reference_att_cluster_se_g=("reference_att_cluster_se_g", "mean"),
        mean_test_att_cluster_se_g=("test_att_cluster_se_g", "mean"),
        mean_max_abs_smd_before=("max_abs_smd_before", "mean"),
        mean_max_abs_smd_after=("max_abs_smd_after", "mean"),
        mean_test_treated_n=("test_treated_n", "mean"),
        mean_test_unique_controls_n=("test_unique_controls_n", "mean"),
        mean_test_max_control_reuse=("test_max_control_reuse", "mean"),
    )
    summary["reference_error_rmse_g"] = np.sqrt(summary["reference_error_mse_g2"])
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_path, index=False)
    print(f"Wrote aggregate summary to {summary_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--repeats", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--test-fraction",
        type=float,
        default=DEFAULT_TEST_FRACTION,
        help="Test fraction within each treatment stratum (default: 0.01).",
    )
    parser.add_argument(
        "--pilot-rows",
        type=int,
        help="Optional random subset size for a development pilot; not a study result.",
    )
    parser.add_argument(
        "--weights-json",
        type=Path,
        help="Optional JSON object with one nonnegative value for each of the 10 fields.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    weights = _load_weights(args.weights_json) if args.weights_json else None
    run_experiment(
        input_path=args.input,
        output_path=args.output,
        summary_path=args.summary_output,
        repeats=args.repeats,
        seed=args.seed,
        test_fraction=args.test_fraction,
        pilot_rows=args.pilot_rows,
        weights=weights,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
