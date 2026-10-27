"""Run outcome-blind matching methods on one ACIC 2016 replication."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from scipy.spatial.distance import cdist

from load_acic_replication import (
    CATEGORICAL_LEVELS,
    DEFAULT_DATA_DIR,
    load_replication,
)


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = PROJECT_DIR / "results"
EIGENVALUE_FLOOR_RATIO = 1e-8
PCA_VARIANCE_THRESHOLD = 0.90


def _inverse_sqrt_covariance(features: np.ndarray) -> np.ndarray:
    covariance = np.cov(features, rowvar=False, ddof=1)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    largest = float(eigenvalues[-1])
    if not np.isfinite(largest) or largest <= 0:
        raise ValueError("Covariate covariance has no positive finite eigenvalue")
    eigenvalues = np.maximum(eigenvalues, largest * EIGENVALUE_FLOOR_RATIO)
    return (eigenvectors * (1.0 / np.sqrt(eigenvalues))) @ eigenvectors.T


def _mahalanobis_coordinates(
    features: np.ndarray, diagonal_weights: np.ndarray | None = None
) -> np.ndarray:
    """Coordinates whose Euclidean distances implement generalized Mahalanobis."""
    inverse_root = _inverse_sqrt_covariance(features)
    if diagonal_weights is None:
        diagonal_weights = np.ones(features.shape[1], dtype=float)
    weighted_metric = inverse_root @ np.diag(diagonal_weights) @ inverse_root
    weighted_metric = (weighted_metric + weighted_metric.T) / 2.0
    values, vectors = np.linalg.eigh(weighted_metric)
    values = np.maximum(values, 0.0)
    factor = vectors * np.sqrt(values)
    return features @ factor


def _pca_coordinates(features: np.ndarray) -> tuple[np.ndarray, int, float]:
    means = features.mean(axis=0)
    scales = features.std(axis=0, ddof=0)
    scales[scales == 0] = 1.0
    standardized = (features - means) / scales
    _, singular_values, right_vectors = np.linalg.svd(
        standardized, full_matrices=False
    )
    component_variances = singular_values**2
    cumulative = np.cumsum(component_variances) / component_variances.sum()
    component_count = int(
        np.searchsorted(cumulative, PCA_VARIANCE_THRESHOLD, side="left") + 1
    )
    scores = standardized @ right_vectors[:component_count].T
    coordinates = _mahalanobis_coordinates(scores)
    return coordinates, component_count, float(cumulative[component_count - 1])


def _propensity_logits(features: np.ndarray, treatment: np.ndarray) -> np.ndarray:
    """Fit an unpenalized logistic model with stable objective/gradient."""
    means = features.mean(axis=0)
    scales = features.std(axis=0, ddof=0)
    scales[scales == 0] = 1.0
    standardized = (features - means) / scales
    design = np.column_stack([np.ones(len(features)), standardized])

    def objective_gradient(beta: np.ndarray) -> tuple[float, np.ndarray]:
        logits = design @ beta
        loss = np.logaddexp(0.0, logits).sum() - treatment @ logits
        gradient = design.T @ (expit(logits) - treatment)
        return float(loss), gradient

    fit = minimize(
        objective_gradient,
        np.zeros(design.shape[1], dtype=float),
        jac=True,
        method="L-BFGS-B",
        options={"maxiter": 1000, "ftol": 1e-12, "gtol": 1e-8, "maxls": 50},
    )
    if not fit.success or not np.isfinite(fit.x).all():
        raise RuntimeError(f"Unpenalized logistic model failed: {fit.message}")
    return design @ fit.x


def _load_field_weights(path: Path, source_fields: list[str]) -> dict[str, float]:
    with path.open("r", encoding="utf-8") as stream:
        weights = json.load(stream)
    if not isinstance(weights, dict) or set(weights) != set(source_fields):
        raise ValueError(
            "Weight JSON must contain exactly one numeric value for each source field: "
            + ", ".join(source_fields)
        )
    parsed: dict[str, float] = {}
    for field in source_fields:
        value = weights[field]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"Weight for {field} must be an integer from 0 to 10")
        if not 0 <= value <= 10:
            raise ValueError(f"Weight for {field} must be an integer from 0 to 10")
        parsed[field] = float(value)
    if sum(parsed.values()) <= 0:
        raise ValueError("At least one field weight must be greater than zero")
    return parsed


def _expand_field_weights(
    feature_map: pd.DataFrame,
    field_weights: Mapping[str, float],
    encoded_columns: list[str],
) -> np.ndarray:
    by_source = feature_map.set_index("encoded_column")["source_field"]
    expanded = np.asarray(
        [field_weights[by_source[column]] for column in encoded_columns], dtype=float
    )
    expanded /= expanded.mean()
    return expanded


def _matching_indices(
    coordinates: np.ndarray, treatment: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    treated_indices = np.flatnonzero(treatment == 1)
    control_indices = np.flatnonzero(treatment == 0)
    if not len(treated_indices) or not len(control_indices):
        raise ValueError("Replication must contain at least one treated and one control")
    distances = cdist(
        coordinates[treated_indices], coordinates[control_indices], metric="euclidean"
    )
    nearest_positions = np.argmin(distances, axis=1)
    matched_controls = control_indices[nearest_positions]
    matched_distances = distances[np.arange(len(treated_indices)), nearest_positions]
    return treated_indices, matched_controls, matched_distances


def _numeric_smd(treated: np.ndarray, controls: np.ndarray) -> float:
    denominator = np.sqrt((np.var(treated, ddof=1) + np.var(controls, ddof=1)) / 2)
    difference = float(np.mean(treated) - np.mean(controls))
    if denominator == 0:
        return 0.0 if difference == 0 else float(np.sign(difference) * np.inf)
    return difference / denominator


def _proportion_smd(treated: np.ndarray, controls: np.ndarray) -> float:
    p_t = float(np.mean(treated))
    p_c = float(np.mean(controls))
    denominator = np.sqrt((p_t * (1 - p_t) + p_c * (1 - p_c)) / 2)
    difference = p_t - p_c
    if denominator == 0:
        return 0.0 if difference == 0 else float(np.sign(difference) * np.inf)
    return difference / denominator


def _balance_metrics(
    covariates: pd.DataFrame,
    treatment: np.ndarray,
    treated_indices: np.ndarray | None = None,
    control_indices: np.ndarray | None = None,
    prefix: str = "before",
) -> dict[str, float]:
    if treated_indices is None:
        treated_indices = np.flatnonzero(treatment == 1)
    if control_indices is None:
        control_indices = np.flatnonzero(treatment == 0)
    result: dict[str, float] = {}
    field_maxima = []
    for field in covariates.columns:
        if field in CATEGORICAL_LEVELS:
            level_smds = []
            for level in CATEGORICAL_LEVELS[field]:
                treated_level = (
                    covariates.iloc[treated_indices][field].astype(str).to_numpy()
                    == level
                ).astype(float)
                control_level = (
                    covariates.iloc[control_indices][field].astype(str).to_numpy()
                    == level
                ).astype(float)
                smd = _proportion_smd(treated_level, control_level)
                result[f"smd_{prefix}_{field}_level_{level}"] = float(smd)
                level_smds.append(abs(smd))
            maximum = float(np.max(level_smds))
            result[f"max_abs_smd_{prefix}_{field}"] = maximum
        else:
            values = pd.to_numeric(covariates[field], errors="raise").to_numpy(float)
            smd = float(
                _numeric_smd(values[treated_indices], values[control_indices])
            )
            result[f"smd_{prefix}_{field}"] = smd
            maximum = abs(smd)
        field_maxima.append(maximum)
    result[f"max_abs_smd_{prefix}"] = float(np.max(field_maxima))
    return result


def _clustered_standard_error(
    paired_differences: np.ndarray, matched_controls: np.ndarray
) -> float:
    count = len(paired_differences)
    _, cluster_ids = np.unique(matched_controls, return_inverse=True)
    cluster_count = int(cluster_ids.max()) + 1
    if count < 2 or cluster_count < 2:
        return float("nan")
    centered = paired_differences - paired_differences.mean()
    cluster_sums = np.bincount(cluster_ids, weights=centered)
    variance = (
        cluster_count
        / (cluster_count - 1)
        * np.square(cluster_sums).sum()
        / count**2
    )
    return float(np.sqrt(max(variance, 0.0)))


def _evaluate_method(
    method: str,
    coordinates: np.ndarray,
    treatment: np.ndarray,
    observed_outcome: np.ndarray,
    realized_satt: float,
    expected_satt: float,
    covariates: pd.DataFrame,
    extra: dict[str, float] | None = None,
) -> dict[str, float | str]:
    treated, matched_controls, distances = _matching_indices(coordinates, treatment)
    differences = observed_outcome[treated] - observed_outcome[matched_controls]
    att = float(differences.mean())
    row: dict[str, float | str] = {
        "method": method,
        "matched_att": att,
        "matched_att_cluster_se": _clustered_standard_error(
            differences, matched_controls
        ),
        "error_vs_realized_satt": att - realized_satt,
        "absolute_error_vs_realized_satt": abs(att - realized_satt),
        "error_vs_expected_satt": att - expected_satt,
        "absolute_error_vs_expected_satt": abs(att - expected_satt),
        "treated_n": int(len(treated)),
        "unique_controls_n": int(np.unique(matched_controls).size),
        "max_control_reuse": int(np.bincount(matched_controls).max()),
        "distance_median": float(np.median(distances)),
        "distance_p90": float(np.quantile(distances, 0.90)),
    }
    row.update(_balance_metrics(covariates, treatment, prefix="before"))
    row.update(
        _balance_metrics(
            covariates,
            treatment,
            treated_indices=treated,
            control_indices=matched_controls,
            prefix="after",
        )
    )
    if extra:
        row.update(extra)
    return row


def run_replication(
    setting: int,
    replication: str,
    data_dir: Path = DEFAULT_DATA_DIR,
    weights_json: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    data = load_replication(setting, replication, data_dir)
    features = data.encoded_covariates.to_numpy(dtype=float)
    treatment = data.treatment.to_numpy(dtype=int)
    observed = data.observed_outcome.to_numpy(dtype=float)
    treated_n = int(treatment.sum())
    if treated_n == 0 or treated_n == len(treatment):
        raise ValueError("Replication must include treated and control units")

    methods: list[tuple[str, np.ndarray, dict[str, float] | None]] = []
    methods.append(
        ("identity_generalized_mahalanobis", _mahalanobis_coordinates(features), None)
    )
    propensity = _propensity_logits(features, treatment)
    methods.append(("propensity_score_logit", propensity[:, None], None))
    pca_coordinates, pca_n, pca_variance = _pca_coordinates(features)
    methods.append(
        (
            "pca_mahalanobis",
            pca_coordinates,
            {
                "pca_components_n": float(pca_n),
                "pca_cumulative_variance": pca_variance,
            },
        )
    )

    if weights_json is not None:
        source_fields = list(data.covariates.columns)
        field_weights = _load_field_weights(weights_json, source_fields)
        column_weights = _expand_field_weights(
            data.feature_map, field_weights, list(data.encoded_covariates.columns)
        )
        methods.append(
            (
                "llm_weighted_generalized_mahalanobis",
                _mahalanobis_coordinates(features, column_weights),
                {"llm_field_weight_mean": float(np.mean(list(field_weights.values())))},
            )
        )

    rows = [
        _evaluate_method(
            method,
            coordinates,
            treatment,
            observed,
            data.realized_satt,
            data.expected_satt,
            data.covariates,
            extra,
        )
        for method, coordinates, extra in methods
    ]
    method_results = pd.DataFrame(rows)
    method_results.insert(0, "replication", data.replication_file)
    method_results.insert(0, "setting", data.setting)
    references = pd.DataFrame(
        [
            {
                "setting": data.setting,
                "replication": data.replication_file,
                "n": len(treatment),
                "treated_n": treated_n,
                "realized_satt": data.realized_satt,
                "expected_satt": data.expected_satt,
            }
        ]
    )
    return method_results, references, data.feature_map


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--setting", type=int, required=True, help="Setting, 1-77")
    parser.add_argument(
        "--replication", required=True, help="Filename such as zymu_13.csv"
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--weights-json",
        type=Path,
        help="Optional JSON with one nonnegative weight for each x_1 through x_58",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output folder (default: next runN_TIMESTAMP folder in acic2016/results)",
    )
    return parser.parse_args()


def _next_run_output_dir(timestamp: str) -> Path:
    """Choose the next numbered run folder without overwriting prior results."""
    pattern = re.compile(r"^run(\d+)_\d{8}T\d{6}Z$")
    existing_numbers = [
        int(match.group(1))
        for path in DEFAULT_RESULTS_DIR.iterdir()
        if path.is_dir() and (match := pattern.fullmatch(path.name))
    ]
    next_number = max(existing_numbers, default=0) + 1
    return DEFAULT_RESULTS_DIR / f"run{next_number}_{timestamp}"


def main() -> None:
    args = _parse_args()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir or _next_run_output_dir(timestamp)
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing output: {output_dir}")
    output_dir.mkdir(parents=True)

    results, references, feature_map = run_replication(
        args.setting, args.replication, args.data_dir, args.weights_json
    )
    results.to_csv(output_dir / "complete_information.csv", index=False)
    references.to_csv(output_dir / "replication_reference.csv", index=False)
    feature_map.to_csv(output_dir / "feature_map.csv", index=False)
    results.groupby("method", as_index=False).agg(
        matched_att=("matched_att", "mean"),
        matched_att_cluster_se=("matched_att_cluster_se", "mean"),
        absolute_error_vs_realized_satt=(
            "absolute_error_vs_realized_satt",
            "mean",
        ),
        max_abs_smd_before=("max_abs_smd_before", "mean"),
        max_abs_smd_after=("max_abs_smd_after", "mean"),
        treated_n=("treated_n", "mean"),
        unique_controls_n=("unique_controls_n", "mean"),
        max_control_reuse=("max_control_reuse", "mean"),
    ).to_csv(output_dir / "summary.csv", index=False)
    print(f"Setting {args.setting}, replication {args.replication}")
    print(f"Methods: {', '.join(results['method'].tolist())}")
    print(f"Wrote results to {output_dir}")


if __name__ == "__main__":
    main()
