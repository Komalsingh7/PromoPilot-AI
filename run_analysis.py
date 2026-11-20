"""Batch-process screenplay TXT files and write ranked JSON/CSV outputs."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import time

from promo_detector import detect_episode
from screenplay_parser import parse_file
from scoring import rank_promos, validate_promo


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/input")
    parser.add_argument("--output", default="outputs")
    parser.add_argument(
        "--heuristic",
        action="store_true",
        help="Use offline heuristic detection without calling Gemini.",
    )
    args = parser.parse_args()

    input_directory = Path(args.input)
    if not input_directory.is_dir():
        parser.error(f"input directory does not exist: {input_directory}")

    batch_started = time.perf_counter()
    output_directory = Path(args.output)
    raw_directory = output_directory / "raw"
    raw_directory.mkdir(parents=True, exist_ok=True)

    input_files = sorted(input_directory.glob("*.txt"))
    if not input_files:
        parser.error(f"no .txt screenplay files found in: {input_directory}")

    all_promos = []
    summary = []
    episode_durations = {}
    for input_file in input_files:
        episode_started = time.perf_counter()
        episode = parse_file(input_file)
        episode_durations[episode["episode"]] = episode["duration_seconds"]
        promos = detect_episode(episode, prefer_llm=not args.heuristic)
        valid_count = 0
        for promo in promos:
            is_valid, message = validate_promo(promo, episode["duration_seconds"])
            promo["validation"] = {"valid": is_valid, "message": message}
            if is_valid:
                all_promos.append(promo)
                valid_count += 1

        raw_path = raw_directory / f"{Path(episode['source_file']).stem}.json"
        raw_path.write_text(
            json.dumps(
                {"episode": episode, "promos": promos},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        summary.append(
            {
                "episode": episode["episode"],
                "source_file": episode["source_file"],
                "duration_seconds": episode["duration_seconds"],
                "declared_duration_seconds": episode["declared_duration_seconds"],
                "last_event_seconds": episode["last_event_seconds"],
                "duration_gap_seconds": episode["duration_gap_seconds"],
                "events_parsed": len(episode["events"]),
                "promos_found": valid_count,
                "parse_warnings": episode["parse_warnings"],
                "processing_seconds": round(time.perf_counter() - episode_started, 4),
            }
        )

    ranked = rank_promos(all_promos, episode_durations)
    for rank, promo in enumerate(ranked, start=1):
        promo["rank"] = rank

    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "ranked_promos.json").write_text(
        json.dumps(ranked, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_directory / "episode_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (output_directory / "ranked_promos.csv").open(
        "w", newline="", encoding="utf-8"
    ) as csv_file:
        fields = [
            "rank",
            "episode",
            "segments",
            "duration_seconds",
            "score",
            "hook",
            "cliffhanger",
            "why_it_works",
            "method",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        for promo in ranked:
            row = {field: promo.get(field, "") for field in fields}
            row["segments"] = json.dumps(promo.get("segments", []))
            writer.writerow(row)

    print(
        f"Processed {len(summary)} episodes; parsed "
        f"{sum(item['events_parsed'] for item in summary)} events; "
        f"valid promos: {len(ranked)}"
    )
    print(f"Batch elapsed: {time.perf_counter() - batch_started:.2f}s")
    print("Top 5:")
    for promo in ranked[:5]:
        print(
            promo["rank"],
            promo["episode"],
            promo["segments"],
            promo["score"],
            promo["hook"][:90],
        )


if __name__ == "__main__":
    main()
