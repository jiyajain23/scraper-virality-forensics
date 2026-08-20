"""
router.py

FastAPI route definitions for the Virality Forensics API.

Routes:
    POST /api/v1/predict                  — single story prediction
    POST /api/v1/predict/{story_id}       — single story, ID echoed in response
    POST /api/v1/batch_predict            — batch up to 500 stories
    POST /api/v1/collect                  — trigger a BrightData collector (newest / front_page)

All routes under /api/v1/* require the X-API-Key header.
"""
from __future__ import annotations

import logging
import os
from typing import Optional  # noqa: F401 — used in _verify_api_key signature

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from .model import ViralityModel, get_model
from .schema import (
    BatchRequest,
    BatchResponse,
    CollectRequest,
    CollectResponse,
    PredictionResponse,
    StoryFeatures,
)

log = logging.getLogger("virality.router")

# ---------------------------------------------------------------------------
# API key auth
# ---------------------------------------------------------------------------

API_KEY_NAME = "X-API-Key"
# auto_error=False: let our own function decide, so dev-mode (no env var) works
_api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def _verify_api_key(api_key: Optional[str] = Security(_api_key_header)) -> str:
    expected = os.environ.get("VIRALITY_API_KEY", "")
    if not expected:
        # No key configured → dev mode, allow all requests
        return api_key or ""
    if api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
    return api_key


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

BATCH_MAX = 500

router = APIRouter(
    prefix="/api/v1",
    tags=["predictions"],
    dependencies=[Depends(_verify_api_key)],
)


# ------------------------------------------------------------------
# Single-story prediction
# ------------------------------------------------------------------

@router.post(
    "/predict",
    response_model=PredictionResponse,
    summary="Score a single story (no story_id)",
)
def predict(
    body: StoryFeatures,
    model: ViralityModel = Depends(get_model),
) -> PredictionResponse:
    """
    Accepts the 12 early-engagement features measured at the 15-minute horizon
    and returns the model's probability estimate and binary predictions.
    """
    result = model.predict_one(body.model_dump())
    return PredictionResponse(**result)


@router.post(
    "/predict/{story_id}",
    response_model=PredictionResponse,
    summary="Score a single story with a known story_id",
)
def predict_with_id(
    story_id: str,
    body: StoryFeatures,
    model: ViralityModel = Depends(get_model),
) -> PredictionResponse:
    """
    Same as /predict but echoes the story_id in the response, useful for
    correlating predictions back to a specific HN story.
    """
    result = model.predict_one(body.model_dump())
    return PredictionResponse(**result, story_id=story_id)


# ------------------------------------------------------------------
# Batch prediction
# ------------------------------------------------------------------

@router.post(
    "/batch_predict",
    response_model=BatchResponse,
    summary="Score up to 500 stories in a single request",
)
def batch_predict(
    body: BatchRequest,
    model: ViralityModel = Depends(get_model),
) -> BatchResponse:
    """
    Accepts a list of up to 500 stories.  Each entry may include an optional
    story_id which is echoed in the corresponding response element.
    Results are returned in the same order as the input list.
    """
    if len(body.stories) > BATCH_MAX:
        raise HTTPException(
            status_code=422,
            detail=f"Batch size {len(body.stories)} exceeds the limit of {BATCH_MAX}.",
        )
    if not body.stories:
        return BatchResponse(predictions=[])

    rows = [s.features.model_dump() for s in body.stories]
    results = model.predict_batch(rows)

    predictions = [
        PredictionResponse(**r, story_id=s.story_id)
        for r, s in zip(results, body.stories)
    ]
    return BatchResponse(predictions=predictions)


# ---------------------------------------------------------------------------
# Collect trigger
# ---------------------------------------------------------------------------

collect_router = APIRouter(
    prefix="/api/v1",
    tags=["collection"],
    dependencies=[Depends(_verify_api_key)],
)

VALID_COLLECTORS = {"newest", "front_page"}


def _poll_and_download_task(collector: str, collection_id: str):
    try:
        from src.collector_sync import (
            fetch_result,
            save_raw_result,
            _load_state,
            _mark_triggered,
            _mark_downloaded,
            _mark_failed,
            _build_session,
            _run_ingestion,
        )
        token = os.environ.get("BRIGHTDATA_API_TOKEN", "").strip()
        if not token:
            return
        session = _build_session(token)
        state = _load_state()
        _mark_triggered(state, collector, collection_id)
        
        fetch = fetch_result(session, collector, collection_id)
        if fetch is None:
            _mark_failed(state, collector, collection_id, "fetch_result returned None")
            return
            
        records, scraped_at = fetch
        out_path = save_raw_result(collector, collection_id, records, scraped_at)
        _mark_downloaded(state, collector, collection_id, str(out_path))
        _run_ingestion()
    except Exception:
        log.exception("Background poll and download failed for collection_id=%s", collection_id)


@collect_router.post(
    "/collect",
    response_model=CollectResponse,
    summary="Trigger a BrightData collector to scrape fresh HN data",
)
def trigger_collect(
    body: CollectRequest,
    background_tasks: BackgroundTasks,
) -> CollectResponse:
    """
    Fires a single collection cycle for the requested collector and returns
    the collection_id immediately.  The collection runs asynchronously on
    BrightData's infrastructure; use the collection_id to poll status if needed.

    Requires BRIGHTDATA_API_TOKEN to be set in the environment.
    """
    if body.collector not in VALID_COLLECTORS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown collector '{body.collector}'. "
                   f"Valid options: {sorted(VALID_COLLECTORS)}",
        )

    try:
        import requests as req_lib
        from src.collector_sync import (
            COLLECTORS,
            TRIGGER_URL,
            REQUEST_TIMEOUT,
            _build_session,
        )

        token = os.environ.get("BRIGHTDATA_API_TOKEN", "").strip()
        if not token:
            raise HTTPException(
                status_code=400,
                detail="BRIGHTDATA_API_TOKEN environment variable is not set."
            )
        session = _build_session(token)
        collector_id = COLLECTORS[body.collector]["collector"]
        collector_url = COLLECTORS[body.collector]["url"]
        resp = session.post(
            TRIGGER_URL,
            params={"collector": collector_id, "queue_next": 1},
            json=[{"url": collector_url}],
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        collection_id = data.get("collection_id") or data.get("id", "unknown")

        background_tasks.add_task(_poll_and_download_task, body.collector, collection_id)

        return CollectResponse(
            collector=body.collector,
            collection_id=collection_id,
            status="triggered",
            message=f"Collection started and queued for background save/ingest. Poll /dca/dataset?id={collection_id} if checking progress manually.",
        )

    except Exception as exc:
        log.exception("Collect trigger failed for collector=%s", body.collector)
        raise HTTPException(
            status_code=502,
            detail=f"Failed to trigger collector '{body.collector}': {exc}",
        ) from exc
