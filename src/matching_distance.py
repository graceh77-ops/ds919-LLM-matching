"""Feature preparation and distance transforms for Natality matching.

The feature coding is fixed from the maternal smoking analysis protocol.
Callers fit preprocessing and covariance on the cohort specified for that
task, then reuse the resulting object to transform its rows consistently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


NUMERIC_FIELDS = ("MAGER", "PRIORLIVE", "PRIORDEAD")
CATEGORICAL_FIELDS = ("MRACEHISP", "MEDUC", "CIG0_R", "BMI_R")
BINARY_FIELDS = ("RF_PDIAB", "RF_PHYPE", "SEX")
FIELD_ORDER = (
    "MAGER",
    "MRACEHISP",
    "MEDUC",
    "CIG0_R",
    "PRIORLIVE",
    "PRIORDEAD",
    "BMI_R",
    "RF_PDIAB",
    "RF_PHYPE",
    "SEX",
)

CATEGORY_LEVELS: Mapping[str, tuple[str, ...]] = {
    "MRACEHISP": ("1", "2", "3", "4", "5", "6", "7"),
    "MEDUC": ("1-2", "3-4", "5-6", "7-8"),
    "CIG0_R": ("0", "1-2", "3", "4-5"),
    "BMI_R": ("1", "2", "3", "4", "5", "6"),
}
BINARY_LEVELS: Mapping[str, tuple[str, str]] = {
    "RF_PDIAB": ("N", "Y"),
    "RF_PHYPE": ("N", "Y"),
    "SEX": ("F", "M"),
}

# The protocol requires one common, prespecified rule if the covariance matrix
# is singular or ill-conditioned. Eigenvalues below this relative threshold
# are floored for the distance transform in every method within a split.
COVARIANCE_EIGENVALUE_FLOOR_RATIO = 1e-8


def _helmert_contrasts(level_count: int) -> np.ndarray:
    """Return an orthonormal (level_count - 1) by level_count contrast matrix."""
    if level_count < 2:
        raise ValueError("A categorical field must have at least two levels.")

    contrasts = np.zeros((level_count - 1, level_count), dtype=np.float64)
    for contrast_index in range(level_count - 1):
        preceding_count = contrast_index + 1
        denominator = np.sqrt(preceding_count * (preceding_count + 1))
        contrasts[contrast_index, :preceding_count] = 1.0 / denominator
        contrasts[contrast_index, preceding_count] = -preceding_count / denominator
    return contrasts


def _clean_strings(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.upper()


def _categorical_values(field: str, values: pd.Series) -> pd.Series:
    cleaned = _clean_strings(values)
    if field == "MEDUC":
        mapping = {
            "1": "1-2",
            "2": "1-2",
            "3": "3-4",
            "4": "3-4",
            "5": "5-6",
            "6": "5-6",
            "7": "7-8",
            "8": "7-8",
        }
        cleaned = cleaned.map(mapping)
    elif field == "CIG0_R":
        mapping = {"0": "0", "1": "1-2", "2": "1-2", "3": "3", "4": "4-5", "5": "4-5"}
        cleaned = cleaned.map(mapping)
    return cleaned


@dataclass(frozen=True)
class NatalityFeatureTransform:
    """Cohort-fitted feature coding, centering, scaling, and covariance."""

    numeric_means: Mapping[str, float]
    numeric_scales: Mapping[str, float]
    categorical_means: Mapping[str, np.ndarray]
    binary_means: Mapping[str, float]
    covariance: np.ndarray
    covariance_eigenvalues: np.ndarray
    covariance_eigenvectors: np.ndarray
    field_slices: Mapping[str, slice]
    feature_names: tuple[str, ...]

    def transform(self, data: pd.DataFrame) -> np.ndarray:
        """Encode rows using this transform's fitted preprocessing values."""
        blocks: list[np.ndarray] = []

        for field in FIELD_ORDER:
            if field in NUMERIC_FIELDS:
                values = pd.to_numeric(data[field], errors="raise").to_numpy(dtype=np.float64)
                block = ((values - self.numeric_means[field]) / self.numeric_scales[field])[:, None]
            elif field in CATEGORICAL_FIELDS:
                levels = CATEGORY_LEVELS[field]
                values = _categorical_values(field, data[field])
                level_to_index = {level: index for index, level in enumerate(levels)}
                indices = values.map(level_to_index)
                if indices.isna().any():
                    invalid = sorted(values[indices.isna()].dropna().unique().tolist())
                    raise ValueError(f"Unrecognized {field} categories: {invalid}")
                contrasts = _helmert_contrasts(len(levels)).T
                block = contrasts[indices.to_numpy(dtype=np.int64)]
                block = block - self.categorical_means[field]
            else:
                levels = BINARY_LEVELS[field]
                values = _clean_strings(data[field])
                if not values.isin(levels).all():
                    invalid = sorted(values[~values.isin(levels)].dropna().unique().tolist())
                    raise ValueError(f"Unrecognized {field} categories: {invalid}")
                positive = (values == levels[1]).to_numpy(dtype=np.float64)
                block = (positive - self.binary_means[field])[:, None]
            blocks.append(block)

        return np.ascontiguousarray(np.column_stack(blocks), dtype=np.float64)

    def diagonal_field_weights(self, field_weights: Mapping[str, float] | None = None) -> np.ndarray:
        """Expand ten field weights over encoded columns in the declared order.

        With no argument, return the equal-weight identity baseline. Otherwise,
        require nonnegative weights for all fields and rescale them to mean 1.
        """
        if field_weights is None:
            return np.ones(len(self.feature_names), dtype=np.float64)

        missing = set(FIELD_ORDER) - set(field_weights)
        extra = set(field_weights) - set(FIELD_ORDER)
        if missing or extra:
            raise ValueError(f"Weight fields mismatch; missing={sorted(missing)}, extra={sorted(extra)}")

        weights = np.asarray([field_weights[field] for field in FIELD_ORDER], dtype=np.float64)
        if not np.isfinite(weights).all() or (weights < 0).any() or weights.mean() <= 0:
            raise ValueError("Field weights must be finite, nonnegative, and have positive mean.")
        weights /= weights.mean()

        expanded = np.empty(len(self.feature_names), dtype=np.float64)
        for field, weight in zip(FIELD_ORDER, weights):
            expanded[self.field_slices[field]] = weight
        return expanded

    def column_normalized_field_weights(self, field_weights: Mapping[str, float]) -> np.ndarray:
        """Return the field-block allocation used in the sensitivity analysis."""
        diagonal = self.diagonal_field_weights(field_weights)
        for field in FIELD_ORDER:
            diagonal[self.field_slices[field]] /= self.field_slices[field].stop - self.field_slices[field].start
        return diagonal

    def distance_factor(self, diagonal_weights: Sequence[float] | None = None) -> np.ndarray:
        """Return F such that ||(x_i - x_j) @ F|| is the specified distance."""
        if diagonal_weights is None:
            diagonal_weights = np.ones(len(self.feature_names), dtype=np.float64)
        diagonal_weights = np.asarray(diagonal_weights, dtype=np.float64)
        if diagonal_weights.shape != (len(self.feature_names),):
            raise ValueError(f"Expected {len(self.feature_names)} encoded-column weights.")
        if not np.isfinite(diagonal_weights).all() or (diagonal_weights < 0).any():
            raise ValueError("Encoded-column weights must be finite and nonnegative.")

        values = self.covariance_eigenvalues
        vectors = self.covariance_eigenvectors
        inverse_root = (vectors * (1.0 / np.sqrt(values))) @ vectors.T
        weighted_metric = inverse_root @ np.diag(diagonal_weights) @ inverse_root
        metric_values, metric_vectors = np.linalg.eigh(weighted_metric)
        metric_values = np.maximum(metric_values, 0.0)
        return metric_vectors * np.sqrt(metric_values)

    def distance_coordinates(
        self,
        data: pd.DataFrame,
        diagonal_weights: Sequence[float] | None = None,
    ) -> np.ndarray:
        """Return Euclidean coordinates equivalent to the specified distance."""
        encoded = self.transform(data)
        return np.ascontiguousarray(encoded @ self.distance_factor(diagonal_weights))


@dataclass(frozen=True)
class MatchResult:
    """Nearest control assigned to each treated record, with replacement."""

    control_indices: np.ndarray
    distances: np.ndarray


def nearest_neighbor_with_replacement(
    treated_coordinates: np.ndarray,
    control_coordinates: np.ndarray,
    control_ids: Sequence[int] | None = None,
    *,
    tie_tolerance: float = 1e-12,
) -> MatchResult:
    """Match each treated record to its nearest control, allowing reuse.

    Distances within ``tie_tolerance * max(1, nearest_distance)`` are treated
    as ties. Resolve ties using the smallest source record ID, or the earliest
    control row when IDs are not supplied. ``workers=1`` keeps tree queries
    deterministic across calls on the same SciPy version and input ordering.
    """
    treated_coordinates = np.ascontiguousarray(treated_coordinates, dtype=np.float64)
    control_coordinates = np.ascontiguousarray(control_coordinates, dtype=np.float64)
    if treated_coordinates.ndim != 2 or control_coordinates.ndim != 2:
        raise ValueError("Treated and control coordinates must be two-dimensional.")
    if treated_coordinates.shape[1] != control_coordinates.shape[1]:
        raise ValueError("Treated and control feature dimensions do not match.")
    if control_coordinates.shape[0] == 0:
        raise ValueError("No eligible controls are available for matching.")
    if not np.isfinite(treated_coordinates).all() or not np.isfinite(control_coordinates).all():
        raise ValueError("Matching coordinates must be finite.")
    if not np.isfinite(tie_tolerance) or tie_tolerance < 0:
        raise ValueError("Tie tolerance must be finite and nonnegative.")

    if control_ids is None:
        ids = np.arange(control_coordinates.shape[0], dtype=np.int64)
    else:
        ids = np.asarray(control_ids)
        if ids.shape != (control_coordinates.shape[0],):
            raise ValueError("control_ids must have one ID for each control row.")

    tree = cKDTree(control_coordinates)
    distances, indices = tree.query(treated_coordinates, k=2 if len(control_coordinates) > 1 else 1, workers=1)
    if len(control_coordinates) > 1:
        nearest_distances = distances[:, 0].astype(np.float64, copy=True)
        nearest_indices = indices[:, 0].astype(np.int64, copy=True)
        possible_ties = np.flatnonzero(
            np.abs(distances[:, 1] - distances[:, 0])
            <= tie_tolerance * np.maximum(1.0, distances[:, 0])
        )
    else:
        nearest_distances = np.asarray(distances, dtype=np.float64).reshape(-1)
        nearest_indices = np.asarray(indices, dtype=np.int64).reshape(-1)
        possible_ties = np.empty(0, dtype=np.int64)

    for treated_index in possible_ties:
        nearest_distance = nearest_distances[treated_index]
        tolerance = tie_tolerance * max(1.0, nearest_distance)
        candidates = tree.query_ball_point(
            treated_coordinates[treated_index], nearest_distance + tolerance, workers=1
        )
        candidate_indices = np.asarray(candidates, dtype=np.int64)
        offsets = control_coordinates[candidate_indices] - treated_coordinates[treated_index]
        candidate_distances = np.sqrt(np.einsum("ij,ij->i", offsets, offsets))
        tied = candidate_indices[candidate_distances <= nearest_distance + tolerance]
        winner = tied[np.argmin(ids[tied])]
        nearest_indices[treated_index] = winner
        nearest_distances[treated_index] = np.linalg.norm(
            control_coordinates[winner] - treated_coordinates[treated_index]
        )

    return MatchResult(control_indices=nearest_indices, distances=nearest_distances)


def estimate_att(
    treated_outcomes: Sequence[float],
    control_outcomes: Sequence[float],
    match: MatchResult,
) -> float:
    """Estimate the 1:1 matched ATT; matched controls may be reused."""
    treated_outcomes = np.asarray(treated_outcomes, dtype=np.float64)
    control_outcomes = np.asarray(control_outcomes, dtype=np.float64)
    if treated_outcomes.ndim != 1 or control_outcomes.ndim != 1:
        raise ValueError("Treatment and outcome arrays must be one-dimensional.")
    if match.control_indices.shape != treated_outcomes.shape:
        raise ValueError("There must be one matched control for every treated record.")
    if not np.isfinite(treated_outcomes).all() or not np.isfinite(control_outcomes).all():
        raise ValueError("Outcome values must be finite.")
    if (match.control_indices < 0).any() or (match.control_indices >= len(control_outcomes)).any():
        raise ValueError("A matched control index is outside the control outcome array.")
    return float(np.mean(treated_outcomes - control_outcomes[match.control_indices]))


def fit_natality_transform(cohort: pd.DataFrame) -> NatalityFeatureTransform:
    """Fit fixed 23-column encoding and covariance using cohort records."""
    required = set(FIELD_ORDER)
    missing = required - set(cohort.columns)
    if missing:
        raise ValueError(f"Missing required covariate columns: {sorted(missing)}")
    if cohort.empty:
        raise ValueError("The cohort used to fit preprocessing is empty.")

    numeric_means: dict[str, float] = {}
    numeric_scales: dict[str, float] = {}
    categorical_means: dict[str, np.ndarray] = {}
    binary_means: dict[str, float] = {}
    field_slices: dict[str, slice] = {}
    feature_names: list[str] = []
    columns: list[np.ndarray] = []
    offset = 0

    for field in FIELD_ORDER:
        if field in NUMERIC_FIELDS:
            values = pd.to_numeric(cohort[field], errors="raise").to_numpy(dtype=np.float64)
            mean = float(values.mean())
            scale = float(values.std(ddof=0))
            if not np.isfinite(scale) or scale <= 0:
                raise ValueError(f"Fitting-cohort standard deviation is zero for {field}.")
            numeric_means[field] = mean
            numeric_scales[field] = scale
            columns.append(((values - mean) / scale)[:, None])
            names = [field]
        elif field in CATEGORICAL_FIELDS:
            levels = CATEGORY_LEVELS[field]
            values = _categorical_values(field, cohort[field])
            level_to_index = {level: index for index, level in enumerate(levels)}
            indices = values.map(level_to_index)
            if indices.isna().any():
                invalid = sorted(values[indices.isna()].dropna().unique().tolist())
                raise ValueError(f"Unrecognized {field} categories: {invalid}")
            contrasts = _helmert_contrasts(len(levels)).T
            block = contrasts[indices.to_numpy(dtype=np.int64)]
            mean = block.mean(axis=0)
            categorical_means[field] = mean
            columns.append(block - mean)
            names = [f"{field}_helmert_{index + 1}" for index in range(len(levels) - 1)]
        else:
            levels = BINARY_LEVELS[field]
            values = _clean_strings(cohort[field])
            if not values.isin(levels).all():
                invalid = sorted(values[~values.isin(levels)].dropna().unique().tolist())
                raise ValueError(f"Unrecognized {field} categories: {invalid}")
            positive = (values == levels[1]).to_numpy(dtype=np.float64)
            mean = float(positive.mean())
            binary_means[field] = mean
            columns.append((positive - mean)[:, None])
            names = [f"{field}_contrast"]

        field_slices[field] = slice(offset, offset + len(names))
        feature_names.extend(names)
        offset += len(names)

    encoded = np.ascontiguousarray(np.column_stack(columns), dtype=np.float64)
    covariance = np.cov(encoded, rowvar=False, ddof=1)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    largest = float(eigenvalues[-1])
    if not np.isfinite(largest) or largest <= 0:
        raise ValueError("Fitting-cohort covariance has no positive finite eigenvalues.")
    floor = largest * COVARIANCE_EIGENVALUE_FLOOR_RATIO
    eigenvalues = np.maximum(eigenvalues, floor)
    regularized_covariance = (eigenvectors * eigenvalues) @ eigenvectors.T

    return NatalityFeatureTransform(
        numeric_means=numeric_means,
        numeric_scales=numeric_scales,
        categorical_means=categorical_means,
        binary_means=binary_means,
        covariance=regularized_covariance,
        covariance_eigenvalues=eigenvalues,
        covariance_eigenvectors=eigenvectors,
        field_slices=field_slices,
        feature_names=tuple(feature_names),
    )
