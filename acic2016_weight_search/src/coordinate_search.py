"""Small, reusable coordinate-wise search over positive field weights."""

from __future__ import annotations

from time import perf_counter
from typing import Callable, Mapping, Sequence


def coordinate_search(
    initial_weights: Mapping[str, float],
    fields: Sequence[str],
    multipliers: Sequence[float],
    score: Callable[[dict[str, float]], float],
    max_sweeps: int,
    *,
    start_name: str,
) -> tuple[dict[str, float], float, list[dict[str, object]]]:
    """Optimize one field at a time, retaining accepted updates between fields.

    The search is deterministic when ``score`` is deterministic. A candidate
    multiplier is applied to the current value of one field; all other fields
    are held fixed. Equal scores retain the current value.
    """
    weights = {str(field): float(value) for field, value in initial_weights.items()}
    if not fields or len(set(fields)) != len(fields):
        raise ValueError("fields must be a nonempty sequence without duplicates")
    if set(fields) - set(weights):
        raise ValueError("initial_weights must contain every searched field")
    if any(value <= 0 for value in weights.values()):
        raise ValueError("All starting field weights must be positive")
    factors = [float(value) for value in multipliers]
    if not factors or any(value <= 0 for value in factors):
        raise ValueError("multipliers must be a nonempty sequence of positive values")
    if len(set(factors)) != len(factors):
        raise ValueError("multipliers must not contain duplicates")
    if 1.0 not in factors:
        raise ValueError("multipliers must include 1 so the current weight is an option")
    if max_sweeps < 1:
        raise ValueError("max_sweeps must be at least 1")

    started = perf_counter()
    current_score = float(score(dict(weights)))
    if current_score < 0:
        raise ValueError("score must be a nonnegative RMSE")
    history: list[dict[str, object]] = [{
        "start": start_name,
        "sweep": 0,
        "field": "__initial__",
        "multiplier": 1.0,
        "candidate_weight": None,
        "rmse": current_score,
        "accepted": True,
        "evaluation_seconds": perf_counter() - started,
    }]

    for sweep in range(1, max_sweeps + 1):
        any_update = False
        for field in fields:
            base_weight = weights[field]
            best_weight = base_weight
            best_factor = 1.0
            best_score = current_score
            candidate_rows: list[dict[str, object]] = []

            for factor in factors:
                candidate = dict(weights)
                candidate_weight = base_weight * factor
                candidate[field] = candidate_weight
                evaluation_started = perf_counter()
                candidate_score = float(score(candidate))
                evaluation_seconds = perf_counter() - evaluation_started
                if candidate_score < 0:
                    raise ValueError("score must be a nonnegative RMSE")
                candidate_rows.append({
                    "start": start_name,
                    "sweep": sweep,
                    "field": field,
                    "multiplier": factor,
                    "candidate_weight": candidate_weight,
                    "rmse": candidate_score,
                    "accepted": False,
                    "evaluation_seconds": evaluation_seconds,
                })
                if candidate_score < best_score:
                    best_weight = candidate_weight
                    best_factor = factor
                    best_score = candidate_score

            for row in candidate_rows:
                row["accepted"] = row["multiplier"] == best_factor
            history.extend(candidate_rows)
            if best_factor != 1.0:
                weights[field] = best_weight
                current_score = best_score
                any_update = True

        if not any_update:
            break

    return weights, current_score, history
