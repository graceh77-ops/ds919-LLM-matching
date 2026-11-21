"""Run all ACIC 2016 settings/replications sequentially with checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from load_acic_replication import DEFAULT_DATA_DIR, list_replications
from run_matching_experiment import run_replication


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = PROJECT_DIR / "results"
EXPECTED_METHODS = {
    "identity_generalized_mahalanobis",
    "propensity_score_logit",
    "pca_mahalanobis",
    "llm_weighted_generalized_mahalanobis",
}
PS_AUGMENTED_BASE_METHODS = {
    "identity_ps_augmented_generalized_mahalanobis",
    "pca_ps_augmented_mahalanobis",
}
RESULT_FILES = {
    "complete_information.csv",
    "replication_reference.csv",
    "feature_map.csv",
    "ps_augmented_feature_map.csv",
    "failures.csv",
    "progress.jsonl",
    "run_metadata.json",
    "summary_by_setting.csv",
    "summary_overall.csv",
}


def _new_output_dir(timestamp: str) -> Path:
    pattern = re.compile(r"^full_run(\d+)_\d{8}T\d{6}Z$")
    run_numbers = [
        int(match.group(1))
        for path in DEFAULT_RESULTS_DIR.iterdir()
        if path.is_dir() and (match := pattern.fullmatch(path.name))
    ]
    return DEFAULT_RESULTS_DIR / f"full_run{max(run_numbers, default=0) + 1}_{timestamp}"


def _load_completed(progress_path: Path) -> set[tuple[int, str]]:
    completed: set[tuple[int, str]] = set()
    if not progress_path.is_file():
        return completed
    for line in progress_path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
            completed.add((int(record["setting"]), str(record["replication"])))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            # An interrupted final append is ignored; successful records are
            # flushed only after both result CSV rows have been written.
            continue
    return completed


def _keep_completed_rows(path: Path, completed: set[tuple[int, str]]) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        return
    frame = pd.read_csv(path)
    keys = list(zip(frame["setting"].astype(int), frame["replication"].astype(str)))
    frame = frame.loc[[key in completed for key in keys]]
    frame.to_csv(path, index=False)


def _append_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, mode="a", header=not path.exists() or path.stat().st_size == 0, index=False)


def _write_summaries(results_path: Path, output_dir: Path) -> None:
    if not results_path.is_file() or results_path.stat().st_size == 0:
        return
    results = pd.read_csv(results_path)
    metric_aggs = {
        "replications_n": ("replication", "nunique"),
        "matched_att_mean": ("matched_att", "mean"),
        "matched_att_sd": ("matched_att", "std"),
        "error_vs_realized_satt_mean": ("error_vs_realized_satt", "mean"),
        "absolute_error_vs_realized_satt_mean": (
            "absolute_error_vs_realized_satt",
            "mean",
        ),
        "absolute_error_vs_realized_satt_sd": (
            "absolute_error_vs_realized_satt",
            "std",
        ),
        "max_abs_smd_before_mean": ("max_abs_smd_before", "mean"),
        "max_abs_smd_after_mean": ("max_abs_smd_after", "mean"),
        "max_abs_smd_after_sd": ("max_abs_smd_after", "std"),
        "treated_n_mean": ("treated_n", "mean"),
        "unique_controls_n_mean": ("unique_controls_n", "mean"),
        "max_control_reuse_mean": ("max_control_reuse", "mean"),
    }
    by_setting = (
        results.groupby(["setting", "method"], as_index=False)
        .agg(**metric_aggs)
        .sort_values(["setting", "method"])
    )
    by_setting.to_csv(output_dir / "summary_by_setting.csv", index=False)

    overall = (
        results.groupby("method", as_index=False)
        .agg(**metric_aggs)
        .sort_values("method")
    )
    overall.to_csv(output_dir / "summary_overall.csv", index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--weights-json",
        type=Path,
        required=True,
        help="One saved DeepSeek JSON vector with keys x_1 through x_58",
    )
    parser.add_argument(
        "--ps-augmented-weights-json",
        type=Path,
        help=(
            "Optional saved vector with keys x_1 through x_58 plus propensity_score; "
            "elicited with the prior-judgment prompt"
        ),
    )
    parser.add_argument(
        "--ps-augmented-evidence-weights-json",
        type=Path,
        help=(
            "Optional 59-score vector elicited with the evidence-focused prompt; "
            "can be run alongside the prior-judgment vector"
        ),
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="New output folder by default; pass an existing run folder to resume it",
    )
    parser.add_argument(
        "--settings",
        default="all",
        help="'all' or a comma-separated list of settings from 1 through 77",
    )
    parser.add_argument(
        "--replications-per-setting",
        type=int,
        default=100,
        help="Number of first replications per selected setting (1-100)",
    )
    args = parser.parse_args()

    if args.settings.strip().lower() == "all":
        selected_settings = list(range(1, 78))
    else:
        try:
            selected_settings = [int(value.strip()) for value in args.settings.split(",")]
        except ValueError:
            parser.error("--settings must be 'all' or comma-separated integers")
        if (
            not selected_settings
            or len(set(selected_settings)) != len(selected_settings)
            or any(setting < 1 or setting > 77 for setting in selected_settings)
        ):
            parser.error("--settings must contain unique integers from 1 through 77")
    if not 1 <= args.replications_per_setting <= 100:
        parser.error("--replications-per-setting must be between 1 and 100")

    weights_path = args.weights_json.resolve()
    if not weights_path.is_file():
        parser.error(f"Weights file not found: {weights_path}")
    weights_hash = hashlib.sha256(weights_path.read_bytes()).hexdigest()
    ps_augmented_weights_path = (
        args.ps_augmented_weights_json.resolve()
        if args.ps_augmented_weights_json
        else None
    )
    if ps_augmented_weights_path is not None and not ps_augmented_weights_path.is_file():
        parser.error(f"PS-augmented weights file not found: {ps_augmented_weights_path}")
    ps_augmented_evidence_weights_path = (
        args.ps_augmented_evidence_weights_json.resolve()
        if args.ps_augmented_evidence_weights_json
        else None
    )
    if (
        ps_augmented_evidence_weights_path is not None
        and not ps_augmented_evidence_weights_path.is_file()
    ):
        parser.error(
            "Evidence-focused PS-augmented weights file not found: "
            f"{ps_augmented_evidence_weights_path}"
        )
    ps_augmented_weights_hash = (
        hashlib.sha256(ps_augmented_weights_path.read_bytes()).hexdigest()
        if ps_augmented_weights_path is not None
        else None
    )
    ps_augmented_evidence_weights_hash = (
        hashlib.sha256(ps_augmented_evidence_weights_path.read_bytes()).hexdigest()
        if ps_augmented_evidence_weights_path is not None
        else None
    )
    augmented_vectors = {
        style: path
        for style, path in (
            ("prior_judgment", ps_augmented_weights_path),
            ("evidence_focused", ps_augmented_evidence_weights_path),
        )
        if path is not None
    }
    expected_methods = EXPECTED_METHODS | (
        (
            PS_AUGMENTED_BASE_METHODS
            | {
                f"llm_weighted_ps_augmented_{style}_generalized_mahalanobis"
                for style in augmented_vectors
            }
        )
        if augmented_vectors
        else set()
    )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir.resolve() if args.output_dir else _new_output_dir(timestamp)
    if output_dir.exists():
        if not args.output_dir:
            raise FileExistsError(f"Refusing to overwrite existing run: {output_dir}")
        unexpected = [
            path.name for path in output_dir.iterdir() if path.name not in RESULT_FILES
        ]
        if unexpected:
            raise ValueError(
                f"Cannot resume folder with unrelated contents: {unexpected}"
            )
    else:
        output_dir.mkdir(parents=True)

    progress_path = output_dir / "progress.jsonl"
    results_path = output_dir / "complete_information.csv"
    references_path = output_dir / "replication_reference.csv"
    completed = _load_completed(progress_path)
    # Discard any result rows written before an interrupted checkpoint marker.
    _keep_completed_rows(results_path, completed)
    _keep_completed_rows(references_path, completed)

    expected_pairs = [
        (setting, replication)
        for setting in selected_settings
        for replication in list_replications(setting, args.data_dir)[
            : args.replications_per_setting
        ]
    ]
    expected_replications = len(expected_pairs)

    start_time = datetime.now(timezone.utc)
    started = time.monotonic()
    metadata = {
        "status": "running",
        "started_at_utc": start_time.isoformat(),
        "expected_replications": len(expected_pairs),
        "completed_before_run": len(completed),
        "weights_path": str(weights_path),
        "weights_sha256": weights_hash,
        "ps_augmented_weights_path": (
            str(ps_augmented_weights_path)
            if ps_augmented_weights_path is not None
            else None
        ),
        "ps_augmented_weights_sha256": ps_augmented_weights_hash,
        "ps_augmented_evidence_weights_path": (
            str(ps_augmented_evidence_weights_path)
            if ps_augmented_evidence_weights_path is not None
            else None
        ),
        "ps_augmented_evidence_weights_sha256": ps_augmented_evidence_weights_hash,
        "data_dir": str(args.data_dir.resolve()),
        "settings": selected_settings,
        "settings_n": len(selected_settings),
        "replications_per_setting": args.replications_per_setting,
        "methods": sorted(expected_methods),
    }
    metadata_path = output_dir / "run_metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    failures_path = output_dir / "failures.csv"
    if not failures_path.exists():
        pd.DataFrame(columns=["setting", "replication", "error"]).to_csv(
            failures_path, index=False
        )

    done_this_run = 0
    for index, (setting, replication) in enumerate(expected_pairs, start=1):
        if (setting, replication) in completed:
            continue
        try:
            method_results, references, feature_map, augmented_feature_map = run_replication(
                setting,
                replication,
                args.data_dir,
                weights_path,
                ps_augmented_weights_path,
                ps_augmented_evidence_weights_path,
            )
            actual_methods = set(method_results["method"].astype(str))
            if actual_methods != expected_methods:
                raise RuntimeError(f"Unexpected method set: {sorted(actual_methods)}")
            if not (output_dir / "feature_map.csv").exists():
                feature_map.to_csv(output_dir / "feature_map.csv", index=False)
            if augmented_feature_map is not None and not (
                output_dir / "ps_augmented_feature_map.csv"
            ).exists():
                augmented_feature_map.to_csv(
                    output_dir / "ps_augmented_feature_map.csv", index=False
                )
            _append_csv(method_results, results_path)
            _append_csv(references, references_path)
            with progress_path.open("a", encoding="utf-8", newline="\n") as progress:
                progress.write(
                    json.dumps({"setting": setting, "replication": replication}) + "\n"
                )
                progress.flush()
            completed.add((setting, replication))
            done_this_run += 1
        except Exception as exc:  # keep the benchmark moving; retain failure details
            _append_csv(
                pd.DataFrame(
                    [{"setting": setting, "replication": replication, "error": repr(exc)}]
                ),
                failures_path,
            )

        if index % 10 == 0 or index == expected_replications:
            elapsed = time.monotonic() - started
            print(
                f"Scanned {index}/{expected_replications}; "
                f"successful {len(completed)}/{expected_replications}; "
                f"failures {sum(1 for _ in failures_path.open(encoding='utf-8')) - 1}; "
                f"elapsed {elapsed / 60:.1f} min",
                flush=True,
            )

    _write_summaries(results_path, output_dir)
    failure_count = max(
        0,
        sum(1 for _ in failures_path.open(encoding="utf-8")) - 1,
    )
    metadata.update(
        {
            "status": "complete" if not failure_count else "complete_with_failures",
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "successful_replications_total": len(completed),
            "successful_replications_this_run": done_this_run,
            "failure_rows": failure_count,
            "elapsed_seconds_this_run": time.monotonic() - started,
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Benchmark status: {metadata['status']}")
    print(f"Results folder: {output_dir}")
    return 0 if len(completed) == expected_replications and not failure_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
