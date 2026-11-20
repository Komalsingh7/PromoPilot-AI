"""Discover promo candidates with Gemini or an explainable offline heuristic."""
from __future__ import annotations

import json
import logging
import math
import os
import re
from collections.abc import Mapping
from numbers import Real
from typing import Any

from screenplay_parser import fmt_time, to_seconds
from scoring import SCORE_WEIGHTS, validate_promo


logger = logging.getLogger(__name__)
GEMINI_TIMEOUT_MS = 30_000
HOOK_WORDS = {
    "abandon",
    "arrest",
    "betray",
    "blood",
    "cheat",
    "dead",
    "divorce",
    "impossible",
    "kill",
    "marry",
    "murder",
    "never",
    "pregnant",
    "secret",
    "stop",
    "thief",
    "traitor",
    "what",
    "who",
    "why",
}
CLIFF_WORDS = {
    "accuse",
    "arrest",
    "blackmail",
    "betray",
    "caught",
    "danger",
    "discover",
    "expose",
    "evidence",
    "fingerprint",
    "kill",
    "murder",
    "proof",
    "reveal",
    "revenge",
    "secret",
    "threat",
    "truth",
    "unless",
    "witness",
}
EMOTION_WORDS = {
    "collapse",
    "confession",
    "cry",
    "desperate",
    "devastate",
    "furious",
    "gasp",
    "heartbroken",
    "betray",
    "plead",
    "shock",
    "scream",
    "slap",
    "terrified",
    "tremble",
}
EVIDENCE_LAYERS = {
    "camera": "camera",
    "action": "action",
    "sound fx": "sound",
}
CHARACTER_WORDS = re.compile(r"\b[A-Z][A-Z .'-]{1,30}\s*\(")
QUESTION_WORDS = {"how", "what", "when", "where", "who", "why"}
TENSION_WORDS = {
    "approach",
    "appear",
    "crash",
    "discover",
    "drop",
    "emerge",
    "enter",
    "freeze",
    "grab",
    "hide",
    "knock",
    "locked",
    "open",
    "reveal",
    "run",
    "scream",
    "slam",
    "sudden",
    "turn",
    "tremble",
    "vanish",
}
REVEAL_PATTERNS = (
    re.compile(r"\bwhat happened\b", re.IGNORECASE),
    re.compile(r"\b(?:you|he|she|they|we)\s+(?:were|was|are|is)\s+(?:at|in|on|with|there)\b", re.IGNORECASE),
    re.compile(r"\b(?:i|we)\s+(?:tried|found|saw|lied|hid)\b", re.IGNORECASE),
    re.compile(r"\bnever made it\b", re.IGNORECASE),
    re.compile(r"\b(?:belongs? to|wearing (?:your|his|her)|exactly like|then explain why)\b", re.IGNORECASE),
    re.compile(r"\b(?:cut to black|before an abrupt cut)\b", re.IGNORECASE),
    re.compile(r"\b(?:figure|shadow|silhouette|someone|something) (?:appears|emerges|steps out|stands)\b", re.IGNORECASE),
    re.compile(r"\b(?:door slams|lock clicks)\b", re.IGNORECASE),
    re.compile(r"\b(?:do not|don't) (?:open|move|look|come|go)\b", re.IGNORECASE),
)


def _tokens(text: str) -> set[str]:
    tokens = set(re.findall(r"[a-z']+", text.lower()))
    normalized = set(tokens)
    for token in tokens:
        if token.endswith("ied") and len(token) > 4:
            normalized.add(token[:-3] + "y")
        elif token.endswith("ed") and len(token) > 4:
            stem = token[:-2]
            normalized.update((stem, stem + "e"))
        elif token.endswith("ing") and len(token) > 5:
            stem = token[:-3]
            normalized.add(stem[:-1] if len(stem) > 2 and stem[-1] == stem[-2] else stem)
        elif token.endswith("s") and len(token) > 4:
            normalized.add(token[:-1])
    return normalized


def _event_score(event: Mapping[str, Any], kind: str) -> float:
    cached = event.get(f"_promo_score_{kind}")
    if isinstance(cached, Real) and not isinstance(cached, bool):
        return float(cached)

    text = str(event.get("text", "")).lower()
    tokens = _tokens(text)
    if kind == "hook":
        score = min(1.8, len(tokens & HOOK_WORDS) * 0.75)
        if "?" in text and tokens & QUESTION_WORDS:
            score += 1.2
        elif "?" in text:
            score += 0.5
        if "!" in text:
            score += 0.4
        score += min(1.4, len(tokens & EMOTION_WORDS) * 0.65)
        if tokens & TENSION_WORDS:
            score += 1.5
        meaningful_hook_words = (HOOK_WORDS - QUESTION_WORDS) | EMOTION_WORDS | TENSION_WORDS
        non_question_words = tokens - QUESTION_WORDS - {
            "a", "an", "are", "be", "did", "do", "does", "he", "i", "in",
            "is", "it", "of", "on", "she", "the", "they", "to", "was",
            "this", "were", "we", "you",
        }
        if (
            "?" in text
            and len(non_question_words) <= 1
            and not tokens & meaningful_hook_words
        ):
            score = min(score, 1.3)
        if len(tokens) <= 2 and not tokens & meaningful_hook_words:
            score = min(score, 1.3)
        return min(5.0, score)

    if kind == "emotion":
        score = min(4.0, len(tokens & EMOTION_WORDS) * 1.2)
        score += min(0.5, (text.count("!") + text.count("?")) * 0.2)
        if tokens & TENSION_WORDS:
            score += 0.7
        return min(5.0, score)

    matched_reveal = any(pattern.search(text) for pattern in REVEAL_PATTERNS)
    score = min(1.8, len(tokens & CLIFF_WORDS) * 0.75)
    if matched_reveal:
        score += 1.8
    if "?" in text and tokens & QUESTION_WORDS:
        score += 0.8
    score += min(1.0, len(tokens & EMOTION_WORDS) * 0.45)
    if "!" in text:
        score += 0.3
    if len(tokens) <= 3 and not (tokens & CLIFF_WORDS or matched_reveal):
        score = min(score, 1.2)
    return min(5.0, score)


def _evidence_layer(event: Mapping[str, Any]) -> str:
    label = str(event.get("label", "")).lower()
    for label_prefix, layer in EVIDENCE_LAYERS.items():
        if label.startswith(label_prefix):
            return layer
    return "dialogue"


def _valid_events(raw_events: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_events, list):
        return []
    events: list[dict[str, Any]] = []
    for event in raw_events:
        if not isinstance(event, Mapping):
            continue
        try:
            start = float(event["start"])
            end = float(event["end"])
        except (KeyError, OverflowError, TypeError, ValueError):
            continue
        if (
            isinstance(event.get("start"), bool)
            or isinstance(event.get("end"), bool)
            or not math.isfinite(start)
            or not math.isfinite(end)
            or start < 0
            or end < start
        ):
            continue
        normalized = dict(event)
        normalized["start"] = start
        normalized["end"] = end
        events.append(normalized)
    return sorted(events, key=lambda event: (event["start"], event["end"]))


def _content_duration(episode: Mapping[str, Any], events: list[Mapping[str, Any]]) -> float:
    last_event = max((float(event["end"]) for event in events), default=0.0)
    raw_duration = episode.get("duration_seconds")
    if isinstance(raw_duration, bool):
        return last_event
    try:
        duration = float(raw_duration)
    except (OverflowError, TypeError, ValueError):
        return last_event
    if not math.isfinite(duration) or duration < 0:
        return last_event
    return min(duration, last_event)


def _timeline_moment_count(events: list[Mapping[str, Any]]) -> int:
    moments = 0
    previous: float | None = None
    for event in events:
        start = round(float(event["start"]), 1)
        if previous is None or start - previous > 2.0:
            moments += 1
        if previous is None or start > previous:
            previous = start
    return moments


def _excerpt_event(stage: str, event: Mapping[str, Any], start: float) -> str:
    event_time = max(start, float(event["start"]))
    label = str(event.get("label", "")).strip().rstrip(":")
    text = " ".join(str(event.get("text", "")).split())
    return f"{stage} ({fmt_time(event_time)}): {label}: {text}"


def _candidate(
    episode: Mapping[str, Any],
    start: float,
    end: float,
    events: list[Mapping[str, Any]],
    method: str = "heuristic",
) -> dict[str, Any] | None:
    duration = end - start
    if start < 0 or not 20 <= duration <= 60:
        return None

    relevant: list[Mapping[str, Any]] = []
    early: list[Mapping[str, Any]] = []
    late: list[Mapping[str, Any]] = []
    middle: list[Mapping[str, Any]] = []
    ending_margin = min(12.0, max(5.0, duration * 0.3))
    middle_start = start + duration * 0.2
    middle_end = start + duration * 0.8
    for event in events:
        if event["start"] > end:
            break
        if event["end"] < start:
            continue
        relevant.append(event)
        if event["start"] <= start + 3.0:
            early.append(event)
        if event["end"] >= end - ending_margin:
            late.append(event)
        if middle_start <= event["start"] <= middle_end:
            middle.append(event)
    if not relevant:
        return None

    if not early:
        return None
    if not late:
        return None

    hook_event = max(early, key=lambda event: _event_score(event, "hook"))
    if _event_score(hook_event, "hook") < 1.5:
        return None
    cliff_event = max(
        late,
        key=lambda event: (
            _event_score(event, "cliff"),
            float(event["end"]),
            float(event["start"]),
        ),
    )
    if _event_score(cliff_event, "cliff") < 1.3:
        return None
    middle = [
        event
        for event in middle
        if event is not hook_event and event is not cliff_event
    ]
    if not middle:
        middle = [
            event
            for event in relevant
            if event is not hook_event and event is not cliff_event
        ]
    build_event = max(
        middle or relevant,
        key=lambda event: (
            0.55 * _event_score(event, "cliff")
            + 0.45 * _event_score(event, "emotion"),
            -abs((float(event["start"]) - start) - duration / 2),
        ),
    )

    hook = _event_score(hook_event, "hook")
    cliffhanger = _event_score(cliff_event, "cliff")
    emotional_intensity = max(
        (_event_score(event, "emotion") for event in relevant), default=0.0
    )
    build_strength = max(
        (
            0.55 * _event_score(event, "cliff")
            + 0.45 * _event_score(event, "emotion")
            for event in (middle or relevant)
        ),
        default=0.0,
    )

    layers = {_evidence_layer(event) for event in relevant}
    speakers = {
        match.group(0).strip().split("(", 1)[0].strip()
        for event in relevant
        if (match := CHARACTER_WORDS.search(str(event.get("label", ""))))
    }
    context = min(
        5.0,
        1.0
        + (1.2 if episode.get("logline") else 0.0)
        + min(1.0, len(speakers) * 0.35)
        + (0.8 if len(layers) >= 2 else 0.0),
    )
    phases = (
        (start, start + duration / 3),
        (start + duration / 3, start + duration * 2 / 3),
        (start + duration * 2 / 3, end),
    )
    covered_phases = sum(
        any(
            event["end"] >= phase_start and event["start"] <= phase_end
            for event in relevant
        )
        for phase_start, phase_end in phases
    )
    coherence = min(
        5.0,
        0.5
        + covered_phases * 1.1
        + min(1.2, _timeline_moment_count(relevant) * 0.12)
        + (0.4 if {"dialogue", "action"} <= layers else 0.0),
    )
    arc_completeness = (
        0.25 * hook + 0.30 * build_strength + 0.45 * cliffhanger
    )
    duration_suitability = max(0.0, 5.0 - abs(duration - 45.0) * (2.0 / 15.0))
    breakdown = {
        "hook": round(hook, 2),
        "cliffhanger": round(cliffhanger, 2),
        "context": round(context, 2),
        "coherence": round(coherence, 2),
        "emotional_intensity": round(emotional_intensity, 2),
        "arc_completeness": round(arc_completeness, 2),
        "duration_suitability": round(duration_suitability, 2),
    }
    score = round(
        sum(SCORE_WEIGHTS[name] * breakdown[name] for name in SCORE_WEIGHTS), 2
    )
    stages = [
        ("Hook", hook_event),
        ("Build", build_event),
        ("Payoff", cliff_event),
    ]
    excerpt_parts: list[str] = []
    used_events: set[int] = set()
    for stage, event in stages:
        if id(event) in used_events:
            continue
        used_events.add(id(event))
        excerpt_parts.append(_excerpt_event(stage, event, start))
        event_layer = _evidence_layer(event)
        preferred_layers = (
            {"camera", "action"}
            if event_layer == "dialogue"
            else {"dialogue"}
        )
        companion = max(
            (
                other
                for other in relevant
                if id(other) not in used_events
                and _evidence_layer(other) in preferred_layers
                and abs(float(other["start"]) - float(event["start"])) <= 3.0
            ),
            key=lambda other: _event_score(other, "emotion")
            + 0.25 * _event_score(other, "cliff"),
            default=None,
        )
        if companion is not None:
            used_events.add(id(companion))
            excerpt_parts.append(
                _excerpt_event(f"{stage} context", companion, start)
            )
    excerpt = " | ".join(excerpt_parts)[:1000]

    def explanation_text(event: Mapping[str, Any]) -> str:
        text = " ".join(str(event.get("text", "")).split()).strip()
        if len(text) > 1 and (text[0], text[-1]) in {
            ('"', '"'),
            ("'", "'"),
            ("“", "”"),
            ("‘", "’"),
        }:
            text = text[1:-1]
        return text[:180]

    hook_text = explanation_text(hook_event)
    build_text = explanation_text(build_event)
    cliff_text = explanation_text(cliff_event)
    build_clause = (
        f"builds through \"{build_text}\""
        if build_event is not hook_event and build_event is not cliff_event
        else "develops across the intervening screenplay beats"
    )
    return {
        "episode": episode.get("episode", ""),
        "segments": [{"start": fmt_time(start), "end": fmt_time(end)}],
        "duration_seconds": round(duration, 2),
        "hook": str(hook_event.get("text", ""))[:260],
        "cliffhanger": str(cliff_event.get("text", ""))[:260],
        "why_it_works": (
            f"Opens on \"{hook_text}\", {build_clause}, and cuts on "
            f"\"{cliff_text}\". That progression gives a first-time viewer a "
            "clear setup, rising stakes, and a specific payoff or unresolved turn."
        )[:1000],
        "score": score,
        "score_breakdown": breakdown,
        "evidence_excerpt": excerpt,
        "method": method,
        "needs_human_review": True,
    }


def _same_moment(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    first_intervals = [
        (to_seconds(segment["start"]), to_seconds(segment["end"]))
        for segment in first["segments"]
    ]
    second_intervals = [
        (to_seconds(segment["start"]), to_seconds(segment["end"]))
        for segment in second["segments"]
    ]
    first_duration = sum(end - start for start, end in first_intervals)
    second_duration = sum(end - start for start, end in second_intervals)
    shorter_duration = min(first_duration, second_duration)
    if shorter_duration <= 0:
        return False

    overlap = sum(
        max(0.0, min(first_end, second_end) - max(first_start, second_start))
        for first_start, first_end in first_intervals
        for second_start, second_end in second_intervals
    )
    union = first_duration + second_duration - overlap
    if union > 0 and overlap / union >= 0.8:
        return True
    same_payoff = (
        " ".join(str(first.get("cliffhanger", "")).split()).casefold()
        == " ".join(str(second.get("cliffhanger", "")).split()).casefold()
    )
    return same_payoff and overlap / shorter_duration >= 0.95


def heuristic_candidates(
    episode: Mapping[str, Any], per_episode: int = 4
) -> list[dict[str, Any]]:
    events = _valid_events(episode.get("events", []))
    duration = _content_duration(episode, events)
    if not events or duration < 20 or per_episode <= 0:
        return []

    for event in events:
        for kind in ("hook", "cliff", "emotion"):
            event[f"_promo_score_{kind}"] = _event_score(event, kind)

    starts = sorted(
        {
            round(float(event["start"]), 2)
            for event in events
            if event["start"] <= duration - 20
        }
    )
    ends = sorted(
        {
            round(float(event["end"]), 2)
            for event in events
            if 20 <= event["end"] and event["end"] <= duration
        }
    )
    candidates: list[dict[str, Any]] = []
    for start in starts:
        for end in ends:
            if end < start + 20:
                continue
            if end > start + 60:
                break
            candidate = _candidate(episode, start, end, events)
            if candidate and candidate["score"] >= 2.0:
                candidates.append(candidate)

    candidates.sort(
        key=lambda candidate: (
            candidate["score"],
            candidate["score_breakdown"]["cliffhanger"],
            candidate["score_breakdown"]["arc_completeness"],
            candidate["score_breakdown"]["hook"],
        ),
        reverse=True,
    )
    selected: list[dict[str, Any]] = []
    for candidate in candidates:
        if any(_same_moment(candidate, chosen) for chosen in selected):
            continue
        selected.append(candidate)
        if len(selected) >= max(0, per_episode):
            break
    return selected


PROMPT = """You are an expert short-form drama promo editor. Analyze one timestamped screenplay.
Return JSON only, in this shape:
{"promos":[{"segments":[{"start":"MM:SS.ss","end":"MM:SS.ss"}],"hook":"...","cliffhanger":"...","why_it_works":"...","evidence_excerpt":"...","score":0.0,"score_breakdown":{"hook":0.0,"cliffhanger":0.0,"context":0.0,"coherence":0.0,"emotional_intensity":0.0,"arc_completeness":0.0,"duration_suitability":0.0}}]}

Find up to 3 distinct, self-contained 20-60 second promos for a first-time viewer. The opening
hook must occur within the first 3 seconds and create curiosity, tension, surprise, or emotional
engagement. Assess the whole candidate before choosing its ending: prefer a meaningful reveal,
confession, threat, reversal, or unresolved question over a generic reaction or isolated dramatic
word. Keep enough setup for the ending to make sense, and include a specific explanation and
evidence from the opening, development, and payoff.

Use only events and exact timestamp values present in the input; never invent dialogue, action,
characters, or timestamps. CAMERA, ACTION, DIALOGUE, and SOUND FX events are parallel descriptions
of one timeline, not sequential transcript material; their overlap must not be added as extra
runtime. Segment lists must be chronological and non-overlapping. Do not extend beyond the final
event timestamp, even if the declared episode duration is later.

Score each component from 0 to 5 using the screenplay evidence:
hook 18%, cliffhanger/payoff 24%, context 12%, coherence 14%, emotional intensity 12%,
arc completeness 14%, duration suitability 6%. Use one consistent 0-5 scale for every factor.
Overall score = 0.18*hook + 0.24*cliffhanger + 0.12*context + 0.14*coherence +
0.12*emotional_intensity + 0.14*arc_completeness + 0.06*duration_suitability, rounded to
two decimals. Do not claim predicted audience performance. Return an empty promos list if no
candidate meets the constraints.
"""


def _score_component(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        score = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    if not math.isfinite(score) or not 0 <= score <= 5:
        return None
    return score


def parse_gemini_response(response_text: str, episode: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Parse, normalize, and deterministically validate a model JSON response."""
    if not isinstance(response_text, str) or not response_text.strip():
        return []

    text = response_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Gemini returned malformed JSON; using heuristic fallback")
        return []
    if not isinstance(data, Mapping) or not isinstance(data.get("promos"), list):
        logger.warning("Gemini response is missing a promos list; using heuristic fallback")
        return []

    valid: list[dict[str, Any]] = []
    for promo in data["promos"]:
        if not isinstance(promo, Mapping):
            continue
        segments = promo.get("segments")
        if not isinstance(segments, list):
            continue
        normalized_segments = []
        for segment in segments:
            if not isinstance(segment, Mapping):
                normalized_segments = []
                break
            normalized_segments.append(
                {"start": segment.get("start"), "end": segment.get("end")}
            )
        if not normalized_segments:
            continue

        candidate = {"segments": normalized_segments}
        available_duration = _content_duration(
            episode, _valid_events(episode.get("events", []))
        )
        is_valid, _ = validate_promo(candidate, available_duration)
        if not is_valid:
            continue

        if _score_component(promo.get("score")) is None:
            continue
        breakdown_source = promo.get("score_breakdown")
        if not isinstance(breakdown_source, Mapping):
            continue
        breakdown: dict[str, float] = {}
        for name in SCORE_WEIGHTS:
            score = _score_component(breakdown_source.get(name))
            if score is None:
                breakdown = {}
                break
            breakdown[name] = score
        if not breakdown:
            continue

        text_fields = ("hook", "cliffhanger", "why_it_works", "evidence_excerpt")
        if any(not isinstance(promo.get(field), str) or not promo[field].strip() for field in text_fields):
            continue
        try:
            available_timestamps = {
                float(event[key])
                for event in episode.get("events", [])
                for key in ("start", "end")
            }
            requested_timestamps = {
                to_seconds(segment[key])
                for segment in normalized_segments
                for key in ("start", "end")
            }
        except (KeyError, OverflowError, TypeError, ValueError):
            continue
        if not available_timestamps or not requested_timestamps <= available_timestamps:
            continue

        evidence = " ".join(promo["evidence_excerpt"].split()).casefold()
        source_text = " ".join(
            " ".join(str(event.get("text", "")).split())
            for event in episode.get("events", [])
        ).casefold()
        if not evidence or evidence not in source_text:
            continue

        score = round(sum(SCORE_WEIGHTS[key] * breakdown[key] for key in SCORE_WEIGHTS), 2)
        candidate.update(
            {
                "episode": episode.get("episode", ""),
                "duration_seconds": round(
                    sum(
                        # validate_promo has already established that each timestamp is valid.
                        to_seconds(segment["end"]) - to_seconds(segment["start"])
                        for segment in normalized_segments
                    ),
                    2,
                ),
                "hook": promo["hook"][:1000],
                "cliffhanger": promo["cliffhanger"][:1000],
                "why_it_works": promo["why_it_works"][:1000],
                "evidence_excerpt": promo["evidence_excerpt"][:1000],
                "score": score,
                "score_breakdown": breakdown,
                "method": "gemini",
                "needs_human_review": True,
            }
        )
        valid.append(candidate)

    valid.sort(key=lambda candidate: candidate["score"], reverse=True)
    selected: list[dict[str, Any]] = []
    for candidate in valid:
        if any(_same_moment(candidate, chosen) for chosen in selected):
            continue
        selected.append(candidate)
        if len(selected) == 3:
            break
    return selected


def gemini_candidates(
    episode: Mapping[str, Any], model: str | None = None
) -> list[dict[str, Any]] | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
        )
        model_name = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        payload = {
            "episode": episode.get("episode", ""),
            "logline": episode.get("logline", ""),
            "continuity_notes": episode.get("continuity_notes", ""),
            "duration_seconds": episode.get("duration_seconds"),
            "available_duration_seconds": _content_duration(
                episode, _valid_events(episode.get("events", []))
            ),
            "events": [
                {
                    "label": event.get("label", ""),
                    "start": event.get("start"),
                    "end": event.get("end"),
                    "text": event.get("text", ""),
                    "scene": event.get("scene", ""),
                }
                for event in episode.get("events", [])
            ],
        }
        response = client.models.generate_content(
            model=model_name,
            contents=f"{PROMPT}\nSCREENPLAY JSON:\n{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}",
            config={"response_mime_type": "application/json"},
        )
        return parse_gemini_response(response.text, episode)
    except Exception as exc:
        logger.warning(
            "Gemini request failed (%s); using heuristic fallback",
            type(exc).__name__,
        )
        return None


def detect_episode(
    episode: Mapping[str, Any], prefer_llm: bool = True
) -> list[dict[str, Any]]:
    if prefer_llm:
        result = gemini_candidates(episode)
        if result:
            return result
    return heuristic_candidates(episode)
