import json

from google import genai

from promo_detector import (
    _same_moment,
    detect_episode,
    gemini_candidates,
    heuristic_candidates,
    parse_gemini_response,
)
from scoring import rank_promos, validate_promo
from screenplay_parser import parse_text


EPISODE_TEXT = """EPISODE NUMBER: Episode Test
EPISODE LOGLINE: Mara discovers that her brother hid the truth.
SCENE 01
**LADY MARA (Urgent):**
Start: (00:00) | End: (00:04)
Who took the secret letter?
**ACTION:**
Start: (00:04) | End: (00:15)
Mara discovers the hidden letter and trembles.
**SOUND FX:**
Start: (00:15) | End: (00:18)
A sudden crash.
**LADY MARA (Shocked):**
Start: (00:18) | End: (00:25)
You betrayed me!
**LADY MARA (Urgent):**
Start: (00:25) | End: (00:40)
Unless you tell me the truth, I will reveal your secret!
"""


def valid_model_payload():
    return {
        "promos": [
            {
                "segments": [{"start": "00:00", "end": "00:30"}],
                "hook": "Who took the secret letter?",
                "cliffhanger": "Mara stares at the open doorway.",
                "why_it_works": "The reveal leaves a question unanswered.",
                "evidence_excerpt": "Who took the secret letter?",
                "score": 4.0,
                "score_breakdown": {
                    "hook": 4,
                    "cliffhanger": 4,
                    "context": 3,
                    "coherence": 4,
                    "emotional_intensity": 3,
                    "arc_completeness": 4,
                    "duration_suitability": 4,
                },
            }
        ]
    }


def test_gemini_json_response_and_schema_validation():
    episode = {
        "episode": "Episode Test",
        "duration_seconds": 40,
        "events": [
            {"start": 0.0, "end": 30.0, "text": "Who took the secret letter?"},
            {"start": 30.0, "end": 40.0, "text": "Mara stares at the open doorway."},
        ],
    }
    payload = valid_model_payload()
    payload["promos"].append(
        {
            **payload["promos"][0],
            "segments": [{"start": "00:30", "end": "01:10"}],
        }
    )
    payload["promos"].append(
        {
            **payload["promos"][0],
            "score": 99,
        }
    )
    payload["promos"].append(
        {
            **payload["promos"][0],
            "segments": [{"start": "00:01", "end": "00:30"}],
        }
    )
    payload["promos"].append(
        {
            **payload["promos"][0],
            "evidence_excerpt": "Invented screenplay evidence.",
        }
    )

    candidates = parse_gemini_response(json.dumps(payload), episode)
    assert len(candidates) == 1
    result = candidates[0]
    assert result["method"] == "gemini"
    assert result["duration_seconds"] == 30
    assert result["score"] == 3.76
    assert validate_promo(result, 40)[0]


def test_gemini_response_parser_handles_fences_and_malformed_json(caplog):
    episode = {
        "episode": "Episode Test",
        "duration_seconds": 40,
        "events": [
            {"start": 0.0, "end": 30.0, "text": "Who took the secret letter?"},
            {"start": 30.0, "end": 40.0, "text": "Mara stares at the open doorway."},
        ],
    }
    response = f"```json\n{json.dumps(valid_model_payload())}\n```"
    assert len(parse_gemini_response(response, episode)) == 1
    assert parse_gemini_response("{bad json", episode) == []
    assert "malformed JSON" in caplog.text


def test_gemini_duplicate_windows_keep_the_highest_scored_candidate():
    episode = {
        "episode": "Episode Test",
        "duration_seconds": 40,
        "events": [
            {"start": 0.0, "end": 30.0, "text": "Who took the secret letter?"},
        ],
    }
    weaker = valid_model_payload()["promos"][0]
    stronger = {
        **weaker,
        "score_breakdown": {
            "hook": 5,
            "cliffhanger": 5,
            "context": 5,
            "coherence": 5,
            "emotional_intensity": 5,
            "arc_completeness": 5,
            "duration_suitability": 5,
        },
    }
    candidates = parse_gemini_response(
        json.dumps({"promos": [weaker, stronger]}), episode
    )
    assert len(candidates) == 1
    assert candidates[0]["score"] == 5


def test_gemini_api_failure_returns_none_and_detector_falls_back(monkeypatch, caplog):
    episode = parse_text(EPISODE_TEXT, "episode.txt")

    class BrokenModels:
        def generate_content(self, **kwargs):
            raise TimeoutError("timeout details should not be surfaced")

    class BrokenClient:
        models = BrokenModels()

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(genai, "Client", lambda **kwargs: BrokenClient())

    assert gemini_candidates(episode) is None
    assert "TimeoutError" in caplog.text
    assert "timeout details" not in caplog.text
    assert detect_episode(episode, prefer_llm=True)


def test_missing_key_skips_gemini_request(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert gemini_candidates({"events": []}) is None


def test_heuristic_candidates_are_valid_rankable_and_deduplicated():
    episode = parse_text(EPISODE_TEXT, "episode.txt")
    candidates = heuristic_candidates(episode, per_episode=4)
    assert candidates
    assert len(candidates) <= 4
    assert len(candidates) == len(
        {
            (candidate["segments"][0]["start"], candidate["segments"][0]["end"])
            for candidate in candidates
        }
    )
    assert all(20 <= candidate["duration_seconds"] <= 60 for candidate in candidates)
    assert all(validate_promo(candidate, episode["duration_seconds"])[0] for candidate in candidates)
    assert rank_promos(candidates, {"Episode Test": episode["duration_seconds"]})


def test_overlapping_windows_for_the_same_moment_are_deduplicated():
    short = {
        "segments": [{"start": "00:00", "end": "00:30"}],
        "cliffhanger": "The figure turns around.",
    }
    near_duplicate = {
        "segments": [{"start": "00:02", "end": "00:31"}],
        "cliffhanger": "The figure turns around.",
    }
    nested_same_payoff = {
        "segments": [{"start": "00:00", "end": "00:55"}],
        "cliffhanger": "The figure turns around.",
    }
    nested_payoff = {
        "segments": [{"start": "00:00", "end": "00:55"}],
        "cliffhanger": "Someone else is behind the door.",
    }
    distinct = {"segments": [{"start": "00:25", "end": "00:55"}]}
    assert _same_moment(short, near_duplicate)
    assert _same_moment(short, nested_same_payoff)
    assert not _same_moment(short, nested_payoff)
    assert not _same_moment(short, distinct)


def test_end_to_end_parser_detector_and_ranker():
    episode = parse_text(EPISODE_TEXT, "episode.txt")
    candidates = detect_episode(episode, prefer_llm=False)
    ranked = rank_promos(
        candidates, {episode["episode"]: episode["duration_seconds"]}
    )
    assert ranked
    assert all(candidate["method"] == "heuristic" for candidate in ranked)


NARRATIVE_ARC_TEXT = """EPISODE NUMBER: Arc Test
EPISODE LOGLINE: A family discovers that a photograph hides a crime.
SCENE 01
Scene end: 01:15
**LADY MAYA (Afraid):**
Start: (00:00.00) | End: (00:03.00)
What is hidden inside that locked room?
**CAMERA:**
Start: (00:00.00) | End: (00:03.00)
Close-up on Maya staring at the locked door.
**ACTION:**
Start: (00:12.00) | End: (00:16.00)
Maya opens an envelope and finds a photograph.
**INSPECTOR RAO (Serious):**
Start: (00:21.00) | End: (00:25.00)
I found your fingerprints on the bedroom lock.
**ACTION:**
Start: (00:31.00) | End: (00:36.00)
Kabir turns the photograph over and discovers a handwritten date.
**KABIR (Shocked):**
Start: (00:39.00) | End: (00:43.00)
This date is three years before you met Arjun.
**SOUND FX:**
Start: (00:47.00) | End: (00:50.00)
Low suspense drone.
**KABIR (Angry):**
Start: (00:51.00) | End: (00:55.00)
Then explain why this photograph shows you entering alone.
"""


def test_heuristic_evaluates_full_arc_and_reports_specific_evidence():
    episode = parse_text(NARRATIVE_ARC_TEXT, "arc.txt")
    candidates = heuristic_candidates(episode, per_episode=4)

    payoff_candidate = next(
        candidate
        for candidate in candidates
        if "then explain why" in candidate["cliffhanger"].lower()
    )
    assert "what is hidden" in payoff_candidate["hook"].lower()
    assert "photograph" in payoff_candidate["evidence_excerpt"].lower()
    assert "then explain why" in payoff_candidate["evidence_excerpt"].lower()
    assert "then explain why" in payoff_candidate["why_it_works"].lower()
    assert payoff_candidate["score_breakdown"]["arc_completeness"] > 0
    assert payoff_candidate["score_breakdown"]["duration_suitability"] > 0


def test_heuristic_recognizes_visual_hook_and_suspense_payoff():
    screenplay = """EPISODE NUMBER: Visual Test
SCENE 01
Scene end: 00:45
**CAMERA:**
Start: (00:00.00) | End: (00:03.00)
The dark doorway fills the frame.
**ACTION:**
Start: (00:00.00) | End: (00:03.00)
A figure suddenly appears in the doorway.
**ACTION:**
Start: (00:12.00) | End: (00:17.00)
Maya backs away and reaches for the locked door.
**DIALOGUE:**
Start: (00:23.00) | End: (00:27.00)
Don't open the door.
**CAMERA:**
Start: (00:35.00) | End: (00:40.00)
The shadow appears behind him.
"""
    episode = parse_text(screenplay, "visual.txt")
    candidates = heuristic_candidates(episode, per_episode=4)

    assert candidates
    assert any("figure suddenly appears" in candidate["hook"].lower() for candidate in candidates)
    assert any("shadow appears" in candidate["cliffhanger"].lower() for candidate in candidates)


def test_heuristic_stops_at_final_event_not_declared_episode_tail():
    episode = parse_text(NARRATIVE_ARC_TEXT, "arc.txt")
    candidates = heuristic_candidates(episode, per_episode=4)

    assert candidates
    assert all(
        float(candidate["segments"][0]["end"].split(":")[0]) * 60
        + float(candidate["segments"][0]["end"].split(":")[1])
        <= episode["last_event_seconds"]
        for candidate in candidates
    )
