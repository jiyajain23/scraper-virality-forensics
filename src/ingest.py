"""
ingest.py

Loads raw Bright Data Scraper Studio JSON snapshots (front_page + newest),
flattens them into one row per story-observation, cleans/parses fields,
and writes a combined observation-level dataset.

This module does NOT compute temporal deltas (see temporal_features.py)
and does NOT compute any label / target variable. It only produces a
clean, deduplicated, leak-free base dataset: one row per
(story_id, scraped_at) observation.

Run as:
    python -m src.ingest
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from src.temporal_features import compute_temporal_features
from src.analysis import run_diagnostics

RAW_DIR = Path("data/raw")
FRONT_PAGE_DIR = RAW_DIR / "front_page"
NEWEST_DIR = RAW_DIR / "newest"
PROCESSED_DIR = Path("data/processed")

ALL_OBSERVATIONS_PATH = PROCESSED_DIR / "all_observations.csv"
TEMPORAL_FEATURES_PATH = PROCESSED_DIR / "temporal_features.csv"
STORY_OVERLAP_PATH = PROCESSED_DIR / "story_id_overlap.csv"

# Known phantom / non-story rows produced by the scraper's pinned/highlighted
# slot at the top of the page. This is not a real story observation and is
# always dropped.
PHANTOM_STORY_IDS = {"bigbox"}

RELATIVE_AGE_PATTERN = re.compile(
    r"^\s*(\d+)\s+(minute|minutes|hour|hours|day|days)\s+ago\s*$", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

@dataclass
class RawFile:
    path: Path
    source_scraper: str  # "front_page" or "newest"


def discover_raw_files() -> list[RawFile]:
    """Recursively find all JSON files under the two raw data directories."""
    files: list[RawFile] = []
    for path in sorted(FRONT_PAGE_DIR.rglob("*.json")):
        files.append(RawFile(path=path, source_scraper="front_page"))
    for path in sorted(NEWEST_DIR.rglob("*.json")):
        files.append(RawFile(path=path, source_scraper="newest"))
    return files


def load_snapshot_json(path: Path) -> list[dict]:
    """
    Load a single JSON file and normalize it into a list of "snapshot" dicts,
    each shaped like {"scraped_at": ..., "stories": [...]}.

    Bright Data Scraper Studio has been observed to return:
      (a) a top-level list containing one snapshot dict, e.g.
          [{"scraped_at": "...", "stories": [...], "input": {...}}]
      (b) a single snapshot dict directly, e.g.
          {"scraped_at": "...", "stories": [...]}

    We do not assume the structure; we inspect it and normalize both cases
    into a list of snapshot dicts.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        snapshots = data
    elif isinstance(data, dict):
        snapshots = [data]
    else:
        raise ValueError(f"Unrecognized top-level JSON structure in {path}: {type(data)}")

    normalized = []
    for snap in snapshots:
        if not isinstance(snap, dict):
            raise ValueError(f"Unrecognized snapshot structure in {path}: {type(snap)}")
        if "stories" not in snap:
            raise ValueError(f"Snapshot in {path} is missing a 'stories' key: keys={list(snap.keys())}")
        if "scraped_at" not in snap:
            raise ValueError(f"Snapshot in {path} is missing a 'scraped_at' key: keys={list(snap.keys())}")
        normalized.append(snap)

    return normalized


# ---------------------------------------------------------------------------
# Flattening
# ---------------------------------------------------------------------------

KEEP_FIELDS = [
    "story_id",
    "title",
    "story_url",
    "author",
    "publication_time",
    "points",
    "comment_count",
    "rank",
    "story_type",
]


def flatten_raw_file(raw_file: RawFile) -> list[dict]:
    """Flatten one raw JSON file into a list of row dicts (one per story observation)."""
    snapshots = load_snapshot_json(raw_file.path)
    rows: list[dict] = []

    for snapshot in snapshots:
        scraped_at = snapshot["scraped_at"]
        stories = snapshot["stories"]

        if not isinstance(stories, list):
            raise ValueError(
                f"'stories' is not a list in {raw_file.path} "
                f"(got {type(stories)}) — cannot flatten."
            )

        for story in stories:
            story_id = story.get("story_id")

            if story_id in PHANTOM_STORY_IDS:
                continue

            # Front-page snapshots use "points"/"comment_count" too in our
            # samples, but some Bright Data configs may use "comments"/"time"
            # instead. Handle both without assuming a single schema.
            points_raw = story.get("points", story.get("score"))
            comments_raw = story.get("comment_count", story.get("comments"))
            age_raw = story.get("publication_time", story.get("time"))

            row = {
                "story_id": story_id,
                "title": story.get("title"),
                "story_url": story.get("story_url", story.get("url")),
                "author": story.get("author"),
                "publication_time_raw": age_raw,
                "points_raw": points_raw,
                "comment_count_raw": comments_raw,
                "rank_raw": story.get("rank"),
                "story_type": story.get("story_type"),
                "scraped_at_raw": scraped_at,
                "source_scraper": raw_file.source_scraper,
                "source_file": raw_file.path.name,
            }
            rows.append(row)

    return rows


def load_all_raw_files() -> tuple[pd.DataFrame, int]:
    """Load and flatten every raw JSON file. Returns (dataframe, num_files_loaded)."""
    raw_files = discover_raw_files()
    all_rows: list[dict] = []

    for raw_file in raw_files:
        try:
            all_rows.extend(flatten_raw_file(raw_file))
        except ValueError as e:
            print(f"[WARN] Skipping unreadable file {raw_file.path}: {e}")

    df = pd.DataFrame(all_rows)
    return df, len(raw_files)


# ---------------------------------------------------------------------------
# Cleaning / parsing
# ---------------------------------------------------------------------------

def to_numeric_safe(series: pd.Series) -> pd.Series:
    """Coerce a series (possibly strings with commas, or already numeric) to numeric, NaN on failure."""
    if series.dtype == object:
        series = series.astype(str).str.replace(",", "", regex=False)
        series = series.replace({"None": None, "none": None, "": None, "nan": None})
    return pd.to_numeric(series, errors="coerce")


def parse_relative_age_hours(age_str: Optional[str]) -> Optional[float]:
    """
    Convert a Hacker-News-style relative age string ("8 minutes ago",
    "1 hour ago", "2 days ago") into a float number of hours.

    Returns None for missing/unparseable input rather than raising, since
    this runs over scraped web data where malformed values are expected.
    """
    if not age_str or not isinstance(age_str, str):
        return None

    match = RELATIVE_AGE_PATTERN.match(age_str)
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2).lower()

    if unit.startswith("minute"):
        return value / 60.0
    if unit.startswith("hour"):
        return float(value)
    if unit.startswith("day"):
        return float(value * 24)

    return None  # pragma: no cover — unreachable given the regex alternation


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply type conversion, timestamp parsing, and submission_time derivation."""
    df = df.copy()

    df["points"] = to_numeric_safe(df["points_raw"])
    df["comment_count"] = to_numeric_safe(df["comment_count_raw"])
    df["rank"] = to_numeric_safe(df["rank_raw"])

    df["scraped_at"] = pd.to_datetime(df["scraped_at_raw"], utc=True, errors="coerce")

    df["age_hours"] = df["publication_time_raw"].apply(parse_relative_age_hours)

    # submission_time = scraped_at - age_hours. This should be stable for a
    # given story_id across multiple snapshots; large drift signals a parse
    # error or (rarely) a story_id collision, and is flagged in diagnostics
    # rather than silently trusted.
    df["submission_time_est"] = df.apply(
        lambda r: (r["scraped_at"] - pd.Timedelta(hours=r["age_hours"]))
        if pd.notna(r["scraped_at"]) and pd.notna(r["age_hours"])
        else pd.NaT,
        axis=1,
    )

    df = df.drop(
        columns=[
            "points_raw",
            "comment_count_raw",
            "rank_raw",
            "publication_time_raw",
            "scraped_at_raw",
        ]
    )

    return df


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop only EXACT duplicate observations: same story_id at the same
    scraped_at timestamp (e.g. if a snapshot file was accidentally uploaded
    twice, or the same collector run got saved under two filenames).

    Repeated observations of the same story_id at DIFFERENT scraped_at
    timestamps are the entire point of this dataset and are always kept.
    """
    before = len(df)
    df = df.drop_duplicates(subset=["story_id", "scraped_at", "source_scraper"], keep="first")
    after = len(df)
    if before != after:
        print(f"[INFO] Dropped {before - after} exact duplicate observations.")
    return df


def sort_dataset(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(["story_id", "scraped_at"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_df, num_files = load_all_raw_files()
    if raw_df.empty:
        print("[ERROR] No observations were loaded. Check data/raw/front_page and data/raw/newest.")
        return

    df = clean_dataframe(raw_df)
    df = deduplicate(df)
    df = sort_dataset(df)

    df.to_csv(ALL_OBSERVATIONS_PATH, index=False)

    temporal_df = compute_temporal_features(df)
    temporal_df.to_csv(TEMPORAL_FEATURES_PATH, index=False)

    run_diagnostics(
        df=df,
        temporal_df=temporal_df,
        num_files=num_files,
        overlap_output_path=STORY_OVERLAP_PATH,
    )


if __name__ == "__main__":
    main()
