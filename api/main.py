"""
main.py

FastAPI application factory for the Virality Forensics prediction API.

Start with:
    uvicorn api.main:app --reload --port 8000

Environment variables:
    VIRALITY_API_KEY      — Required for protected routes. If unset, auth is
                            disabled (dev mode). Set in .env or shell.
    BRIGHTDATA_API_TOKEN  — Required only for the /collect endpoint.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .feed_router import router as feed_router
from .model import load_model
from .monitor_router import router as monitor_router
from .router import collect_router, router
from .title_router import router as title_router

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("virality.main")


# ---------------------------------------------------------------------------
# Lifespan: load model once at startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading virality model...")
    load_model()
    log.info("Model loaded. API ready.")
    yield
    log.info("Shutting down.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Virality Forensics API",
    description=(
        "Predicts whether a newly submitted Hacker News story will reach the top-20% "
        "of eventual engagement (Label B), using only signals available within the first "
        "15 minutes post-submission.\n\n"
        "**Model:** Logistic Regression trained on 469 stories with 89 positives (~19%).\n\n"
        "**Primary metric:** PR-AUC (more informative than ROC-AUC for this imbalanced task).\n\n"
        "**Thresholds:** Default = 0.50 | F1-optimal = 0.778 (Precision 0.875 / Recall 0.636)"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow all origins for dev
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(router)
app.include_router(collect_router)
app.include_router(feed_router)
app.include_router(title_router)
app.include_router(monitor_router)


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root():
    return {"message": "Virality Forensics API", "docs": "/docs"}


@app.get("/health", tags=["ops"], summary="Liveness check")
def health():
    """Returns 200 OK if the API and model are loaded and ready."""
    return {
        "status": "ok",
        "model": "final_logistic_regression_15min.joblib",
        "version": "v1",
        "auth_enabled": bool(os.environ.get("VIRALITY_API_KEY")),
    }
