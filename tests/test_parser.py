from pathlib import Path

import pytest

from screenplay_parser import fmt_time, parse_file, parse_text, to_seconds


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_timestamp_formats_and_roundtrip():
    assert to_seconds("01:23.50") == 83.5
    assert to_seconds("1:23") == 83
    assert to_seconds("01:02:03.250") == 3723.25
    assert fmt_time(83.5) == "01:23.50"
    assert fmt_time(59.999) == "01:00.00"


@pytest.mark.parametrize("value", ["", "1", "00:60", "00:99.1", "NaN", "-1:02", "1:2:3:4"])
def test_invalid_timestamps_are_rejected(value):
    with pytest.raises(ValueError):
        to_seconds(value)


def test_parse_preserves_parallel_layers_and_duplicate_timestamps():
    screenplay = """\ufeffEPISODE NUMBER: Episode X
EPISODE LOGLINE: A family secret emerges.
CONTINUITY NOTES: One timeline.

SCENE 01
Scene heading: INT. HOUSE
Scene start: 00:00
Scene end: 00:25
**CAMERA:**
Start: (00:00.00) | End: (00:25.00)
Close-up on the door.
**ACTION:**
Start: (00:00.00) | End: (00:25.00)
Mara opens the door.
**LADY MARA (Urgent):**
Start: (00:00.00) | End: (00:20.00)
Who is there?
**SOUND FX:**
Start: (00:20.00) | End: (00:25.00)
A loud knock.
"""
    episode = parse_text(screenplay, "episode.txt")

    assert episode["episode"] == "Episode X"
    assert episode["duration_seconds"] == 25
    assert {event["label"] for event in episode["events"]} == {
        "CAMERA:",
        "ACTION:",
        "LADY MARA (Urgent):",
        "SOUND FX:",
    }
    assert sum(event["start"] == 0 for event in episode["events"]) == 3
    assert episode["events"][0]["scene"] == "01"
    assert episode["parse_warnings"] == []


def test_parse_reports_invalid_ranges_and_handles_empty_or_missing_metadata():
    screenplay = """**CAMERA:**
Start: (00:75) | End: (00:80)
Invalid event.
"""
    episode = parse_text(screenplay, "fallback-name.txt")
    assert episode["episode"] == "fallback-name"
    assert episode["events"] == []
    assert episode["duration_seconds"] == 0
    assert episode["parse_warnings"]
    assert parse_text("", "empty.txt")["events"] == []


def test_unsupported_inline_format_reports_expected_block_syntax():
    episode = parse_text(
        "EPISODE_ID: TEST_001 TITLE: Example DURATION: 04:00\n"
        "[00:00.00] CAMERA: A timestamped event.",
        "inline.txt",
    )
    assert episode["events"] == []
    assert "Kuku-style event blocks" in episode["parse_warnings"][0]


def test_parse_supplied_episode():
    path = PROJECT_ROOT / "data" / "input" / "episode-001-Episode 1671703.txt"
    episode = parse_file(path)
    assert episode["episode"] == "Episode 1"
    assert episode["events"]
    assert episode["duration_seconds"] > 20
    assert any(event["label"] == "CAMERA:" for event in episode["events"])
    assert any(event["label"].startswith("LADY JULIANA") for event in episode["events"])


def test_parse_reports_significant_gap_after_final_event():
    screenplay = """EPISODE NUMBER: Episode Gap
SCENE 01
Scene end: 04:00
**DIALOGUE:**
Start: (02:55.00) | End: (03:00.00)
We found the missing key.
"""
    episode = parse_text(screenplay, "gap.txt")

    assert episode["duration_seconds"] == 240
    assert episode["declared_duration_seconds"] == 240
    assert episode["last_event_seconds"] == 180
    assert episode["duration_gap_seconds"] == 60
    assert any("60.00s before the declared duration" in warning for warning in episode["parse_warnings"])


def test_parse_does_not_warn_for_small_duration_gap():
    screenplay = """SCENE 01
Scene end: 01:00
**DIALOGUE:**
Start: (00:50.00) | End: (00:55.00)
The door is open.
"""
    episode = parse_text(screenplay, "small-gap.txt")

    assert episode["duration_gap_seconds"] == 5
    assert episode["parse_warnings"] == []
