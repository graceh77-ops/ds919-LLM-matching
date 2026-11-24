"""Select the global validation winner and evaluate it once on the held-out pilot test split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from matching_distance import FIELD_ORDER
from run_matching_experiment import PROPENSITY_SCORE_WEIGHT_FIELD
from run_weight_search_pilot import (
    _covariate_field_weights,
    _evaluate_test_models,
    _write_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-dir", type=Path, required=True)
    parser.add_argument("--prefix-dimensions", type=int, required=True)
    args = parser.parse_args()

    root = args.prepared_dir.resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    if not 1 <= args.prefix_dimensions <= len(manifest["grid_fields"]):
        parser.error("Invalid prefix dimension count for this prepared grid")
    multipliers = [float(value) for value in manifest["multipliers"]]
    expected_shards = len(multipliers) ** args.prefix_dimensions
    suffix_count = len(multipliers) ** (len(manifest["grid_fields"]) - args.prefix_dimensions)
    shard_root = root / "shards"
    summaries: list[dict[str, Any]] = []
    missing: list[int] = []
    for shard_index in range(expected_shards):
        path = shard_root / f"prefix{args.prefix_dimensions}_shard{shard_index:08d}" / "shard_summary.json"
        if not path.is_file():
            missing.append(shard_index)
            continue
        summary = json.loads(path.read_text(encoding="utf-8"))
        if summary.get("status") != "completed":
            raise RuntimeError(f"Shard {shard_index} is not complete: {path}")
        if summary.get("signature", {}).get("prepared_signature") != manifest["prepared_signature"]:
            raise RuntimeError(f"Shard {shard_index} belongs to a different prepared pilot.")
        if summary.get("signature", {}).get("prefix_dimensions") != args.prefix_dimensions:
            raise RuntimeError(f"Shard {shard_index} used a different prefix dimension count.")
        if int(summary.get("completed_candidate_count", -1)) != suffix_count:
            raise RuntimeError(f"Shard {shard_index} did not score its full candidate allocation.")
        summaries.append(summary)

    if missing:
        sample = ", ".join(str(value) for value in missing[:20])
        raise SystemExit(
            f"Refusing test evaluation: missing {len(missing):,} of {expected_shards:,} shards; "
            f"first missing indices: {sample}"
        )
    if not summaries:
        raise SystemExit("No completed shard results were found.")

    winners = [summary["best"] for summary in summaries]
    winner = min(
        winners,
        key=lambda row: (
            float(row["validation_gap_g"]),
            float(row["training_gap_g"]),
            int(row["candidate_index"]),
        ),
    )
    _write_csv(
        root / "shard_winners.csv",
        [
            {
                "shard_index": int(summary["signature"]["shard_index"]),
                "candidate_count": int(summary["candidate_count"]),
                "best_candidate_index": int(summary["best"]["candidate_index"]),
                "training_gap_g": float(summary["best"]["training_gap_g"]),
                "validation_gap_g": float(summary["best"]["validation_gap_g"]),
                "multipliers": json.dumps(summary["best"]["multipliers"], sort_keys=True),
            }
            for summary in summaries
        ],
    )

    result = {
        "status": "partial_merge" if missing else "complete",
        "prepared_signature": manifest["prepared_signature"],
        "grid_fields": manifest["grid_fields"],
        "multipliers": multipliers,
        "total_grid_candidates": int(manifest["grid_candidate_count"]),
        "expected_shards": expected_shards,
        "completed_shards": len(summaries),
        "missing_shards": len(missing),
        "candidate_count_scored": sum(int(row["completed_candidate_count"]) for row in summaries),
        "best_global_candidate": winner,
    }
    (root / "grid_winner.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    # A test set is touched only after the global validation winner is selected.
    import pickle
    with (root / "test.pkl").open("rb") as f:
        test = pickle.load(f)
    with (root / "llm_weights.pkl").open("rb") as f:
        llm_weights = pickle.load(f)
    dimensions = list(FIELD_ORDER)
    if PROPENSITY_SCORE_WEIGHT_FIELD in llm_weights:
        dimensions.append(PROPENSITY_SCORE_WEIGHT_FIELD)
    use_ps = PROPENSITY_SCORE_WEIGHT_FIELD in llm_weights
    test_models = {
        "identity_ps_augmented" if use_ps else "identity": {field: 1.0 for field in dimensions},
        "llm_ps_augmented" if use_ps else "llm": llm_weights,
        "grid_llm_selected": winner["weights"],
    }
    if use_ps:
        test_models["identity_covariates_only"] = {field: 1.0 for field in FIELD_ORDER}
        test_models["llm_covariates_only"] = _covariate_field_weights(llm_weights)
    test_rows = _evaluate_test_models(test, test_models)
    _write_csv(root / "test_results.csv", test_rows)

    final = {
        **result,
        "test_evaluation_performed": True,
        "test_evaluation_scope": "pilot test split; development and timing evidence only",
        "aipw_interpretation": "estimated reference, not known causal ground truth",
        "test_results": test_rows,
    }
    (root / "merged_run_metadata.json").write_text(json.dumps(final, indent=2) + "\n", encoding="utf-8")
    print(
        f"Merged {len(summaries):,}/{expected_shards:,} shards; "
        f"best validation gap={winner['validation_gap_g']:.4f} g; "
        f"winner multipliers={json.dumps(winner['multipliers'], sort_keys=True)}.",
        flush=True,
    )
    for row in test_rows:
        print(
            f"{row['model']}: test ATT={row['matched_att_g']:.3f} g; "
            f"AIPW gap={row['absolute_gap_vs_aipw_g']:.3f} g; "
            f"max SMD={row['max_abs_smd_after']:.3f}",
            flush=True,
        )
    if missing:
        print(f"Missing shard indices (first 20): {missing[:20]}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
