"""
tests/test_collector_sync.py

Unit tests for src/collector_sync.py.

All HTTP calls are mocked using pytest-mock / unittest.mock.
No Bright Data credits are consumed.

Run with:
    python -m pytest tests/test_collector_sync.py -v
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

# ---------------------------------------------------------------------------
# Ensure the env var is set to a dummy value for imports that call os.environ
# ---------------------------------------------------------------------------
os.environ.setdefault("BRIGHTDATA_API_TOKEN", "test-token-does-not-matter")

from src.collector_sync import (  # noqa: E402  (import after env setup)
    COLLECTORS,
    DATASET_URL,
    TRIGGER_URL,
    _already_downloaded,
    _build_session,
    _is_building,
    _load_state,
    _mark_downloaded,
    _mark_failed,
    _mark_triggered,
    _save_state,
    fetch_result,
    run_once,
    save_raw_result,
    trigger_collection,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def mock_session():
    """A MagicMock that quacks like a requests.Session."""
    return MagicMock()


@pytest.fixture()
def empty_state():
    return {}


@pytest.fixture()
def tmp_state_file(tmp_path, monkeypatch):
    """Redirect STATE_FILE to a temp location for each test."""
    import src.collector_sync as cs
    state_path = tmp_path / ".collector_state.json"
    monkeypatch.setattr(cs, "STATE_FILE", state_path)
    return state_path


@pytest.fixture()
def sample_records():
    return [
        {
            "story_id": "12345",
            "title": "Test Story",
            "url": "https://example.com",
            "points": 42,
            "comment_count": 7,
            "rank": 3,
            "publication_time": "5 minutes ago",
            "story_type": "story",
        }
    ]


# ===========================================================================
# 1. Collector configuration
# ===========================================================================

class TestCollectorConfig:
    def test_newest_collector_id(self):
        assert COLLECTORS["newest"]["collector"] == "c_msxgknap1ptjrrcetr"

    def test_front_page_collector_id(self):
        assert COLLECTORS["front_page"]["collector"] == "c_msxfwz2h1v0fxwlu83"

    def test_newest_url(self):
        assert COLLECTORS["newest"]["url"] == "https://news.ycombinator.com/newest"

    def test_front_page_url(self):
        assert COLLECTORS["front_page"]["url"] == "https://news.ycombinator.com/"

    def test_output_dirs_set(self):
        assert "newest" in COLLECTORS["newest"]["output_dir"]
        assert "front_page" in COLLECTORS["front_page"]["output_dir"]


# ===========================================================================
# 2. Session / auth header
# ===========================================================================

class TestSessionAuth:
    def test_auth_header_from_env_var(self):
        token = "secret-token-xyz"
        session = _build_session(token)
        assert session.headers["Authorization"] == f"Bearer {token}"

    def test_token_not_empty_string(self):
        """Token must come from env, never be a literal string in source."""
        import inspect
        import src.collector_sync as cs
        source = inspect.getsource(cs)
        # Ensure the actual token value is not embedded in source
        assert "Bearer API_TOKEN" not in source
        assert "hardcoded" not in source.lower()


# ===========================================================================
# 3. trigger_collection
# ===========================================================================

class TestTriggerCollection:
    def test_sends_correct_collector_id_newest(self, mock_session):
        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {
            "collection_id": "j_abc123",
            "start_eta": "2026-01-01T00:00:00Z",
        }
        cid = trigger_collection(mock_session, "newest")
        assert cid == "j_abc123"
        call_kwargs = mock_session.post.call_args
        assert call_kwargs.kwargs["params"]["collector"] == "c_msxgknap1ptjrrcetr"

    def test_sends_correct_collector_id_front_page(self, mock_session):
        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {
            "collection_id": "j_fp_001",
        }
        cid = trigger_collection(mock_session, "front_page")
        assert cid == "j_fp_001"
        call_kwargs = mock_session.post.call_args
        assert call_kwargs.kwargs["params"]["collector"] == "c_msxfwz2h1v0fxwlu83"

    def test_sends_correct_url_newest(self, mock_session):
        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {"collection_id": "j_x"}
        trigger_collection(mock_session, "newest")
        body = mock_session.post.call_args.kwargs["json"]
        assert body == [{"url": "https://news.ycombinator.com/newest"}]

    def test_sends_correct_url_front_page(self, mock_session):
        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {"collection_id": "j_y"}
        trigger_collection(mock_session, "front_page")
        body = mock_session.post.call_args.kwargs["json"]
        assert body == [{"url": "https://news.ycombinator.com/"}]

    def test_posts_to_correct_trigger_url(self, mock_session):
        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {"collection_id": "j_z"}
        trigger_collection(mock_session, "newest")
        assert mock_session.post.call_args.args[0] == TRIGGER_URL

    def test_returns_none_on_http_error(self, mock_session):
        mock_session.post.return_value.status_code = 403
        mock_session.post.return_value.text = "Forbidden"
        result = trigger_collection(mock_session, "newest")
        assert result is None

    def test_returns_none_when_collection_id_missing(self, mock_session):
        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {"start_eta": "now"}
        result = trigger_collection(mock_session, "newest")
        assert result is None

    def test_returns_none_on_network_exception(self, mock_session):
        import requests as req
        mock_session.post.side_effect = req.exceptions.ConnectionError("refused")
        result = trigger_collection(mock_session, "newest")
        assert result is None


# ===========================================================================
# 4. fetch_result (polling)
# ===========================================================================

class TestFetchResult:
    def test_returns_records_when_immediately_ready(self, mock_session, sample_records):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = sample_records
        mock_session.get.return_value = resp

        result = fetch_result(mock_session, "newest", "j_abc")
        assert result is not None
        records, _ = result
        assert records == sample_records

    def test_polls_until_ready(self, mock_session, sample_records):
        """Returns building twice, then ready."""
        building_resp = MagicMock(status_code=200)
        building_resp.json.return_value = {
            "status": "building",
            "message": "Dataset is not ready yet, try again in 5s",
        }
        ready_resp = MagicMock(status_code=200)
        ready_resp.json.return_value = sample_records

        mock_session.get.side_effect = [building_resp, building_resp, ready_resp]

        with patch("src.collector_sync.time.sleep"):  # don't actually sleep
            result = fetch_result(mock_session, "newest", "j_abc")

        assert result is not None
        records, _ = result
        assert records == sample_records
        assert mock_session.get.call_count == 3

    def test_returns_none_on_non_200_error(self, mock_session):
        resp = MagicMock(status_code=500)
        resp.text = "Internal Server Error"
        mock_session.get.return_value = resp

        result = fetch_result(mock_session, "newest", "j_abc")
        assert result is None

    def test_rate_limit_retries(self, mock_session, sample_records):
        """HTTP 429 should be retried."""
        rate_resp = MagicMock(status_code=429)
        ok_resp   = MagicMock(status_code=200)
        ok_resp.json.return_value = sample_records
        mock_session.get.side_effect = [rate_resp, ok_resp]

        with patch("src.collector_sync.time.sleep"):
            result = fetch_result(mock_session, "newest", "j_abc")

        assert result is not None
        records, _ = result
        assert records == sample_records

    def test_times_out_when_always_building(self, mock_session):
        """After max_wait_seconds is exceeded, returns None."""
        building_resp = MagicMock(status_code=200)
        building_resp.json.return_value = {"status": "building", "message": "nope"}
        mock_session.get.return_value = building_resp

        with patch("src.collector_sync.time.sleep"):
            # Use a very small max_wait so the test runs fast
            result = fetch_result(
                mock_session, "newest", "j_abc", max_wait_seconds=1
            )

        assert result is None

    def test_uses_correct_collection_id_in_get_params(self, mock_session, sample_records):
        resp = MagicMock(status_code=200)
        resp.json.return_value = sample_records
        mock_session.get.return_value = resp

        fetch_result(mock_session, "newest", "j_mycollection123")
        get_params = mock_session.get.call_args.kwargs["params"]
        assert get_params == {"id": "j_mycollection123"}

    def test_requests_to_correct_dataset_url(self, mock_session, sample_records):
        resp = MagicMock(status_code=200)
        resp.json.return_value = sample_records
        mock_session.get.return_value = resp

        fetch_result(mock_session, "newest", "j_x")
        assert mock_session.get.call_args.args[0] == DATASET_URL


# ===========================================================================
# 5. _is_building helper
# ===========================================================================

class TestIsBuilding:
    def test_building_status_dict(self):
        assert _is_building({"status": "building", "message": "not ready"})

    def test_empty_list_is_building(self):
        assert _is_building([])

    def test_non_empty_list_not_building(self):
        assert not _is_building([{"story_id": "1"}])

    def test_other_dict_not_building(self):
        assert not _is_building({"status": "complete"})


# ===========================================================================
# 6. Deduplication / state
# ===========================================================================

class TestDeduplication:
    def test_not_downloaded_initially(self, empty_state):
        assert not _already_downloaded(empty_state, "newest", "j_abc")

    def test_marked_downloaded_detected(self, empty_state):
        _mark_triggered(empty_state, "newest", "j_abc")
        # Manually set to downloaded
        empty_state["newest"]["jobs"]["j_abc"]["status"] = "downloaded"
        assert _already_downloaded(empty_state, "newest", "j_abc")

    def test_triggered_not_downloaded(self, empty_state):
        _mark_triggered(empty_state, "newest", "j_abc")
        assert not _already_downloaded(empty_state, "newest", "j_abc")

    def test_run_once_skips_already_downloaded(self, mock_session, sample_records, tmp_path, monkeypatch):
        """run_once must not re-download a collection that is already in state."""
        import src.collector_sync as cs
        monkeypatch.setattr(cs, "STATE_FILE", tmp_path / "state.json")

        # Trigger returns an already-downloaded id
        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {"collection_id": "j_already"}

        state = {"newest": {"jobs": {"j_already": {"status": "downloaded"}}}}

        result = run_once(mock_session, state, "newest")
        # Should return True (idempotent) but never call GET
        assert result is True
        mock_session.get.assert_not_called()


# ===========================================================================
# 7. State persistence
# ===========================================================================

class TestStatePersistence:
    def test_state_saved_after_trigger(self, tmp_state_file, empty_state):
        _mark_triggered(empty_state, "newest", "j_111")
        loaded = _load_state()
        assert loaded["newest"]["jobs"]["j_111"]["status"] == "triggered"

    def test_state_saved_after_download(self, tmp_state_file, empty_state):
        _mark_triggered(empty_state, "newest", "j_222")
        _mark_downloaded(empty_state, "newest", "j_222", "/some/path.json")
        loaded = _load_state()
        assert loaded["newest"]["jobs"]["j_222"]["status"] == "downloaded"
        assert loaded["newest"]["jobs"]["j_222"]["output_file"] == "/some/path.json"
        assert "last_successful_sync" in loaded["newest"]

    def test_state_saved_after_failure(self, tmp_state_file, empty_state):
        _mark_triggered(empty_state, "newest", "j_333")
        _mark_failed(empty_state, "newest", "j_333", "timeout")
        loaded = _load_state()
        assert loaded["newest"]["jobs"]["j_333"]["status"] == "failed"
        assert loaded["newest"]["jobs"]["j_333"]["reason"] == "timeout"

    def test_corrupt_state_file_returns_empty(self, tmp_state_file):
        tmp_state_file.write_text("NOT JSON", encoding="utf-8")
        result = _load_state()
        assert result == {}

    def test_missing_state_file_returns_empty(self, tmp_state_file):
        # File doesn't exist yet
        assert not tmp_state_file.exists()
        result = _load_state()
        assert result == {}


# ===========================================================================
# 8. save_raw_result
# ===========================================================================

class TestSaveRawResult:
    def test_file_created_in_correct_dir(self, tmp_path, sample_records, monkeypatch):
        import src.collector_sync as cs
        fake_output = str(tmp_path / "newest")
        monkeypatch.setitem(cs.COLLECTORS["newest"], "output_dir", fake_output)

        path = save_raw_result("newest", "j_save001", sample_records, "2026-01-01T00:00:00Z")
        assert path.exists()
        assert "api_j_save001" in path.name

    def test_saved_json_has_scraped_at_and_stories(self, tmp_path, sample_records, monkeypatch):
        import src.collector_sync as cs
        monkeypatch.setitem(cs.COLLECTORS["newest"], "output_dir", str(tmp_path / "newest"))

        path = save_raw_result("newest", "j_save002", sample_records, "2026-05-01T12:00:00Z")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        snap = data[0]
        assert snap["scraped_at"] == "2026-05-01T12:00:00Z"
        assert snap["stories"] == sample_records

    def test_stories_not_modified(self, tmp_path, sample_records, monkeypatch):
        """Ensure we don't flatten or alter the story records."""
        import src.collector_sync as cs
        monkeypatch.setitem(cs.COLLECTORS["newest"], "output_dir", str(tmp_path / "newest"))

        path = save_raw_result("newest", "j_save003", sample_records, "2026-01-01T00:00:00Z")
        data = json.loads(path.read_text(encoding="utf-8"))
        saved_stories = data[0]["stories"]
        assert saved_stories == sample_records

    def test_collection_id_stored_in_metadata(self, tmp_path, sample_records, monkeypatch):
        import src.collector_sync as cs
        monkeypatch.setitem(cs.COLLECTORS["newest"], "output_dir", str(tmp_path / "newest"))

        path = save_raw_result("newest", "j_metacheck", sample_records, "2026-01-01T00:00:00Z")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data[0]["_api_collection_id"] == "j_metacheck"

    def test_does_not_overwrite_existing_historical_files(self, tmp_path, sample_records, monkeypatch):
        """API files use 'api_' prefix; historical files should never match."""
        import src.collector_sync as cs
        out_dir = tmp_path / "newest"
        out_dir.mkdir(parents=True, exist_ok=True)
        # Create a fake historical file (no 'api_' prefix)
        historical = out_dir / "j_msyfnf512oaghfx2y7.json"
        historical.write_text("historical", encoding="utf-8")
        monkeypatch.setitem(cs.COLLECTORS["newest"], "output_dir", str(out_dir))

        save_raw_result("newest", "j_newsave", sample_records, "2026-01-01T00:00:00Z")
        # Historical file untouched
        assert historical.read_text() == "historical"


# ===========================================================================
# 9. run_once integration
# ===========================================================================

class TestRunOnce:
    def test_successful_run_once(
        self, mock_session, sample_records, empty_state, tmp_path, monkeypatch
    ):
        import src.collector_sync as cs
        monkeypatch.setattr(cs, "STATE_FILE", tmp_path / "state.json")
        monkeypatch.setitem(cs.COLLECTORS["newest"], "output_dir", str(tmp_path / "newest"))

        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {"collection_id": "j_run001"}

        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = sample_records

        result = run_once(mock_session, empty_state, "newest")
        assert result is True
        # State should record download
        assert empty_state["newest"]["jobs"]["j_run001"]["status"] == "downloaded"

    def test_failed_trigger_returns_false(self, mock_session, empty_state):
        mock_session.post.return_value.status_code = 500
        mock_session.post.return_value.text = "Server error"
        result = run_once(mock_session, empty_state, "newest")
        assert result is False

    def test_failed_fetch_marks_job_failed(
        self, mock_session, empty_state, tmp_path, monkeypatch
    ):
        import src.collector_sync as cs
        monkeypatch.setattr(cs, "STATE_FILE", tmp_path / "state.json")

        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {"collection_id": "j_fail001"}

        # Dataset endpoint always errors
        mock_session.get.return_value.status_code = 500
        mock_session.get.return_value.text = "error"

        result = run_once(mock_session, empty_state, "newest")
        assert result is False
        assert empty_state["newest"]["jobs"]["j_fail001"]["status"] == "failed"

    def test_ingest_called_when_flag_set(
        self, mock_session, sample_records, empty_state, tmp_path, monkeypatch
    ):
        import src.collector_sync as cs
        monkeypatch.setattr(cs, "STATE_FILE", tmp_path / "state.json")
        monkeypatch.setitem(cs.COLLECTORS["newest"], "output_dir", str(tmp_path / "newest"))

        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {"collection_id": "j_ing001"}
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = sample_records

        with patch("src.collector_sync._run_ingestion") as mock_ingest:
            run_once(mock_session, empty_state, "newest", run_ingest=True)
            mock_ingest.assert_called_once()

    def test_ingest_not_called_when_flag_not_set(
        self, mock_session, sample_records, empty_state, tmp_path, monkeypatch
    ):
        import src.collector_sync as cs
        monkeypatch.setattr(cs, "STATE_FILE", tmp_path / "state.json")
        monkeypatch.setitem(cs.COLLECTORS["newest"], "output_dir", str(tmp_path / "newest"))

        mock_session.post.return_value.status_code = 200
        mock_session.post.return_value.json.return_value = {"collection_id": "j_noing"}
        mock_session.get.return_value.status_code = 200
        mock_session.get.return_value.json.return_value = sample_records

        with patch("src.collector_sync._run_ingestion") as mock_ingest:
            run_once(mock_session, empty_state, "newest", run_ingest=False)
            mock_ingest.assert_not_called()
