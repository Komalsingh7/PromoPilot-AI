# PromoPilot AI

AI-assisted promo discovery for timestamped microdrama screenplays.

## What it does
- Parses episode loglines, continuity notes and timestamped dialogue/action/camera events.
- Finds candidate 20–60 second promo windows.
- Scores hook, payoff, context, coherence, emotional intensity, arc completeness and duration suitability.
- Validates duration and episode bounds, then ranks candidates globally.
- Offers optional Gemini analysis; offline heuristic mode always works.

## Run locally
```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```
Upload one or more `.txt` screenplays in the app.

For tests, install the development dependencies and run pytest:
```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Gemini configuration
Gemini is optional. Set `GEMINI_API_KEY` in the process environment and, optionally,
`GEMINI_MODEL` (defaults to `gemini-2.0-flash`). The client has a 30-second request
timeout. If no key is present, a response is malformed, or the request fails, candidate
detection falls back to the offline heuristic and logs a warning. API keys are never
included in the UI or generated output. `.env.example` documents the variables; the app
does not load `.env` files automatically.

## Run the full supplied input pack
The 50 screenplay files are included in `data/input/`.
```bash
# Reproducible offline run
python run_analysis.py --heuristic

# Optional Gemini run (set GEMINI_API_KEY first)
python run_analysis.py
```
Outputs are written to `outputs/`: one unedited per-episode JSON file in `outputs/raw/`, a global ranked JSON/CSV, and an episode parsing summary. The checked-in outputs were generated in heuristic mode, not with a paid API.

## How it works
1. `screenplay_parser.py` reads the Kuku screenplay format, accepts MM:SS and HH:MM:SS timestamps, and retains CAMERA, ACTION, dialogue, and SOUND FX blocks as separate, potentially overlapping events.
2. `promo_detector.py` asks Gemini for up to three candidates when configured; it checks response shape, evidence text, 0–5 rubric scores, duration, and boundaries before accepting them. Otherwise it uses the offline lexical/rule heuristic.
3. `scoring.py` independently rejects malformed, overlapping, out-of-order, out-of-bounds, or out-of-duration segments. Ranking only considers valid candidates and uses the same weighted 0–5 rubric for both detection methods.
4. `run_analysis.py` processes episodes independently and writes per-episode JSON, global ranked JSON/CSV, and per-episode processing times. `app.py` provides upload progress, file-size checks, result explanations, and downloads.

## Scoring (heuristic fallback)
The detector evaluates windows whose event boundaries yield durations from 20 to 60 seconds, then suppresses near-duplicate overlaps. Its transparent 0–5 weighted score is: hook 18%, cliffhanger/payoff 24%, first-time-viewer context 12%, narrative coherence 14%, emotional intensity 12%, promo-arc completeness 14%, and duration suitability 6%. The same formula is used to recompute Gemini scores. Duration suitability mildly favors the middle of the allowed range; it is not a prediction of audience performance. Offline signals use explainable lexical and timeline heuristics, not a trained model. Ranked results are editorial triage, not a claim of virality.

## Input and output
Inputs are UTF-8 `.txt` screenplays in the Kuku block format (`**CAMERA:**` followed by `Start: (MM:SS.ss) | End: (MM:SS.ss)`). BOM and replacement decoding are handled. Events with invalid ranges are skipped and reported in `parse_warnings`; same-time events and parallel layers are kept. If the last event ends significantly before the declared episode duration, the parser reports the gap and candidate generation stops at the last event rather than treating the empty tail as footage. Streamlit uploads are limited to 10 MB per file.

Each promo contains ordered `segments`, its total duration, hook/cliffhanger explanations, evidence excerpt, a 0–5 score and component breakdown, detection method, and human-review flag. Batch outputs include raw parsed events and per-candidate validation status. These checks ensure technical constraints only; they do not prove editorial quality.

## Assumptions and limitations
- Timestamps are episode-relative `MM:SS.ss` values, and all segment endpoints are inclusive for human interpretation (duration calculation uses end minus start).
- The parser accepts `MM:SS[.fraction]` and `HH:MM:SS[.fraction]`; seconds and (for hour-based values) minutes must be in the range 00–59.
- The supplied scripts describe visuals in text; the system cannot verify the actual filmed performance, shot quality, audio, pacing or whether the footage matches the screenplay.
- A screenplay timestamp may describe overlapping dialogue/action/camera layers. They are retained as parallel evidence, not concatenated into extra runtime.
- Heuristic mode evaluates event-boundary windows and the full opening-to-payoff arc, but its lexical cues may still miss subtle hooks or misread irony and context. It may choose a window whose opening is not visually compelling or whose ending resolves more than expected.
- Gemini output is schema- and duration-validated, but semantic correctness still needs human review. No generated timestamps are accepted if outside the episode or invalid in duration.
- Multi-episode cross-cuts are not generated by the current prototype; it focuses on one episode per promo.

## Quality checks
- Run on all 50 input episodes.
- Check parser event counts and per-episode raw JSON.
- Validate every selected promo is 20–60 seconds and within episode bounds.
- Review the hook and cliffhanger against the cited evidence excerpt and original screenplay.
- For a meaningful offline evaluation, manually label a sample of candidates and compare precision@k; no human labels or audience performance data are included in this submission.

## AI tools and disclosure
This project is structured to use Gemini through the official `google-genai` SDK when an API key is supplied. The included raw run uses offline heuristics because no API key is bundled. ChatGPT assisted with project scaffolding and code drafting. One concrete AI-drafting mistake: an early parser idea treated timestamped screenplay blocks as a simple sequential transcript. Inspection of the supplied files showed overlapping CAMERA, ACTION and dialogue layers, so the parser was corrected to retain them as parallel timestamped evidence. The model must not be trusted blindly: an LLM can select a dramatic moment that is not actually a cliffhanger or invent a timestamp, so this project validates timestamps/duration in code and flags all results for human review.

## Suggested next steps
- Add human editor feedback (accept/reject and reason) to build an evaluation set.
- Add candidate-window search over adjacent scenes and controlled cross-episode segments.
- Use stronger models for semantic analysis while keeping parsing/validation/model adapters independent.
- Evaluate against editor selections and downstream view-through/conversion, not model scores alone.
