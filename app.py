"""Streamlit interface for reviewing screenplay promo candidates."""
from __future__ import annotations

import json
import logging
import os

import pandas as pd
import streamlit as st

from model import model_status
from promo_detector import detect_episode
from screenplay_parser import parse_text
from scoring import rank_promos, validate_promo


logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024

st.set_page_config(page_title="PromoPilot AI", page_icon="🎬", layout="wide")
st.title("🎬 PromoPilot AI")
st.caption(
    "Find, explain and rank 20–60 second microdrama promos from timestamped screenplays."
)

with st.sidebar:
    st.subheader("Settings")
    st.write(model_status())
    prefer_llm = st.checkbox(
        "Use Gemini when API key is configured",
        value=bool(os.getenv("GEMINI_API_KEY")),
    )
    st.caption(
        "Without a key, the app uses transparent offline heuristics. "
        "Review recommendations before publishing."
    )

files = st.file_uploader(
    "Upload screenplay TXT files",
    type=["txt"],
    accept_multiple_files=True,
    help="Each file is limited to 10 MB. Overlapping screenplay evidence layers are preserved.",
)

if not files:
    st.info("Upload one or more .txt screenplays to find promo candidates.")

if files and st.button("Analyze screenplays", type="primary"):
    all_promos = []
    parsed_episodes = []
    errors = []
    progress = st.progress(0, text="Preparing screenplays…")

    for index, uploaded_file in enumerate(files):
        progress.progress(
            index / len(files), text=f"Analyzing {uploaded_file.name}…"
        )
        if not uploaded_file.name.lower().endswith(".txt"):
            errors.append(f"{uploaded_file.name}: only .txt files are supported.")
            continue
        if uploaded_file.size > MAX_UPLOAD_BYTES:
            errors.append(f"{uploaded_file.name}: exceeds the 10 MB file limit.")
            continue

        try:
            content = uploaded_file.getvalue().decode("utf-8-sig", errors="replace")
            episode = parse_text(content, source_file=uploaded_file.name)
            parsed_episodes.append(episode)
            promos = detect_episode(episode, prefer_llm=prefer_llm)
            for promo in promos:
                is_valid, message = validate_promo(
                    promo, episode["duration_seconds"]
                )
                promo["validation"] = {"valid": is_valid, "message": message}
                if is_valid:
                    all_promos.append(promo)
        except Exception as exc:
            logger.exception("Could not analyze uploaded screenplay %s", uploaded_file.name)
            errors.append(
                f"{uploaded_file.name}: could not analyze file ({type(exc).__name__})."
            )

    progress.progress(1.0, text="Analysis complete.")
    episode_durations = {
        episode["episode"]: episode["duration_seconds"]
        for episode in parsed_episodes
    }
    ranked = rank_promos(all_promos, episode_durations)
    for rank, promo in enumerate(ranked, start=1):
        promo["rank"] = rank
    st.session_state["ranked"] = ranked
    st.session_state["parsed"] = parsed_episodes
    st.session_state["errors"] = errors

if "ranked" in st.session_state:
    ranked = st.session_state["ranked"]
    parsed = st.session_state["parsed"]
    errors = st.session_state.get("errors", [])
    for error in errors:
        st.error(error)
    for episode in parsed:
        for warning in episode.get("parse_warnings", []):
            st.warning(f"{episode['source_file']}: {warning}")

    columns = st.columns(3)
    columns[0].metric("Episodes analyzed", len(parsed))
    columns[1].metric("Promos found", len(ranked))
    columns[2].metric(
        "Events parsed", sum(len(episode["events"]) for episode in parsed)
    )

    if ranked:
        st.subheader("Ranked promo candidates")
        for promo in ranked:
            first_segment = promo["segments"][0]
            with st.expander(
                f"#{promo['rank']} · {promo['episode']} · "
                f"{first_segment['start']}–{first_segment['end']} · "
                f"{promo['duration_seconds']:.2f}s · score {promo['score']:.2f}",
                expanded=promo["rank"] == 1,
            ):
                st.write("**Segments**", promo["segments"])
                st.write("**Hook**", promo.get("hook", ""))
                st.write("**Cliffhanger**", promo.get("cliffhanger", ""))
                st.write("**Why it works**", promo.get("why_it_works", ""))
                if promo.get("evidence_excerpt"):
                    st.write("**Screenplay evidence**", promo["evidence_excerpt"])
                st.json(promo.get("score_breakdown", {}))
                st.caption(
                    "Human review required · "
                    + promo.get("method", "unknown")
                )

        st.download_button(
            "Download ranked JSON",
            json.dumps(ranked, indent=2, ensure_ascii=False),
            file_name="ranked_promos.json",
            mime="application/json",
        )
        st.download_button(
            "Download ranked CSV",
            pd.DataFrame(ranked).to_csv(index=False),
            file_name="ranked_promos.csv",
            mime="text/csv",
        )
    elif not errors:
        st.warning(
            "No valid promo candidates found. Try Gemini or inspect the screenplay timestamps."
        )
