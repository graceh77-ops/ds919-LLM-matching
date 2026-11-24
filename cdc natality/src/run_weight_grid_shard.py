"""Score one resumable, non-overlapping shard of a prepared CDC weight grid."""

from __future__ import annotations

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

from run_weight_search_pilot import _score


def _unrank_product(index: int, radix: int, length: int) -> list[int]:
    if index < 0 or index >= radix**length:
        raise ValueError("Product index is outside the requested range")
    digits = [0] * length
    for position in range(length - 1, -1, -1):
        digits[position] = index % radix
        index //= radix
    return digits


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _candidate(
    manifest: dict[str, Any],
    prefix_digits: list[int],
    suffix_digits: list[int],
    multipliers: list[float],
) -> tuple[dict[str, float], dict[str, float]]:
    fields = manifest["grid_fields"]
    digits = [*prefix_digits, *suffix_digits]
    multiplier_by_field = {
        field: float(multipliers[digit]) for field, digit in zip(fields, digits)
    }
    weights = {
        field: float(value) for field, value in manifest["starting_weights"].items()
    }
    for field, multiplier in multiplier_by_field.items():
        weights[field] *= multiplier
    return weights, multiplier_by_field


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared-dir", type=Path, required=True)
    parser.add_argument("--prefix-dimensions", type=int, required=True)
    parser.add_argument("--shard-index", type=int, required=True, help="Zero-based prefix-combination index.")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=0, help="Candidates per checkpoint batch; default is 8x workers.")
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=10,
        help="Save after this many batches (default 10).",
    )
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    prepared_dir = args.prepared_dir.resolve()
    manifest_path = prepared_dir / "manifest.json"
    if not manifest_path.is_file():
        parser.error(f"Prepared manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    fields = list(manifest["grid_fields"])
    multipliers = [float(value) for value in manifest["multipliers"]]
    dimension_count = len(fields)
    if not 1 <= args.prefix_dimensions <= dimension_count:
        parser.error("--prefix-dimensions must be from 1 through the grid dimension count")
    if args.workers < 1 or args.checkpoint_every < 1 or args.batch_size < 0:
        parser.error("workers/checkpoint-every must be positive and batch-size nonnegative")
    shard_count = len(multipliers) ** args.prefix_dimensions
    if not 0 <= args.shard_index < shard_count:
        parser.error(f"--shard-index must be 0 through {shard_count - 1}")

    suffix_dimensions = dimension_count - args.prefix_dimensions
    candidates_in_shard = len(multipliers) ** suffix_dimensions
    prefix_digits = _unrank_product(args.shard_index, len(multipliers), args.prefix_dimensions)
    prefix_multipliers = [multipliers[index] for index in prefix_digits]
    shard_dir = prepared_dir / "shards" / f"prefix{args.prefix_dimensions}_shard{args.shard_index:08d}"
    checkpoint_path = shard_dir / "checkpoint.json"
    signature = {
        "prepared_signature": manifest["prepared_signature"],
        "prefix_dimensions": args.prefix_dimensions,
        "shard_index": args.shard_index,
        "candidate_count": candidates_in_shard,
    }
    if args.resume:
        if not checkpoint_path.is_file():
            parser.error(f"No checkpoint exists for this shard: {checkpoint_path}")
        state = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if state.get("signature") != signature:
            parser.error("Checkpoint signature does not match this shard configuration")
        if state.get("status") == "completed":
            print(f"Shard is already complete: {shard_dir}", flush=True)
            return 0
    else:
        shard_dir.mkdir(parents=True, exist_ok=False)
        state = {
            "status": "running",
            "signature": signature,
            "next_suffix_index": 0,
            "best": None,
            "training_evaluation_seconds_sum": 0.0,
            "validation_evaluation_seconds_sum": 0.0,
            "started_at_epoch": time.time(),
        }
        _atomic_json(checkpoint_path, state)

    import pickle

    with (prepared_dir / "train.pkl").open("rb") as f:
        train = pickle.load(f)
    with (prepared_dir / "validation.pkl").open("rb") as f:
        validation = pickle.load(f)

    batch_size = args.batch_size or max(8, args.workers * 8)
    suffix_start = int(state["next_suffix_index"])
    started = time.perf_counter()
    elapsed_before = float(state.get("elapsed_seconds_total", 0.0))
    batches_completed = 0
    print(
        f"Shard {args.shard_index + 1}/{shard_count}: prefix={prefix_multipliers}; "
        f"candidates={candidates_in_shard:,}; starting at {suffix_start:,}.",
        flush=True,
    )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        while suffix_start < candidates_in_shard:
            suffix_end = min(suffix_start + batch_size, candidates_in_shard)
            weight_batch: list[dict[str, float]] = []
            multiplier_batch: list[dict[str, float]] = []
            index_batch: list[int] = []
            for suffix_index in range(suffix_start, suffix_end):
                suffix_digits = _unrank_product(
                    suffix_index, len(multipliers), suffix_dimensions
                ) if suffix_dimensions else []
                weights, multiplier_by_field = _candidate(
                    manifest, prefix_digits, suffix_digits, multipliers
                )
                weight_batch.append(weights)
                multiplier_batch.append(multiplier_by_field)
                index_batch.append(args.shard_index * candidates_in_shard + suffix_index)

            def evaluate_one(item):
                weights = item
                tick = time.perf_counter()
                score = _score(train, weights)
                return score, time.perf_counter() - tick

            train_results = list(pool.map(evaluate_one, weight_batch))

            def evaluate_validation(item):
                tick = time.perf_counter()
                score = _score(validation, item)
                return score, time.perf_counter() - tick

            validation_results = list(pool.map(evaluate_validation, weight_batch))
            for i, (weights, multipliers_for_candidate) in enumerate(zip(weight_batch, multiplier_batch)):
                train_score, train_seconds = train_results[i]
                validation_score, validation_seconds = validation_results[i]
                row = {
                    "candidate_index": index_batch[i],
                    "multipliers": multipliers_for_candidate,
                    "weights": weights,
                    "training_gap_g": float(train_score),
                    "validation_gap_g": float(validation_score),
                    "training_evaluation_seconds": float(train_seconds),
                    "validation_evaluation_seconds": float(validation_seconds),
                }
                best = state.get("best")
                order = (row["validation_gap_g"], row["training_gap_g"], row["candidate_index"])
                if best is None or order < (
                    float(best["validation_gap_g"]),
                    float(best["training_gap_g"]),
                    int(best["candidate_index"]),
                ):
                    state["best"] = row
                state["training_evaluation_seconds_sum"] += train_seconds
                state["validation_evaluation_seconds_sum"] += validation_seconds

            state["next_suffix_index"] = suffix_end
            batches_completed += 1
            if batches_completed % args.checkpoint_every == 0 or suffix_end == candidates_in_shard:
                state["elapsed_seconds_total"] = elapsed_before + time.perf_counter() - started
                _atomic_json(checkpoint_path, state)
            suffix_start = suffix_end
            if batches_completed % args.checkpoint_every == 0 or suffix_end == candidates_in_shard:
                print(
                    f"Shard {args.shard_index}: {suffix_end:,}/{candidates_in_shard:,} "
                    f"candidates; best validation gap={state['best']['validation_gap_g']:.4f} g.",
                    flush=True,
                )

    elapsed = time.perf_counter() - started
    summary = {
        "status": "completed",
        "signature": signature,
        "shard_count": shard_count,
        "candidate_count": candidates_in_shard,
        "completed_candidate_count": int(state["next_suffix_index"]),
        "prefix_multipliers": {
            field: multipliers[digit]
            for field, digit in zip(fields[:args.prefix_dimensions], prefix_digits)
        },
        "best": state["best"],
        "elapsed_seconds_total": elapsed_before + elapsed,
        "training_evaluation_seconds_sum": state["training_evaluation_seconds_sum"],
        "validation_evaluation_seconds_sum": state["validation_evaluation_seconds_sum"],
        "completed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_json(shard_dir / "shard_summary.json", summary)
    state["status"] = "completed"
    state["elapsed_seconds_total"] = elapsed_before + elapsed
    state["completed_at_utc"] = summary["completed_at_utc"]
    _atomic_json(checkpoint_path, state)
    print(
        f"Completed shard {args.shard_index}; {candidates_in_shard:,} candidates; "
        f"best validation gap={state['best']['validation_gap_g']:.4f} g; "
        f"elapsed={elapsed:.1f}s; output={shard_dir}.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
