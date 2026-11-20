"""Parse Kuku-style timestamped screenplay TXT files into structured events."""
from __future__ import annotations

from pathlib import Path
import math
import re
from typing import Any


TIME_PATTERN = r"\d+(?::\d{1,2})?:\d{1,2}(?:\.\d+)?"
START_END = re.compile(
    rf"Start:\s*\(({TIME_PATTERN})\)\s*\|\s*End:\s*\(({TIME_PATTERN})\)",
    re.IGNORECASE,
)
EP_RE = re.compile(r"^\s*EPISODE NUMBER:\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
LOG_RE = re.compile(r"^\s*EPISODE LOGLINE:\s*(.*?)\s*$", re.IGNORECASE | re.MULTILINE)
NOTE_RE = re.compile(
    r"^\s*CONTINUITY NOTES:\s*(.*?)\s*$", re.IGNORECASE | re.MULTILINE
)
HEADER_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")
SCENE_RE = re.compile(r"^\s*SCENE\s+(.+?)\s*$", re.IGNORECASE)


def to_seconds(value: str) -> float:
    """Convert MM:SS[.fraction] or HH:MM:SS[.fraction] to seconds."""
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")

    parts = value.strip().split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"invalid timestamp: {value!r}")

    try:
        if len(parts) == 2:
            minutes, seconds = parts
            hours = 0
        else:
            hours, minutes, seconds = parts
        hours_value = int(hours)
        minutes_value = int(minutes)
        seconds_value = float(seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc

    if (
        hours_value < 0
        or not 0 <= minutes_value < 60
        or not 0 <= seconds_value < 60
        or not math.isfinite(seconds_value)
    ):
        raise ValueError(f"invalid timestamp: {value!r}")

    try:
        total = hours_value * 3600 + minutes_value * 60 + seconds_value
    except OverflowError as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc
    if not math.isfinite(total):
        raise ValueError(f"invalid timestamp: {value!r}")
    return total


def fmt_time(seconds: float) -> str:
    try:
        value = float(seconds)
    except (OverflowError, TypeError, ValueError) as exc:
        raise ValueError("seconds must be a finite, non-negative number") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError("seconds must be a finite, non-negative number")

    total = round(value, 2)
    minutes = int(total // 60)
    remaining = total - minutes * 60
    if remaining >= 60:
        minutes += 1
        remaining = 0.0
    return f"{minutes:02d}:{remaining:05.2f}"


def _extract_events(raw: str) -> tuple[list[dict[str, Any]], list[str], float]:
    lines = raw.splitlines()
    events: list[dict[str, Any]] = []
    warnings: list[str] = []
    scene = ""
    scene_heading = ""
    declared_duration = 0.0
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        scene_match = SCENE_RE.match(line)
        if scene_match and not line.lower().startswith(
            ("scene heading:", "scene start:", "scene end:")
        ):
            scene = scene_match.group(1).strip()
        elif line.lower().startswith("scene heading:"):
            scene_heading = line.split(":", 1)[1].strip()
        elif line.lower().startswith("scene end:"):
            try:
                scene_end = to_seconds(line.split(":", 1)[1].strip())
            except ValueError:
                warnings.append(f"Invalid scene end timestamp on line {i + 1}")
            else:
                declared_duration = max(declared_duration, scene_end)

        header_match = HEADER_RE.match(line)
        if not header_match:
            i += 1
            continue

        label = header_match.group(1).strip()
        range_match = None
        range_line = -1
        j = i + 1
        while j < len(lines):
            candidate = START_END.search(lines[j])
            if candidate:
                range_match = candidate
                range_line = j
                break
            candidate_line = lines[j].strip()
            if (
                HEADER_RE.match(candidate_line)
                or SCENE_RE.match(candidate_line)
                or candidate_line == "--- SCRIPT END ---"
            ):
                break
            if candidate_line.lower().startswith("start:"):
                warnings.append(f"Invalid timestamp range for {label!r} near line {j + 1}")
                break
            j += 1

        if not range_match:
            i += 1
            continue

        try:
            start, end = map(to_seconds, range_match.groups())
        except ValueError:
            warnings.append(f"Invalid timestamp range for {label!r} near line {range_line + 1}")
            i += 1
            continue

        content: list[str] = []
        k = range_line + 1
        while k < len(lines):
            content_line = lines[k].strip()
            if (
                HEADER_RE.match(content_line)
                or SCENE_RE.match(content_line)
                or content_line == "--- SCRIPT END ---"
            ):
                break
            if content_line and not content_line.lower().startswith(("start:", "end:")):
                content.append(content_line)
            k += 1

        description = " ".join(content).strip()
        description = re.sub(r"\*\*|__", "", description)
        if start < 0 or end < start:
            warnings.append(f"Invalid event range for {label!r} near line {range_line + 1}")
        elif description:
            events.append(
                {
                    "label": label,
                    "start": start,
                    "end": end,
                    "text": description,
                    "scene": scene,
                    "scene_heading": scene_heading,
                }
            )
        else:
            warnings.append(f"Empty event description for {label!r} near line {range_line + 1}")
        i = k

    events.sort(key=lambda event: (event["start"], event["end"]))
    return events, warnings, declared_duration


def parse_text(raw: str, source_file: str = "<memory>") -> dict[str, Any]:
    """Parse screenplay text while retaining overlapping timeline evidence as separate events."""
    if not isinstance(raw, str):
        raise TypeError("screenplay content must be text")
    raw = raw.lstrip("\ufeff")

    def metadata(regex: re.Pattern[str]) -> str:
        match = regex.search(raw)
        return match.group(1).strip() if match else ""

    events, warnings, declared_duration = _extract_events(raw)
    last_event_seconds = max((event["end"] for event in events), default=0.0)
    duration_gap_seconds = max(0.0, declared_duration - last_event_seconds)
    discrepancy_threshold = max(10.0, declared_duration * 0.05)
    if events and duration_gap_seconds >= discrepancy_threshold:
        warnings.append(
            f"Final screenplay event ends at {fmt_time(last_event_seconds)}, "
            f"{duration_gap_seconds:.2f}s before the declared duration "
            f"{fmt_time(declared_duration)}; promo windows will stop at the final event."
        )
    if not events and not warnings and raw.strip():
        warnings.append(
            "No Kuku-style event blocks found; expected **LABEL:** followed by "
            "Start: (MM:SS.ss) | End: (MM:SS.ss)."
        )

    return {
        "source_file": Path(source_file).name,
        "episode": metadata(EP_RE) or Path(source_file).stem,
        "logline": metadata(LOG_RE),
        "continuity_notes": metadata(NOTE_RE),
        "declared_duration_seconds": declared_duration or None,
        "last_event_seconds": last_event_seconds,
        "duration_gap_seconds": round(duration_gap_seconds, 2),
        "duration_seconds": max(
            declared_duration, max((event["end"] for event in events), default=0.0)
        ),
        "events": events,
        "parse_warnings": warnings,
    }


def parse_file(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    raw = path.read_text(encoding="utf-8-sig", errors="replace")
    return parse_text(raw, source_file=path.name)


def parse_directory(directory: str | Path) -> list[dict[str, Any]]:
    files = sorted(Path(directory).glob("*.txt"))
    return [parse_file(path) for path in files]
