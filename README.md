# PromoPilot AI

**AI-assisted promo discovery for timestamped microdrama screenplays.**

[Open the live Streamlit app](https://promopilot-ai-vc6y9bvhexchxl89pdsnck.streamlit.app/)

PromoPilot AI recommends and ranks 20–60 second moments from screenplay text. It provides candidate timestamps, the opening hook, the ending payoff or cliffhanger, an explanation, and screenplay evidence. The editor remains responsible for checking the actual footage and making the final selection.

## Assignment deliverables

- [Two-page solution document](submission/Komal_Singh_KUKUFM.pdf)
- [Full-pack raw output archive (50 episodes)](submission/PromoPilot_AI_Raw_Outputs.zip)
- [Ranked candidate JSON](outputs/ranked_promos.json)
- [Ranked candidate CSV](outputs/ranked_promos.csv)
- [Per-episode processing summary](outputs/episode_summary.json)
- [Per-episode raw JSON folder](outputs/raw/)

The raw JSON outputs include parsed screenplay text. Share them publicly only if you have permission to distribute the screenplay content.

## Features

- Upload one or more UTF-8 `.txt` screenplays and review ranked promo candidates.
- Retain overlapping CAMERA, ACTION, DIALOGUE, and SOUND FX evidence as parallel descriptions of one timeline.
- Run with an offline heuristic detector; Gemini is optional.
- Check candidate duration, timestamp order, and episode boundaries deterministically.
- Report a significant gap between declared episode duration and the final screenplay event.
- Download ranked results as JSON or CSV.
- Review a normalized score breakdown and evidence excerpt for each candidate.

## Quick start

### Windows PowerShell

```powershell
Set-Location 'C:\path\to\PromoPilot-AI'
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

### macOS or Linux

```bash
cd /path/to/PromoPilot-AI
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`. Upload a screenplay `.txt` file, select **Analyze screenplays**, then inspect the ranked candidates. The app limits each uploaded file to 10 MB.

The app does not load `.env` files automatically. Without `GEMINI_API_KEY`, it uses the offline heuristic and does not require credentials or network access for detection.

## Supported screenplay format

The parser intentionally supports the supplied **Kuku block format** only. A screenplay contains scene metadata and blocks like:

```text
EPISODE NUMBER: Episode 1
EPISODE LOGLINE: A family secret changes everything.

SCENE 01
Scene heading: INT. HOUSE
Scene start: 00:00
Scene end: 01:00
**CAMERA:**
Start: (00:00.00) | End: (00:03.00)
Close-up on the locked door.
**ACTION:**
Start: (00:00.00) | End: (00:03.00)
Maya freezes as someone knocks.
**CHARACTER NAME (Urgent):**
Start: (00:02.00) | End: (00:05.00)
Who is there?
```

Accepted timestamps are `MM:SS`, `MM:SS.fraction`, and `HH:MM:SS.fraction`; seconds and hour-based minutes must be less than 60. A UTF-8 BOM is accepted. Invalid or empty event blocks are skipped and described in parser warnings.

**Parallel evidence is not sequential dialogue.** Events that overlap or share timestamps remain separate. Their durations are not summed. Inline records such as `[00:00] CAMERA: ...` are not supported by this parser.

## How it works

1. **Parse — [screenplay_parser.py](screenplay_parser.py):** Extract episode metadata, scenes, timestamps, labels, and event text. Preserve parallel evidence layers and calculate the final event time.
2. **Generate and detect — [promo_detector.py](promo_detector.py):** Search event-boundary windows between 20 and 60 seconds. The heuristic assesses the opening hook, development, emotional intensity, and ending payoff; it suppresses near-duplicate candidates. When configured, Gemini can propose candidates, with the heuristic retained as a fallback.
3. **Validate and rank — [scoring.py](scoring.py):** Reject invalid durations, timestamps, ordering, overlaps, or episode bounds. Recompute the weighted score for Gemini candidates and rank valid candidates.
4. **Review — [app.py](app.py):** Show upload progress, parser warnings, ranked candidates, score breakdowns, explanations, evidence, and downloads.
5. **Batch — [run_analysis.py](run_analysis.py):** Process all `.txt` files in a directory and write per-episode JSON, a global ranking, and a summary.

Candidate starts and ends are selected from screenplay event boundaries; the prototype does not search arbitrary video frames. If the last event ends significantly before the declared duration, a warning is recorded and candidate generation does not use the empty tail as footage. The discrepancy threshold is the greater of 10 seconds or 5% of the declared duration.

## Scoring

Every factor is scored from 0 to 5. The composite score is:

| Factor | Weight | Intent |
|---|---:|---|
| Hook | 18% | Curiosity, tension, surprise, or emotional engagement near the start |
| Cliffhanger/payoff | 24% | Meaningful reveal, threat, reversal, confession, or unresolved question |
| First-time-viewer context | 12% | How understandable the people and situation are without prior episodes |
| Narrative coherence | 14% | Whether selected events form a connected progression |
| Emotional intensity | 12% | Evidence of emotional or dramatic intensity |
| Promo-arc completeness | 14% | Strength of the opening-to-build-to-ending progression |
| Duration suitability | 6% | A modest preference for the middle of the allowed duration range |

These are explainable ranking signals, **not calibrated probabilities or evidence of predicted audience performance**. The heuristic is rule- and lexicon-based, not a trained machine-learning model.

## Run the supplied 50-episode pack

Run from the project root:

```bash
python run_analysis.py --heuristic
```

The offline run avoids Gemini requests. To process a different input directory or write outputs elsewhere:

```bash
python run_analysis.py --heuristic --input path/to/screenplays --output path/to/results
```

`--input` must contain `.txt` files. By default, inputs come from `data/input/` and outputs are written to `outputs/`.

### Output files

- `outputs/raw/<episode>.json`: parsed episode, warnings, candidates, and per-candidate validation.
- `outputs/ranked_promos.json`: globally ranked valid candidates, including score components and evidence.
- `outputs/ranked_promos.csv`: tabular view of the global ranking.
- `outputs/episode_summary.json`: event and promo counts, declared/final-event durations, gap warnings, and processing time.

## Gemini (optional)

Set `GEMINI_API_KEY` in the process environment and optionally set `GEMINI_MODEL` (default: `gemini-2.0-flash`). The official `google-genai` SDK is installed from `requirements.txt`. The request timeout is 30 seconds. Missing keys, malformed responses, and request failures fall back to the offline heuristic. When Gemini is enabled, screenplay event text and timestamps are sent to Google's Gemini API; only use this mode when you are authorized to send that content.

PowerShell example:

```powershell
$env:GEMINI_API_KEY = '<your-key>'
$env:GEMINI_MODEL = 'gemini-2.0-flash'
streamlit run app.py
```

Never commit a real key or put it in source code. `.env.example` contains placeholders only, and the application does not load `.env` files. The deployed app works in offline mode without a key. The current detector reads `GEMINI_API_KEY` from the process environment; before using a hosting provider's secrets store, confirm that it exposes the value as an environment variable or update the app to read that provider's secret API.

## Tests and verification

Install development dependencies and run the test suite:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests cover timestamp conversion, parallel evidence, malformed input, gap warnings, deterministic duration/boundary checks, scoring/ranking, near-duplicate handling, Gemini response parsing and failure fallback, heuristic behavior, and end-to-end processing. Gemini API tests are mocked; tests do not require a key or network access.

Latest recorded local offline run:

- 50 episodes and 3,727 parsed events
- 34 valid promo candidates; zero failed duration or episode-boundary validation
- Candidate durations: 26.50–58.90 seconds
- Batch elapsed time: approximately 3.29 seconds on the recorded local environment
- The bundled pack had no significant duration-gap warnings

This is technical validation only. The project has no editor-labeled ground-truth set, so precision, recall, and recommendation quality have not been established.


## Assumptions and limitations

- The supported screenplay format is the Kuku block format described above.
- The offline heuristic emits one contiguous segment per candidate. The Gemini response schema can represent multiple ordered segments within an episode, but neither detector combines episodes or performs video editing.
- The screenplay describes events but does not prove what the filmed footage looks or sounds like. Editors should verify shot quality, performance, pacing, audio, and continuity.
- Lexical rules may miss subtle, culturally specific, ironic, or context-dependent hooks and payoffs. Candidate scores require human review.
- No human labels or audience outcomes are available. The score must not be interpreted as virality or predictive accuracy.
- The Rohan/Naina train screenplay used for example reference windows was not available during the latest offline run; those specific examples remain unverified.

## Scaling and future evaluation

The current batch runner processes episodes sequentially and independently, which keeps the prototype simple. For a substantially larger slate, episodes can be sent to bounded parallel workers while retaining per-episode retries, model rate limits, deterministic post-validation, and structured JSON results. A queue or database is unnecessary until throughput or persistence requirements justify one.

The next quality step is to collect editor accept/reject decisions and reasons, then evaluate candidate ranking against held-out editor selections. Useful measures include precision@K, recall, and temporal intersection-over-union. Do not claim recommendation accuracy until this evaluation data exists.

## AI assistance

Gemini integration is optional and its output is validated in code. The included full-pack results were generated offline with the heuristic detector. AI-assisted drafting helped develop the project; the final implementation preserves CAMERA, ACTION, DIALOGUE, and SOUND FX as parallel timeline evidence rather than treating them as sequential transcript blocks.
