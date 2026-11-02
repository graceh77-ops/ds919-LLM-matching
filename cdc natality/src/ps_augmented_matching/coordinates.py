"""Build test-only encoded-covariate-plus-propensity-probability features."""

from __future__ import annotations

import numpy as np
from scipy.special import expit


EIGENVALUE_FLOOR_RATIO = 1e-8


def build_representation(
    encoded_features: np.ndarray,
    propensity_coefficients: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, float | int]]:
    """Return centered ``[encoded X, p(X)]``, its inverse covariance root,
    and diagnostics.

    The logistic coefficients must be fit using test-cohort treatment and
    encoded covariates only. Original encoded covariates are retained; no
    residualization is performed. This function has no outcome input.
    """
    features = np.asarray(encoded_features, dtype=np.float64)
    coefficients = np.asarray(propensity_coefficients, dtype=np.float64)
    if features.ndim != 2 or features.shape[0] < 2 or features.shape[1] < 1:
        raise ValueError("Encoded test features must be a nonempty 2D matrix with 2+ rows.")
    if coefficients.shape != (features.shape[1] + 1,):
        raise ValueError("Propensity coefficients must include an intercept and one per feature.")
    if not np.isfinite(features).all() or not np.isfinite(coefficients).all():
        raise ValueError("Features and propensity coefficients must be finite.")

    probability = expit(coefficients[0] + features @ coefficients[1:])
    probability_centered = probability - probability.mean()
    probability_variance = float(np.dot(probability_centered, probability_centered)) / (
        features.shape[0] - 1
    )
    if not np.isfinite(probability_variance) or probability_variance <= 0.0:
        raise ValueError("The fitted probability propensity score has no variation.")

    row_count, feature_count = features.shape
    representation = np.empty((row_count, feature_count + 1), dtype=np.float64)
    representation[:, :feature_count] = features
    representation[:, :feature_count] -= features.mean(axis=0)
    representation[:, feature_count] = probability_centered

    covariance = representation.T @ representation / (row_count - 1)
    covariance = (covariance + covariance.T) * 0.5
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    largest = float(eigenvalues[-1])
    if not np.isfinite(largest) or largest <= 0.0:
        raise ValueError("Augmented-covariate covariance has no positive eigenvalue.")

    rank_tolerance = largest * max(covariance.shape) * np.finfo(np.float64).eps
    numerical_rank = int(np.count_nonzero(eigenvalues > rank_tolerance))
    floor = largest * EIGENVALUE_FLOOR_RATIO
    floored_count = int(np.count_nonzero(eigenvalues < floor))
    floored_eigenvalues = np.maximum(eigenvalues, floor)
    inverse_root = (eigenvectors * (1.0 / np.sqrt(floored_eigenvalues))) @ eigenvectors.T
    raw_condition_number = (
        float(largest / eigenvalues[0]) if eigenvalues[0] > 0.0 else float("inf")
    )
    condition_number = float(floored_eigenvalues[-1] / floored_eigenvalues[0])

    diagnostics: dict[str, float | int] = {
        "ps_probability_min": float(probability.min()),
        "ps_probability_max": float(probability.max()),
        "ps_probability_sd": float(np.sqrt(probability_variance)),
        "ps_augmented_covariance_rank": numerical_rank,
        "ps_augmented_covariance_dimension": feature_count + 1,
        "ps_augmented_covariance_min_eigenvalue": float(eigenvalues[0]),
        "ps_augmented_covariance_max_eigenvalue": largest,
        "ps_augmented_covariance_condition_number_before_floor": raw_condition_number,
        "ps_augmented_covariance_condition_number_after_floor": condition_number,
        "ps_augmented_covariance_eigenvalues_floored_n": floored_count,
    }
    if not np.isfinite(representation).all() or not np.isfinite(inverse_root).all():
        raise ValueError("Augmented representation or covariance transform is non-finite.")
    return representation, inverse_root, diagnostics
