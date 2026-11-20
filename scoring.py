"""Deterministic validation and global ranking for promo candidates."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from numbers import Real
from typing import Any

from screenplay_parser import to_seconds


SCORE_WEIGHTS = {
    "hook": 0.18,
    "cliffhanger": 0.24,
    "context": 0.12,
    "coherence": 0.14,
    "emotional_intensity": 0.12,
    "arc_completeness": 0.14,
    "duration_suitability": 0.06,
}


def validate_promo(
    promo: Any, episode_duration: float | None = None
) -> tuple[bool, str]:
    if not isinstance(promo, Mapping):
        return False, "candidate must be an object"

    segments = promo.get("segments")
    if not isinstance(segments, list) or not segments:
        return False, "candidate must contain at least one segment"

    duration_limit: float | None = None
    if episode_duration is not None:
        if (
            isinstance(episode_duration, bool)
            or not isinstance(episode_duration, Real)
        ):
            return False, "episode duration must be finite and non-negative"
        try:
            duration_limit = float(episode_duration)
        except (OverflowError, TypeError, ValueError):
            return False, "episode duration must be finite and non-negative"
        if not math.isfinite(duration_limit) or duration_limit < 0:
            return False, "episode duration must be finite and non-negative"

    total = 0.0
    previous_end = -1.0
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, Mapping):
            return False, f"segment {index} must be an object"
        start_value, end_value = segment.get("start"), segment.get("end")
        if not isinstance(start_value, str) or not isinstance(end_value, str):
            return False, f"segment {index} must have string start and end timestamps"
        try:
            start = to_seconds(start_value)
            end = to_seconds(end_value)
        except ValueError:
            return False, f"segment {index} has an invalid timestamp"

        if start < 0:
            return False, f"segment {index} start must be non-negative"
        if end <= start:
            return False, f"segment {index} end must be after start"
        if index > 1 and start < previous_end:
            return False, "segments must be ordered and must not overlap"
        if duration_limit is not None and end > duration_limit:
            return False, "segment exceeds episode duration"
        total += end - start
        previous_end = end

    if not math.isfinite(total) or not 20 <= total <= 60:
        return False, f"total duration {total:.2f}s is outside 20-60s"
    return True, "ok"


def _score_value(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        return 0.0
    try:
        score = float(value)
    except (OverflowError, TypeError, ValueError):
        return 0.0
    if not math.isfinite(score):
        return 0.0
    return min(5.0, max(0.0, score))


def rank_promos(
    promos: Sequence[Mapping[str, Any]],
    episode_durations: Mapping[str, float] | None = None,
) -> list[Mapping[str, Any]]:
    """Rank valid candidates by their comparable 0-5 scores and explainable tie-breakers."""
    valid: list[Mapping[str, Any]] = []
    for promo in promos:
        if not isinstance(promo, Mapping):
            continue
        if isinstance(promo.get("validation"), Mapping) and promo["validation"].get("valid") is False:
            continue

        episode = promo.get("episode")
        duration = episode_durations.get(episode) if episode_durations and isinstance(episode, str) else None
        is_valid, _ = validate_promo(promo, duration)
        if is_valid:
            valid.append(promo)

    return sorted(
        valid,
        key=lambda promo: (
            _score_value(promo.get("score")),
            _score_value(
                promo.get("score_breakdown", {}).get("cliffhanger", 0)
                if isinstance(promo.get("score_breakdown"), Mapping)
                else 0
            ),
            _score_value(
                promo.get("score_breakdown", {}).get("hook", 0)
                if isinstance(promo.get("score_breakdown"), Mapping)
                else 0
            ),
            _score_value(
                promo.get("score_breakdown", {}).get("arc_completeness", 0)
                if isinstance(promo.get("score_breakdown"), Mapping)
                else 0
            ),
        ),
        reverse=True,
    )
