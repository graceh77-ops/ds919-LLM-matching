"""Run ATE matching comparisons and a reference AIPW-ATE analysis."""

from __future__ import annotations

import argparse
import json
import math
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd
from scipy.special import expit

from matching_distance import (
    FIELD_ORDER,
    fit_natality_transform,
    nearest_neighbor_with_replacement,
)
from ps_augmented_matching.coordinates import build_representation
from run_matching_experiment import (
    DEFAULT_INPUT,
    DEFAULT_TEST_FRACTION,
    PROPENSITY_SCORE_WEIGHT_FIELD,
    _covariate_balance_smds,
    _covariate_field_weights,
    _fit_propensity_model,
    _fit_reference_control_outcome,
    _load_streamed_pilot,
    _make_streamed_split,
    _pca_mahalanobis_coordinates,
    _ps_augmented_diagonal_weights,
    _stratified_split,
    _test_propensity_coordinates,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS = (
    PROJECT_ROOT
    / "results"
    / "matching results_2016-2024"
    / "deepseek_api"
    / "20261026T052201Z"
    / "weights.json"
)
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "results" / "ate_matching"
DEFAULT_PS_WEIGHTS = (
    PROJECT_ROOT
    / "results"
    / "ps_augmented_matching"
    / "deepseek_api"
    / "20261102T060435Z"
    / "weights.json"
)


def _load_weights(path: Path) -> dict[str, float]:
    with path.open("r", encoding="utf-8-sig") as source:
        raw = json.load(source)
    if not isinstance(raw, dict):
        raise ValueError("Weight JSON must be an object keyed by field name.")
    allowed = (set(FIELD_ORDER), set(FIELD_ORDER) | {PROPENSITY_SCORE_WEIGHT_FIELD})
    if set(raw) not in allowed:
        raise ValueError("Weights must contain the eleven covariates, optionally plus PROPENSITY_SCORE.")
    values = {str(field): float(value) for field, value in raw.items()}
    if not np.isfinite(list(values.values())).all() or min(values.values()) < 0:
        raise ValueError("Weights must be finite and nonnegative.")
    if sum(values.values()) <= 0:
        raise ValueError("At least one weight must be positive.")
    if PROPENSITY_SCORE_WEIGHT_FIELD in values and sum(
        values[field] for field in FIELD_ORDER
    ) <= 0:
        raise ValueError("PS-augmented matching also needs positive covariate weight.")
    return values


def _fit_reference_outcome_group(
    reference: Callable[[], Iterable[pd.DataFrame]],
    transform: Any,
    treatment_value: int,
    expected_count: int,
) -> np.ndarray:
    """Fit linear E[Y|X,T=t] by incremental QR over a repeatable batch source."""
    if expected_count <= len(transform.feature_names):
        raise ValueError("Too few records in a treatment group for the outcome model.")
    triangular: np.ndarray | None = None
    observed = 0
    for batch in reference():
        rows = batch.loc[batch["treatment_binary"] == treatment_value]
        if rows.empty:
            continue
        observed += len(rows)
        features = transform.transform(rows)
        design = np.column_stack((np.ones(len(rows), dtype=np.float64), features))
        outcome = rows["birthweight_g"].to_numpy(dtype=np.float64)
        augmented = np.column_stack((design, outcome))
        stack = augmented if triangular is None else np.vstack((triangular, augmented))
        triangular = np.linalg.qr(stack, mode="r")
    if observed != expected_count or triangular is None:
        raise ValueError(f"Observed {observed} group-{treatment_value} rows; expected {expected_count}.")
    coefficient_count = len(transform.feature_names) + 1
    coefficients, _, _, _ = np.linalg.lstsq(
        triangular[:, :coefficient_count], triangular[:, coefficient_count], rcond=None
    )
    return np.asarray(coefficients, dtype=np.float64)


def _reference_aipw_ate(
    reference: Callable[[], Iterable[pd.DataFrame]],
    transform: Any,
    propensity_coefficients: np.ndarray,
    outcome0_coefficients: np.ndarray,
    outcome1_coefficients: np.ndarray,
    cohort_size: int,
) -> dict[str, float | int]:
    """Stream the AIPW-ATE score and return its estimate, SE, and overlap diagnostics."""
    score_sum = 0.0
    score_square_sum = 0.0
    observed = 0
    clip_count = 0
    treated_weight_sum = treated_weight_square_sum = 0.0
    control_weight_sum = control_weight_square_sum = 0.0
    probability_min = 1.0
    probability_max = 0.0
    epsilon = 1e-6
    for batch in reference():
        features = transform.transform(batch)
        treatment = batch["treatment_binary"].to_numpy(dtype=np.int8)
        outcome = batch["birthweight_g"].to_numpy(dtype=np.float64)
        raw_probability = expit(propensity_coefficients[0] + features @ propensity_coefficients[1:])
        probability_min = min(probability_min, float(raw_probability.min()))
        probability_max = max(probability_max, float(raw_probability.max()))
        probability = np.clip(raw_probability, epsilon, 1.0 - epsilon)
        clip_count += int(np.count_nonzero(probability != raw_probability))
        mu0 = outcome0_coefficients[0] + features @ outcome0_coefficients[1:]
        mu1 = outcome1_coefficients[0] + features @ outcome1_coefficients[1:]
        score = (
            mu1 - mu0
            + treatment * (outcome - mu1) / probability
            - (1 - treatment) * (outcome - mu0) / (1.0 - probability)
        )
        score_sum += float(score.sum())
        score_square_sum += float(np.dot(score, score))
        observed += len(batch)
        treated_weights = 1.0 / probability[treatment == 1]
        control_weights = 1.0 / (1.0 - probability[treatment == 0])
        treated_weight_sum += float(treated_weights.sum())
        treated_weight_square_sum += float(np.dot(treated_weights, treated_weights))
        control_weight_sum += float(control_weights.sum())
        control_weight_square_sum += float(np.dot(control_weights, control_weights))
    if observed != cohort_size:
        raise ValueError(f"AIPW stream yielded {observed} rows; expected {cohort_size}.")
    estimate = score_sum / observed
    variance = max((score_square_sum - score_sum * score_sum / observed) / max(observed - 1, 1), 0.0)
    standard_error = math.sqrt(variance / observed)
    return {
        "reference_aipw_ate_g": estimate,
        "reference_aipw_ate_se_g": standard_error,
        "reference_aipw_ate_ci_lower_g": estimate - 1.96 * standard_error,
        "reference_aipw_ate_ci_upper_g": estimate + 1.96 * standard_error,
        "reference_propensity_min": probability_min,
        "reference_propensity_max": probability_max,
        "reference_propensity_clipped_n": clip_count,
        "reference_treated_ipw_ess": treated_weight_sum**2 / treated_weight_square_sum,
        "reference_control_ipw_ess": control_weight_sum**2 / control_weight_square_sum,
    }


def _match_ate(
    frame: pd.DataFrame,
    treated_coordinates: np.ndarray,
    control_coordinates: np.ndarray,
) -> dict[str, Any]:
    """Estimate ATE by two-way 1:1 nearest-neighbor imputation with replacement."""
    treated_mask = frame["treatment_binary"].to_numpy(dtype=np.int8) == 1
    treated = frame.loc[treated_mask]
    controls = frame.loc[~treated_mask]
    if treated.empty or controls.empty:
        raise ValueError("Matching requires both treated and control records.")
    treated_outcomes = treated["birthweight_g"].to_numpy(dtype=np.float64)
    control_outcomes = controls["birthweight_g"].to_numpy(dtype=np.float64)
    treated_ids = treated["record_number"].to_numpy(dtype=np.int64)
    control_ids = controls["record_number"].to_numpy(dtype=np.int64)

    treated_to_control = nearest_neighbor_with_replacement(
        treated_coordinates, control_coordinates, control_ids
    )
    control_to_treated = nearest_neighbor_with_replacement(
        control_coordinates, treated_coordinates, treated_ids
    )
    att = float(np.mean(treated_outcomes - control_outcomes[treated_to_control.control_indices]))
    atc = float(np.mean(treated_outcomes[control_to_treated.control_indices] - control_outcomes))
    treated_fraction = len(treated) / len(frame)
    ate = treated_fraction * att + (1.0 - treated_fraction) * atc

    matched_controls = controls.iloc[treated_to_control.control_indices]
    matched_treated = treated.iloc[control_to_treated.control_indices]
    balance_att = _covariate_balance_smds(treated, matched_controls)
    balance_atc = _covariate_balance_smds(matched_treated, controls)
    return {
        "test_ate_g": ate,
        "test_att_component_g": att,
        "test_atc_component_g": atc,
        "test_treated_n": len(treated),
        "test_control_n": len(controls),
        "att_unique_controls_n": int(np.unique(treated_to_control.control_indices).size),
        "atc_unique_treated_n": int(np.unique(control_to_treated.control_indices).size),
        "att_max_control_reuse": int(np.bincount(treated_to_control.control_indices).max()),
        "atc_max_treated_reuse": int(np.bincount(control_to_treated.control_indices).max()),
        "att_match_distance_median": float(np.median(treated_to_control.distances)),
        "atc_match_distance_median": float(np.median(control_to_treated.distances)),
        "att_max_abs_smd_after": float(balance_att["max_abs_smd"]),
        "atc_max_abs_smd_after": float(balance_atc["max_abs_smd"]),
    }


def _evaluate_methods(
    frame: pd.DataFrame,
    transform: Any,
    features: np.ndarray,
    weights: dict[str, float] | None,
    include_ps_augmented: bool,
) -> list[dict[str, Any]]:
    treatment = frame["treatment_binary"].to_numpy(dtype=np.int8)
    treated_mask = treatment == 1
    methods: list[tuple[str, np.ndarray, np.ndarray]] = []

    identity_weights = np.ones(len(transform.feature_names), dtype=np.float64)
    identity_coords = features @ transform.distance_factor(identity_weights)
    methods.append(("identity_generalized_mahalanobis", identity_coords[treated_mask], identity_coords[~treated_mask]))

    propensity_coefficients = _fit_propensity_model(frame, transform)
    propensity_coordinates = _test_propensity_coordinates(
        frame, transform, propensity_coefficients, test_features=features
    )
    methods.append(("propensity_score_logit", *propensity_coordinates))

    pca_coordinates, pca_components, pca_variance = _pca_mahalanobis_coordinates(
        features, treatment, expected_feature_count=len(transform.feature_names)
    )
    methods.append(("pca_mahalanobis", *pca_coordinates))

    if weights is not None:
        covariate_weights = _covariate_field_weights(weights)
        diagonal = transform.diagonal_field_weights(covariate_weights)
        llm_coords = features @ transform.distance_factor(diagonal)
        methods.append(("llm_weighted_generalized_mahalanobis", llm_coords[treated_mask], llm_coords[~treated_mask]))

    ps_diagnostics = None
    if include_ps_augmented:
        representation, inverse_root, ps_diagnostics = build_representation(
            features, propensity_coefficients
        )
        np.matmul(representation, inverse_root, out=representation)
        ps_pca_coordinates, ps_pca_components, ps_pca_variance = _pca_mahalanobis_coordinates(
            representation,
            treatment,
            expected_feature_count=len(transform.feature_names) + 1,
        )
        methods.append(("identity_ps_augmented_generalized_mahalanobis", representation[treated_mask].copy(), representation[~treated_mask].copy()))
        methods.append(("pca_ps_augmented_mahalanobis", *ps_pca_coordinates))
        ps_diagonal, _ = _ps_augmented_diagonal_weights(weights or {}, transform)
        llm_representation = representation * np.sqrt(ps_diagonal)[None, :]
        methods.append(("llm_weighted_ps_augmented_generalized_mahalanobis", llm_representation[treated_mask], llm_representation[~treated_mask]))

    rows = []
    for name, treated_coordinates, control_coordinates in methods:
        result = _match_ate(frame, treated_coordinates, control_coordinates)
        result["method"] = name
        if name == "pca_mahalanobis":
            result.update({"pca_components_n": pca_components, "pca_cumulative_variance": pca_variance})
        elif name == "pca_ps_augmented_mahalanobis":
            result.update({"pca_components_n": ps_pca_components, "pca_cumulative_variance": ps_pca_variance})
        if name in {
            "identity_ps_augmented_generalized_mahalanobis",
            "pca_ps_augmented_mahalanobis",
            "llm_weighted_ps_augmented_generalized_mahalanobis",
        } and ps_diagnostics is not None:
            result.update(ps_diagnostics)
        rows.append(result)
    return rows


def run_experiment(
    input_path: Path,
    output_dir: Path,
    repeats: int,
    seed: int,
    test_fraction: float,
    pilot_rows: int | None,
    weights: dict[str, float] | None,
    include_ps_augmented: bool,
) -> None:
    if not input_path.is_file():
        raise FileNotFoundError(f"Analysis cohort not found: {input_path}")
    if repeats < 1 or not 0 < test_fraction < 1:
        raise ValueError("repeats must be positive and test_fraction must be between 0 and 1.")
    if pilot_rows is not None and pilot_rows < 100:
        raise ValueError("pilot_rows must be at least 100.")
    if include_ps_augmented and (
        weights is None or PROPENSITY_SCORE_WEIGHT_FIELD not in weights
    ):
        raise ValueError("PS-augmented methods require a 12-score weights file including PROPENSITY_SCORE.")
    output_dir.mkdir(parents=True, exist_ok=False)

    sample = _load_streamed_pilot(input_path, pilot_rows, seed) if pilot_rows else None
    result_rows: list[dict[str, Any]] = []
    reference_rows: list[dict[str, Any]] = []
    for split_number in range(1, repeats + 1):
        if sample is None:
            split_seed = int(np.random.SeedSequence([seed, split_number]).generate_state(1)[0])
            test, reference_source, counts = _make_streamed_split(
                input_path, test_fraction, split_seed
            )
        else:
            rng = np.random.default_rng(np.random.SeedSequence([seed, split_number]))
            reference_indices, test_indices = _stratified_split(sample, test_fraction, rng)
            reference = sample.iloc[reference_indices]
            test = sample.iloc[test_indices]
            counts = {
                "rows": len(reference),
                "treated": int(reference["treatment_binary"].sum()),
                "controls": int((reference["treatment_binary"] == 0).sum()),
                "test_rows": len(test),
            }

            def reference_source(reference_frame: pd.DataFrame = reference) -> Iterable[pd.DataFrame]:
                for start in range(0, len(reference_frame), 100_000):
                    yield reference_frame.iloc[start : start + 100_000]

        print(f"Split {split_number}: fitting reference models; reference rows={counts['rows']:,}.", flush=True)
        reference_transform = fit_natality_transform(reference_source, cohort_size=counts["rows"])
        propensity = _fit_propensity_model(
            reference_source,
            reference_transform,
            cohort_size=counts["rows"],
            treated_count=counts["treated"],
        )
        outcome0 = _fit_reference_control_outcome(
            reference_source, reference_transform, control_count=counts["controls"]
        )
        outcome1 = _fit_reference_outcome_group(
            reference_source, reference_transform, 1, counts["treated"]
        )
        aipw = _reference_aipw_ate(
            reference_source, reference_transform, propensity, outcome0, outcome1, counts["rows"]
        )
        reference_rows.append({"split": split_number, **counts, **aipw})

        # Each matching rule is fit on the same 1% test sample, matching the established CDC runner.
        matching_transform = fit_natality_transform(test)
        features = matching_transform.transform(test)
        test_rows = _evaluate_methods(test, matching_transform, features, weights, include_ps_augmented)
        for row in test_rows:
            row.update({
                "split": split_number,
                "test_fraction": test_fraction,
                **aipw,
                "error_vs_reference_aipw_ate_g": float(row["test_ate_g"] - aipw["reference_aipw_ate_g"]),
            })
            result_rows.append(row)
        print(f"Split {split_number}: evaluated {len(test_rows)} matching methods.", flush=True)

    results = pd.DataFrame(result_rows)
    results_path = output_dir / "ate_matching_results.csv"
    results.to_csv(results_path, index=False)
    summary = results.groupby("method", as_index=False).agg(
        splits=("split", "count"),
        mean_test_ate_g=("test_ate_g", "mean"),
        sd_across_splits_test_ate_g=("test_ate_g", "std"),
        mean_test_att_component_g=("test_att_component_g", "mean"),
        mean_test_atc_component_g=("test_atc_component_g", "mean"),
        mean_reference_aipw_ate_g=("reference_aipw_ate_g", "mean"),
        mean_reference_aipw_ate_se_g=("reference_aipw_ate_se_g", "mean"),
        rmse_vs_reference_aipw_ate_g=("error_vs_reference_aipw_ate_g", lambda x: float(np.sqrt(np.mean(np.square(x))))),
        mean_att_max_abs_smd_after=("att_max_abs_smd_after", "mean"),
        mean_atc_max_abs_smd_after=("atc_max_abs_smd_after", "mean"),
    )
    summary_path = output_dir / "ate_summary.csv"
    summary.to_csv(summary_path, index=False)
    pd.DataFrame(reference_rows).to_csv(output_dir / "reference_aipw_ate.csv", index=False)
    metadata = {
        "status": "completed",
        "estimand": "ATE for singleton births in the analysis cohort",
        "treatment": "CIG_REC=Y versus CIG_REC=N (treatment_binary)",
        "outcome": "birthweight_g",
        "matching_ate_definition": "treated fraction * matched ATT + control fraction * matched ATC; bidirectional 1:1 nearest-neighbor imputation with replacement",
        "reference_estimator": "AIPW-ATE with logistic propensity and separate linear outcome models by treatment group",
        "reference_aipw_is_truth": False,
        "matching_split_method": "treatment-by-year stratified reference/test splits; matching transformations fit on each test sample, reference nuisance models fit on reference sample",
        "matched_ate_uncertainty": "not estimated; variation across repeated splits is descriptive, not a confidence interval",
        "overlap_handling": "no trimming; propensity probabilities are clipped to [1e-6, 1-1e-6] in the AIPW score, with overlap and effective sample size diagnostics reported",
        "input": str(input_path.resolve()),
        "weights": None if weights is None else weights,
        "include_ps_augmented": include_ps_augmented,
        "pilot_rows": pilot_rows,
        "repeats": repeats,
        "seed": seed,
        "test_fraction": test_fraction,
        "output_dir": str(output_dir.resolve()),
    }
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"ATE results: {results_path}", flush=True)
    print(f"ATE summary: {summary_path}", flush=True)
    print(summary.to_string(index=False), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seed", type=int, default=919)
    parser.add_argument("--test-fraction", type=float, default=DEFAULT_TEST_FRACTION)
    parser.add_argument("--pilot-rows", type=int, default=None, help="Optional sampled subset for code/timing checks.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--weights-json", type=Path, default=None)
    group.add_argument("--no-llm-weights", action="store_true")
    parser.add_argument("--include-ps-covariate", action="store_true")
    args = parser.parse_args()

    weights_path = args.weights_json
    if weights_path is None and not args.no_llm_weights:
        weights_path = DEFAULT_PS_WEIGHTS if args.include_ps_covariate else DEFAULT_WEIGHTS
    weights = None if args.no_llm_weights else _load_weights(weights_path)
    if args.include_ps_covariate and (
        weights is None or PROPENSITY_SCORE_WEIGHT_FIELD not in weights
    ):
        parser.error("--include-ps-covariate requires a 12-score weights JSON including PROPENSITY_SCORE.")
    if args.output_dir is None:
        label = f"{args.repeats}-split {date.today():%Y%m%d}"
        output_dir = DEFAULT_OUTPUT_ROOT / label
        suffix = 2
        while output_dir.exists():
            output_dir = DEFAULT_OUTPUT_ROOT / f"{label} ({suffix})"
            suffix += 1
    else:
        output_dir = args.output_dir
    run_experiment(
        input_path=args.input,
        output_dir=output_dir,
        repeats=args.repeats,
        seed=args.seed,
        test_fraction=args.test_fraction,
        pilot_rows=args.pilot_rows,
        weights=weights,
        include_ps_augmented=args.include_ps_covariate,
    )


if __name__ == "__main__":
    main()
