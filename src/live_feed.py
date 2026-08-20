"""
live_feed.py

Real-time aggregation over already-collected raw scrape files.
No BrightData API calls — reads only data/raw/ and data/processed/.

Provides:
    trending_keywords()   — top keywords by recent story activity
    domain_leaderboard()  — domains ranked by avg peak points
    best_posting_time()   — hourly / daily heatmap from historical data
    similar_stories()     — recent stories matching a topic keyword
    recent_snapshot()     — flat list of stories seen in the last N hours
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import pandas as pd

RAW_DIR       = Path("data/raw")
NEWEST_DIR    = RAW_DIR / "newest"
FP_DIR        = RAW_DIR / "front_page"
PROCESSED_DIR = Path("data/processed")
OBS_CSV       = PROCESSED_DIR / "all_observations.csv"

# ---------------------------------------------------------------------------
# Stop-words for keyword extraction
# ---------------------------------------------------------------------------

_STOP = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "is","are","was","were","be","been","has","have","had","do","does","did",
    "i","my","we","our","you","your","its","it","this","that","these","those",
    "from","by","as","up","how","what","why","when","who","which","use","using",
    "can","will","new","get","make","show","hn","ask","launch","tell",
    "about","than","more","into","after","over","also","just","not","no",
    "vs","via","—","-",":","|","all","some","one","two","three","first","second",
    "every","find","part","way","itself","own","may","could","would","should",
    "like","good","bad","best","simple","easy","better","world","today",
}

_WORD_RE = re.compile(r"[A-Za-z0-9+#\.\-]{2,}")


def _extract_keywords(title: str) -> list[str]:
    """
    Extract meaningful keyphrases (bigrams, trigrams) and domain unigrams
    from a title. Filters out noise and generic filler words.
    """
    if not title:
        return []
    # Strip prefix like Show HN:
    clean = re.sub(r"^(show hn|ask hn|launch hn)\s*[:\-]?\s*", "", str(title), flags=re.I)
    raw_words = _WORD_RE.findall(clean)
    words = [w.lower().strip(".,:;()[]\"'") for w in raw_words]
    words = [w for w in words if w and len(w) >= 2]

    phrases: list[str] = []

    # 1. Multi-word phrases (bigrams & trigrams)
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i+1]
        if w1 not in _STOP and w2 not in _STOP and not w1.isdigit() and not w2.isdigit():
            phrases.append(f"{w1} {w2}")

    for i in range(len(words) - 2):
        w1, w2, w3 = words[i], words[i+1], words[i+2]
        if w1 not in _STOP and w3 not in _STOP and not (w1.isdigit() and w3.isdigit()):
            phrases.append(f"{w1} {w2} {w3}")

    # 2. Salient unigrams (strong tech, product, or topic words)
    for w in words:
        if w not in _STOP and len(w) >= 4 and not w.isdigit():
            phrases.append(w)

    return list(set(phrases))


# ---------------------------------------------------------------------------
# Raw file reader — loads all JSON files from a directory, newest-first
# ---------------------------------------------------------------------------

def _load_raw_files(
    directory: Path,
    max_age_hours: float = 24.0,
) -> list[dict]:
    """
    Load story dicts from all JSON snapshot files in *directory*.
    Each file is `[{"scraped_at": ..., "stories": [...]}]` or `{"scraped_at": ..., "stories": [...]}`.
    Returns a flat list of story dicts, each augmented with `scraped_at` (datetime).
    Correctly sorts files by the actual scraped_at timestamp.
    """
    parsed_files: list[tuple[datetime, list[dict], str]] = []
    for path in directory.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
            envelope = payload[0] if isinstance(payload, list) else payload
            ts_str = envelope.get("scraped_at", "")
            if not ts_str:
                continue
            ts = datetime.fromisoformat(ts_str.rstrip("Z")).replace(tzinfo=timezone.utc)
            stories = envelope.get("stories", [])
            if isinstance(stories, list):
                parsed_files.append((ts, stories, path.name))
        except Exception:
            continue

    if not parsed_files:
        return []

    # Sort descending by timestamp
    parsed_files.sort(key=lambda x: x[0], reverse=True)

    # Reference time: either current time or latest available scrape timestamp
    now = datetime.now(timezone.utc)
    latest_ts = parsed_files[0][0]
    # If the latest scrape is older than 2 hours from now, anchor to latest_ts
    ref_time = now if (now - latest_ts).total_seconds() < 7200 else latest_ts
    cutoff = ref_time - timedelta(hours=max_age_hours)

    records: list[dict] = []
    for ts, stories, filename in parsed_files:
        if ts < cutoff:
            continue
        for story in stories:
            if isinstance(story, dict):
                s = dict(story)
                s["_scraped_at"] = ts
                s["_source_file"] = filename
                records.append(s)

    return records


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def recent_snapshot(max_age_hours: float = 2.0) -> list[dict]:
    """
    Return all story records scraped from /newest in the last `max_age_hours`.
    Each record has keys: story_id, title, story_url, author, points,
    comment_count, rank, story_type, _scraped_at.
    """
    return _load_raw_files(NEWEST_DIR, max_age_hours=max_age_hours)


def trending_keywords(
    max_age_hours: float = 2.0,
    top_n: int = 10,
) -> list[dict]:
    """
    Top `top_n` keywords from recent /newest stories, weighted by max points
    seen across scrapes within the window.  Returns list of dicts:
        {keyword, story_count, total_points, top_story_title, top_story_url}
    """
    records = recent_snapshot(max_age_hours=max_age_hours)
    if not records:
        return []

    # Aggregate max points per story_id
    story_pts: dict[str, int] = {}
    story_meta: dict[str, dict] = {}
    for r in records:
        sid = r.get("story_id", "")
        pts = int(r.get("points") or 0)
        if pts > story_pts.get(sid, -1):
            story_pts[sid] = pts
            story_meta[sid] = r

    # Map keyword → list of (story_id, points, title, url)
    kw_stories: dict[str, list[tuple]] = defaultdict(list)
    for sid, meta in story_meta.items():
        title = meta.get("title") or ""
        for kw in set(_extract_keywords(title)):
            kw_stories[kw].append((sid, story_pts[sid], title, meta.get("story_url", "")))

    results = []
    for kw, entries in kw_stories.items():
        if len(entries) < 1:
            continue
        best = max(entries, key=lambda x: x[1])
        is_multi = " " in kw
        total_pts = sum(e[1] for e in entries)
        # Give a boost to multi-word phrases so compound topics surface above lone tokens
        score = (len(entries) * (1.6 if is_multi else 1.0), total_pts)
        results.append({
            "keyword":          kw,
            "is_phrase":        is_multi,
            "story_count":      len(entries),
            "total_points":     total_pts,
            "avg_points":       round(total_pts / len(entries), 1),
            "top_story_title":  best[2],
            "top_story_url":    best[3],
            "_score":           score,
        })

    results.sort(key=lambda x: x["_score"], reverse=True)
    # Strip internal sort key
    for r in results:
        del r["_score"]
    return results[:top_n]


@lru_cache(maxsize=16)
def domain_leaderboard(top_n: int = 15) -> list[dict]:
    """
    Domains ranked by average peak points, using all_observations.csv.
    Returns list of dicts: {domain, story_count, avg_peak_points, max_points, top_title}
    """
    if not OBS_CSV.exists():
        return []

    obs = pd.read_csv(OBS_CSV, dtype={"story_id": str})
    obs["domain"] = obs["story_url"].apply(
        lambda u: urlparse(str(u)).netloc.replace("www.", "") if pd.notna(u) else ""
    )
    obs = obs[obs["domain"] != ""]

    peak = obs.groupby(["story_id", "domain"])["points"].max().reset_index()
    peak.columns = ["story_id", "domain", "peak_points"]

    # Join title
    titles = obs.groupby("story_id")["title"].first().reset_index()
    peak = peak.merge(titles, on="story_id", how="left")

    stats = peak.groupby("domain").agg(
        story_count=("story_id", "nunique"),
        avg_peak_points=("peak_points", "mean"),
        max_points=("peak_points", "max"),
    ).reset_index()

    # Keep only domains with ≥2 stories
    stats = stats[stats["story_count"] >= 2].copy()
    stats["avg_peak_points"] = stats["avg_peak_points"].round(1)

    # Attach top story title for each domain
    top_story = (
        peak.sort_values("peak_points", ascending=False)
        .groupby("domain")["title"].first()
        .reset_index()
        .rename(columns={"title": "top_story_title"})
    )
    stats = stats.merge(top_story, on="domain", how="left")

    stats = stats.sort_values("avg_peak_points", ascending=False).head(top_n)
    return stats.to_dict(orient="records")


@lru_cache(maxsize=1)
def best_posting_time() -> dict:
    """
    Analyses submission_time_est for high-engagement stories (top-25% by peak points)
    to find the best hour and day to post.

    Returns:
        {
          "hourly":  [{hour_utc: 0..23, avg_points, story_count}, ...],
          "daily":   [{day: "Monday".., avg_points, story_count}, ...],
          "recommendation": {"best_hour_utc": N, "best_day": "...", "note": "..."},
          "data_note": "Based on N stories from DATE to DATE"
        }
    """
    if not OBS_CSV.exists():
        return {}

    obs = pd.read_csv(OBS_CSV, parse_dates=["scraped_at", "submission_time_est"],
                      dtype={"story_id": str})
    obs = obs.dropna(subset=["submission_time_est"])

    # Ensure UTC
    for col in ("scraped_at", "submission_time_est"):
        if obs[col].dt.tz is None:
            obs[col] = obs[col].dt.tz_localize("UTC")
        else:
            obs[col] = obs[col].dt.tz_convert("UTC")

    # Peak points per story
    peak = obs.groupby("story_id").agg(
        peak_points=("points", "max"),
        submission_time=("submission_time_est", "first"),
    ).reset_index()

    threshold = peak["peak_points"].quantile(0.75)
    high = peak[peak["peak_points"] >= threshold].copy()

    high["hour"] = high["submission_time"].dt.hour
    high["day"]  = high["submission_time"].dt.day_name()

    hourly = (
        high.groupby("hour")["peak_points"]
        .agg(avg_points="mean", story_count="count")
        .reset_index()
        .rename(columns={"hour": "hour_utc"})
    )
    hourly["avg_points"] = hourly["avg_points"].round(1)
    hourly = hourly.sort_values("hour_utc").to_dict(orient="records")

    day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    daily = (
        high.groupby("day")["peak_points"]
        .agg(avg_points="mean", story_count="count")
        .reset_index()
    )
    daily["avg_points"] = daily["avg_points"].round(1)
    daily["_order"] = daily["day"].map({d: i for i, d in enumerate(day_order)})
    daily = daily.sort_values("_order").drop("_order", axis=1).to_dict(orient="records")

    # Best single hour / day
    if hourly:
        best_hour = max(hourly, key=lambda x: x["avg_points"])["hour_utc"]
    else:
        best_hour = None

    if daily:
        best_day = max(daily, key=lambda x: x["avg_points"])["day"]
    else:
        best_day = None

    date_min = obs["scraped_at"].min().date().isoformat()
    date_max = obs["scraped_at"].max().date().isoformat()

    return {
        "hourly":  hourly,
        "daily":   daily,
        "recommendation": {
            "best_hour_utc": best_hour,
            "best_day":      best_day,
            "note": (
                f"Post around {best_hour:02d}:00 UTC on {best_day} for the highest "
                f"average engagement in the corpus."
            ) if best_hour is not None and best_day is not None else "Insufficient data.",
        },
        "data_note": (
            f"Based on {len(peak)} stories ({int(threshold)}+ points = top 25%) "
            f"collected {date_min} to {date_max}."
        ),
    }


def similar_stories(
    topic: str,
    max_age_hours: float = 48.0,
    top_n: int = 10,
) -> list[dict]:
    """
    Find recent /newest stories whose title contains any word from `topic`.
    Returns stories sorted by peak points descending.
    """
    if not topic or not topic.strip():
        return []

    topic_keywords = set(_extract_keywords(topic))
    if not topic_keywords:
        return []

    records = _load_raw_files(NEWEST_DIR, max_age_hours=max_age_hours)
    records += _load_raw_files(FP_DIR, max_age_hours=max_age_hours)

    # Deduplicate: keep highest-points snapshot per story_id
    best: dict[str, dict] = {}
    for r in records:
        sid = r.get("story_id", "")
        pts = int(r.get("points") or 0)
        if pts > int((best.get(sid) or {}).get("points") or -1):
            best[sid] = r

    results = []
    for sid, r in best.items():
        title = r.get("title") or ""
        title_kws = set(_extract_keywords(title))
        if topic_keywords & title_kws:
            results.append({
                "story_id":    sid,
                "title":       title,
                "story_url":   r.get("story_url", ""),
                "author":      r.get("author", ""),
                "points":      int(r.get("points") or 0),
                "comment_count": int(r.get("comment_count") or 0),
                "scraped_at":  r["_scraped_at"].isoformat(),
                "matched_keywords": sorted(topic_keywords & title_kws),
            })

    results.sort(key=lambda x: x["points"], reverse=True)
    return results[:top_n]
