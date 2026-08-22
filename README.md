# Hacker News Virality Forensics

> Submitted to **ScrapeVerse** — the WeMakeDevs x Bright Data Hackathon.
> A full-stack intelligence platform that turns continuous web scraping into actionable content strategy for writers and developers who publish on Hacker News.
>
> **Live Application Dashboard:** [https://virality-forensics-frontend.onrender.com/](https://virality-forensics-frontend.onrender.com/)

[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.6.1-F7931E?style=flat&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![React 19](https://img.shields.io/badge/React-19.0-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev/)
[![Bright Data](https://img.shields.io/badge/Bright_Data-DCA_API-0099FF?style=flat)](https://brightdata.com/)
[![Tests](https://img.shields.io/badge/Tests-66_Passed-22C55E?style=flat&logo=pytest)](https://pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table of Contents

- [The Problem This Solves](#the-problem-this-solves)
- [How It Works — The Full Journey](#how-it-works--the-full-journey)
- [Bright Data Integration](#bright-data-integration)
- [The Four Workflows](#the-four-workflows)
- [Machine Learning Model](#machine-learning-model)
- [Frontend Dashboard](#frontend-dashboard)
- [API Reference](#api-reference)
- [Quickstart](#quickstart)
- [Testing](#testing)
- [Repository Structure](#repository-structure)
- [ScrapeVerse Hackathon](#scrapeverse-hackathon)
- [License](#license)

---

## The Problem This Solves

Every day, thousands of developers, researchers, and writers post on Hacker News hoping to reach the front page. Most never do — not because their content is poor, but because they posted at the wrong time, chose a title that did not match HN community conventions, or had no way to know their story was losing momentum before it was too late to engage.

The surface problem is content strategy. The deeper problem is information asymmetry: the platform sees all the signal; the author sees none of it until it is too late.

This project closes that gap. It continuously scrapes Hacker News using **Bright Data Scraper Studio**, ingests the raw data into a structured observation corpus, trains a machine learning classifier on temporal engagement signals, and surfaces the results through four distinct workflows in a production-ready web dashboard.

The system answers four questions a content creator actually asks:

1. **Before I post** — Is my title strong? Does it pattern-match against historically successful HN submissions?
2. **After I post** — Is my story gaining or losing momentum? What does the model think my probability of front-page reach is right now?
3. **Right now** — What topics and domains is the HN front page currently rewarding? What hour should I be posting?
4. **Competitive research** — Has someone already posted something like my idea? How did it perform?

---

## How It Works — The Full Journey

```
Bright Data Scraper Studio
         |
         |  DCA API  (POST /dca/trigger)
         |  Collector IDs: c_msxgknap1ptjrrcetr  (newest)
         |                 c_msxfwz2h1v0fxwlu83  (front_page)
         v
data/raw/newest/*.json          — raw HN /newest snapshots  (every 8 minutes)
data/raw/front_page/*.json      — raw HN front page snapshots  (every hour)
         |
         v
src/ingest.py                   — normalizes, deduplicates, back-calculates timestamps
         |
         v
data/processed/all_observations.csv   — the structured observation corpus
data/processed/temporal_features.csv — backward-looking velocity features
data/processed/title_corpus.json     — phrases and TF-IDF vectors from high-engagement titles
         |
         v
FastAPI Backend  (api/)         — ML inference, live HN polling, trend aggregation
         |
         v
React Frontend  (frontend/)     — four content-strategy workflows served as a SPA
```

The scraper runs as a background thread inside the FastAPI process. Each time a new snapshot arrives, `ingest.py` processes it, updates the CSVs, and the API endpoints serve the freshest data on the next request. There is no separate worker process, no message queue, and no database — the entire pipeline runs on flat files with an in-process scheduler.

---

## Bright Data Integration

Data collection is entirely powered by the **Bright Data Data Collector API (DCA)**.

### Collector Configuration

| Collector Name | Bright Data Collector ID | Target URL | Polling Interval |
| :--- | :--- | :--- | :--- |
| `newest` | `c_msxgknap1ptjrrcetr` | `https://news.ycombinator.com/newest` | Every 8 minutes |
| `front_page` | `c_msxfwz2h1v0fxwlu83` | `https://news.ycombinator.com/` | Every 1 hour |

### How a Collection Cycle Works

**1. Trigger**

```http
POST https://api.brightdata.com/dca/trigger
     ?collector=c_msxgknap1ptjrrcetr
     &queue_next=1

Body: [{"url": "https://news.ycombinator.com/newest"}]
Authorization: Bearer <BRIGHTDATA_API_TOKEN>
```

Bright Data returns a `collection_id` immediately (e.g. `j_mt4by5gjqbluomyha`). The scraper is now running on Bright Data's infrastructure.

**2. Poll for completion**

```http
GET https://api.brightdata.com/dca/dataset?id=j_mt4by5gjqbluomyha
Authorization: Bearer <BRIGHTDATA_API_TOKEN>
```

The application polls with exponential backoff until the dataset is ready.

**3. Download and save**

The completed dataset is saved as `data/raw/newest/api_j_mt4by5gjqbluomyha.json`. The file name embeds the Bright Data `collection_id` for full traceability. Each file contains a timestamped envelope:

```json
[
  {
    "scraped_at": "2026-08-22T12:03:57.072Z",
    "stories": [
      {
        "story_id": "49398857",
        "title": "Apple Papercuts Summer Edition",
        "story_url": "https://taoofmac.com/space/blog/2026/08/22/1147",
        "author": "rcarmo",
        "points": 1,
        "comment_count": 0,
        "rank": 1,
        "story_type": "story"
      }
    ]
  }
]
```

**4. Ingest**

`src/ingest.py` runs automatically after each collection cycle. It:
- Deduplicates story observations across overlapping snapshots
- Back-calculates submission timestamps from relative publication strings
- Computes temporal velocity features (`points_velocity`, `comments_velocity`, `rank_change`) using strict backward-looking `shift(1)` windows to prevent data leakage
- Appends to `data/processed/all_observations.csv`
- Rebuilds `title_corpus.json` and refits TF-IDF vectors

### Collector IDs in the Live API

The `/health` endpoint exposes the collector IDs directly so they are verifiable without reading source code:

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "model": "final_logistic_regression_15min.joblib",
  "version": "v1",
  "collectors": {
    "newest": "c_msxgknap1ptjrrcetr",
    "front_page": "c_msxfwz2h1v0fxwlu83"
  },
  "bright_data_trigger_url": "https://api.brightdata.com/dca/trigger"
}
```

### Triggering a Collection via the API

You can trigger a fresh scrape without touching the command line:

```bash
curl -X POST http://localhost:8000/api/v1/collect \
  -H "Content-Type: application/json" \
  -d '{"collector": "newest"}'
```

The endpoint fires the Bright Data job asynchronously and returns the `collection_id`. Ingestion runs in the background once the dataset is ready.

---

## The Four Workflows

### Workflow 1 — Title Intelligence (Before You Post)

A developer finishes writing a blog post and wants to submit it to Hacker News. They have a draft title. Before posting, they open the Title Intelligence page and paste the title.

The engine does three things:

**N-gram keyphrase extraction.** The title is tokenized into unigrams, bigrams, and trigrams. These are matched against a corpus of phrases extracted from the highest-engagement HN stories in the observation dataset. Matching multi-word phrases signal strong topic alignment; absent phrases suggest the title uses niche or uncommonly-searched phrasing.

**Structural signal scoring.** The system checks seven measurable structural properties derived from analysis of high-performing submissions: title character length (optimal 34–67 chars), word count (optimal 5–11 words), presence of a specific number or metric, colon-separated value proposition structure, `Show HN` or `Ask HN` prefix, bracket tags like `[pdf]` or `[video]`, and question format. Each property has a measurable prevalence rate in the top-quartile corpus. The result is a 0–10 pattern score.

**TF-IDF semantic similarity.** A `TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)` is fitted on the high-engagement title corpus. The input title is transformed and cosine similarity is computed against all corpus entries. The three closest matches are returned with similarity percentages and their original point totals — giving the author concrete reference points for how similar titles performed.

Additionally, the engine reads the `best_posting_time` analysis and recommends the specific UTC hour and day of week with historically highest average peak engagement.

**API:**
```
POST /api/v1/score_title
Body: {"title": "How I scaled a side project to 50k users without paid ads"}
```

---

### Workflow 2 — Live Story Monitor (After You Post)

A developer submits their story and now has 60 minutes to influence its trajectory through comment engagement and social sharing. The question is: is it working?

They open the Monitor page, paste the numeric HN story ID, and the system starts live polling.

On each poll, the system:
1. Fetches current points, comments, and approximate rank from the public Algolia HN API
2. Compares against the previous cached snapshot to compute `points_velocity` and `comments_velocity`
3. Feeds the 12-feature vector into the trained logistic regression pipeline
4. Returns `P(viral)` — the estimated probability the story reaches the top 20% of eventual engagement

The result is a live number that updates every 15 seconds. A probability of 0.70 at 8 minutes post-submission means the story is in the top 25% of stories at this age in the training set. A probability of 0.20 falling means it is losing ground relative to front-page trajectories.

The monitor stores each snapshot locally. After two or more snapshots, a probability trajectory chart renders — a time series of the model's confidence as the story ages. This is the core diagnostic: not just "what is my score" but "which direction is it moving and how fast."

**API:**
```
GET /api/v1/monitor/{story_id}
GET /api/v1/monitor/{story_id}/history
```

---

### Workflow 3 — Topic Intelligence and Trends

A writer planning next week's post wants to know what subjects the HN community is currently engaging with, which domains consistently produce high-performing content, and the best time to post.

The Trends page pulls three aggregations computed from the raw scraped data:

**Trending keyphrases.** All stories scraped in the last N hours (configurable: 5h, 12h, 24h, 48h) are tokenized. Phrases are scored by a combination of story count and total points. Multi-word phrases are boosted because they represent more specific, actionable topics than single-word terms. The result is a ranked list of the exact phrases that are generating engagement right now.

**Domain leaderboard.** Using the full `all_observations.csv` corpus, domains are ranked by their average peak points across all observed stories. Only domains with at least two stories in the corpus are included to filter noise. This shows which publishers and sites have the strongest track record of HN engagement.

**Posting window.** Stories in the top 25% by peak engagement are filtered, and their submission times are aggregated by UTC hour and day of week. The result is a concrete recommendation: post on Tuesday between 14:00 and 15:00 UTC, for example — not a generic "post in the morning" advice, but a data-derived window from actual HN outcomes.

**API:**
```
GET /api/v1/trending?hours=5&top_n=10
GET /api/v1/trending/domains?top_n=15
GET /api/v1/trending/best_time
```

---

### Workflow 4 — Competitive Research

Before writing a post, a developer wants to know if this story has already been told on HN and how it performed.

They enter a topic on the Research page. The system searches all raw snapshots from the last 12–72 hours (configurable) for stories whose titles share keyword overlap with the query. Results are returned sorted by peak points, showing the author whether the space is already saturated, which angle performed best, and how much engagement the topic drove.

**API:**
```
GET /api/v1/similar?topic=vector+database&hours=48
```

---

## Machine Learning Model

### Target Definition

**Label B** (primary): Whether a story reaches the top 20% of eventual peak points among stories observed across the same horizon window. Approximately 19% positive rate. This is a quota-based label — the model predicts relative competitive rank, not an absolute engagement threshold.

### Feature Engineering (12 Features)

All temporal features are constructed with strict backward-looking `shift(1)` per story, ensuring zero future-data leakage:

| Feature | Type | Description |
| :--- | :--- | :--- |
| `early_points` | Integer | Total points at snapshot cutoff |
| `early_comments` | Integer | Total comments at snapshot cutoff |
| `early_rank` | Integer | Position on /newest at snapshot cutoff |
| `points_velocity` | Float | Points gained per hour since prior snapshot |
| `comments_velocity` | Float | Comments added per hour since prior snapshot |
| `rank_change` | Integer | Position improvement (prev_rank - current_rank) |
| `observation_count_early` | Integer | Number of scraper hits inside the cutoff window |
| `title_length` | Integer | Character count |
| `title_word_count` | Integer | Word count |
| `title_has_question_mark` | Binary | 1 if ? present |
| `title_has_number` | Binary | 1 if digits present |
| `engagement_ratio` | Float | early_comments / early_points |

### Pipeline

```
Raw Input Dict
  -> SimpleImputer(strategy='median')
  -> StandardScaler()
  -> LogisticRegression(C=1.0, class_weight='balanced')
```

Logistic regression was selected over tree-based alternatives because it: outperforms on Precision-Recall AUC for this imbalanced task, exhibits a low generalization gap (Train ROC-AUC 0.9255 vs CV 0.8996), produces calibrated probabilities suitable for a live probability display, and yields directly interpretable coefficients.

### Cross-Validation Performance (15-Minute Horizon)

| Model | CV ROC-AUC | CV PR-AUC | Train ROC-AUC |
| :--- | :---: | :---: | :---: |
| **Logistic Regression (chosen)** | **0.8996** | **0.8171** | **0.9255** |
| Regularized Random Forest | 0.8986 | 0.7942 | 0.9669 |
| Regularized XGBoost | 0.8839 | 0.8023 | 0.9479 |
| Baseline (points only) | 0.8897 | 0.7383 | — |

The full 12-feature model delivers a +0.0788 PR-AUC gain over the points-only baseline at 15 minutes, confirming that velocity and structural signals carry meaningful predictive information beyond raw point totals.

### Multi-Horizon Scaling

| Horizon | Positive Rate | Baseline PR-AUC | Full Model PR-AUC | Gain |
| :---: | :---: | :---: | :---: | :---: |
| 15 min | 18.98% | 0.7383 | **0.8171** | +0.0788 |
| 30 min | 18.98% | 0.8987 | **0.9189** | +0.0202 |
| 60 min | 18.98% | 0.9266 | **0.9413** | +0.0147 |

The gain is largest at 15 minutes precisely because that is the window where velocity features carry the most information relative to accumulated points — early-signal dynamics are most predictive before the crowd has settled.

---

## Frontend Dashboard

The frontend is a Vite + React 19 single-page application located in `frontend/`. It communicates exclusively with the FastAPI backend — no data is computed or fabricated in the browser.

**Pages:**

| Route | Workflow |
| :--- | :--- |
| `/` | Landing — project introduction |
| `/overview` | Live pulse — trending topics and recommended posting window |
| `/title` | Title intelligence — pre-submission scoring |
| `/monitor` | Live story momentum tracking |
| `/trends` | Full topic, domain, and timing intelligence |
| `/research` | Competitive topic research |
| `/system` | API health, collector IDs, and manual collection trigger |

---

## API Reference

All endpoints are under `http://localhost:8000` and documented via Swagger UI at `/docs`.

**Authentication:** All routes accept an optional `X-API-Key` header. If `VIRALITY_API_KEY` is not set in the environment, the API runs in developer mode and accepts all requests.

### System

| Method | Path | Description |
| :--- | :--- | :--- |
| GET | `/health` | Liveness check, model status, and collector IDs |
| POST | `/api/v1/collect` | Trigger a Bright Data collection job |

### Title Intelligence

| Method | Path | Description |
| :--- | :--- | :--- |
| POST | `/api/v1/score_title` | Score a draft title (pattern score, flags, similar stories, posting window) |
| POST | `/api/v1/refresh_corpus` | Rebuild title corpus and TF-IDF vectors from latest ingested data |

### Live Monitor

| Method | Path | Description |
| :--- | :--- | :--- |
| GET | `/api/v1/monitor/{story_id}` | Live P(viral) snapshot with velocity features |
| GET | `/api/v1/monitor/{story_id}/history` | Full prediction trajectory history |
| DELETE | `/api/v1/monitor/{story_id}/history` | Clear cached snapshot history |

### Topic Intelligence and Feeds

| Method | Path | Description |
| :--- | :--- | :--- |
| GET | `/api/v1/trending` | Top trending keyphrases (params: hours, top_n) |
| GET | `/api/v1/trending/domains` | Domain performance leaderboard |
| GET | `/api/v1/trending/best_time` | Recommended posting day and UTC hour |
| GET | `/api/v1/similar` | Topic search across recent captures (params: topic, hours) |

### Core Prediction

| Method | Path | Description |
| :--- | :--- | :--- |
| POST | `/api/v1/predict` | Single story prediction from raw feature dict |
| POST | `/api/v1/predict/{story_id}` | Single prediction with story_id echoed in response |
| POST | `/api/v1/batch_predict` | Batch prediction up to 500 stories per request |

---

## Quickstart

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Bright Data account with the two Scraper Studio collectors configured (IDs above)

### 1. Clone

```bash
git clone https://github.com/jiyajain23/scraper-virality-forensics.git
cd scraper-virality-forensics
```

### 2. Python Backend

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Environment Variables

Create `.env` in the project root:

```env
# Required for automated Bright Data scraping
BRIGHTDATA_API_TOKEN=your_brightdata_api_token

# Optional: protect API routes in production (leave unset for dev mode)
VIRALITY_API_KEY=your_secret_key
```

### 4. Start the API

```bash
uvicorn api.main:app --reload --port 8000
```

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

- Dashboard: `http://localhost:5173`

### 6. Trigger Your First Scrape

```bash
# Via CLI
python -m src.collector_sync --once --collector newest --ingest

# Via API
curl -X POST http://localhost:8000/api/v1/collect \
  -H "Content-Type: application/json" \
  -d '{"collector": "newest"}'
```

### Deployed on Render

The project ships with a `render.yaml` blueprint. Deploy in one click:

1. Fork this repository
2. Connect it to Render via the Blueprint dashboard
3. Set `BRIGHTDATA_API_TOKEN` in the Render environment dashboard
4. Both the API service and the static frontend site deploy automatically

Live deployments:
- Frontend Client: [https://virality-forensics-frontend.onrender.com/](https://virality-forensics-frontend.onrender.com/)
- Backend API Endpoint: [https://virality-forensics-api.onrender.com](https://virality-forensics-api.onrender.com)

---

## Testing

```bash
pytest -v
```

66 tests across two suites:

**`tests/test_api.py` — 21 tests**
Health checks, single and batch prediction, threshold logic, missing value imputation, title intelligence scoring, feed endpoints, and monitor endpoints.

**`tests/test_collector_sync.py` — 45 tests**
Collector configuration, authentication headers, HTTP trigger payload structure, polling retry loops, exponential backoff, rate limit handling, deduplication logic, and raw file integrity.

---

## Repository Structure

```
scraper-virality-forensics/
├── api/
│   ├── main.py                  # App factory, CORS, lifespan model loader, background scraper thread
│   ├── model.py                 # Singleton ViralityModel wrapper
│   ├── schema.py                # Pydantic request and response schemas
│   ├── router.py                # Core prediction and collect endpoints
│   ├── title_router.py          # Title intelligence routes
│   ├── monitor_router.py        # Live story monitoring routes
│   └── feed_router.py           # Trending, domains, best time, similar stories
├── data/
│   ├── .collector_state.json    # Scraper sync state and deduplication tracker
│   ├── raw/
│   │   ├── newest/              # Raw /newest captures (named by Bright Data collection_id)
│   │   └── front_page/          # Raw front page captures
│   └── processed/
│       ├── all_observations.csv # Flattened observation corpus
│       ├── temporal_features.csv
│       ├── story_id_overlap.csv
│       └── title_corpus.json    # TF-IDF corpus for title intelligence
├── frontend/
│   └── src/
│       ├── api/                 # Typed fetch wrappers
│       ├── components/          # UI, motion, and intel components
│       ├── hooks/               # TanStack Query data hooks
│       ├── routes/              # All seven workflow pages
│       └── types/api.ts         # TypeScript mirrors of backend schemas
├── model/
│   ├── features.json
│   ├── final_logistic_regression_15min.joblib
│   ├── coefficient_stability_summary.csv
│   └── horizon_cv_performance.csv
├── notebooks/
│   └── virality_forensics_notebook_v1.ipynb
├── src/
│   ├── collector_sync.py        # Bright Data DCA API client and polling worker
│   ├── ingest.py                # Ingestion and normalization pipeline
│   ├── temporal_features.py     # Backward-looking velocity feature calculation
│   ├── title_intelligence.py    # N-gram extraction and TF-IDF similarity engine
│   └── live_feed.py             # Real-time keyword, domain, and timing aggregators
├── tests/
│   ├── test_api.py
│   └── test_collector_sync.py
├── render.yaml                  # Render blueprint for one-click deployment
├── requirements.txt
└── README.md
```

---

## ScrapeVerse Hackathon

This project was built for **ScrapeVerse**, the WeMakeDevs x Bright Data Hackathon.

### What the Hackathon Required

ScrapeVerse asks participants to build a project that uses **Bright Data Scraper Studio** as its data source, with a full downstream pipeline that transforms scraped data into something meaningfully useful. The evaluation criteria are:

- **Functionality and pipeline depth** — does scraped data flow into a real analytical or machine learning application?
- **UI and presentation** — is there a frontend that demonstrates the value of the data?
- **Code quality and documentation** — is the project understandable and reproducible?
- **Creativity of use case** — does the project solve a genuine problem?

### How This Project Meets Those Requirements

**Scraper Studio integration.** Two production collectors are configured in Bright Data Scraper Studio — one targeting `news.ycombinator.com/newest` (collector ID `c_msxgknap1ptjrrcetr`) and one targeting the front page (collector ID `c_msxfwz2h1v0fxwlu83`). Both trigger via the DCA API, poll for completion, and download structured JSON datasets automatically.

**End-to-end pipeline.** Raw JSON files flow through an ingestion layer that normalizes timestamps, deduplicates observations, computes backward-looking velocity features, and builds a structured CSV corpus. That corpus trains a scikit-learn logistic regression classifier and powers four separate API-backed analytical workflows.

**Genuine use case.** Content creators publishing technical writing on Hacker News face a real information problem. This platform addresses it directly — before, during, and after publication — using only data that Bright Data's scrapers make available.

**Full-stack implementation.** The project ships a production FastAPI backend with 15 endpoints, a Vite + React SPA with seven workflow pages, 66 automated tests, a Render deployment blueprint, and this documentation.

### Hackathon Submission Details

- **Collector IDs:** `c_msxgknap1ptjrrcetr` (newest), `c_msxfwz2h1v0fxwlu83` (front_page)
- **Live via health endpoint:** `GET /health` returns both IDs in the response body
- **Raw data sample:** `data/raw/newest/` — each file name contains the Bright Data `collection_id`

---

## License

Distributed under the MIT License. See `LICENSE` for details.
