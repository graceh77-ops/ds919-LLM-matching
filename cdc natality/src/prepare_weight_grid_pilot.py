"""Create one reusable pilot split for parallel grid-search shards."""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from run_weight_search_pilot import DEFAULT_MULTIPLIERS, DEFAULT_WEIGHTS, _prepare_split, _read_weights, _split_sample
from run_matching_experiment import DEFAULT_INPUT, _load_streamed_pilot
from matching_distance import FIELD_ORDER
from run_matching_experiment import PROPENSITY_SCORE_WEIGHT_FIELD


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = PROJECT_DIR / "results" / "weight_search_pilots"


def _write_pickle(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        pickle.dump(value, stream, protocol=pickle.HIGHEST_PROTOCOL)
        stream.flush()
    temporary.replace(path)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--weights-json", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--pilot-rows", type=int, default=30_000)
    parser.add_argument("--seed", type=int, default=919)
    parser.add_argument("--multipliers", type=float, nargs="+", default=list(DEFAULT_MULTIPLIERS))
    parser.add_argument("--grid-fields", nargs="+", default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"Input cohort not found: {args.input}")
    if not args.weights_json.is_file():
        parser.error(f"Weights file not found: {args.weights_json}")
    if args.pilot_rows < 100:
        parser.error("--pilot-rows must be at least 100")
    if not args.multipliers or len(set(args.multipliers)) != len(args.multipliers):
        parser.error("--multipliers must be nonempty and unique")
    if any(value <= 0 for value in args.multipliers):
        parser.error("--multipliers must be positive")

    weights = _read_weights(args.weights_json)
    dimensions = [*FIELD_ORDER]
    if PROPENSITY_SCORE_WEIGHT_FIELD in weights:
        dimensions.append(PROPENSITY_SCORE_WEIGHT_FIELD)
    fields = args.grid_fields or dimensions
    unknown = set(fields) - set(dimensions)
    if unknown or not fields or len(fields) != len(set(fields)):
        parser.error(f"Invalid grid fields; unknown={sorted(unknown)}")
    if not set(fields).issubset(weights):
        parser.error("Every grid field must have a starting weight in the weights file")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    print(f"Sampling {args.pilot_rows:,} rows from {args.input}.", flush=True)
    sample = _load_streamed_pilot(args.input, args.pilot_rows, args.seed)
    splits = _split_sample(sample, args.seed)
    use_ps = PROPENSITY_SCORE_WEIGHT_FIELD in weights
    for name in ("train", "validation", "test"):
        print(f"Preparing {name}: {len(splits[name]):,} rows.", flush=True)
        prepared = _prepare_split(name, splits[name], use_ps)
        _write_pickle(output_dir / f"{name}.pkl", prepared)

    weights_hash = _sha256_file(args.weights_json)
    _write_pickle(output_dir / "llm_weights.pkl", weights)
    manifest = {
        "format_version": 1,
        "status": "prepared",
        "input": str(args.input.resolve()),
        "input_size_bytes": args.input.stat().st_size,
        "weights_json": str(args.weights_json.resolve()),
        "weights_sha256": weights_hash,
        "starting_weights": weights,
        "pilot_rows": int(args.pilot_rows),
        "seed": int(args.seed),
        "split_fractions": {"train": 0.6, "validation": 0.2, "test": 0.2},
        "split_counts": {
            name: {
                "rows": int(len(frame)),
                "treated": int(frame["treatment_binary"].sum()),
                "controls": int((frame["treatment_binary"] == 0).sum()),
            }
            for name, frame in splits.items()
        },
        "grid_fields": list(fields),
        "multipliers": [float(value) for value in args.multipliers],
        "starts": ["identity", "llm"],
        "grid_combinations_per_start": len(args.multipliers) ** len(fields),
        "total_candidate_weight_vectors": 2 * len(args.multipliers) ** len(fields),
        "propensity_score_in_weight_vector": use_ps,
    }
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    manifest["prepared_signature"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    manifest["prepared_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest["prepared_dir"] = str(output_dir)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared shared pilot splits: {output_dir}", flush=True)
    print(
        f"Grid dimensions: {len(fields)}; combinations per start: "
        f"{manifest['grid_combinations_per_start']:,}; total weight-vector evaluations: "
        f"{manifest['total_candidate_weight_vectors']:,}.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
