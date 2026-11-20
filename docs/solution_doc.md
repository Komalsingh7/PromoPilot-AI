# PromoPilot AI — Kuku Generalist Assignment (Problem 1)

**Problem chosen.** Find the strongest 20–60 second promotional moments in timestamped microdrama screenplays. I chose this because it is a repeatable editorial workflow with concrete inputs, outputs and checks.

**Assumptions.** The supplied 50 TXT files are the source of truth; timestamps are episode-relative `MM:SS.ss`. CAMERA, ACTION, dialogue and SOUND FX entries are parallel descriptions of the same timeline. This prototype creates single-episode promos; cross-episode montage support is future work.

**Solution.** A Python parser extracts episode metadata and timestamped evidence. A replaceable detector uses Gemini when configured, otherwise an offline heuristic fallback. The detector proposes 20–60 second windows and explains the hook and cliffhanger. Deterministic Python validation rejects invalid duration or out-of-episode endpoints, then ranks candidates. Streamlit provides an upload-and-review UI.

**Scale.** Process episodes independently, persist structured JSON, and rank candidates globally. At production volume, use a queue/batch worker, cache parsed episodes, retry model failures, and keep the model behind an adapter so Kuku can supply a stronger model without changing validation.

**Quality and limits.** The full pack is processed in offline mode and raw per-episode outputs are included. Checks cover parse counts, duration and episode bounds. The fallback is keyword-based and is not a learned predictor; it may miss subtle moments or overrate dramatic words. Screenplay text cannot verify actual acting, visuals, audio or edit rhythm. All candidates require editor review. No audience performance or human-editor ground truth was supplied, so no accuracy/virality claim is made.

**AI disclosure.** ChatGPT assisted with scaffolding/code drafting. One concrete AI-drafting error was an early assumption that screenplay blocks formed a sequential transcript; the real files contain overlapping CAMERA, ACTION and dialogue timelines, so the parser was changed to preserve parallel evidence layers. Gemini integration is optional and requires the user's API key; no API key is embedded. One expected model failure is selecting a dramatic line as a cliffhanger even when the next beat resolves it. Timestamp and duration checks are therefore enforced in code, and humans verify semantics.

**How to run.** `pip install -r requirements.txt`; `streamlit run app.py`. Full-pack offline run: `python run_analysis.py --heuristic`.
