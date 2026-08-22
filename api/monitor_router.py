"""
monitor_router.py  —  Feature B: Post-Submission Live Monitor

Routes:
    GET /api/v1/monitor/{story_id}
    GET /api/v1/monitor/{story_id}/history
    DELETE /api/v1/monitor/{story_id}/history

Story data is fetched live from the public Algolia HN API.
Prediction snapshots are cached in data/monitor_cache/{story_id}.json.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from .model import get_model
from .router import _verify_api_key

log = logging.getLogger("virality.monitor_router")

MONITOR_CACHE_DIR = Path("data/monitor_cache")
MONITOR_CACHE_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(
    prefix="/api/v1",
    tags=["monitor"],
    dependencies=[Depends(_verify_api_key)],
)


# ---------------------------------------------------------------------------
# Snapshot cache helpers
# ---------------------------------------------------------------------------

def _cache_path(story_id: str) -> Path:
    return MONITOR_CACHE_DIR / f"{story_id}.json"


def _load_snapshots(story_id: str) -> list[dict]:
    p = _cache_path(story_id)
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_snapshot(story_id: str, snap: dict) -> None:
    snaps = _load_snapshots(story_id)
    snaps.append(snap)
    _cache_path(story_id).write_text(
        json.dumps(snaps, indent=2, default=str), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Feature derivation from live HN data
# ---------------------------------------------------------------------------

def _derive_features(
    current: dict,
    previous: Optional[dict],
    title: str,
) -> dict:
    """
    Derive the 12 model features from the current (and optionally previous)
    HN API snapshot.  Missing values default to None and are imputed by the pipeline.
    """
    pts  = current.get("points", 0) or 0
    cmts = current.get("comment_count", 0) or 0
    rank = current.get("estimated_rank")   # may be None

    # Velocities require a previous observation
    pts_vel  = None
    cmt_vel  = None
    rnk_chg  = None

    if previous:
        prev_pts  = previous.get("points",  0) or 0
        prev_cmts = previous.get("comment_count", 0) or 0
        prev_rank = previous.get("estimated_rank")
        age_diff_h = current.get("age_diff_hours")  # Use the current time delta

        if age_diff_h and age_diff_h > 0:
            pts_vel = round((pts - prev_pts) / age_diff_h, 4)
            cmt_vel = round((cmts - prev_cmts) / age_diff_h, 4)

        if rank is not None and prev_rank is not None:
            rnk_chg = prev_rank - rank  # positive = moved toward rank 1

    t = str(title) if title else ""
    obs_count = min(3.0, current.get("story_age_minutes", 0) / 8.0 + 1)

    return {
        "early_points":             float(pts),
        "early_comments":           float(cmts),
        "early_rank":               float(rank) if rank is not None else None,
        "points_velocity":          pts_vel,
        "comments_velocity":        cmt_vel,
        "rank_change":              float(rnk_chg) if rnk_chg is not None else None,
        "observation_count_early":  float(obs_count),
        "title_length":             float(len(t)),
        "title_word_count":         float(len(t.split())),
        "title_has_question_mark":  float("?" in t),
        "title_has_number":         float(any(c.isdigit() for c in t)),
        "engagement_ratio":         round(cmts / pts, 4) if pts > 0 else None,
    }


def _trend_label(snapshots: list[dict]) -> str:
    if len(snapshots) < 2:
        return "not enough data yet"
    probs = [s["p_viral"] for s in snapshots[-3:]]
    delta = probs[-1] - probs[0]
    if delta > 0.05:
        return "rising ↑"
    elif delta < -0.05:
        return "falling ↓"
    return "stable →"


def _percentile_message(p: float) -> str:
    if p >= 0.85:
        return "🔥 Exceptional trajectory — top 5% of stories at this age."
    elif p >= 0.70:
        return "🚀 Strong trajectory — top 25% of stories at this age."
    elif p >= 0.50:
        return "📈 Above average — keep engaging in the comments."
    elif p >= 0.30:
        return "⏳ Below average so far — early engagement is slower than typical front-page stories."
    return "📉 Very low engagement so far. Front-page is unlikely at current trajectory."


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/monitor/{story_id}",
    summary="Live virality monitor for a submitted HN story",
)
def monitor_story(
    story_id: str,
    model=Depends(get_model),
):
    """
    Fetches the current HN story data (points, comments, rank) from the
    public Algolia API, derives the model features, and returns the
    current P(viral) estimate.

    Call this endpoint every few minutes after submission to track your
    story's trajectory.  Each call is saved as a snapshot — use
    `GET /api/v1/monitor/{story_id}/history` to see the full trajectory.

    **story_id**: the numeric HN story ID (e.g. `49366792`)
    """
    from src.hn_api import fetch_story_with_rank

    story = fetch_story_with_rank(story_id)
    if story is None:
        raise HTTPException(
            status_code=404,
            detail=f"Story {story_id} not found on Algolia HN API. "
                   "Check the story_id or try again in a minute.",
        )

    age_min = story.get("story_age_minutes")
    if age_min is not None and age_min < 1:
        raise HTTPException(
            status_code=400,
            detail="Story was submitted less than 1 minute ago. "
                   "Wait a couple of minutes for initial engagement to register.",
        )

    # Previous snapshot for velocity calculation
    history = _load_snapshots(story_id)
    previous_snap = history[-1] if history else None

    # Compute age diff for velocity
    age_diff_h = None
    if previous_snap:
        prev_age_min = previous_snap.get("story_age_minutes")
        if prev_age_min is not None and age_min is not None:
            age_diff_h = (age_min - prev_age_min) / 60.0

    # Derive features
    story["age_diff_hours"] = age_diff_h
    features = _derive_features(story, previous_snap, story.get("title", ""))

    # Run model
    result = model.predict_one(features)
    p = result["p_viral"]

    prev_p = previous_snap.get("p_viral") if previous_snap else None
    prob_delta = round(p - prev_p, 4) if prev_p is not None else 0.0

    # Build snapshot to cache
    now_iso = datetime.now(timezone.utc).isoformat()
    snap = {
        "story_age_minutes": age_min,
        "age_minutes":       age_min,
        "points":            story.get("points", 0),
        "comment_count":     story.get("comment_count", 0),
        "num_comments":      story.get("comment_count", 0),
        "comments":          story.get("comment_count", 0),
        "estimated_rank":    story.get("estimated_rank"),
        "rank":              story.get("estimated_rank"),
        "approx_rank":       story.get("estimated_rank"),
        "p_viral":           p,
        "viral_probability": p,
        "probability":       p,
        "points_velocity":   features.get("points_velocity"),
        "comments_velocity": features.get("comments_velocity"),
        "rank_change":       features.get("rank_change"),
        "engagement_ratio":  features.get("engagement_ratio"),
        "observed_at":       now_iso,
        "timestamp":         now_iso,
        "time":              now_iso,
        "fetched_at":        now_iso,
    }
    _save_snapshot(story_id, snap)

    trend = _trend_label(_load_snapshots(story_id))
    message = _percentile_message(p)

    return {
        "story_id":              story_id,
        "title":                 story.get("title", ""),
        "url":                   story.get("url", ""),
        # Points & comments aliases
        "points":                story.get("points", 0),
        "current_points":        story.get("points", 0),
        "comments":              story.get("comment_count", 0),
        "num_comments":          story.get("comment_count", 0),
        "current_comments":      story.get("comment_count", 0),
        # Rank aliases
        "rank":                  story.get("estimated_rank"),
        "approx_rank":           story.get("estimated_rank"),
        "estimated_rank":        story.get("estimated_rank"),
        # Age
        "age_minutes":           age_min,
        "story_age_minutes":     age_min,
        # Probabilities
        "p_viral":               p,
        "viral_probability":     p,
        "probability":           p,
        "previous_probability":  prev_p,
        "probability_delta":     prob_delta,
        "delta":                 prob_delta,
        "prediction_default":    result["prediction_default"],
        "prediction_f1_optimal": result["prediction_f1_optimal"],
        # Trajectory
        "trajectory":            trend.replace(" ↑", "").replace(" ↓", "").replace(" →", ""),
        "trend":                 trend,
        "message":               message,
        # Velocities & features
        "points_velocity":       features.get("points_velocity"),
        "comments_velocity":     features.get("comments_velocity"),
        "rank_change":           features.get("rank_change"),
        "engagement_ratio":      features.get("engagement_ratio"),
        "features":              features,
        "features_used":         {k: v for k, v in features.items() if v is not None},
        "snapshots_recorded":    len(_load_snapshots(story_id)),
        "observed_at":           now_iso,
        "timestamp":             now_iso,
        "model_note": (
            "p_viral = P(top-20% engagement, Label B). "
            "Threshold 0.778 = F1-optimal. Threshold 0.50 = default. "
            "Model trained on 469 HN stories (15-min horizon)."
        ),
    }


@router.get(
    "/monitor/{story_id}/history",
    summary="Full prediction trajectory for a monitored story",
)
def monitor_history(story_id: str):
    """
    Returns all saved prediction snapshots for a story, showing how
    P(viral) evolved over time since first monitored.
    """
    history = _load_snapshots(story_id)
    if not history:
        raise HTTPException(
            status_code=404,
            detail=f"No history found for story {story_id}. "
                   "Call GET /api/v1/monitor/{story_id} first.",
        )
    return {
        "story_id":        story_id,
        "snapshots":       len(history),
        "count":           len(history),
        "first_seen":      history[0].get("fetched_at"),
        "last_seen":       history[-1].get("fetched_at"),
        "current_p_viral": history[-1].get("p_viral"),
        "trend":           _trend_label(history),
        "history":         history,
        "entries":         history,
    }


@router.delete(
    "/monitor/{story_id}/history",
    summary="Clear cached snapshots for a story",
    include_in_schema=True,
)
def clear_history(story_id: str):
    """Deletes the cached snapshot file for a story. Useful for testing."""
    p = _cache_path(story_id)
    if p.exists():
        p.unlink()
    return {"story_id": story_id, "status": "cleared"}
