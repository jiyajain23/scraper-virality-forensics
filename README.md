# ⚡ Hacker News Virality Forensics & Content Intelligence Platform

> **Predictive Machine Learning Forecasting, Real-Time Post Monitoring, Pre-Submission Title Intelligence, and Live Trend Analytics for Hacker News.**

[![Python 3.14](https://img.shields.io/badge/Python-3.14-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.6.1-F7931E?style=flat&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-6.0-646CFF?style=flat&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS v4](https://img.shields.io/badge/Tailwind_CSS-v4.0-06B6D4?style=flat&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Tests](https://img.shields.io/badge/Tests-66%20Passed-22C55E?style=flat&logo=pytest&logoColor=white)](https://pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📖 Table of Contents

- [🎯 Project Overview](#-project-overview)
- [✨ Key Capabilities & Workflows](#-key-capabilities--workflows)
- [🖥️ Modern React Frontend (`frontend/`)](#️-modern-react-frontend-frontend)
- [🧠 Machine Learning Model & Methodology](#-machine-learning-model--methodology)
- [📡 Bright Data Scraper & Ingestion Pipeline](#-bright-data-scraper--ingestion-pipeline)
- [🔌 FastAPI Endpoints Reference](#-fastapi-endpoints-reference)
- [🚀 Quickstart & Installation](#-quickstart--installation)
- [🧪 Testing & Quality Assurance](#-testing--quality-assurance)
- [📂 Repository Architecture](#-repository-architecture)
- [📜 License](#-license)

---

## 🎯 Project Overview

This project answers a central empirical question:
> *"How much can early engagement dynamics tell us about future Hacker News front-page reach, beyond the information already contained in early point totals alone?"*

It provides a production-ready, full-stack intelligence platform combining:
1. **ML Early-Signal Virality Classifier:** Trained on leakage-free temporal observation data predicting whether a story reaches the top 20% eventual engagement (Label B) within the first 15 minutes.
2. **Title Intelligence Engine (Pre-Submission):** Evaluates draft headlines using N-gram phrase extraction, structural signal scoring, and TF-IDF similarity against historically viral Hacker News posts.
3. **Live Post Monitor:** Live polling via public HN Firebase & Algolia APIs, computing point/comment velocities dynamically to stream $P(\text{viral})$ trajectories.
4. **Live Topic Intelligence Feeds:** Surfaces real-time trending keywords, domain leaderboards, and optimal posting times from continuous scraper snapshots.
5. **Modern Editorial Frontend:** A reactive, cinematic Vite + React SPA with scroll-driven parallax visuals, interactive charts, and real-time backend synchronization.

---

## ✨ Key Capabilities & Workflows

```
                                  ┌──────────────────────────────────────────────┐
                                  │      Virality Forensics Full-Stack           │
                                  └──────────────────────┬───────────────────────┘
                                                         │
                        ┌────────────────────────────────┼───────────────────────────────┐
                        ▼                                ▼                               ▼
            ┌──────────────────────┐         ┌──────────────────────┐        ┌──────────────────────┐
            │ 01. PRE-SUBMISSION   │         │ 02. POST-SUBMISSION  │        │ 03. LIVE INTELLIGENCE│
            │ Title Intelligence   │         │ Story Momentum Watch │        │ Topic & Domain Feeds │
            └──────────┬───────────┘         └──────────┬───────────┘        └──────────┬───────────┘
                       │                                │                               │
             TF-IDF Corpus Match              Real-Time Algolia/Firebase        Bright Data DCA Scraper
             Structural Scoring               Point/Comment Velocity            Hourly / Daily Trends
             Best Posting Window              Probability Trajectory            Domain Leaderboard
```

### 1. Title Intelligence Engine (`/title`)
* **N-Gram Keyphrase Extraction:** Analyzes multi-word phrases (bigrams/trigrams) against the successful-story corpus.
* **TF-IDF Cosine Similarity:** Retrieves the closest matching historical submissions with similarity percentages.
* **Structural Signal Scoring (0–10):** Evaluates character length sweet spots (34–67 chars), word count (5–11 words), colon value-prop structures, specific metrics/numbers, and `Show HN` / bracket tags (`[video]`, `[pdf]`).
* **Timing Recommendations:** Suggests optimal UTC hours and days of the week for maximum organic traction.

### 2. Live Story Momentum Monitor (`/monitor`)
* **Zero Configuration:** Input only the numeric Hacker News `story_id`.
* **Public HN API Integration:** Pulls live points, comments, publication timestamp, and rank approximation with zero API keys required.
* **Dynamic Velocity Derivation:** Automatically calculates point velocity ($\Delta\text{pts}/\Delta t$), comment velocity, and rank movement between successive requests.
* **Trajectory Tracking:** Categorizes momentum (Rising ↑, Stable →, Falling ↓) and plots the chronological probability curve with interactive Recharts.

### 3. Live Topic Intelligence & Feeds (`/trends`, `/overview`, `/research`)
* **Trending Keyphrases:** Real-time trending topics and multi-word terms on `/newest` weighted by velocity and points.
* **Domain Performance Leaderboard:** Ranks external domains by average peak points across collected historical stories.
* **Competitive Research:** Keyword search across recent raw captures to verify if similar submissions already ran.
* **Posting Window Heatmap:** Engagement distributions across 24 UTC hours and 7 days of the week.

---

## 🖥️ Modern React Frontend (`frontend/`)

The user interface is a dedicated **Vite + React 19 SPA** located in [`frontend/`](./frontend):

* **Editorial Design System:** High-contrast cream paper + dark ink surfaces, Oklch palettes, glassmorphism cards, and grain textures.
* **Cinematic Motion:** Scroll-expansion hero video (`fifnal-video.mp4`), GSAP + Lenis inertial scrolling, and Framer Motion reveals.
* **Typography:** Modern variable font pairing featuring *Archivo*, *Instrument Serif*, and *JetBrains Mono*.
* **State Management:** TanStack React Query with optimistic UI updates and auto-refetching.
* **Client-Side Routing:** TanStack Router across 7 distinct workflow pages (`/`, `/overview`, `/title`, `/monitor`, `/trends`, `/research`, `/system`).

---

## 🧠 Machine Learning Model & Methodology

### 1. Target Label Definitions
* **Label B (Primary / Benchmark):** Quota-based top-20% by eventual maximum points achieved ($\approx 19.0\%$ positive rate across common-horizon stories). Ties broken deterministically by `story_id` (0 label flips under reverse tie-breaking).
* **Label A (Secondary):** Actual observed crossover from `/newest` to `/front_page` (22 total crossover positives in the dataset).

### 2. Feature Engineering (12 Features)
All temporal features are constructed strictly backward-looking using `shift(1)` per story, guaranteeing **zero future-data leakage**:

| Feature Name | Type | Description |
| :--- | :--- | :--- |
| `early_points` | Integer | Total points at snapshot cutoff |
| `early_comments` | Integer | Total comments at snapshot cutoff |
| `early_rank` | Integer | Position on `/newest` at snapshot cutoff |
| `points_velocity` | Float | Points gained per hour since prior snapshot |
| `comments_velocity` | Float | Comments added per hour since prior snapshot |
| `rank_change` | Integer | Position improvement ($\text{prev\_rank} - \text{current\_rank}$) |
| `observation_count_early` | Integer | Number of scraper hits inside the cutoff window |
| `title_length` | Integer | Total character count |
| `title_word_count` | Integer | Total word count |
| `title_has_question_mark` | Binary | $1$ if `?` present, else $0$ |
| `title_has_number` | Binary | $1$ if numeric digits present, else $0$ |
| `engagement_ratio` | Float | Ratio of $\text{early\_comments} / \text{early\_points}$ |

### 3. Model Architecture & Pipeline
```
Raw Input Dict ──► SimpleImputer(strategy='median') ──► StandardScaler() ──► LogisticRegression(C=1.0, class_weight='balanced')
```

* **Why Logistic Regression?** Outperforms tree models on Precision-Recall AUC, exhibits low generalization gap (Train ROC-AUC `0.9255` vs CV `0.8996`), produces calibrated probabilities, and enables direct coefficient interpretability.
* **Evaluation Metric:** PR-AUC (Average Precision) prioritized over ROC-AUC due to class imbalance ($\approx 19\%$ positive rate).

### 4. Cross-Validation Performance (15-Minute Horizon)

| Model | CV ROC-AUC | ROC-AUC Std | CV PR-AUC | PR-AUC Std | Train ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Logistic Regression (Chosen)** | **0.8996** | **0.0324** | **0.8171** | **0.0321** | **0.9255** |
| Regularized Random Forest | 0.8986 | 0.0302 | 0.7942 | 0.0281 | 0.9669 |
| Regularized XGBoost | 0.8839 | 0.0419 | 0.8023 | 0.0369 | 0.9479 |
| Baseline (Points Only) | 0.8897 | 0.0410 | 0.7383 | 0.0504 | — |

*The full 12-feature model yields a **+0.0788 PR-AUC gain** over the points-only baseline at 15 minutes.*

### 5. Multi-Horizon Scaling

| Horizon | Stories | Positive Rate | Baseline PR-AUC | Full Model PR-AUC | Marginal Gain |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **15 min** | 469 | 18.98% | 0.7383 | **0.8171** | **+0.0788** |
| **30 min** | 469 | 18.98% | 0.8987 | **0.9189** | **+0.0202** |
| **60 min** | 469 | 18.98% | 0.9266 | **0.9413** | **+0.0147** |

---

## 📡 Bright Data Scraper & Ingestion Pipeline

Continuous background data collection is powered by **Bright Data Data Collector API (DCA)**, saving raw JSON snapshots under `data/raw/`:

| Collector Name | Bright Data Collector ID | Target URL | Polling Interval |
| :--- | :--- | :--- | :--- |
| **`newest`** | `c_msxgknap1ptjrrcetr` | `https://news.ycombinator.com/newest` | Every 8 minutes (`480s`) |
| **`front_page`** | `c_msxfwz2h1v0fxwlu83` | `https://news.ycombinator.com/` | Every 1 hour (`3600s`) |

* **State Tracking:** Managed via `data/.collector_state.json` ensuring zero duplicate processing.
* **Auto Ingestion (`src/ingest.py`):** Automatically back-calculates submission timestamps, cleans scraper artifacts, computes temporal velocity features, and updates processed CSV datasets.

---

## 🔌 FastAPI Endpoints Reference

All endpoints are hosted under `http://127.0.0.1:8000` and documented via Swagger UI at **`/docs`**.

### Title Intelligence (Pre-Submission)
* `POST /api/v1/score_title` — Evaluates a draft title, returning `pattern_score` (0–10), matched phrases, structural flags, similar stories, and recommended posting time.
* `POST /api/v1/refresh_corpus` — Rebuilds `title_corpus.json` and refits TF-IDF vectors from `all_observations.csv`.

### Live Post Monitor
* `GET /api/v1/monitor/{story_id}` — Polls real-time HN data, extracts velocity features, and returns $P(\text{viral})$.
* `GET /api/v1/monitor/{story_id}/history` — Returns chronological snapshot history and trajectory direction (rising ↑, stable →, falling ↓).
* `DELETE /api/v1/monitor/{story_id}/history` — Clears cached monitoring history for a story.

### Live Feeds & Trends
* `GET /api/v1/trending?hours=5&top_n=10` — Top keywords/topics weighted by frequency and points.
* `GET /api/v1/trending/domains?top_n=15` — Domain performance leaderboard ranked by historical average peak points.
* `GET /api/v1/trending/best_time` — Recommended posting day and UTC hour.
* `GET /api/v1/similar?topic=vector+db&hours=48` — Topic matching against recent captures.

### Core Model & System
* `POST /api/v1/predict` / `POST /api/v1/predict/{story_id}` — Direct 12-feature prediction ($P \ge 0.50$ default, $0.778$ F1-optimal).
* `POST /api/v1/batch_predict` — Batch scores up to 500 stories in a single request.
* `POST /api/v1/collect` — Triggers an asynchronous Bright Data collection job.
* `GET /health` — Liveness check and model verification.

---

## 🚀 Quickstart & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/jiyajain23/scraper-virality-forensics.git
cd scraper-virality-forensics
```

### 2. Set Up the Python Backend
```bash
# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the project root:
```env
# Optional: Required only if you want the automated Bright Data scraper running
BRIGHTDATA_API_TOKEN=your_brightdata_token_here

# Optional: Set an API key to protect routes in production (runs in dev mode if unset)
VIRALITY_API_KEY=your_secret_api_key_here
```

### 4. Start the FastAPI Backend
```bash
uvicorn api.main:app --reload --port 8000
```
* Backend API: **`http://127.0.0.1:8000`**
* Interactive Swagger Docs: **`http://127.0.0.1:8000/docs`**

### 5. Start the React Frontend
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
* Web Dashboard: **`http://localhost:5173/`**

---

## 🧪 Testing & Quality Assurance

Run the automated test suite with pytest:
```bash
pytest -v
```

**Test Coverage (66 Tests Total):**
* **API Tests (`tests/test_api.py`):** 21 tests covering health checks, single/batch prediction, threshold logic, missing value imputation, title intelligence scoring, feeds, and monitor endpoints.
* **Collector Tests (`tests/test_collector_sync.py`):** 45 tests covering configuration, authentication, HTTP trigger payloads, polling retry loops, rate limit handling, deduplication, and raw file integrity.

---

## 📂 Repository Architecture

```text
scraper-virality-forensics/
├── api/                                # FastAPI application & routers
│   ├── main.py                         # App factory, CORS, lifespan model loader & background scraper
│   ├── model.py                        # Singleton ViralityModel wrapper (with sklearn version bridge)
│   ├── schema.py                       # Pydantic request/response schemas
│   ├── router.py                       # Core prediction & collect endpoints
│   ├── title_router.py                 # Title intelligence scoring routes
│   ├── monitor_router.py               # Live story monitoring routes
│   └── feed_router.py                  # Live feeds, trends, domain rankings & best time
├── data/                               # Data storage & state
│   ├── .collector_state.json           # Scraper sync state & deduplication tracker
│   ├── raw/                            # Raw JSON snapshot captures
│   │   ├── newest/                     # Raw /newest captures
│   │   └── front_page/                 # Raw /front_page captures
│   ├── processed/                      # Normalized datasets & velocity features
│   │   ├── all_observations.csv        # Flattened observation records
│   │   ├── temporal_features.csv       # Extracted velocity features
│   │   └── story_id_overlap.csv        # Crossover tracking (newest -> front_page)
│   └── corpus/                         # Historical title corpus & TF-IDF vectors
├── frontend/                           # Modern Vite + React 19 Frontend SPA
│   ├── public/                         # Static assets (favicons, hero video)
│   ├── src/
│   │   ├── api/                        # Typed client API layer (fetch wrappers)
│   │   ├── assets/                     # Parallax images & graphics
│   │   ├── components/                 # UI, motion, intel, and site components
│   │   ├── hooks/                      # TanStack React Query hooks
│   │   ├── routes/                     # TanStack Router pages (all 7 workflows)
│   │   ├── styles.css                  # Editorial design system & Tailwind v4 tokens
│   │   └── main.tsx                    # Client SPA entrypoint
│   ├── package.json
│   └── vite.config.ts
├── model/                              # Trained ML artifacts & diagnostic reports
│   ├── features.json                   # Ordered 12-feature schema
│   ├── final_logistic_regression_15min.joblib  # Serialized scikit-learn Pipeline
│   ├── coefficient_stability_summary.csv       # Feature weights & stability metrics
│   └── horizon_cv_performance.csv              # Multi-horizon benchmark records
├── notebooks/                          # Research & experimental analysis
│   └── virality_forensics_notebook_v1.ipynb
├── src/                                # Core data science & ingestion modules
│   ├── collector_sync.py               # Bright Data DCA API client & polling worker
│   ├── ingest.py                       # Ingestion & normalization pipeline
│   ├── temporal_features.py            # Backward-looking velocity calculation
│   ├── title_intelligence.py           # N-gram extraction & TF-IDF similarity engine
│   └── live_feed.py                    # Real-time keyword & domain trend aggregators
├── tests/                              # Pytest test suite (66 tests)
│   ├── test_api.py
│   └── test_collector_sync.py
├── .gitignore
├── requirements.txt                    # Python dependencies
└── README.md                           # Project documentation
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.
