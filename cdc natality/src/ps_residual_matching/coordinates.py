"""Build test-only probability-PS and covariate-residual representations."""

from __future__ import annotations

import numpy as np
from scipy.special import expit


EIGENVALUE_FLOOR_RATIO = 1e-8


def build_representation(
    encoded_features: np.ndarray,
    propensity_coefficients: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, dict[str, float | int]]:
    """Return centered ``[p(X), OLS residuals]``, its inverse covariance root,
    and diagnostics.

    The supplied logistic coefficients must be fit from test-cohort treatment
    and covariates. Each encoded covariate is regressed on predicted probability
    with an intercept. This function has no outcome input.
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
    probability_mean = float(probability.mean())
    probability_centered = probability - probability_mean
    probability_ss = float(np.dot(probability_centered, probability_centered))
    if not np.isfinite(probability_ss) or probability_ss <= 0.0:
        raise ValueError("The fitted probability propensity score has no variation.")

    row_count, feature_count = features.shape
    feature_means = features.mean(axis=0)
    probability_variance = probability_ss / (row_count - 1)
    covariance_xp = (
        features.T @ probability_centered
        - feature_means * probability_centered.sum()
    ) / (row_count - 1)
    slopes = covariance_xp / probability_variance

    # Reuse one cohort-sized matrix for the residual representation and the
    # later identity/LLM Mahalanobis coordinates.
    representation = np.empty((row_count, feature_count + 1), dtype=np.float64)
    representation[:, 0] = probability_centered
    representation[:, 1:] = features
    representation[:, 1:] -= feature_means
    representation[:, 1:] -= probability_centered[:, None] * slopes

    covariance = representation.T @ representation / (row_count - 1)
    covariance = (covariance + covariance.T) * 0.5
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    largest = float(eigenvalues[-1])
    if not np.isfinite(largest) or largest <= 0.0:
        raise ValueError("Probability-score/residual covariance has no positive eigenvalue.")

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

    residual_covariance_with_score = covariance_xp - probability_variance * slopes
    residual_sd = np.sqrt(np.maximum(np.diag(covariance[1:, 1:]), 0.0))
    correlation_denominator = np.sqrt(probability_variance) * residual_sd
    valid = correlation_denominator > 0.0
    score_residual_correlations = np.zeros_like(residual_covariance_with_score)
    score_residual_correlations[valid] = (
        residual_covariance_with_score[valid] / correlation_denominator[valid]
    )

    diagnostics: dict[str, float | int] = {
        "ps_probability_min": float(probability.min()),
        "ps_probability_max": float(probability.max()),
        "ps_probability_sd": float(np.sqrt(probability_variance)),
        "ps_residual_covariance_rank": numerical_rank,
        "ps_residual_covariance_dimension": feature_count + 1,
        "ps_residual_covariance_min_eigenvalue": float(eigenvalues[0]),
        "ps_residual_covariance_max_eigenvalue": largest,
        "ps_residual_covariance_condition_number_before_floor": raw_condition_number,
        "ps_residual_covariance_condition_number_after_floor": condition_number,
        "ps_residual_covariance_eigenvalues_floored_n": floored_count,
        "ps_residual_max_abs_score_correlation": float(
            np.max(np.abs(score_residual_correlations))
        ),
    }
    if not np.isfinite(representation).all() or not np.isfinite(inverse_root).all():
        raise ValueError("PS-residual representation or covariance transform is non-finite.")
    return representation, inverse_root, diagnostics
