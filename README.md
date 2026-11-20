# PromoPilot AI 🎬
### AI-Assisted Promo Discovery for Timestamped Microdrama Screenplays

PromoPilot AI is an AI-assisted tool that automatically identifies, evaluates, validates, and ranks potential promotional clips from timestamped microdrama screenplays.

It helps editors discover compelling **20–60 second promotional moments** that can be used on platforms such as Instagram Reels, YouTube Shorts, and TikTok.

The system combines optional Gemini-based semantic analysis with an explainable offline heuristic engine, ensuring that promo discovery works even without an API key.

---

## 🚀 Key Features

- **Screenplay Parsing:** Extracts timestamped dialogue, camera directions, action, and sound effects from screenplay files.
- **Automated Promo Detection:** Identifies potential 20–60 second promotional windows.
- **AI-Powered Analysis:** Optionally uses Google's Gemini API to identify dramatic hooks, cliffhangers, and compelling story moments.
- **Offline Heuristic Detection:** Provides an independent rule-based detection mechanism when Gemini is unavailable.
- **Multi-Dimensional Scoring:** Evaluates candidates based on seven criteria: hook, payoff, context, coherence, emotional intensity, promo-arc completeness, and duration suitability.
- **Validation Engine:** Rejects invalid, overlapping, out-of-order, out-of-bounds, and incorrectly sized segments.
- **Global Ranking:** Ranks valid promotional candidates across multiple episodes.
- **Interactive Streamlit Interface:** Supports screenplay uploads, progress tracking, result explanations, and downloadable outputs.
- **Batch Processing:** Processes multiple episodes and generates structured JSON and CSV reports.

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
| Configuration | Environment Variables |
| Logging | Python Logging |

---

## 🏗️ System Architecture

The project follows a modular architecture:

1. **Screenplay Parser (`screenplay_parser.py`)**
   - Reads UTF-8 screenplay files.
   - Extracts timestamped CAMERA, ACTION, dialogue, and SOUND FX events.
   - Supports MM:SS and HH:MM:SS timestamp formats.
   - Preserves overlapping events as independent timeline layers.

2. **Promo Detector (`promo_detector.py`)**
   - Generates candidate promotional windows.
   - Uses Gemini when an API key is available.
   - Falls back to an offline heuristic approach when Gemini is unavailable.
   - Identifies hooks, cliffhangers, and supporting evidence.

3. **Scoring Engine (`scoring.py`)**
   - Independently validates candidate segments.
   - Checks duration and episode boundaries.
   - Calculates weighted scores.
   - Ranks valid promotional candidates.

4. **Batch Processing (`run_analysis.py`)**
   - Processes multiple screenplay files.
   - Generates individual episode outputs.
   - Produces globally ranked JSON and CSV reports.
   - Records episode-level processing information.

5. **Interactive Application (`app.py`)**
   - Provides a Streamlit-based interface.
   - Accepts one or more `.txt` screenplay files.
   - Displays detected promos and their explanations.
   - Allows users to download results.

---

## 📊 Scoring Methodology

Each candidate is evaluated using a weighted scoring system with individual component scores ranging from 0 to 5.

| Evaluation Criteria | Weight |
|---|---:|
| Hook | 18% |
| Cliffhanger / Payoff | 24% |
| First-time Viewer Context | 12% |
| Narrative Coherence | 14% |
| Emotional Intensity | 12% |
| Promo Arc Completeness | 14% |
| Duration Suitability | 6% |
| **Total** | **100%** |

The same scoring formula is used to recompute and rank candidates from both Gemini and heuristic detection.

The heuristic engine uses explainable lexical and timeline-based signals rather than a trained machine learning model.

**Note:** Scores indicate editorial suitability, not predicted virality or actual audience engagement.

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
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 📂 Output Location and Generated Files

All batch-processing results are automatically saved inside the **`outputs/` directory** in the project root.

After running the analysis, the following files are generated:

| Output Location | Description |
|---|---|
| `outputs/raw/` | Individual JSON files containing parsed events and promo results for each episode. |
| `outputs/ranked_promos.json` | Globally ranked promotional candidates in JSON format. |
| `outputs/ranked_promos.csv` | Globally ranked promotional candidates in CSV format for spreadsheet analysis. |
| `outputs/episode_summary.json` | Episode-level parsing summaries and processing information. |

### Understanding the Outputs

**1. Raw Episode Outputs**

The `outputs/raw/` directory stores individual episode-level JSON files, including parsed screenplay events, detected candidates, validation information, and scoring details.

**2. Global Ranked Results**

`ranked_promos.json` and `ranked_promos.csv` contain promotional candidates ranked across all processed episodes.

**3. Episode Summary**

`episode_summary.json` contains episode-level processing information and parsing summaries.

The Streamlit application also provides downloadable results through its interface.

---

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Komalsingh7/PromoPilot-AI.git
cd PromoPilot-AI
```

### 2. Create a Virtual Environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Streamlit Application

```bash
streamlit run app.py
```

Open the local URL displayed in the terminal and upload one or more `.txt` screenplay files.

---

## 🤖 Gemini API Configuration (Optional)

PromoPilot AI supports Google's Gemini API for semantic promo analysis.

To enable Gemini:

1. Obtain a Gemini API key.
2. Set the `GEMINI_API_KEY` environment variable.
3. Optionally configure `GEMINI_MODEL`.

Example for Windows PowerShell:

```powershell
$env:GEMINI_API_KEY="your_api_key"
$env:GEMINI_MODEL="gemini-2.0-flash"
```

The default model is `gemini-2.0-flash`.

**Fallback Mechanism:**

- If no API key is configured, the system automatically uses heuristic detection.
- If the Gemini request fails or returns malformed output, the system falls back to offline detection.
- API keys are never displayed in the application or included in generated outputs.

The Gemini client uses a 30-second request timeout.

---

## ▶️ Running the Full Input Pack

The project includes a supplied pack of 50 screenplay episodes.

To process all episodes using the offline heuristic engine:

```bash
python run_analysis.py --heuristic
```

To run with Gemini enabled:

```bash
python run_analysis.py
```

For Gemini execution, configure `GEMINI_API_KEY` first.

Generated files are saved in the `outputs/` directory.

---

## 🧪 Testing

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the test suite:

```bash
python -m pytest -q
```

### Quality Checks

The solution supports the following quality checks:

- Processing all 50 supplied episodes.
- Checking parser event counts and raw episode outputs.
- Validating that every selected promo is between 20 and 60 seconds.
- Ensuring candidate timestamps remain within episode boundaries.
- Reviewing hooks and cliffhangers against the original screenplay evidence.
- Checking candidate validation status and global ranking.

---

## ⚠️ Assumptions and Limitations

- The system assumes screenplay timestamps are episode-relative.
- Promo duration is calculated as end timestamp minus start timestamp.
- Overlapping dialogue, camera, and action events are preserved as parallel timeline evidence.
- The current implementation generates candidates within individual episodes and does not support cross-episode promotional sequences.
- Heuristic detection relies on lexical and timeline signals and may miss subtle emotional context, irony, or nuanced cliffhangers.
- Gemini-generated candidates undergo structural and timestamp validation, but still require human editorial review.
- The system analyzes screenplay text, not actual video or audio footage. Therefore, it cannot verify visual quality, actor performance, sound, or final editing suitability.
- Rankings represent editorial triage and should not be interpreted as guaranteed audience performance.

---

## 🔍 Future Improvements

- Introduce human editor feedback to build a labelled evaluation dataset.
- Add candidate-window search across adjacent scenes.
- Support controlled cross-episode promotional sequences.
- Evaluate precision@k against manually selected promotional clips.
- Introduce stronger interchangeable AI models through a modular model adapter.
- Track editor acceptance rates and actual audience engagement metrics.

---

## 🤝 AI Tools and Disclosure

- **Google Gemini:** Optional semantic analysis of screenplay content.
- **ChatGPT:** Assisted with project scaffolding, code drafting, and documentation.

One important correction during development involved screenplay parsing. An early approach treated screenplay blocks as a sequential transcript. However, inspection revealed that CAMERA, ACTION, and dialogue events could overlap. The parser was consequently designed to preserve them as independent timestamped evidence.

AI-generated results are not trusted blindly. The implementation independently validates timestamps, duration, boundaries, and scoring, while flagging candidates for human review.

---

## 🎯 Assignment Context

**Organization:** Kuku

**Assignment:** AI Generalist – Problem 1: Find the Promos

**Objective:** Build a reusable tool that discovers, evaluates, validates, and ranks 20–60 second promotional moments from timestamped microdrama screenplays.

**Repository:** https://github.com/Komalsingh7/PromoPilot-AI

