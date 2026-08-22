"""
feed_router.py  —  Feature C: Live Topic Intelligence

Routes:
    GET /api/v1/trending
    GET /api/v1/trending/domains
    GET /api/v1/trending/best_time
    GET /api/v1/similar
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from .router import _verify_api_key

log = logging.getLogger("virality.feed_router")

router = APIRouter(
    prefix="/api/v1",
    tags=["live-feed"],
    dependencies=[Depends(_verify_api_key)],
)


@router.get(
    "/trending",
    summary="Top trending keywords on HN /newest right now",
)
def trending_keywords(
    hours: float = Query(default=2.0, ge=0.5, le=48.0,
                         description="Look-back window in hours"),
    top_n: int   = Query(default=10, ge=1, le=30,
                         description="Number of keywords to return"),
):
    """
    Returns the top keywords from recent /newest stories, weighted by points
    and story count.  Uses already-collected raw snapshot files — no new API call.
    """
    from src.live_feed import trending_keywords as _trending
    raw_results = _trending(max_age_hours=hours, top_n=top_n)

    # Format items with frontend aliases
    topics = []
    for t in raw_results:
        item = dict(t)
        item["topic"] = t["keyword"]
        item["phrase"] = t["keyword"]
        item["score"] = t["total_points"]
        item["count"] = t["story_count"]
        item["points"] = t["total_points"]
        topics.append(item)

    return {
        "window_hours": hours,
        "hours": hours,
        "count": len(topics),
        "topics": topics,
        "trending": topics,
        "note": "Based on locally collected /newest snapshots. Refresh by running collector_sync.",
    }


@router.get(
    "/trending/domains",
    summary="Domain performance leaderboard",
)
def domain_leaderboard(
    top_n: int = Query(default=15, ge=1, le=50,
                       description="Number of domains to return"),
):
    """
    Domains ranked by average peak points across all collected stories.
    Only domains with ≥2 stories in the corpus are included.
    """
    from src.live_feed import domain_leaderboard as _domains
    raw_results = _domains(top_n=top_n)
    domains = []
    for d in raw_results:
        item = dict(d)
        item["avg_points"] = d.get("avg_peak_points")
        item["count"] = d.get("story_count")
        domains.append(item)

    return {
        "count": len(domains),
        "domains": domains,
        "note": "Average peak points per domain across the full collected corpus.",
    }


@router.get(
    "/trending/best_time",
    summary="Best time to post on HN based on historical data",
)
def best_posting_time():
    """
    Analyses submission times of high-engagement stories (top-25% by peak points)
    to identify the best hour (UTC) and day of week to post.
    """
    from src.live_feed import best_posting_time as _best_time
    raw = _best_time()
    if not raw:
        raise HTTPException(status_code=503, detail="Processed data not available. Run src.ingest first.")

    # Build aliases WITHOUT mutating the lru_cache dict
    original_rec = raw.get("recommendation", {})
    rec_obj = {
        "day":        original_rec.get("best_day"),
        "day_of_week": original_rec.get("best_day"),
        "hour":       original_rec.get("best_hour_utc"),
        "hour_utc":   original_rec.get("best_hour_utc"),
        "avg_points": None,  # filled below if available
        "note":       original_rec.get("note"),
    }

    # Enrich rec_obj.avg_points from hourly data
    hourly = raw.get("hourly", [])
    if rec_obj["hour_utc"] is not None:
        for h in hourly:
            if h.get("hour_utc") == rec_obj["hour_utc"]:
                rec_obj["avg_points"] = h.get("avg_points")
                break

    # Normalise hourly slots: each item → {day_label, hour_utc, hour, avg_points, story_count}
    # (Frontend PostingWindow reads slot.day and slot.hour)
    hourly_slots = [
        {
            "hour_utc":    h.get("hour_utc"),
            "hour":        h.get("hour_utc"),
            "day":         f"{h.get('hour_utc', 0):02d}:00 UTC",
            "avg_points":  h.get("avg_points"),
            "story_count": h.get("story_count"),
        }
        for h in hourly
    ]

    # Normalise daily slots: each item → {day, day_of_week, avg_points, story_count}
    daily_slots = [
        {
            "day":         d.get("day"),
            "day_of_week": d.get("day"),
            "avg_points":  d.get("avg_points"),
            "story_count": d.get("story_count"),
        }
        for d in raw.get("daily", [])
    ]

    return {
        "hourly":             hourly,
        "daily":              raw.get("daily", []),
        "data_note":          raw.get("data_note", ""),
        # Frontend-compatible aliases
        "best_window":        rec_obj,
        "recommended_window": rec_obj,
        "recommendation":     rec_obj,
        # slots for the timeline grid (show daily by default, fall back to hourly)
        "slots":   daily_slots if daily_slots else hourly_slots,
        "by_day":  daily_slots,
        "by_hour": hourly_slots,
    }


@router.get(
    "/similar",
    summary="Find recent HN stories similar to your topic",
)
def similar_stories(
    topic: str  = Query(..., description="Topic or keywords to search for"),
    hours: float = Query(default=48.0, ge=1.0, le=168.0,
                         description="How far back to search (hours)"),
    top_n: int   = Query(default=10, ge=1, le=30),
):
    """
    Returns recent /newest (and /front_page) stories whose titles contain
    any keyword from your topic query.  Useful for competitive research
    before you submit your own post.
    """
    if not topic or not topic.strip():
        raise HTTPException(status_code=422, detail="topic must be a non-empty string")

    from src.live_feed import similar_stories as _similar
    raw_results = _similar(topic=topic, max_age_hours=hours, top_n=top_n)

    stories = []
    for s in raw_results:
        item = dict(s)
        item["url"] = s.get("story_url")
        item["comments"] = s.get("comment_count", 0)
        item["num_comments"] = s.get("comment_count", 0)
        stories.append(item)

    return {
        "topic":        topic,
        "window_hours": hours,
        "hours":        hours,
        "count":        len(stories),
        "stories":      stories,
        "results":      stories,
    }
