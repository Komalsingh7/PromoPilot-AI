# PromoPilot AI 🎬

### AI-Assisted Promo Discovery for Timestamped Microdrama Screenplays

<p align="center">
  <a href="https://promopilot-ai-vc6y9bvhexchxl89pdsnck.streamlit.app/">
    🚀 <strong>Live Demo</strong>
  </a>
  &nbsp; | &nbsp;
  <a href="https://drive.google.com/file/d/1V_u2fkniLBmfyVpmNgwiTHbjiTtx4_1-/view?usp=sharing">
    🎥 <strong>Watch Demo Video</strong>
  </a>
  &nbsp; | &nbsp;
  <a href="https://github.com/Komalsingh7/PromoPilot-AI">
    💻 <strong>GitHub Repository</strong>
  </a>
</p>

---

## 📌 Overview

PromoPilot AI is an AI-assisted promotional clip discovery system designed for timestamped microdrama screenplays.

It automatically identifies, evaluates, validates, and ranks potential **20–60 second promotional clips** from screenplay text.

The system helps editors discover compelling moments that can be used as promotional content on platforms such as Instagram Reels, YouTube Shorts, and TikTok.

For every candidate, it provides:
- Episode number and candidate timestamps.
- Opening hook and ending payoff or cliffhanger.
- Supporting screenplay evidence.
- Explanation of why the promo might work.
- Individual scoring breakdown and overall ranking.

The system combines an optional Gemini-powered semantic analysis engine with an explainable offline heuristic detector. This ensures that the application remains functional even without an API key.

**The goal is to assist editors in identifying promising promotional moments, not to replace human editorial judgment.**

---

## ✨ Key Features

- **Automated Screenplay Parsing:** Extracts timestamped CAMERA, ACTION, DIALOGUE, and SOUND FX events.
- **Promo Candidate Detection:** Identifies potential promotional windows between 20 and 60 seconds.
- **AI-Powered Analysis:** Optionally uses Google's Gemini API to identify dramatic hooks, emotional moments, and cliffhangers.
- **Offline Heuristic Detection:** Provides an independent rule-based detection mechanism without requiring an external API.
- **Multi-Dimensional Scoring:** Evaluates candidates using seven weighted criteria.
- **Candidate Validation:** Checks duration, timestamp ordering, overlaps, and episode boundaries.
- **Global Ranking:** Ranks valid promotional candidates across multiple episodes.
- **Interactive Streamlit Interface:** Supports screenplay uploads, progress tracking, result explanations, and downloadable outputs.
- **Batch Processing:** Processes multiple episodes and generates structured JSON and CSV reports.
- **Human-in-the-Loop:** Flags candidates for editorial review rather than treating AI-generated results as final decisions.

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| User Interface | Streamlit |
| AI Model | Google Gemini 2.0 Flash (Optional) |
| AI Integration | Google GenAI SDK |
| Data Processing | JSON, CSV |
| Testing | Pytest |
| Logging | Python Logging |
| Configuration | Environment Variables |

---

## 🏗️ System Architecture

The project follows a modular architecture with independent parsing, detection, validation, scoring, and presentation components.

### Workflow

```text
       Screenplay Input (.txt)
                 |
                 v
       Screenplay Parser
       (screenplay_parser.py)
                 |
                 v
       Timestamped Events
                 |
                 v
          Promo Detector
       (promo_detector.py)
                 |
          +------+------+
          |             |
          v             v
      Gemini API    Heuristic Engine
       (Optional)      (Offline)
          |             |
          +------+------+
                 |
                 v
        Candidate Promos
                 |
                 v
        Scoring & Validation
           (scoring.py)
                 |
                 v
          Global Ranking
                 |
          +------+------+
          |             |
          v             v
      Streamlit       Batch
      Interface      Processing
       (app.py)    (run_analysis.py)
          |             |
          v             v
       Interactive    JSON / CSV
         Results       Outputs
```

### Core Components

**1. Screenplay Parser — `screenplay_parser.py`**

- Reads UTF-8 screenplay files.
- Extracts episode metadata, scenes, timestamps, labels, and event descriptions.
- Supports MM:SS and HH:MM:SS timestamp formats.
- Preserves overlapping dialogue, camera, action, and sound events as independent timeline layers.
- Detects parsing warnings and significant gaps between declared episode duration and the final screenplay event.

**2. Promo Detector — `promo_detector.py`**

- Searches event-boundary windows between 20 and 60 seconds.
- Identifies potential opening hooks and ending payoffs.
- Evaluates narrative development and emotional intensity.
- Suppresses near-duplicate candidates.
- Uses Gemini when configured, with the offline heuristic detector as a fallback.

**3. Scoring and Validation — `scoring.py`**

- Validates candidate duration and timestamp boundaries.
- Rejects invalid, overlapping, out-of-order, or out-of-bounds segments.
- Recomputes scores using a consistent weighted scoring formula.
- Ranks valid promotional candidates.

**4. Interactive Application — `app.py`**

- Provides a Streamlit-based user interface.
- Supports uploading one or more `.txt` screenplay files.
- Displays progress, parsing warnings, candidate explanations, and score breakdowns.
- Provides downloadable JSON and CSV results.

**5. Batch Processing — `run_analysis.py`**

- Processes multiple screenplay files independently.
- Generates individual episode-level JSON files.
- Produces globally ranked JSON and CSV reports.
- Records episode-level processing information and parsing summaries.

---

## 📊 Scoring Methodology

Each promotional candidate is evaluated using seven criteria, with individual component scores ranging from 0 to 5.

| Evaluation Criteria | Weight |
|---|---:|
| Hook | 18% |
| Cliffhanger / Payoff | 24% |
| First-Time Viewer Context | 12% |
| Narrative Coherence | 14% |
| Emotional Intensity | 12% |
| Promo Arc Completeness | 14% |
| Duration Suitability | 6% |
| **Total** | **100%** |

The weighted score is calculated as:

\[
S = \sum_{i=1}^{7} w_i \times s_i
\]

Where:
- \(s_i\) represents an individual criterion score.
- \(w_i\) represents its corresponding weight.

The same scoring formula is used to recompute and rank candidates from both Gemini and heuristic detection.

**Important:** These are explainable editorial ranking signals, not calibrated probabilities or predictions of virality.

The heuristic engine uses lexical and timeline-based rules rather than a trained machine learning model.

---

## 📁 Project Structure

```text
PromoPilot-AI/
│
├── app.py
├── screenplay_parser.py
├── promo_detector.py
├── scoring.py
├── run_analysis.py
│
├── data/
│   └── input/
│       └── screenplay_*.txt
│
├── outputs/
│   ├── raw/
│   │   ├── episode_*.json
│   │   └── ...
│   │
│   ├── ranked_promos.json
│   ├── ranked_promos.csv
│   └── episode_summary.json
│
├── tests/
│   └── ...
│
├── submission/
│   ├── Komal_Singh_KUKUFM.pdf
│   └── PromoPilot_AI_Raw_Outputs.zip
│
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 📂 Output Files and Storage Location

All batch-processing outputs are automatically stored inside the **`outputs/` directory** in the project root.

After executing the batch analysis, the following files are generated:

| File / Directory | Description |
|---|---|
| `outputs/raw/` | Individual JSON files containing parsed episode information, detected candidates, warnings, and validation details. |
| `outputs/ranked_promos.json` | Globally ranked valid promotional candidates in JSON format. |
| `outputs/ranked_promos.csv` | Tabular representation of the global promotional ranking. |
| `outputs/episode_summary.json` | Episode-level event counts, promo counts, duration information, warnings, and processing time. |

### Understanding the Generated Outputs

**1. Raw Episode Outputs**

The `outputs/raw/` directory contains individual JSON files for each processed episode.

These files preserve parsed screenplay information, candidate results, and validation details.

**2. Globally Ranked Results**

- `ranked_promos.json`: Structured results containing ranked candidates, scores, and evidence.
- `ranked_promos.csv`: Spreadsheet-friendly representation of the ranked candidates.

**3. Episode Summary**

`episode_summary.json` contains processing statistics for each episode, including parsed event counts, detected promo counts, duration information, and parsing warnings.

**4. Streamlit Downloads**

The interactive application also allows users to download ranked results in JSON and CSV formats.

**Note:** Outputs are saved locally in the project directory when running the batch script. Streamlit-hosted application files should not be treated as permanent storage.

---

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Komalsingh7/PromoPilot-AI.git

cd PromoPilot-AI
```

### 2. Create a Virtual Environment

**Windows PowerShell:**

```powershell
py -m venv .venv

.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python3 -m venv .venv

source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Run the Application

```bash
streamlit run app.py
```

Open the local URL printed in the terminal, normally:

```text
http://localhost:8501
```

Upload one or more `.txt` screenplay files and select **Analyze screenplays** to view ranked promo candidates.

The application limits each uploaded file to 10 MB.

---

## 🤖 Gemini API Configuration (Optional)

PromoPilot AI supports Google's Gemini API for semantic promo analysis.

The default model is:

```text
gemini-2.0-flash
```

### Configure Gemini

Obtain a Gemini API key and set the following environment variables.

**Windows PowerShell:**

```powershell
$env:GEMINI_API_KEY = "your_api_key"

$env:GEMINI_MODEL = "gemini-2.0-flash"

streamlit run app.py
```

### Offline Fallback Mechanism

Gemini is completely optional.

- If no API key is configured, the system uses offline heuristic detection.
- If a Gemini request fails, the system falls back to the heuristic engine.
- If Gemini returns malformed output, the response is rejected and fallback detection is used.
- API keys are never included in the application interface or generated outputs.

The Gemini client uses a 30-second request timeout.

**Security:** Never commit real API keys or include them directly in source code. The application does not automatically load `.env` files.

When Gemini is enabled, screenplay event text and timestamps are sent to Google's Gemini API. Only use this mode when authorized to share the screenplay content.

---

## ▶️ Running the Full 50-Episode Input Pack

The project includes a supplied pack of 50 screenplay episodes.

To process all episodes using offline heuristic detection:

```bash
python run_analysis.py --heuristic
```

To process using Gemini when configured:

```bash
python run_analysis.py
```

To process a different input directory or save outputs to another location:

```bash
python run_analysis.py --heuristic --input path/to/screenplays --output path/to/results
```

The input directory must contain `.txt` files.

By default:
- Input directory: `data/input/`
- Output directory: `outputs/`

The offline execution does not require a Gemini API key or paid API calls.

---

## 🧪 Testing and Quality Checks

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run the test suite:

```bash
python -m pytest -q
```

### Testing Coverage

The test suite covers:

- Timestamp conversion and parsing.
- Parallel screenplay evidence.
- Malformed and invalid input handling.
- Episode duration-gap warnings.
- Candidate duration and boundary validation.
- Scoring and global ranking.
- Near-duplicate candidate handling.
- Gemini response parsing.
- Gemini failure and fallback behavior.
- Heuristic detection.
- End-to-end batch processing.

Gemini API tests are mocked, so running the test suite does not require an API key or network access.

### Recorded Offline Execution Results

The latest recorded local offline run produced:

| Metric | Result |
|---|---:|
| Episodes Processed | 50 |
| Parsed Events | 3,727 |
| Valid Promo Candidates | 34 |
| Duration / Boundary Validation Failures | 0 |
| Minimum Candidate Duration | 26.50 seconds |
| Maximum Candidate Duration | 58.90 seconds |
| Batch Processing Time | Approximately 3.29 seconds |

The bundled input pack had no significant duration-gap warnings during this recorded run.

These results demonstrate technical execution and validation, not proven editorial accuracy. No human-labelled ground-truth dataset is currently available.

---

## ⚠️ Assumptions and Limitations

- The parser intentionally supports the supplied Kuku screenplay block format.
- Accepted timestamps include MM:SS, MM:SS.fraction, and HH:MM:SS.fraction.
- Overlapping CAMERA, ACTION, DIALOGUE, and SOUND FX events are preserved as parallel timeline evidence rather than treated as sequential dialogue.
- The offline heuristic generates one contiguous segment per candidate.
- The current prototype does not generate cross-episode promotional sequences.
- Candidate timestamps are selected from screenplay event boundaries, not arbitrary video frames.
- The system analyzes screenplay text and cannot verify actual video footage, actor performance, shot quality, sound, pacing, or continuity.
- Lexical heuristics may miss subtle emotional context, irony, and culturally specific hooks.
- Gemini-generated candidates are structurally validated but still require human editorial review.
- Scores are not predictions of virality or audience engagement.
- No human-labelled ground-truth dataset or audience performance data is currently available.

---

## 📈 Future Improvements

- **Human Feedback:** Collect editor accept/reject decisions and reasons to build an evaluation dataset.
- **Advanced Candidate Search:** Explore candidate windows across adjacent scenes.
- **Cross-Episode Promos:** Support controlled promotional sequences spanning multiple episodes.
- **Model Flexibility:** Introduce stronger interchangeable AI models through a modular model adapter.
- **Evaluation:** Measure precision@K, recall, and temporal intersection-over-union against editor-selected promotional clips.
- **Performance:** Introduce bounded parallel processing, per-episode retries, and model rate limiting for larger workloads.
- **Real-World Metrics:** Evaluate editor acceptance rates and audience engagement rather than relying only on model scores.

---

## 🤝 AI Tools and Disclosure

- **Google Gemini:** Optional semantic screenplay analysis through the official Google GenAI SDK.
- **ChatGPT:** Assisted with project scaffolding, code drafting, and documentation.

The included full-pack results were generated using offline heuristic detection rather than paid API calls.

### One Important Development Correction

An early parser approach treated timestamped screenplay blocks as a simple sequential transcript.

However, inspection of the supplied screenplay files revealed that CAMERA, ACTION, DIALOGUE, and SOUND FX events could overlap in time.

The parser was therefore designed to preserve these events as independent timestamped evidence layers.

AI-generated candidates are not trusted blindly. The implementation independently validates timestamps, duration, episode boundaries, and scoring, while keeping human editors responsible for the final decision.

---

## 🎯 Assignment Context

**Organization:** Kuku

**Assignment:** AI Generalist – Problem 1: Find the Promos

**Objective:** Build a reusable tool that discovers, evaluates, validates, and ranks 20–60 second promotional moments from timestamped microdrama screenplays.

**Developer:** Komal Singh

**Live Application:** https://promopilot-ai-vc6y9bvhexchxl89pdsnck.streamlit.app/

**Demo Video:** https://drive.google.com/file/d/1V_u2fkniLBmfyVpmNgwiTHbjiTtx4_1-/view?usp=sharing

---

<p align="center">
  <strong>PromoPilot AI — Turning Screenplay Moments into Promotional Opportunities 🎬</strong>
</p>
