import json

from promo_detector import parse_gemini_response
from scoring import rank_promos, validate_promo


def candidate(start="00:00", end="00:20", **values):
    return {"segments": [{"start": start, "end": end}], **values}


def test_duration_bounds_are_inclusive_and_episode_end_is_valid():
    assert validate_promo(candidate("00:00", "00:20"), 20) == (True, "ok")
    assert validate_promo(candidate("00:00", "01:00"), 60) == (True, "ok")


def test_validation_rejects_bad_timestamps_ranges_and_episode_bounds():
    assert not validate_promo(candidate("-1:00", "00:20"))[0]
    assert not validate_promo(candidate("00:20", "00:20"))[0]
    assert not validate_promo(candidate("00:00", "00:19.99"))[0]
    assert not validate_promo(candidate("00:00", "00:20"), 19.99)[0]
    assert not validate_promo({"segments": [{"start": "00:00"}]})[0]
    assert not validate_promo({"segments": []})[0]


def test_validation_rejects_overlapping_or_out_of_order_segments():
    overlapping = {
        "segments": [
            {"start": "00:00", "end": "00:15"},
            {"start": "00:10", "end": "00:20"},
        ]
    }
    out_of_order = {
        "segments": [
            {"start": "00:20", "end": "00:30"},
            {"start": "00:00", "end": "00:10"},
        ]
    }
    assert not validate_promo(overlapping)[0]
    assert not validate_promo(out_of_order)[0]


def test_ranking_filters_invalid_candidates_and_uses_score_and_tiebreakers():
    lower = candidate(score=4, score_breakdown={"hook": 3, "cliffhanger": 3})
    higher = candidate(
        "00:20",
        "00:40",
        score=4,
        score_breakdown={"hook": 3, "cliffhanger": 4},
    )
    invalid = candidate("00:00", "00:19", score=5)

    ranked = rank_promos([lower, invalid, higher], {"": 60})
    assert ranked == [higher, lower]


def test_gemini_response_is_validated_and_score_is_recomputed_from_rubric():
    episode = {
        "episode": "Episode 1",
        "duration_seconds": 30,
        "events": [{"start": 0.0, "end": 20.0, "text": "Who is there?"}],
    }
    payload = {
        "promos": [
            {
                "segments": [{"start": "00:00", "end": "00:20"}],
                "hook": "A door opens.",
                "cliffhanger": "Who is there?",
                "why_it_works": "It opens with a question.",
                "evidence_excerpt": "Who is there?",
                "score": 4,
                "score_breakdown": {
                    "hook": 5,
                    "cliffhanger": 4,
                    "context": 3,
                    "coherence": 2,
                    "emotional_intensity": 4,
                    "arc_completeness": 3,
                    "duration_suitability": 4,
                },
            },
            {
                "segments": [{"start": "00:10", "end": "00:50"}],
                "hook": "Overlong moment.",
                "cliffhanger": "It ends.",
                "why_it_works": "Too long.",
                "evidence_excerpt": "Evidence.",
                "score": 4,
                "score_breakdown": {
                    "hook": 5,
                    "cliffhanger": 5,
                    "context": 5,
                    "coherence": 5,
                },
            },
        ]
    }

    candidates = parse_gemini_response(json.dumps(payload), episode)
    assert len(candidates) == 1
    assert candidates[0]["score"] == 3.64


def test_score_weights_are_normalized_and_include_full_promo_arc():
    from scoring import SCORE_WEIGHTS

    assert sum(SCORE_WEIGHTS.values()) == 1
    assert {
        "hook",
        "cliffhanger",
        "context",
        "coherence",
        "emotional_intensity",
        "arc_completeness",
        "duration_suitability",
    } == set(SCORE_WEIGHTS)
