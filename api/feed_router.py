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
    results = _trending(max_age_hours=hours, top_n=top_n)
    return {
        "window_hours": hours,
        "count": len(results),
        "trending": results,
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
    results = _domains(top_n=top_n)
    return {
        "count": len(results),
        "domains": results,
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
    result = _best_time()
    if not result:
        raise HTTPException(status_code=503, detail="Processed data not available. Run src.ingest first.")
    return result


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
    results = _similar(topic=topic, max_age_hours=hours, top_n=top_n)
    return {
        "topic":        topic,
        "window_hours": hours,
        "count":        len(results),
        "stories":      results,
    }
