# Hacker News Virality Forensics & Content Intelligence API

> **Predictive ML forecasting, real-time post monitoring, and pre-submission title intelligence for Hacker News.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.6.1-orange.svg)](https://scikit-learn.org/)
[![Tests](https://img.shields.io/badge/pytest-66%20passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-purple.svg)]()

---

## 📖 Table of Contents

1. [Project Overview](#-project-overview)
2. [Key Features & Capabilities](#-key-features--capabilities)
3. [Machine Learning Model & Methodology](#-machine-learning-model--methodology)
4. [Data Pipeline & Bright Data Scrapers](#-data-pipeline--bright-data-scrapers)
5. [FastAPI Endpoints Reference](#-fastapi-endpoints-reference)
6. [Installation & Setup](#-installation--setup)
7. [Running the Application](#-running-the-application)
8. [Testing & Quality Assurance](#-testing--quality-assurance)
9. [Repository Structure](#-repository-structure)

---

## 🎯 Project Overview

This project answers a central empirical question:  
**"How much can early engagement dynamics tell us about future Hacker News front-page reach, beyond the information already contained in early point totals alone?"**

It provides a production-ready **FastAPI** service combining:
- **ML Early-Signal Virality Classifier:** Trained on leakage-free temporal observation data at 15, 30, and 60-minute prediction windows.
- **Title Intelligence Engine (Pre-Submission):** Evaluates draft titles using N-gram extraction, structural conventions, and **TF-IDF cosine similarity** against historical top-performing stories.
- **Live Post-Submission Monitor:** Real-time polling via public Algolia HN APIs, calculating point/comment velocities dynamically to stream $P(\text{viral})$ trajectories.
- **Live Topic Intelligence Feeds:** Surfaces real-time trending keywords/phrases, domain performance leaderboards, and optimal posting times from continuous scraper snapshots.

---

## ⚡ Key Features & Capabilities

### 🟢 1. Title Intelligence Engine (Pre-Submission)
Helps writers, bloggers, and founders optimize headlines before posting:
- **N-Gram Keyphrase Extraction:** Analyzes multi-word phrases (bigrams/trigrams) against high-performing HN posts.
- **TF-IDF Cosine Similarity:** Retrieves the closest matching successful stories from the corpus with similarity percentages.
- **Structural Convention Scoring ($0–10$):** Evaluates character length sweet spots (34–67 chars), word count (5–11 words), colon value-prop structures, specific metrics/numbers, and `Show HN` / bracket tags (`[video]`, `[pdf]`).
- **Timing Guidance:** Recommends the highest-engagement UTC hours and days of the week based on corpus outcomes.

### 🔵 2. Post-Submission Live Monitor
Tracks live submissions after posting:
- **Zero Configuration:** Input only the numeric `story_id`.
- **Live Algolia API Integration:** Fetches points, comments, publication time, and rank approximation with zero credentials required.
- **Dynamic Feature Derivation:** Automatically calculates point velocity ($\Delta \text{pts} / \Delta t$), comment velocity, and rank movement between successive requests.
- **Trajectory Categorization:** Streams predictions with status labels (`rising ↑`, `stable →`, `falling ↓`) and saves chronological snapshot histories.

### 🟡 3. Live Topic Intelligence & Feeds
Continuous market research from active scraper captures:
- **Trending Keyphrases:** Real-time trending topics and multi-word terms on `/newest` weighted by velocity and points.
- **Domain Performance Leaderboard:** Ranks domains by average peak points across all collected historical stories.
- **Similar Stories Search:** Searches recent raw captures for competitive topic research.
- **Best Posting Time Heatmap:** Historical engagement distributions by hour (UTC) and day of week.

---

## 🧠 Machine Learning Model & Methodology

### 1. Label Construction
- **Label B (Primary / Benchmark):** Quota-based top-20% by eventual maximum points achieved ($\approx 19.0\%$ positive rate across common-horizon stories). Ties broken deterministically by `story_id` (sensitivity checks confirmed $0$ label flips under reverse tie-breaking).
- **Label A (Secondary):** Actual observed crossover from `/newest` to `/front_page` ($22$ total crossover positives in the dataset). Used for directional sanity checks with bootstrap confidence intervals ($90\%\text{ CI: } [0.101, 0.420]$).

### 2. Feature Engineering (12 Features)
All temporal features are constructed strictly backward-looking using `shift(1)` per story, guaranteeing zero future-data leakage:
1. `early_points`: Total points at snapshot cutoff.
2. `early_comments`: Total comments at snapshot cutoff.
3. `early_rank`: Position on `/newest` at snapshot cutoff.
4. `points_velocity`: Points gained per hour since prior snapshot.
5. `comments_velocity`: Comments added per hour since prior snapshot.
6. `rank_change`: Position improvement ($\text{prev\_rank} - \text{current\_rank}$).
7. `observation_count_early`: Number of scraper hits inside the cutoff window.
8. `title_length`: Total character count.
9. `title_word_count`: Total word count.
10. `title_has_question_mark`: Binary flag for `?`.
11. `title_has_number`: Binary flag for numeric digits.
12. `engagement_ratio`: $\text{early\_comments} / \text{early\_points}$.

### 3. Model Architecture & Pipeline
The selected headline model is a scikit-learn `Pipeline`:
$$\text{SimpleImputer(strategy='median')} \longrightarrow \text{StandardScaler()} \longrightarrow \text{LogisticRegression(C=1.0, class\_weight='balanced')}$$

- **Why Logistic Regression?** Outperforms tree models on Precision-Recall AUC, exhibits low generalization gap (Train ROC-AUC $0.9255$ vs CV $0.8996$), produces stable calibrated probabilities, and enables direct coefficient interpretability.
- **Primary Evaluation Metric:** **PR-AUC (Average Precision)** is prioritized over ROC-AUC due to class imbalance ($\approx 19\%$ positive rate).

### 4. Cross-Validation Performance (15-Minute Horizon)

| Model | CV ROC-AUC | ROC-AUC Std | CV PR-AUC | PR-AUC Std | Train ROC-AUC |
|---|---|---|---|---|---|
| **Logistic Regression (Chosen)** | **0.8996** | **0.0324** | **0.8171** | **0.0321** | **0.9255** |
| Regularized Random Forest | 0.8986 | 0.0302 | 0.7942 | 0.0281 | 0.9669 |
| Regularized XGBoost | 0.8839 | 0.0419 | 0.8023 | 0.0369 | 0.9479 |
| Baseline (Early Points Only) | 0.8897 | 0.0410 | 0.7383 | 0.0504 | — |

*Full 12-feature model yields a **+0.0788 PR-AUC gain** over the points-only baseline at 15 minutes.*

### 5. Multi-Horizon Scaling

| Horizon | Stories | Positive Rate | Baseline PR-AUC | Full Model PR-AUC | Marginal Gain |
|---|---|---|---|---|---|
| **15 min** | 469 | 18.98% | 0.7383 | **0.8171** | +0.0788 |
| **30 min** | 469 | 18.98% | 0.8987 | **0.9189** | +0.0202 |
| **60 min** | 469 | 18.98% | 0.9266 | **0.9413** | +0.0147 |

### 6. Operating Thresholds

| Use Case | Threshold | Precision | Recall | Expected Behavior |
|---|---|---|---|---|
| **High-Precision Alerting** | `0.80 – 0.85` | $\approx 0.88+$ | Lower | Minimizes false positives; surfaces only high-conviction virals. |
| **Balanced (F1-Optimal)** | `0.778` | **0.875** | **0.636** | Optimal F1-score balance on held-out evaluations. |
| **High-Recall Screening** | `0.50` (Default) | $0.490$ | $0.770$ | Maximizes discovery of potential virals; tolerates false alarms. |
| **Feed Ranking** | Continuous | — | — | Use raw $P(\text{viral})$ directly as a sort key. |

---

## 📡 Data Pipeline & Bright Data Scrapers

Continuous collection is powered by Bright Data Web Scrapers, storing raw JSON snapshots under `data/raw/`.

### Collector Profiles

| Collector Name | Bright Data Collector ID | Target URL | Polling Cadence |
|---|---|---|---|
| `newest` | `c_msxgknap1ptjrrcetr` | `https://news.ycombinator.com/newest` | 480 seconds (8 min) |
| `front_page` | `c_msxfwz2h1v0fxwlu83` | `https://news.ycombinator.com/` | 3600 seconds (1 hour) |

### Collector Sync Architecture (`src/collector_sync.py`)
- **Deduplication:** State tracked in `data/.collector_state.json`. Every collection ID is processed and saved exactly once.
- **Resilient Polling:** Automatically handles in-progress states (`building`, `collecting`, HTTP 202/429 rate limits with exponential backoff).
- **Format Normalization:** Ingests dictionary (`scraped_at` + `stories`) and list shapes, outputting `data/raw/<collector>/api_<collection_id>.json`.

### Ingestion Pipeline (`src/ingest.py`)
1. **Flattening & Deduplication:** Removes scraper artifacts (e.g. phantom pinned row `bigbox`).
2. **Timestamp Back-Calculation:** Parses relative strings (`"8 minutes ago"`) into `age_hours` and back-calculates `submission_time_est`. Flags drift $> 10$ minutes.
3. **Temporal Feature Generation (`src/temporal_features.py`):** Computes per-story point/comment velocities and rank shifts across consecutive scrapes.
4. **Outputs:**
   - `data/processed/all_observations.csv` (1 row per story observation)
   - `data/processed/temporal_features.csv` (features computed across all snapshots)
   - `data/processed/story_id_overlap.csv` (crossover stories between `/newest` and `/front_page`)

---

## 🔌 FastAPI Endpoints Reference

All endpoints are prefixed with `/api/v1` and support optional `X-API-Key` authentication.

### Title Intelligence (Pre-Submission)
- **`POST /api/v1/score_title`**
  - **Body:** `{"title": "Show HN: Fast open-source vector database built in Rust"}`
  - **Response:** `pattern_score` ($0–10$), matched n-gram phrases, actionable structural flags, similar successful stories with match percentages, and best posting time.
- **`POST /api/v1/refresh_corpus`**
  - Rebuilds `title_corpus.json` cache and re-fits TF-IDF vectors from `all_observations.csv`.

### Live Story Monitor (Post-Submission)
- **`GET /api/v1/monitor/{story_id}`**
  - Fetches real-time story data from Algolia HN API, derives features on the fly, and computes $P(\text{viral})$.
- **`GET /api/v1/monitor/{story_id}/history`**
  - Returns chronological prediction history and trend direction (`rising ↑`, `stable →`, `falling ↓`).
- **`DELETE /api/v1/monitor/{story_id}/history`**
  - Clears cached monitoring snapshots for a story.

### Live Feeds & Trends
- **`GET /api/v1/trending?hours=5&top_n=10`**
  - Top trending keyphrases/topics on `/newest` weighted by activity and points.
- **`GET /api/v1/trending/domains?top_n=15`**
  - Domain performance leaderboard ranked by historical average peak points.
- **`GET /api/v1/trending/best_time`**
  - Optimal posting day and UTC hour derived from high-engagement distributions.
- **`GET /api/v1/similar?topic=vector+database&hours=48`**
  - Competitive topic research matching recent raw captures.

### Core Model & System
- **`POST /api/v1/predict`** / **`POST /api/v1/predict/{story_id}`**
  - Direct 12-feature prediction at the 15-minute horizon.
- **`POST /api/v1/batch_predict`**
  - Batch score up to 500 stories in a single request.
- **`POST /api/v1/collect`**
  - Trigger an on-demand Bright Data scraper run. This triggers the scrape asynchronously and automatically queues a background task in FastAPI to poll, download, save, and ingest the scraped data into your local folders when ready.
- **`GET /health`**
  - Liveness check, model artifact verification, and auth status.

---

## 💻 Installation & Setup

### 1. Clone & Environment Setup
```bash
git clone https://github.com/jiyajain23/scraper-virality-forensics.git
cd scraper-virality-forensics

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux / macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file from `.env.example`:
```ini
# Required only for triggering Bright Data scrapers
BRIGHTDATA_API_TOKEN=your_brightdata_token_here

# Optional: Set an API key to protect /api/v1/* routes (if unset, runs in dev mode)
VIRALITY_API_KEY=your_secret_api_key_here
```

---

## 🚀 Running the Application

### Start the FastAPI Server
```bash
uvicorn api.main:app --reload --port 8000
```
- **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Automated Background Scraper
The background scraper is **fully integrated into the FastAPI backend lifecycle**. 
When you start the FastAPI server, it automatically spawns a background thread that polls Bright Data for `/newest` (every 8 minutes) and `/front_page` (every 1 hour), downloading and ingesting the data automatically. 

*(Make sure your `BRIGHTDATA_API_TOKEN` is set in your `.env` or system environment for this to run).*

### Run the Background Data Collector Manually (Optional CLI)
If you want to run the collector or ingestion manually from the CLI without running the API server:
```bash
# Run one-off collection for newest
python -m src.collector_sync --once --collector newest

# Run continuous 8-minute polling manually
python -m src.collector_sync --poll --interval 480 --collector newest --ingest
```

### Refresh Processed Data Manually
```bash
python -m src.ingest
```

---

## 🧪 Testing & Quality Assurance

Run the comprehensive unit, integration, and API test suite:

```bash
pytest -v
```

### Test Breakdown (66 Total Tests):
- **API Tests (`tests/test_api.py`):** 21 tests covering health checks, single/batch prediction, threshold logic, missing value median imputation, Title Intelligence scoring, corpus rebuilds, live feeds, and mock Algolia monitor endpoints.
- **Collector Tests (`tests/test_collector_sync.py`):** 45 tests covering configuration, authentication, HTTP trigger payloads, polling retry loops, rate limit handling, deduplication, state persistence, and raw file integrity.

---

## 📂 Repository Structure

```
scraper-virality-forensics/
├── api/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app factory, CORS, lifespan model loader
│   ├── model.py                 # Singleton ML pipeline wrapper
│   ├── schema.py                # Pydantic request / response models
│   ├── router.py                # Core ML inference & /collect endpoints
│   ├── title_router.py          # Feature A: /score_title, /refresh_corpus
│   ├── monitor_router.py        # Feature B: /monitor/{story_id}, /history
│   └── feed_router.py           # Feature C: /trending, /domains, /best_time, /similar
├── data/
│   ├── .collector_state.json    # Deduplication and sync state tracker
│   ├── raw/
│   │   ├── newest/              # Raw /newest scraper snapshots
│   │   └── front_page/          # Raw /front_page scraper snapshots
│   ├── processed/
│   │   ├── all_observations.csv # Flattened observation rows
│   │   ├── temporal_features.csv# Derived backward-looking velocities
│   │   ├── story_id_overlap.csv # /newest -> /front_page crossovers
│   │   └── title_corpus.json    # Cached corpus stats and TF-IDF vectors
│   └── monitor_cache/           # Per-story live monitor snapshot history
├── figures/                     # 11 Exploratory Data Analysis figures
├── model/
│   ├── features.json            # Ordered 12-feature list
│   ├── final_logistic_regression_15min.joblib # Serialized scikit-learn Pipeline
│   ├── horizon_cv_performance.csv
│   ├── coefficient_stability_summary.csv
│   └── shap_vs_coef_importance.csv
├── notebooks/
│   └── virality_forensics_notebook_v1.ipynb # Full research & experimental notebook
├── src/
│   ├── collector_sync.py        # Bright Data API client & polling daemon
│   ├── ingest.py                # Raw JSON parsing & clean dataset builder
│   ├── temporal_features.py     # Leakage-free velocity computation
│   ├── analysis.py              # Diagnostics, overlap & consistency checks
│   ├── title_intelligence.py    # N-gram & TF-IDF title scoring engine
│   ├── hn_api.py                # Algolia public HN API client
│   ├── live_feed.py             # Feed aggregation over raw snapshots
│   └── eda.py                   # Plotting utilities for figures/
├── tests/
│   ├── test_api.py              # FastAPI test suite (21 tests)
│   └── test_collector_sync.py   # Collector sync test suite (45 tests)
├── .env.example
├── .gitignore
├── requirements.txt             # Pinned project dependencies (scikit-learn 1.6.1)
└── README.md
```

---

## 📜 License
This project is open-source and available under the [MIT License](LICENSE).
