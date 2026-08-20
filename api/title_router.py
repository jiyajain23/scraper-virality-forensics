"""
title_router.py  —  Feature A: Title Intelligence

Routes:
    POST /api/v1/score_title
    POST /api/v1/refresh_corpus   (admin — rebuilds title_corpus.json)
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .router import _verify_api_key

log = logging.getLogger("virality.title_router")

router = APIRouter(
    prefix="/api/v1",
    tags=["title-intelligence"],
    dependencies=[Depends(_verify_api_key)],
)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

class TitleScoreRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=300,
                       description="Draft HN title to analyse")

    model_config = {"json_schema_extra": {
        "example": {"title": "How I grew my blog to 100k readers using RSS in 6 months"}
    }}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/score_title",
    summary="Score a draft HN title against the corpus",
)
def score_title(body: TitleScoreRequest):
    """
    Analyses your draft title against patterns from collected HN stories.

    Returns:
    - **pattern_score** (0–10): how well the title matches high-engagement patterns
    - **flags**: specific actionable insights (length, numbers, keywords, etc.)
    - **similar_successful_titles**: top-3 real HN stories from the corpus with keyword overlap
    - **best_posting_time**: best hour/day based on historical submission data
    - **disclaimer**: honest note that this is pattern-based, not a virality guarantee
    """
    try:
        from src.title_intelligence import score_title as _score
        return _score(body.title)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Corpus not available: {exc}. Run POST /api/v1/refresh_corpus first.",
        ) from exc
    except Exception as exc:
        log.exception("score_title failed for title=%r", body.title)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post(
    "/refresh_corpus",
    summary="Rebuild the title corpus cache from latest ingested data",
    include_in_schema=True,
)
def refresh_corpus():
    """
    Rebuilds `data/processed/title_corpus.json` from the current
    `all_observations.csv`.  Call this after running `python -m src.ingest`
    to incorporate newly collected stories into the title analysis.
    """
    try:
        from src.title_intelligence import build_corpus
        stats = build_corpus()
        return {
            "status": "rebuilt",
            "corpus_size":       stats["corpus_size"],
            "high_engagement_n": stats["high_engagement_n"],
            "threshold_points":  stats["threshold_points"],
        }
    except Exception as exc:
        log.exception("refresh_corpus failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
