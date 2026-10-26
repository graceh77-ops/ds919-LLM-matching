"""Calibrate ATT entropy-balancing weights and validate them on the full reference."""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp, softmax

from matching_distance import FIELD_ORDER, fit_natality_transform
from run_matching_experiment import (
    DEFAULT_INPUT,
    REFERENCE_MODEL_CHUNK_SIZE,
    _make_streamed_split,
    _update_priority_sample,
)


APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AIPW_RESULTS = (
    APP_ROOT
    / "results"
    / "matching results_2016-2024"
    / "1-split 20261026"
    / "complete_information.csv"
)
OUTPUT_ROOT = APP_ROOT / "results" / "entropy-balancing"
DIAGNOSTIC_SAMPLE_SIZE = 100_000
CALIBRATION_SAMPLE_SIZE = 500_000


def _read_saved_aipw(path: Path) -> tuple[float, float, int]:
    rows = pd.read_csv(path)
    required = {
        "split",
        "reference_aipw_att_g",
        "reference_aipw_se_g",
        "test_treated_n",
    }
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"AIPW output is missing columns: {sorted(missing)}")
    selected = rows.loc[rows["split"] == 1]
    if selected.empty:
        raise ValueError("Saved AIPW output has no split 1 row.")
    values = {}
    for field in ("reference_aipw_att_g", "reference_aipw_se_g", "test_treated_n"):
        unique = selected[field].dropna().unique()
        if len(unique) != 1:
            raise ValueError(f"Saved methods do not share one {field} value.")
        values[field] = float(unique[0])
    return (
        values["reference_aipw_att_g"],
        values["reference_aipw_se_g"],
        int(values["test_treated_n"]),
    )


def _collect_target_and_control_sample(
    reference_source: Callable[[], Iterable[pd.DataFrame]],
    transform: Any,
    treated_count: int,
    sample_size: int,
    seed: int = 7319,
) -> tuple[np.ndarray, np.ndarray]:
    """Get exact reference treated means and a uniform control sample by streaming."""
    feature_count = len(transform.feature_names)
    treated_feature_sum = np.zeros(feature_count, dtype=np.float64)
    treated_seen = 0
    rng = np.random.default_rng(seed)
    priorities = np.empty(0, dtype=np.float64)
    sample_features = np.empty((0, feature_count), dtype=np.float64)

    for rows in reference_source():
        treatment = rows["treatment_binary"].to_numpy(dtype=np.int8)
        treated = rows.loc[treatment == 1]
        if not treated.empty:
            features = transform.transform(treated)
            treated_feature_sum += features.sum(axis=0)
            treated_seen += len(treated)

        controls = rows.loc[treatment == 0]
        if controls.empty:
            continue
        control_features = transform.transform(controls)
        candidate_priorities = np.concatenate((priorities, rng.random(len(controls))))
        candidate_features = np.vstack((sample_features, control_features))
        if len(candidate_priorities) > sample_size:
            keep = np.argpartition(candidate_priorities, sample_size - 1)[:sample_size]
            priorities = candidate_priorities[keep]
            sample_features = candidate_features[keep]
        else:
            priorities = candidate_priorities
            sample_features = candidate_features

    if treated_seen != treated_count:
        raise ValueError(f"Observed {treated_seen} treated rows; expected {treated_count}.")
    if len(sample_features) != sample_size:
        raise ValueError(
            f"Collected {len(sample_features)} control calibration rows; expected {sample_size}."
        )
    return treated_feature_sum / treated_count, sample_features


def _fit_sample_entropy_balancing(
    sample_features: np.ndarray,
    target_mean: np.ndarray,
    max_iterations: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Fit exponential-tilting dual weights on the bounded calibration sample."""
    started = time.perf_counter()

    def objective_gradient(coefficients: np.ndarray) -> tuple[float, np.ndarray]:
        logits = sample_features @ coefficients
        log_partition = float(logsumexp(logits))
        weights = softmax(logits)
        weighted_mean = weights @ sample_features
        objective = (
            log_partition
            - np.log(len(sample_features))
            - float(coefficients @ target_mean)
        )
        gradient = weighted_mean - target_mean
        return objective, gradient

    result = minimize(
        objective_gradient,
        np.zeros(sample_features.shape[1], dtype=np.float64),
        method="L-BFGS-B",
        jac=True,
        options={
            "maxiter": max_iterations,
            "maxfun": max_iterations * 8,
            "ftol": 1e-10,
            "gtol": 1e-7,
            "maxls": 20,
        },
    )
    final_gap = float(np.max(np.abs(result.jac)))
    return np.asarray(result.x, dtype=np.float64), {
        "optimizer_success_on_calibration_sample": bool(result.success),
        "optimizer_message": str(result.message),
        "optimizer_iterations": int(result.nit),
        "optimizer_evaluations": int(result.nfev),
        "optimizer_sample_max_abs_mean_gap": final_gap,
        "optimizer_gradient_gap_le_1e-6_on_sample": bool(final_gap <= 1e-6),
        "optimizer_objective": float(result.fun),
        "optimizer_elapsed_seconds": float(time.perf_counter() - started),
        "calibration_sample_controls_n": int(len(sample_features)),
    }


def _evaluate_on_full_reference(
    reference_source: Callable[[], Iterable[pd.DataFrame]],
    transform: Any,
    coefficients: np.ndarray,
    treated_count: int,
    control_count: int,
    target_mean: np.ndarray,
) -> dict[str, Any]:
    """Apply weights over all reference rows; accumulate in a single CSV pass."""
    feature_count = len(transform.feature_names)
    treated_outcome_sum = 0.0
    observed_treated = 0

    log_scale = -np.inf
    scaled_partition = 0.0
    scaled_stats = np.zeros(feature_count + 1, dtype=np.float64)
    squared_log_scale = -np.inf
    scaled_squared_partition = 0.0
    max_logit = -np.inf
    min_logit = np.inf
    rng = np.random.default_rng(5489)
    priority_sample = np.empty(0, dtype=np.float64)
    logit_sample = np.empty(0, dtype=np.float64)
    observed_controls = 0

    for rows in reference_source():
        treatment = rows["treatment_binary"].to_numpy(dtype=np.int8)
        treated = rows.loc[treatment == 1]
        if not treated.empty:
            treated_outcome_sum += float(treated["birthweight_g"].sum())
            observed_treated += len(treated)

        controls = rows.loc[treatment == 0]
        if controls.empty:
            continue
        observed_controls += len(controls)
        features = transform.transform(controls)
        logits = features @ coefficients
        batch_max = float(logits.max())
        batch_scaled_weights = np.exp(logits - batch_max)
        batch_partition = float(batch_scaled_weights.sum())
        batch_stats = np.column_stack(
            (features, controls["birthweight_g"].to_numpy(dtype=np.float64))
        )
        batch_weighted_stats = batch_scaled_weights @ batch_stats

        new_scale = max(log_scale, batch_max)
        old_factor = 0.0 if not np.isfinite(log_scale) else np.exp(log_scale - new_scale)
        batch_factor = np.exp(batch_max - new_scale)
        scaled_partition = scaled_partition * old_factor + batch_partition * batch_factor
        scaled_stats = scaled_stats * old_factor + batch_weighted_stats * batch_factor
        log_scale = new_scale

        twice_logits = 2.0 * logits
        batch_sq_max = float(twice_logits.max())
        batch_sq_sum = float(np.exp(twice_logits - batch_sq_max).sum())
        new_sq_scale = max(squared_log_scale, batch_sq_max)
        old_sq_factor = (
            0.0
            if not np.isfinite(squared_log_scale)
            else np.exp(squared_log_scale - new_sq_scale)
        )
        batch_sq_factor = np.exp(batch_sq_max - new_sq_scale)
        scaled_squared_partition = (
            scaled_squared_partition * old_sq_factor + batch_sq_sum * batch_sq_factor
        )
        squared_log_scale = new_sq_scale
        max_logit = max(max_logit, batch_max)
        min_logit = min(min_logit, float(logits.min()))
        priority_sample, logit_sample = _update_priority_sample(
            priority_sample,
            logit_sample,
            logits,
            rng,
            capacity=DIAGNOSTIC_SAMPLE_SIZE,
        )

    if observed_treated != treated_count or observed_controls != control_count:
        raise ValueError("Reference rows did not match the split's treatment counts.")
    if scaled_partition <= 0 or scaled_squared_partition <= 0:
        raise FloatingPointError("Entropy weight normalization failed.")

    log_partition = log_scale + np.log(scaled_partition)
    log_partition_squared = squared_log_scale + np.log(scaled_squared_partition)
    treated_mean_outcome = treated_outcome_sum / treated_count
    weighted_control_mean_outcome = float(scaled_stats[-1] / scaled_partition)
    entropy_att = treated_mean_outcome - weighted_control_mean_outcome
    weighted_control_mean = scaled_stats[:-1] / scaled_partition
    mean_gap = weighted_control_mean - target_mean
    ess = float(np.exp(2.0 * log_partition - log_partition_squared))
    sample_weights = treated_count * np.exp(logit_sample - log_partition)
    weight_quantiles = np.quantile(sample_weights, [0.0, 0.5, 0.95, 0.99, 1.0])

    return {
        "entropy_balancing_att_g": float(entropy_att),
        "entropy_balancing_weight_sum": int(treated_count),
        "entropy_balancing_target_treated_n": int(treated_count),
        "entropy_balancing_reference_controls_n": int(control_count),
        "entropy_balancing_weight_ess": ess,
        "entropy_balancing_weight_min": float(treated_count * np.exp(min_logit - log_partition)),
        "entropy_balancing_weight_median_approx": float(weight_quantiles[1]),
        "entropy_balancing_weight_p95_approx": float(weight_quantiles[2]),
        "entropy_balancing_weight_p99_approx": float(weight_quantiles[3]),
        "entropy_balancing_weight_max": float(treated_count * np.exp(max_logit - log_partition)),
        "entropy_balancing_weight_quantile_sample_n": int(len(logit_sample)),
        "entropy_balancing_weight_quantiles_approximate": True,
        "entropy_balancing_max_abs_encoded_mean_gap_full_reference": float(
            np.max(np.abs(mean_gap))
        ),
        "entropy_balancing_mean_gap_by_encoded_feature": json.dumps(
            {name: float(gap) for name, gap in zip(transform.feature_names, mean_gap)},
            sort_keys=True,
        ),
        "entropy_balancing_full_reference_weights_approximate": True,
    }


def run(
    input_path: Path,
    saved_aipw_path: Path,
    seed: int,
    test_fraction: float,
    output_dir: Path,
    max_iterations: int,
) -> None:
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    aipw_att, aipw_se, expected_test_treated = _read_saved_aipw(saved_aipw_path)
    split_seed = int(np.random.SeedSequence([seed, 1]).generate_state(1)[0])
    test, reference_source, counts = _make_streamed_split(
        input_path,
        test_fraction,
        split_seed,
    )
    if int(test["treatment_binary"].sum()) != expected_test_treated:
        raise ValueError(
            "Recreated split does not match the saved run's treated test count. "
            "Refusing to compare against an unrelated AIPW split."
        )
    print(
        f"Recreated split 1: {len(test):,} test rows, {counts['rows']:,} reference rows, "
        f"{counts['treated']:,} reference treated, {counts['controls']:,} reference controls."
    )

    print("Fitting reference encoding in batches.")
    transform = fit_natality_transform(
        reference_source,
        chunk_rows=REFERENCE_MODEL_CHUNK_SIZE,
        cohort_size=counts["rows"],
    )
    print(f"Collecting exact treated targets and {CALIBRATION_SAMPLE_SIZE:,} sampled controls.")
    target_mean, calibration_features = _collect_target_and_control_sample(
        reference_source,
        transform,
        counts["treated"],
        CALIBRATION_SAMPLE_SIZE,
    )
    print("Optimizing entropy weights on the in-memory covariate sample.")
    coefficients, optimizer_diagnostics = _fit_sample_entropy_balancing(
        calibration_features,
        target_mean,
        max_iterations,
    )
    del calibration_features

    print("Applying weights to the full reference cohort and measuring balance.")
    results = _evaluate_on_full_reference(
        reference_source,
        transform,
        coefficients,
        counts["treated"],
        counts["controls"],
        target_mean,
    )
    results["entropy_balancing_difference_vs_aipw_g"] = (
        results["entropy_balancing_att_g"] - aipw_att
    )
    results["entropy_balancing_difference_vs_aipw_se"] = (
        results["entropy_balancing_difference_vs_aipw_g"] / aipw_se
        if aipw_se > 0
        else np.nan
    )
    results.update(optimizer_diagnostics)
    results.update(
        {
            "split": 1,
            "split_seed": seed,
            "test_fraction": test_fraction,
            "test_rows_n": len(test),
            "test_treated_n": int(test["treatment_binary"].sum()),
            "reference_rows_n": counts["rows"],
            "reference_treated_n": counts["treated"],
            "reference_controls_n": counts["controls"],
            "reference_aipw_att_g": aipw_att,
            "reference_aipw_se_g": aipw_se,
            "reference_aipw_ci_lower_g": aipw_att - 1.96 * aipw_se,
            "reference_aipw_ci_upper_g": aipw_att + 1.96 * aipw_se,
            "covariate_fields": ",".join(FIELD_ORDER),
            "encoded_covariate_columns_n": len(transform.feature_names),
            "entropy_balancing_constraints_n": len(transform.feature_names),
            "outcome_used_to_fit_weights": False,
            "calibration_sample_size": CALIBRATION_SAMPLE_SIZE,
        }
    )

    output_dir.mkdir(parents=True, exist_ok=False)
    output_csv = output_dir / "summary.csv"
    with output_csv.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(results))
        writer.writeheader()
        writer.writerow(results)
    record = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input": str(input_path),
        "saved_aipw_output": str(saved_aipw_path),
        "split_seed": seed,
        "test_fraction": test_fraction,
        "output": str(output_csv),
        "method": "ATT entropy balancing via exponential tilting, calibrated on a uniform control sample",
        "constraints": "Treated target means are exact; calibration solves their match on 500,000 sampled reference controls. Full-reference moment gaps are then measured.",
        "outcomes_used_for_weight_fitting": False,
        "aipw_reference_reused_from_saved_run": True,
        "interpretation": "This is an approximate full-reference entropy-balancing sensitivity estimate. Its validity should be judged from full-reference balance gaps and weight diagnostics. It is not independent ground truth.",
        "summary": results,
    }
    (output_dir / "record.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote entropy-balancing comparison to {output_csv}")
    print(f"Entropy-balancing ATT: {results['entropy_balancing_att_g']:.6f} g")
    print(f"Saved AIPW ATT: {aipw_att:.6f} g")
    print(f"Difference (EB - AIPW): {results['entropy_balancing_difference_vs_aipw_g']:.6f} g")
    print(
        "Full-reference max absolute encoded mean gap: "
        f"{results['entropy_balancing_max_abs_encoded_mean_gap_full_reference']:.6g}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--aipw-results", type=Path, default=DEFAULT_AIPW_RESULTS)
    parser.add_argument("--seed", type=int, default=20261026)
    parser.add_argument("--test-fraction", type=float, default=0.01)
    parser.add_argument("--max-iterations", type=int, default=100)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_ROOT / "1-split 20261026",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    run(
        input_path=arguments.input,
        saved_aipw_path=arguments.aipw_results,
        seed=arguments.seed,
        test_fraction=arguments.test_fraction,
        output_dir=arguments.output_dir,
        max_iterations=arguments.max_iterations,
    )
