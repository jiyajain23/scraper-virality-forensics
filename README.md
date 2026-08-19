# Virality Forensics -- Data Pipeline

This is the **data pipeline stage only**. No model, no label, no SHAP, no
Streamlit yet. The goal here is a clean, leak-free, temporal dataset built
from Bright Data Scraper Studio snapshots of Hacker News.

## Project structure

```
data/
  raw/
    front_page/   <- JSON snapshots of https://news.ycombinator.com/
    newest/       <- JSON snapshots of https://news.ycombinator.com/newest
  processed/
    all_observations.csv      one row per (story_id, scraped_at) observation
    temporal_features.csv     backward-looking deltas/velocities per story
    story_id_overlap.csv      story_ids seen in both collectors

src/
  ingest.py               orchestrates loading -> cleaning -> saving
  temporal_features.py    raw, leak-free temporal feature computation
  analysis.py             dataset diagnostics / readiness report
```

## Running it

```bash
pip install -r requirements.txt
python -m src.ingest
```

Drop new raw JSON snapshot files into `data/raw/front_page/` or
`data/raw/newest/` (any filename, loaded recursively) and rerun the same
command -- it's idempotent and safe to rerun as more snapshots accumulate.

## What this stage deliberately does NOT do

- No "viral" / "high-growth" label. That requires enough accumulated data to
  choose a defensible threshold, and is a separate, later step.
- No feature is computed using information from *after* the observation's
  own `scraped_at` timestamp. All temporal features
  (`points_velocity`, `rank_change`, etc.) look only at the immediately
  preceding observation of the same story, never forward.
- No modeling, no SHAP, no dashboard.

## Known data quirks handled here

- **Phantom `bigbox` row**: both scrapers emit one row per snapshot with
  `story_id == "bigbox"` that duplicates whatever is at rank 1 but with
  hardcoded zero points/comments. This is filtered out during flattening.
  (The better long-term fix is tightening the Scraper Studio field
  description so this row is never extracted in the first place --
  see project notes.)
- **Relative timestamps**: `publication_time` (newest) and `time`
  (front_page-style fallback) arrive as strings like `"8 minutes ago"`.
  These are parsed into `age_hours` and combined with each observation's
  own `scraped_at` to back-calculate `submission_time_est`. Consistency of
  `submission_time_est` across repeated observations of the same story is
  checked automatically and flagged if it drifts more than 10 minutes.
- **Schema variation**: field names have varied slightly between the two
  collectors in practice (`points`/`score`, `comment_count`/`comments`,
  `publication_time`/`time`). The loader checks for both rather than
  assuming one schema.

## Next stage (not yet built)

Once there's enough `newest -> front_page` overlap (see
`story_id_overlap.csv` and the readiness assessment printed at the end of
each run), the next step is defining the high-growth label from the
*distribution* of outcomes actually observed, then training a baseline
model on `temporal_features.csv` restricted to each story's early
observations only.

---

## Automated Future Collection (`src/collector_sync.py`)

### Setup

```bash
pip install -r requirements.txt

# Copy the example env file and add your token
cp .env.example .env

# Export for the current shell (do NOT commit .env)
# macOS / Linux:
export BRIGHTDATA_API_TOKEN=your_token_here
# Windows PowerShell:
$env:BRIGHTDATA_API_TOKEN = "your_token_here"
```

### Run one /newest collection

```bash
python -m src.collector_sync --once --collector newest
```

### Run one front-page collection

```bash
python -m src.collector_sync --once --collector front_page
```

### Run both collectors once

```bash
python -m src.collector_sync --once
```

### Run with automatic ingestion

```bash
python -m src.collector_sync --once --ingest
```

Triggers the collector, downloads results to `data/raw/`, then immediately
runs `python -m src.ingest` to update `data/processed/`.

### 8-minute /newest polling

```bash
python -m src.collector_sync --poll --interval 480 --collector newest
```

### Hourly front-page polling

```bash
python -m src.collector_sync --poll --interval 3600 --collector front_page
```

Press **Ctrl+C** to stop gracefully (finishes the current cycle first).

### State and deduplication

`data/.collector_state.json` tracks every triggered collection ID.

- Each collection is downloaded **exactly once** — safe to restart.
- Failed jobs are marked but not auto-retried; re-run the command.
- The token is **never** stored in the state file.

### Raw output format

```
data/raw/newest/api_<collection_id>.json
data/raw/front_page/api_<collection_id>.json
```

Files are ingest-compatible: `scraped_at` + `stories` at the top level,
matching the existing historical snapshot format.
Historical files (no `api_` prefix) are **never modified or deleted**.

### Tests

```bash
python -m pytest tests/test_collector_sync.py -v
```

All tests use mocked HTTP responses — no Bright Data credits consumed.

### Collector IDs

| Collector | ID | Target URL |
|---|---|---|
| newest | `c_msxgknap1ptjrrcetr` | `https://news.ycombinator.com/newest` |
| front_page | `c_msxfwz2h1v0fxwlu83` | `https://news.ycombinator.com/` |
