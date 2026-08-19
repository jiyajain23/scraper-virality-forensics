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
