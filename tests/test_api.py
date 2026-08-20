"""
tests/test_api.py

Comprehensive tests for the Virality Forensics FastAPI application:
- Health and model prediction (single, batch, thresholds, imputation)
- Feature A: Title Intelligence (scoring, corpus refresh)
- Feature B: Post-Submission Monitor (live fetch, trajectory history, clearing)
- Feature C: Live Topic Intelligence (trending, domains, best time, similar stories)

Run with:
    venv/Scripts/pytest.exe tests/test_api.py -v
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Create a TestClient with the model loaded."""
    # Disable auth for tests (no VIRALITY_API_KEY set)
    os.environ.pop("VIRALITY_API_KEY", None)

    from api.main import app
    with TestClient(app) as c:
        yield c


VALID_FEATURES = {
    "early_points": 5,
    "early_comments": 2,
    "early_rank": 8,
    "points_velocity": 12.0,
    "comments_velocity": 4.0,
    "rank_change": 3,
    "observation_count_early": 2,
    "title_length": 52,
    "title_word_count": 9,
    "title_has_question_mark": 0,
    "title_has_number": 0,
    "engagement_ratio": 0.4,
}

ALL_NONE_FEATURES = {k: None for k in VALID_FEATURES}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "model" in body


# ---------------------------------------------------------------------------
# Single prediction
# ---------------------------------------------------------------------------

def test_predict_valid_features(client):
    r = client.post("/api/v1/predict", json=VALID_FEATURES)
    assert r.status_code == 200, r.text
    body = r.json()
    assert 0.0 <= body["p_viral"] <= 1.0
    assert isinstance(body["prediction_default"], bool)
    assert isinstance(body["prediction_f1_optimal"], bool)
    assert body["horizon"] == "15 min"


def test_predict_all_none_features(client):
    """All-None payload must be handled by the imputer, not raise an error."""
    r = client.post("/api/v1/predict", json=ALL_NONE_FEATURES)
    assert r.status_code == 200, r.text
    body = r.json()
    assert 0.0 <= body["p_viral"] <= 1.0


def test_predict_with_story_id(client):
    r = client.post("/api/v1/predict/49366792", json=VALID_FEATURES)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["story_id"] == "49366792"
    assert 0.0 <= body["p_viral"] <= 1.0


def test_predict_empty_body(client):
    """An empty JSON object should be treated as all-None and imputed."""
    r = client.post("/api/v1/predict", json={})
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# Threshold correctness
# ---------------------------------------------------------------------------

def test_threshold_default(client):
    """prediction_default must be True iff p_viral >= 0.5."""
    r = client.post("/api/v1/predict", json=VALID_FEATURES)
    body = r.json()
    assert body["prediction_default"] == (body["p_viral"] >= 0.5)


def test_threshold_f1_optimal(client):
    """prediction_f1_optimal must be True iff p_viral >= 0.778."""
    r = client.post("/api/v1/predict", json=VALID_FEATURES)
    body = r.json()
    assert body["prediction_f1_optimal"] == (body["p_viral"] >= 0.778)


# ---------------------------------------------------------------------------
# Batch prediction
# ---------------------------------------------------------------------------

def _make_story(story_id: str, features: dict) -> dict:
    return {"story_id": story_id, "features": features}


def test_batch_predict_returns_correct_count(client):
    stories = [_make_story(str(i), VALID_FEATURES) for i in range(3)]
    r = client.post("/api/v1/batch_predict", json={"stories": stories})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["predictions"]) == 3


def test_batch_predict_story_ids_echoed(client):
    stories = [_make_story("abc", VALID_FEATURES), _make_story("xyz", VALID_FEATURES)]
    r = client.post("/api/v1/batch_predict", json={"stories": stories})
    body = r.json()
    assert body["predictions"][0]["story_id"] == "abc"
    assert body["predictions"][1]["story_id"] == "xyz"


def test_batch_predict_empty_list(client):
    r = client.post("/api/v1/batch_predict", json={"stories": []})
    assert r.status_code == 200
    assert r.json()["predictions"] == []


def test_batch_predict_over_limit(client):
    """Batch size > 500 must return 422."""
    stories = [_make_story(str(i), VALID_FEATURES) for i in range(501)]
    r = client.post("/api/v1/batch_predict", json={"stories": stories})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Collect endpoint
# ---------------------------------------------------------------------------

def test_collect_invalid_collector(client):
    r = client.post("/api/v1/collect", json={"collector": "unknown_scraper"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Feature A: Title Intelligence
# ---------------------------------------------------------------------------

def test_score_title_valid(client):
    r = client.post("/api/v1/score_title", json={"title": "Show HN: My New AI Tool for 100k Users"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "pattern_score" in data
    assert 0.0 <= data["pattern_score"] <= 10.0
    assert "flags" in data
    assert isinstance(data["flags"], list)
    assert "similar_successful_titles" in data
    assert "best_posting_time" in data


def test_score_title_validation(client):
    r = client.post("/api/v1/score_title", json={"title": "ab"})
    assert r.status_code == 422


def test_refresh_corpus(client):
    r = client.post("/api/v1/refresh_corpus")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "rebuilt"
    assert data["corpus_size"] > 0


# ---------------------------------------------------------------------------
# Feature C: Live Topic Intelligence
# ---------------------------------------------------------------------------

def test_trending_keywords(client):
    r = client.get("/api/v1/trending?hours=48&top_n=5")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "trending" in data
    assert len(data["trending"]) <= 5


def test_domain_leaderboard(client):
    r = client.get("/api/v1/trending/domains?top_n=5")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "domains" in data
    assert len(data["domains"]) <= 5


def test_best_posting_time(client):
    r = client.get("/api/v1/trending/best_time")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "recommendation" in data
    assert "hourly" in data
    assert "daily" in data


def test_similar_stories(client):
    r = client.get("/api/v1/similar?topic=Python+AI&hours=48")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["topic"] == "Python AI"
    assert "stories" in data


# ---------------------------------------------------------------------------
# Feature B: Post-Submission Live Monitor
# ---------------------------------------------------------------------------

def test_monitor_story_mocked(client):
    fake_story = {
        "story_id": "99999999",
        "title": "Show HN: Fast Vector Search in Rust",
        "url": "https://github.com/example/rust-search",
        "author": "tester",
        "points": 14,
        "comment_count": 5,
        "created_at": None,
        "story_age_seconds": 900,
        "story_age_minutes": 15.0,
        "estimated_rank": 6,
    }
    with patch("src.hn_api.fetch_story_with_rank", return_value=fake_story):
        # 1. Clear any prior test history
        client.delete("/api/v1/monitor/99999999/history")

        # 2. Call monitor
        r = client.get("/api/v1/monitor/99999999")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["story_id"] == "99999999"
        assert 0.0 <= data["p_viral"] <= 1.0
        assert "trend" in data
        assert "message" in data

        # 3. Check history
        r_hist = client.get("/api/v1/monitor/99999999/history")
        assert r_hist.status_code == 200, r_hist.text
        hist_data = r_hist.json()
        assert hist_data["snapshots"] >= 1

        # 4. Clean up
        r_del = client.delete("/api/v1/monitor/99999999/history")
        assert r_del.status_code == 200


def test_monitor_story_not_found(client):
    with patch("src.hn_api.fetch_story_with_rank", return_value=None):
        r = client.get("/api/v1/monitor/00000000")
        assert r.status_code == 404
