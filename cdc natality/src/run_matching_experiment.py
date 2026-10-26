"""Run repeated reference/test matching comparisons on the singleton cohort."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

from matching_distance import (
    BINARY_FIELDS,
    BINARY_LEVELS,
    CATEGORICAL_FIELDS,
    CATEGORY_LEVELS,
    FIELD_ORDER,
    NUMERIC_FIELDS,
    estimate_att,
    fit_natality_transform,
    nearest_neighbor_with_replacement,
    normalize_categorical_values,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "2024" / "analysis_cohort_singletons.csv"
DEFAULT_RESULTS_ROOT = PROJECT_ROOT / "results" / "matching results"
DEFAULT_WEIGHTS_JSON = None
DEFAULT_TEST_FRACTION = 0.01
PCA_CUMULATIVE_VARIANCE_THRESHOLD = 0.90
REFERENCE_MODEL_CHUNK_SIZE = 100_000
PROPENSITY_CLIP_EPSILON = 1e-6

INPUT_COLUMNS = [
    "record_number",
    "treatment_binary",
    "birthweight_g",
    *FIELD_ORDER,
]
INPUT_DTYPES = {
    # Annual extracts use year-prefixed integer IDs so IDs remain unique when
    # several annual cohorts are pooled.
    "record_number": "int64",
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
    "birth_year": "int16",
}


def _stratified_split(
    data: pd.DataFrame,
    test_fraction: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Split each treatment-by-year stratum, rounding its test count."""
    test_parts: list[np.ndarray] = []
    reference_parts: list[np.ndarray] = []
    for (treatment_value, birth_year), stratum in data.groupby(
        ["treatment_binary", "birth_year"], sort=True, observed=True
    ):
        group = stratum.index.to_numpy(dtype=np.int64)
        if len(group) < 2:
            raise ValueError(
                "Treatment-by-year stratum "
                f"({treatment_value}, {birth_year}) has fewer than two records."
            )
        shuffled = rng.permutation(group)
        test_count = max(1, int(np.floor(len(group) * test_fraction + 0.5)))
        if test_count >= len(group):
            raise ValueError(
                "The test fraction leaves no reference records in treatment-by-year "
                f"stratum ({treatment_value}, {birth_year})."
            )
        test_parts.append(shuffled[:test_count])
        reference_parts.append(shuffled[test_count:])

    test_indices = np.sort(np.concatenate(test_parts))
    reference_indices = np.sort(np.concatenate(reference_parts))
    return reference_indices, test_indices


def _match_one_method(
    test: pd.DataFrame,
    transform: Any,
    diagonal_weights: np.ndarray,
    method_name: str,
    split_number: int,
    test_coordinates: tuple[np.ndarray, np.ndarray] | None = None,
    test_features: np.ndarray | None = None,
    method_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Estimate the method's matched ATT in the test portion only."""
    test_treated = test.loc[test["treatment_binary"] == 1]
    test_controls = test.loc[test["treatment_binary"] == 0]
    if test_treated.empty or test_controls.empty:
        raise ValueError("Test portion must contain treated and control records.")

    test_treated_mask = test["treatment_binary"].to_numpy() == 1
    test_control_mask = ~test_treated_mask
    if test_features is None:
        test_treated_features = transform.transform(test_treated)
        test_control_features = transform.transform(test_controls)
    else:
        if test_features.shape != (len(test), len(transform.feature_names)):
            raise ValueError("Cached test features do not align with test rows.")
        test_treated_features = test_features[test_treated_mask]
        test_control_features = test_features[test_control_mask]

    factor = transform.distance_factor(diagonal_weights) if test_coordinates is None else None

    if test_coordinates is None:
        test_control_coordinates = test_control_features @ factor
        test_treated_coordinates = test_treated_features @ factor
    else:
        test_treated_coordinates, test_control_coordinates = test_coordinates
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
    balance_before = _covariate_balance_smds(test_treated, test_controls)
    matched_controls = test_controls.iloc[test_match.control_indices]
    balance_after = _covariate_balance_smds(
        test_treated,
        matched_controls,
    )

    result = {
        "split": split_number,
        "method": method_name,
        "test_att_g": test_att,
        "test_att_cluster_se_g": test_se,
        "test_treated_n": int(len(test_treated)),
        "test_unique_controls_n": int(np.unique(test_match.control_indices).size),
        "test_max_control_reuse": int(test_reuse_counts.max()),
        "test_distance_median": float(np.median(test_match.distances)),
        "test_distance_p90": float(np.quantile(test_match.distances, 0.90)),
        "max_abs_smd_before": balance_before["max_abs_smd"],
        "max_abs_smd_after": balance_after["max_abs_smd"],
        "pca_components_n": np.nan,
        "pca_cumulative_variance": np.nan,
    }
    for field, value in balance_before.items():
        if field.startswith("max_abs_smd_"):
            result[f"max_abs_smd_before_{field.removeprefix('max_abs_smd_')}"] = value
        elif field != "max_abs_smd":
            result[f"smd_before_{field}"] = value
    for field, value in balance_after.items():
        if field.startswith("max_abs_smd_"):
            result[f"max_abs_smd_after_{field.removeprefix('max_abs_smd_')}"] = value
        elif field != "max_abs_smd":
            result[f"smd_after_{field}"] = value
    if method_diagnostics:
        result.update(method_diagnostics)
    return result


def _fit_propensity_model(
    cohort: pd.DataFrame,
    transform: Any,
    chunk_size: int = 100_000,
) -> np.ndarray:
    """Fit an unpenalized logistic propensity model in memory-bounded batches.

    Returns the coefficients for an intercept followed by the shared encoded
    covariate columns. The fitting objective and gradient are accumulated over
    chunks so the full cohort design matrix need not remain in memory.
    """
    treatment = cohort["treatment_binary"].to_numpy(dtype=np.float64)
    treated_fraction = float(treatment.mean())
    if not 0.0 < treated_fraction < 1.0:
        raise ValueError("Propensity-model cohort must contain both treatment groups.")

    initial = np.zeros(len(transform.feature_names) + 1, dtype=np.float64)
    initial[0] = np.log(treated_fraction / (1.0 - treated_fraction))
    row_count = len(cohort)

    def objective_and_gradient(coefficients: np.ndarray) -> tuple[float, np.ndarray]:
        intercept = coefficients[0]
        feature_coefficients = coefficients[1:]
        total_loss = 0.0
        total_gradient = np.zeros_like(coefficients)
        for start in range(0, row_count, chunk_size):
            stop = min(start + chunk_size, row_count)
            rows = cohort.iloc[start:stop]
            features = transform.transform(rows)
            y = treatment[start:stop]
            linear_predictor = intercept + features @ feature_coefficients
            total_loss += np.logaddexp(0.0, linear_predictor).sum() - np.dot(
                y, linear_predictor
            )
            residual = expit(linear_predictor) - y
            total_gradient[0] += residual.sum()
            total_gradient[1:] += features.T @ residual
        return total_loss / row_count, total_gradient / row_count

    fit = minimize(
        objective_and_gradient,
        initial,
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": 100, "ftol": 1e-10},
    )
    if not fit.success:
        raise RuntimeError(f"Propensity model did not converge: {fit.message}")
    return np.asarray(fit.x, dtype=np.float64)


def _fit_reference_control_outcome(
    reference: pd.DataFrame,
    transform: Any,
    chunk_size: int = REFERENCE_MODEL_CHUNK_SIZE,
) -> np.ndarray:
    """Fit OLS birth weight on an intercept and encoded covariates among controls.

    Incremental QR keeps the design matrix bounded to one chunk, while avoiding
    the numerical instability of solving the normal equations.
    """
    treatment = reference["treatment_binary"].to_numpy(dtype=np.int8)
    control_indices = np.flatnonzero(treatment == 0)
    if len(control_indices) <= len(transform.feature_names):
        raise ValueError("Too few reference controls to fit the outcome model.")

    triangular = None
    column_count = len(transform.feature_names) + 2  # intercept, covariates, outcome
    for start in range(0, len(control_indices), chunk_size):
        indices = control_indices[start : start + chunk_size]
        rows = reference.iloc[indices]
        features = transform.transform(rows)
        design = np.column_stack((np.ones(len(rows), dtype=np.float64), features))
        outcome = rows["birthweight_g"].to_numpy(dtype=np.float64)
        augmented = np.column_stack((design, outcome))
        stack = augmented if triangular is None else np.vstack((triangular, augmented))
        triangular = np.linalg.qr(stack, mode="r")

    coefficient_count = len(transform.feature_names) + 1
    coefficients, _, _, _ = np.linalg.lstsq(
        triangular[:, :coefficient_count], triangular[:, coefficient_count], rcond=None
    )
    # A single-year cohort has constant birth-year contrasts after centering.
    # Least squares returns a minimum-norm solution for these redundant columns.
    return np.asarray(coefficients, dtype=np.float64)


def _quantile_diagnostics(prefix: str, values: np.ndarray) -> dict[str, float]:
    quantiles = np.quantile(values, [0.0, 0.01, 0.05, 0.5, 0.95, 0.99, 1.0])
    suffixes = ("min", "p01", "p05", "median", "p95", "p99", "max")
    return {f"{prefix}_{suffix}": float(value) for suffix, value in zip(suffixes, quantiles)}


def _reference_aipw_estimates(
    reference: pd.DataFrame,
    transform: Any,
    propensity_coefficients: np.ndarray,
    control_outcome_coefficients: np.ndarray,
    chunk_size: int = REFERENCE_MODEL_CHUNK_SIZE,
) -> dict[str, Any]:
    """Calculate reference AIPW-ATT, IPW-ATT, OR-ATT, and AIPW diagnostics.

    ATT AIPW is the treated mean residual from m0(X), minus the control
    propensity-odds-weighted residual sum divided by the treated count. The
    odds weights use propensities clipped to [1e-6, 1 - 1e-6] for numerical
    stability; raw propensity scores are retained for overlap diagnostics.
    """
    treatment = reference["treatment_binary"].to_numpy(dtype=np.int8)
    treated_count = int(np.count_nonzero(treatment == 1))
    control_count = int(np.count_nonzero(treatment == 0))
    if treated_count == 0 or control_count == 0:
        raise ValueError("Reference cohort must contain treated and control records.")

    feature_count = len(transform.feature_names)
    treated_propensity = np.empty(treated_count, dtype=np.float64)
    control_propensity = np.empty(control_count, dtype=np.float64)
    control_weights = np.empty(control_count, dtype=np.float64)
    treated_cursor = 0
    control_cursor = 0

    treated_residual_sum = 0.0
    treated_outcome_sum = 0.0
    control_weight_sum = 0.0
    control_weight_squared_sum = 0.0
    control_weighted_outcome_sum = 0.0
    control_weighted_residual_sum = 0.0
    aipw_score_squared_sum = 0.0

    treated_feature_sum = np.zeros(feature_count, dtype=np.float64)
    treated_feature_squared_sum = np.zeros(feature_count, dtype=np.float64)
    control_feature_sum = np.zeros(feature_count, dtype=np.float64)
    control_feature_squared_sum = np.zeros(feature_count, dtype=np.float64)
    weighted_control_feature_sum = np.zeros(feature_count, dtype=np.float64)
    weighted_control_feature_squared_sum = np.zeros(feature_count, dtype=np.float64)

    for start in range(0, len(reference), chunk_size):
        stop = min(start + chunk_size, len(reference))
        rows = reference.iloc[start:stop]
        features = transform.transform(rows)
        treated_mask = treatment[start:stop] == 1
        outcome = rows["birthweight_g"].to_numpy(dtype=np.float64)
        logits = propensity_coefficients[0] + features @ propensity_coefficients[1:]
        propensity = expit(logits)
        m0 = control_outcome_coefficients[0] + features @ control_outcome_coefficients[1:]
        residual = outcome - m0

        if treated_mask.any():
            treated_features = features[treated_mask]
            treated_residual = residual[treated_mask]
            treated_outcome = outcome[treated_mask]
            count = len(treated_outcome)
            treated_propensity[treated_cursor : treated_cursor + count] = propensity[treated_mask]
            treated_cursor += count
            treated_residual_sum += float(treated_residual.sum())
            treated_outcome_sum += float(treated_outcome.sum())
            aipw_score_squared_sum += float(np.dot(treated_residual, treated_residual))
            treated_feature_sum += treated_features.sum(axis=0)
            treated_feature_squared_sum += np.square(treated_features).sum(axis=0)

        control_mask = ~treated_mask
        if control_mask.any():
            control_features = features[control_mask]
            control_outcome = outcome[control_mask]
            control_residual = residual[control_mask]
            raw_propensity = propensity[control_mask]
            clipped_propensity = np.clip(
                raw_propensity,
                PROPENSITY_CLIP_EPSILON,
                1.0 - PROPENSITY_CLIP_EPSILON,
            )
            weights = clipped_propensity / (1.0 - clipped_propensity)
            count = len(control_outcome)
            control_propensity[control_cursor : control_cursor + count] = raw_propensity
            control_weights[control_cursor : control_cursor + count] = weights
            control_cursor += count

            control_weight_sum += float(weights.sum())
            control_weight_squared_sum += float(np.dot(weights, weights))
            control_weighted_outcome_sum += float(np.dot(weights, control_outcome))
            control_weighted_residual_sum += float(np.dot(weights, control_residual))
            weighted_control_residual = weights * control_residual
            aipw_score_squared_sum += float(np.dot(weighted_control_residual, weighted_control_residual))
            control_feature_sum += control_features.sum(axis=0)
            control_feature_squared_sum += np.square(control_features).sum(axis=0)
            weighted_control_feature_sum += weights @ control_features
            weighted_control_feature_squared_sum += np.square(control_features).T @ weights

    if treated_cursor != treated_count or control_cursor != control_count:
        raise RuntimeError("Reference diagnostics did not align with treatment rows.")
    if not np.isfinite(control_weight_sum) or control_weight_sum <= 0:
        raise ValueError("Reference ATT propensity weights have an invalid total.")

    aipw_att = (
        treated_residual_sum - control_weighted_residual_sum
    ) / treated_count
    ipw_att = (
        treated_outcome_sum / treated_count
        - control_weighted_outcome_sum / control_weight_sum
    )
    outcome_regression_att = treated_residual_sum / treated_count

    # Influence-function SE for the orthogonal ATT score, with nuisance fits
    # estimated on the reference cohort. The ratio denominator is the treated n.
    treated_score_sum = treated_residual_sum
    influence_sum_squares = (
        aipw_score_squared_sum
        - 2.0 * aipw_att * treated_score_sum
        + aipw_att * aipw_att * treated_count
    )
    aipw_se = float(np.sqrt(max(influence_sum_squares, 0.0)) / treated_count)

    treated_mean = treated_feature_sum / treated_count
    control_mean = control_feature_sum / control_count
    treated_variance = np.maximum(
        (treated_feature_squared_sum - treated_feature_sum * treated_mean)
        / max(treated_count - 1, 1),
        0.0,
    )
    control_variance = np.maximum(
        (control_feature_squared_sum - control_feature_sum * control_mean)
        / max(control_count - 1, 1),
        0.0,
    )
    smd_before = _smd_from_moments(treated_mean, treated_variance, control_mean, control_variance)

    weighted_control_mean = weighted_control_feature_sum / control_weight_sum
    weighted_control_variance = np.maximum(
        weighted_control_feature_squared_sum / control_weight_sum
        - np.square(weighted_control_mean),
        0.0,
    )
    smd_after = _smd_from_moments(
        treated_mean, treated_variance, weighted_control_mean, weighted_control_variance
    )

    diagnostics: dict[str, Any] = {
        "reference_aipw_att_g": float(aipw_att),
        "reference_aipw_se_g": aipw_se,
        "reference_aipw_ci_lower_g": float(aipw_att - 1.96 * aipw_se),
        "reference_aipw_ci_upper_g": float(aipw_att + 1.96 * aipw_se),
        "reference_ipw_att_g": float(ipw_att),
        "reference_outcome_regression_att_g": float(outcome_regression_att),
        "reference_aipw_max_abs_smd_before": float(np.max(smd_before)),
        "reference_aipw_max_abs_smd_after": float(np.max(smd_after)),
        "reference_aipw_weight_sum": float(control_weight_sum),
        "reference_aipw_weight_mean": float(control_weight_sum / control_count),
        "reference_aipw_weight_ess": float(
            control_weight_sum * control_weight_sum / control_weight_squared_sum
        ),
        "reference_aipw_weight_clipped_n": int(
            np.count_nonzero(
                (control_propensity < PROPENSITY_CLIP_EPSILON)
                | (control_propensity > 1.0 - PROPENSITY_CLIP_EPSILON)
            )
        ),
        "reference_aipw_weight_clipping_epsilon": PROPENSITY_CLIP_EPSILON,
        "reference_aipw_treated_outside_control_propensity_range_n": int(
            np.count_nonzero(
                (treated_propensity < control_propensity.min())
                | (treated_propensity > control_propensity.max())
            )
        ),
        "reference_aipw_control_outside_treated_propensity_range_n": int(
            np.count_nonzero(
                (control_propensity < treated_propensity.min())
                | (control_propensity > treated_propensity.max())
            )
        ),
    }
    diagnostics.update(_quantile_diagnostics("reference_aipw_weight", control_weights))
    diagnostics.update(_quantile_diagnostics("reference_aipw_treated_propensity", treated_propensity))
    diagnostics.update(_quantile_diagnostics("reference_aipw_control_propensity", control_propensity))
    diagnostics["reference_aipw_propensity_overlap_lower"] = float(
        max(treated_propensity.min(), control_propensity.min())
    )
    diagnostics["reference_aipw_propensity_overlap_upper"] = float(
        min(treated_propensity.max(), control_propensity.max())
    )
    for feature, before, after in zip(transform.feature_names, smd_before, smd_after):
        diagnostics[f"reference_aipw_smd_before_{feature}"] = float(before)
        diagnostics[f"reference_aipw_smd_after_{feature}"] = float(after)
    return diagnostics


def _smd_from_moments(
    treated_mean: np.ndarray,
    treated_variance: np.ndarray,
    control_mean: np.ndarray,
    control_variance: np.ndarray,
) -> np.ndarray:
    """Compute absolute standardized mean differences from group moments."""
    pooled_sd = np.sqrt((treated_variance + control_variance) / 2.0)
    differences = treated_mean - control_mean
    result = np.zeros_like(differences, dtype=np.float64)
    positive_scale = pooled_sd > 0
    result[positive_scale] = np.abs(differences[positive_scale] / pooled_sd[positive_scale])
    result[(~positive_scale) & (differences != 0)] = np.inf
    return result


def _attach_reference_estimands(
    result: dict[str, Any],
    reference_estimates: dict[str, Any],
) -> dict[str, Any]:
    """Attach the independent reference estimators and AIPW comparison error."""
    result.update(reference_estimates)
    result["error_vs_reference_aipw_g"] = (
        float(result["test_att_g"]) - float(reference_estimates["reference_aipw_att_g"])
    )
    return result


def _test_propensity_coordinates(
    test: pd.DataFrame,
    transform: Any,
    coefficients: np.ndarray,
    test_features: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return 1D logit-propensity coordinates for treated and control test rows."""
    test_treated = test.loc[test["treatment_binary"] == 1]
    test_controls = test.loc[test["treatment_binary"] == 0]
    if test_features is None:
        treated_features = transform.transform(test_treated)
        control_features = transform.transform(test_controls)
    else:
        if test_features.shape != (len(test), len(transform.feature_names)):
            raise ValueError("Cached test features do not align with test rows.")
        treated_mask = test["treatment_binary"].to_numpy() == 1
        treated_features = test_features[treated_mask]
        control_features = test_features[~treated_mask]
    treated_scores = coefficients[0] + treated_features @ coefficients[1:]
    control_scores = coefficients[0] + control_features @ coefficients[1:]
    return treated_scores[:, None], control_scores[:, None]


def _signed_numeric_smd(treated: np.ndarray, controls: np.ndarray) -> float:
    """Return a signed pooled-sample-SD standardized mean difference."""
    treated_variance = float(np.var(treated, ddof=1)) if len(treated) > 1 else 0.0
    control_variance = float(np.var(controls, ddof=1)) if len(controls) > 1 else 0.0
    pooled_sd = float(np.sqrt((treated_variance + control_variance) / 2.0))
    difference = float(np.mean(treated) - np.mean(controls))
    if pooled_sd == 0.0:
        return float("inf") if difference != 0.0 else 0.0
    return difference / pooled_sd


def _signed_proportion_smd(treated_proportion: float, control_proportion: float) -> float:
    """Return a signed SMD for a binary indicator or categorical level."""
    pooled_sd = float(
        np.sqrt(
            (
                treated_proportion * (1.0 - treated_proportion)
                + control_proportion * (1.0 - control_proportion)
            )
            / 2.0
        )
    )
    difference = treated_proportion - control_proportion
    if pooled_sd == 0.0:
        return float("inf") if difference != 0.0 else 0.0
    return difference / pooled_sd


def _covariate_balance_smds(
    treated: pd.DataFrame,
    controls: pd.DataFrame,
) -> dict[str, float]:
    """Compute balance by original field, not by encoded contrast column."""
    if treated.empty or controls.empty:
        raise ValueError("Both treatment groups are required for balance diagnostics.")

    diagnostics: dict[str, float] = {}
    all_absolute_smds: list[float] = []

    for field in NUMERIC_FIELDS:
        treated_values = pd.to_numeric(treated[field], errors="raise").to_numpy(dtype=np.float64)
        control_values = pd.to_numeric(controls[field], errors="raise").to_numpy(dtype=np.float64)
        smd = _signed_numeric_smd(treated_values, control_values)
        diagnostics[field] = smd
        all_absolute_smds.append(abs(smd))

    for field in BINARY_FIELDS:
        positive_level = BINARY_LEVELS[field][1]
        treated_values = treated[field].astype("string").str.strip().str.upper()
        control_values = controls[field].astype("string").str.strip().str.upper()
        if not treated_values.isin(BINARY_LEVELS[field]).all() or not control_values.isin(BINARY_LEVELS[field]).all():
            raise ValueError(f"Unrecognized binary values for {field} in balance diagnostics.")
        smd = _signed_proportion_smd(
            float((treated_values == positive_level).mean()),
            float((control_values == positive_level).mean()),
        )
        diagnostics[field] = smd
        all_absolute_smds.append(abs(smd))

    for field in CATEGORICAL_FIELDS:
        treated_values = normalize_categorical_values(field, treated[field])
        control_values = normalize_categorical_values(field, controls[field])
        levels = CATEGORY_LEVELS[field]
        if not treated_values.isin(levels).all() or not control_values.isin(levels).all():
            raise ValueError(f"Unrecognized categorical values for {field} in balance diagnostics.")
        level_smds: list[float] = []
        for level in levels:
            treated_proportion = float((treated_values == level).mean())
            control_proportion = float((control_values == level).mean())
            smd = _signed_proportion_smd(treated_proportion, control_proportion)
            safe_level = level.replace("-", "_")
            diagnostics[f"{field}_level_{safe_level}"] = smd
            level_smds.append(abs(smd))
        maximum = max(level_smds)
        diagnostics[f"max_abs_smd_{field}"] = maximum
        all_absolute_smds.extend(level_smds)

    diagnostics["max_abs_smd"] = max(all_absolute_smds)
    return diagnostics


def _pca_mahalanobis_coordinates(
    test_features: np.ndarray,
    treatment: np.ndarray,
    cumulative_variance_threshold: float = PCA_CUMULATIVE_VARIANCE_THRESHOLD,
) -> tuple[tuple[np.ndarray, np.ndarray], int, float]:
    """Fit test-only PCA and return ordinary Mahalanobis coordinates in PC space."""
    if test_features.ndim != 2 or len(test_features) < 2:
        raise ValueError("PCA requires at least two test records and a 2D feature matrix.")
    if test_features.shape[1] != 31:
        raise ValueError(f"PCA expects the 31 encoded covariates, got {test_features.shape[1]}.")
    if treatment.shape != (len(test_features),):
        raise ValueError("PCA treatment labels do not align with test features.")

    column_means = test_features.mean(axis=0)
    column_scales = test_features.std(axis=0, ddof=0)
    column_scales[~np.isfinite(column_scales) | (column_scales == 0.0)] = 1.0
    standardized = (test_features - column_means) / column_scales

    _, singular_values, component_directions = np.linalg.svd(
        standardized, full_matrices=False
    )
    variance = np.square(singular_values)
    total_variance = float(variance.sum())
    if not np.isfinite(total_variance) or total_variance <= 0.0:
        raise ValueError("PCA test features have no finite positive variance.")
    explained_variance_ratio = variance / total_variance
    cumulative = np.cumsum(explained_variance_ratio)
    component_count = min(
        int(np.searchsorted(cumulative, cumulative_variance_threshold, side="left") + 1),
        len(singular_values),
    )
    retained_variance = float(cumulative[component_count - 1])
    scores = standardized @ component_directions[:component_count].T

    score_covariance = np.atleast_2d(np.cov(scores, rowvar=False, ddof=1))
    eigenvalues, eigenvectors = np.linalg.eigh(score_covariance)
    largest = float(eigenvalues[-1])
    if not np.isfinite(largest) or largest <= 0.0:
        raise ValueError("Retained PCA scores have no positive finite covariance eigenvalue.")
    eigenvalues = np.maximum(eigenvalues, largest * 1e-8)
    inverse_root = (eigenvectors * (1.0 / np.sqrt(eigenvalues))) @ eigenvectors.T
    coordinates = np.ascontiguousarray(scores @ inverse_root, dtype=np.float64)

    treated_mask = treatment == 1
    if not treated_mask.any() or treated_mask.all():
        raise ValueError("PCA test cohort must contain treated and control records.")
    return (
        coordinates[treated_mask],
        coordinates[~treated_mask],
    ), component_count, retained_variance


def _feature_mapping(transform: Any) -> list[dict[str, str]]:
    """Map every encoded feature name back to its source covariate field."""
    mapping: list[dict[str, str]] = []
    for field in FIELD_ORDER:
        feature_slice = transform.field_slices[field]
        for feature_name in transform.feature_names[feature_slice]:
            mapping.append({"encoded_column": feature_name, "source_covariate": field})
    return mapping


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
    if set(weights) != set(FIELD_ORDER):
        raise ValueError(
            "Weight keys must exactly match the current eleven-field schema; "
            "prior ten-field weight files need a new outcome-blind elicitation."
        )
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
    feature_map_path = output_path.with_name(f"{output_path.stem}_feature_map.csv")
    existing_outputs = [
        path for path in (output_path, summary_path, feature_map_path) if path.exists()
    ]
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
    if data["record_number"].duplicated().any():
        raise ValueError(
            "record_number values must be unique. For pooled years, create the "
            "annual extracts with src/total_extraction.py so IDs include birth year."
        )
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
    feature_map_rows: list[dict[str, str]] | None = None

    for split_number in range(1, repeats + 1):
        reference_indices, test_indices = _stratified_split(
            data, test_fraction, rng
        )
        reference = data.iloc[reference_indices]
        test = data.iloc[test_indices]
        # Matching-side preprocessing is learned only from the 1% test cohort.
        # Reference-side preprocessing is kept separate for the AIPW benchmark.
        matching_transform = fit_natality_transform(test)
        test_features = matching_transform.transform(test)
        if feature_map_rows is None:
            feature_map_rows = _feature_mapping(matching_transform)
        identity_matrix_weights = matching_transform.diagonal_field_weights()
        reference_transform = fit_natality_transform(reference)

        reference_propensity_coefficients = _fit_propensity_model(
            reference, reference_transform
        )
        control_outcome_coefficients = _fit_reference_control_outcome(
            reference, reference_transform
        )
        reference_estimates = _reference_aipw_estimates(
            reference,
            reference_transform,
            reference_propensity_coefficients,
            control_outcome_coefficients,
        )

        identity = _match_one_method(
            test,
            matching_transform,
            identity_matrix_weights,
            "identity_generalized_mahalanobis",
            split_number,
            test_features=test_features,
        )
        identity = _attach_reference_estimands(identity, reference_estimates)
        identity["pilot_rows"] = pilot_rows
        identity["test_fraction"] = test_fraction
        result_rows.append(identity)

        matching_propensity_coefficients = _fit_propensity_model(
            test, matching_transform
        )
        propensity_coordinates = _test_propensity_coordinates(
            test,
            matching_transform,
            matching_propensity_coefficients,
            test_features=test_features,
        )
        psm = _match_one_method(
            test,
            matching_transform,
            np.ones(len(matching_transform.feature_names), dtype=np.float64),
            "propensity_score_logit",
            split_number,
            test_coordinates=propensity_coordinates,
            test_features=test_features,
        )
        psm = _attach_reference_estimands(psm, reference_estimates)
        psm["pilot_rows"] = pilot_rows
        psm["test_fraction"] = test_fraction
        result_rows.append(psm)

        pca_coordinates, pca_components_n, pca_retained_variance = (
            _pca_mahalanobis_coordinates(
                test_features,
                test["treatment_binary"].to_numpy(dtype=np.int8),
            )
        )
        pca = _match_one_method(
            test,
            matching_transform,
            np.ones(len(matching_transform.feature_names), dtype=np.float64),
            "pca_mahalanobis",
            split_number,
            test_coordinates=pca_coordinates,
            test_features=test_features,
            method_diagnostics={
                "pca_components_n": pca_components_n,
                "pca_cumulative_variance": pca_retained_variance,
            },
        )
        pca = _attach_reference_estimands(pca, reference_estimates)
        pca["pilot_rows"] = pilot_rows
        pca["test_fraction"] = test_fraction
        result_rows.append(pca)

        if weights is not None:
            llm_weights = matching_transform.diagonal_field_weights(weights)
            llm = _match_one_method(
                test,
                matching_transform,
                llm_weights,
                "llm_weighted_generalized_mahalanobis",
                split_number,
                test_features=test_features,
            )
            llm = _attach_reference_estimands(llm, reference_estimates)
            llm["pilot_rows"] = pilot_rows
            llm["test_fraction"] = test_fraction
            result_rows.append(llm)

            sensitivity_weights = matching_transform.column_normalized_field_weights(weights)
            sensitivity = _match_one_method(
                test,
                matching_transform,
                sensitivity_weights,
                "llm_column_normalized_sensitivity",
                split_number,
                test_features=test_features,
            )
            sensitivity = _attach_reference_estimands(sensitivity, reference_estimates)
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

    if feature_map_rows is None:
        raise RuntimeError("No matching feature mapping was generated.")
    feature_map_path.parent.mkdir(parents=True, exist_ok=True)
    with feature_map_path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=["encoded_column", "source_covariate"])
        writer.writeheader()
        writer.writerows(feature_map_rows)
    print(f"Wrote encoded-column source map to {feature_map_path}")

    results = pd.DataFrame(result_rows)
    results["squared_error_vs_reference_aipw_g2"] = results["error_vs_reference_aipw_g"] ** 2
    summary = results.groupby("method", as_index=False).agg(
        splits=("split", "count"),
        error_vs_reference_aipw_mse_g2=("squared_error_vs_reference_aipw_g2", "mean"),
        mean_test_att_g=("test_att_g", "mean"),
        mean_reference_aipw_att_g=("reference_aipw_att_g", "mean"),
        mean_reference_aipw_se_g=("reference_aipw_se_g", "mean"),
        mean_reference_aipw_ci_lower_g=("reference_aipw_ci_lower_g", "mean"),
        mean_reference_aipw_ci_upper_g=("reference_aipw_ci_upper_g", "mean"),
        mean_reference_ipw_att_g=("reference_ipw_att_g", "mean"),
        mean_reference_outcome_regression_att_g=("reference_outcome_regression_att_g", "mean"),
        mean_test_att_cluster_se_g=("test_att_cluster_se_g", "mean"),
        mean_max_abs_smd_before=("max_abs_smd_before", "mean"),
        mean_max_abs_smd_after=("max_abs_smd_after", "mean"),
        mean_reference_aipw_max_abs_smd_before=("reference_aipw_max_abs_smd_before", "mean"),
        mean_reference_aipw_max_abs_smd_after=("reference_aipw_max_abs_smd_after", "mean"),
        mean_reference_aipw_weight_median=("reference_aipw_weight_median", "mean"),
        mean_reference_aipw_weight_p95=("reference_aipw_weight_p95", "mean"),
        mean_reference_aipw_weight_p99=("reference_aipw_weight_p99", "mean"),
        mean_reference_aipw_weight_max=("reference_aipw_weight_max", "mean"),
        mean_reference_aipw_weight_ess=("reference_aipw_weight_ess", "mean"),
        mean_reference_aipw_weight_clipped_n=("reference_aipw_weight_clipped_n", "mean"),
        mean_reference_aipw_treated_propensity_p01=("reference_aipw_treated_propensity_p01", "mean"),
        mean_reference_aipw_treated_propensity_p99=("reference_aipw_treated_propensity_p99", "mean"),
        mean_reference_aipw_control_propensity_p01=("reference_aipw_control_propensity_p01", "mean"),
        mean_reference_aipw_control_propensity_p99=("reference_aipw_control_propensity_p99", "mean"),
        mean_reference_aipw_propensity_overlap_lower=("reference_aipw_propensity_overlap_lower", "mean"),
        mean_reference_aipw_propensity_overlap_upper=("reference_aipw_propensity_overlap_upper", "mean"),
        mean_test_treated_n=("test_treated_n", "mean"),
        mean_test_unique_controls_n=("test_unique_controls_n", "mean"),
        mean_test_max_control_reuse=("test_max_control_reuse", "mean"),
        mean_pca_components_n=("pca_components_n", "mean"),
        mean_pca_cumulative_variance=("pca_cumulative_variance", "mean"),
    )
    balance_aggregations: dict[str, tuple[str, str]] = {}
    for field in NUMERIC_FIELDS + BINARY_FIELDS:
        for phase in ("before", "after"):
            source = f"smd_{phase}_{field}"
            absolute_source = f"abs_{source}"
            results[absolute_source] = results[source].abs()
            balance_aggregations[f"mean_abs_{source}"] = (absolute_source, "mean")
    for field in CATEGORICAL_FIELDS:
        for phase in ("before", "after"):
            maximum_source = f"max_abs_smd_{phase}_{field}"
            balance_aggregations[f"mean_{maximum_source}"] = (maximum_source, "mean")
            for level in CATEGORY_LEVELS[field]:
                safe_level = level.replace("-", "_")
                source = f"smd_{phase}_{field}_level_{safe_level}"
                absolute_source = f"abs_{source}"
                results[absolute_source] = results[source].abs()
                balance_aggregations[f"mean_abs_{source}"] = (absolute_source, "mean")
    balance_summary = results.groupby("method", as_index=False).agg(**balance_aggregations)
    summary = summary.merge(balance_summary, on="method", how="left", validate="one_to_one")
    summary["error_vs_reference_aipw_rmse_g"] = np.sqrt(
        summary["error_vs_reference_aipw_mse_g2"]
    )
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(summary_path, index=False)
    print(f"Wrote aggregate summary to {summary_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional detailed-results CSV path. By default, create a dated run folder.",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        help="Optional summary CSV path. By default, place it beside the detailed results.",
    )
    parser.add_argument("--repeats", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--test-fraction",
        type=float,
        default=DEFAULT_TEST_FRACTION,
        help="Test fraction within each treatment-by-year stratum (default: 0.01).",
    )
    parser.add_argument(
        "--pilot-rows",
        type=int,
        help="Optional random subset size for a development pilot; not a study result.",
    )
    weight_group = parser.add_mutually_exclusive_group()
    weight_group.add_argument(
        "--weights-json",
        type=Path,
        default=DEFAULT_WEIGHTS_JSON,
        help=(
            "JSON object with one nonnegative value for each of the eleven fields. "
            "Prior ten-field weight files do not match the current schema."
        ),
    )
    weight_group.add_argument(
        "--no-llm-weights",
        action="store_true",
        help="Run conventional comparison methods without either LLM-weighted method.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.no_llm_weights and args.weights_json is None:
        raise SystemExit(
            "Provide --weights-json with an outcome-blind eleven-field weight file, "
            "or pass --no-llm-weights to run only conventional comparators."
        )
    if args.output is None and args.summary_output is None:
        run_label = f"{args.repeats}-split {date.today():%Y%m%d}"
        output_dir = DEFAULT_RESULTS_ROOT / run_label
        suffix = 2
        while output_dir.exists():
            output_dir = DEFAULT_RESULTS_ROOT / f"{run_label} ({suffix})"
            suffix += 1
        output_path = output_dir / "complete_information.csv"
        summary_path = output_dir / "summary.csv"
    elif args.output is not None:
        output_path = args.output
        summary_path = args.summary_output or args.output.with_name("summary.csv")
    else:
        summary_path = args.summary_output
        output_path = summary_path.with_name("complete_information.csv")

    weights = None
    if not args.no_llm_weights and args.weights_json is not None:
        weights = _load_weights(args.weights_json)
    run_experiment(
        input_path=args.input,
        output_path=output_path,
        summary_path=summary_path,
        repeats=args.repeats,
        seed=args.seed,
        test_fraction=args.test_fraction,
        pilot_rows=args.pilot_rows,
        weights=weights,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
