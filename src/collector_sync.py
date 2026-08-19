"""
collector_sync.py

Automates Bright Data Scraper Studio collection via the official DCA API.

API contract (confirmed from official Bright Data documentation):
  POST  https://api.brightdata.com/dca/trigger
        params: collector=<id>, queue_next=1
        body:   [{"url": "<target_url>"}]
        auth:   Bearer <BRIGHTDATA_API_TOKEN>
  Response (200 OK):
        {"collection_id": "j_abc123...", "start_eta": "..."}

  GET   https://api.brightdata.com/dca/dataset
        params: id=<collection_id>
        auth:   Bearer <BRIGHTDATA_API_TOKEN>
  Response when still running (200 OK):
        {"status": "building", "message": "Dataset is not ready yet, try again in XXs"}
  Response when complete (200 OK):
        [<list of scraped story dicts>]  -- same structure as existing raw files

State file:  data/.collector_state.json
Raw output:  data/raw/{collector_name}/api_{collection_id}.json

Run examples:
  python -m src.collector_sync --once
  python -m src.collector_sync --once --collector newest
  python -m src.collector_sync --once --collector front_page
  python -m src.collector_sync --once --ingest
  python -m src.collector_sync --poll --interval 480
  python -m src.collector_sync --poll --interval 3600 --collector front_page

SECURITY: API token is read exclusively from the BRIGHTDATA_API_TOKEN
environment variable. It is never logged, stored, or printed.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("collector_sync")

# ---------------------------------------------------------------------------
# Bright Data API constants  (confirmed from official documentation)
# ---------------------------------------------------------------------------
TRIGGER_URL = "https://api.brightdata.com/dca/trigger"
DATASET_URL = "https://api.brightdata.com/dca/dataset"

# ---------------------------------------------------------------------------
# Collector configuration
# ---------------------------------------------------------------------------
COLLECTORS: dict[str, dict[str, str]] = {
    "newest": {
        "collector": "c_msxgknap1ptjrrcetr",
        "url": "https://news.ycombinator.com/newest",
        "output_dir": "data/raw/newest",
    },
    "front_page": {
        "collector": "c_msxfwz2h1v0fxwlu83",
        "url": "https://news.ycombinator.com/",
        "output_dir": "data/raw/front_page",
    },
}

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
STATE_FILE = Path("data/.collector_state.json")

# ---------------------------------------------------------------------------
# Retry / timeout configuration
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT = 30          # seconds per HTTP request
MAX_RETRIES     = 3           # total retries on transient failures
BACKOFF_FACTOR  = 2.0         # exponential backoff multiplier
POLL_WAIT_BASE  = 15          # seconds between dataset poll attempts
POLL_WAIT_MAX   = 300         # cap for poll backoff


# ---------------------------------------------------------------------------
# HTTP session with built-in retry on network errors
# ---------------------------------------------------------------------------

def _build_session(token: str) -> requests.Session:
    """Return a requests.Session with retries, backoff, and auth header set."""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    retry = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def _load_state() -> dict[str, Any]:
    """Load state from disk, returning empty structure if absent or corrupt."""
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not load state file (%s); starting fresh.", exc)
        return {}


def _save_state(state: dict[str, Any]) -> None:
    """Atomically write state to disk."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    tmp.replace(STATE_FILE)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mark_triggered(
    state: dict, collector_name: str, collection_id: str
) -> None:
    jobs = state.setdefault(collector_name, {}).setdefault("jobs", {})
    jobs[collection_id] = {
        "status":      "triggered",
        "triggered_at": _now_iso(),
    }
    _save_state(state)


def _mark_downloaded(
    state: dict, collector_name: str, collection_id: str, output_path: str
) -> None:
    state[collector_name]["jobs"][collection_id].update({
        "status":        "downloaded",
        "downloaded_at": _now_iso(),
        "output_file":   output_path,
    })
    state[collector_name]["last_successful_sync"] = _now_iso()
    _save_state(state)


def _mark_failed(
    state: dict, collector_name: str, collection_id: str, reason: str
) -> None:
    if collector_name in state and collection_id in state[collector_name].get("jobs", {}):
        state[collector_name]["jobs"][collection_id].update({
            "status":    "failed",
            "failed_at": _now_iso(),
            "reason":    reason,
        })
        _save_state(state)


def _already_downloaded(state: dict, collector_name: str, collection_id: str) -> bool:
    jobs = state.get(collector_name, {}).get("jobs", {})
    return jobs.get(collection_id, {}).get("status") == "downloaded"


# ---------------------------------------------------------------------------
# API: Trigger
# ---------------------------------------------------------------------------

def trigger_collection(
    session: requests.Session,
    collector_name: str,
) -> Optional[str]:
    """
    POST to /dca/trigger for the named collector.

    Returns the collection_id string on success, None on failure.
    """
    cfg = COLLECTORS[collector_name]
    params = {"collector": cfg["collector"], "queue_next": "1"}
    body   = [{"url": cfg["url"]}]

    log.info("[%s] Triggering collection (collector=%s)...",
             collector_name, cfg["collector"])
    try:
        resp = session.post(
            TRIGGER_URL, params=params, json=body, timeout=REQUEST_TIMEOUT
        )
    except requests.exceptions.RequestException as exc:
        log.error("[%s] Trigger request failed: %s", collector_name, exc)
        return None

    if resp.status_code != 200:
        log.error("[%s] Trigger returned HTTP %d: %s",
                  collector_name, resp.status_code, resp.text[:300])
        return None

    try:
        data = resp.json()
    except ValueError:
        log.error("[%s] Trigger response is not JSON: %s", collector_name, resp.text[:300])
        return None

    collection_id = data.get("collection_id")
    if not collection_id:
        log.error("[%s] Trigger response missing 'collection_id': %s",
                  collector_name, data)
        return None

    start_eta = data.get("start_eta", "unknown")
    log.info("[%s] Triggered. collection_id=%s  start_eta=%s",
             collector_name, collection_id, start_eta)
    return collection_id


# ---------------------------------------------------------------------------
# API: Poll for completion and download
# ---------------------------------------------------------------------------

def _is_building(data: Any) -> bool:
    """Return True if the /dca/dataset response indicates the job is still running."""
    if isinstance(data, dict) and data.get("status") == "building":
        return True
    # Some API versions return an empty list while building
    if isinstance(data, list) and len(data) == 0:
        return True
    return False


def fetch_result(
    session: requests.Session,
    collector_name: str,
    collection_id: str,
    max_wait_seconds: int = 1800,
) -> Optional[list[dict]]:
    """
    Poll /dca/dataset until results are ready or timeout.

    Returns the list of story records on success, None on failure/timeout.
    The poll interval uses exponential backoff up to POLL_WAIT_MAX seconds.
    """
    wait = POLL_WAIT_BASE
    elapsed = 0
    attempt = 0

    log.info("[%s] Polling for collection_id=%s (max_wait=%ds)...",
             collector_name, collection_id, max_wait_seconds)

    while elapsed < max_wait_seconds:
        attempt += 1
        try:
            resp = session.get(
                DATASET_URL,
                params={"id": collection_id},
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            log.warning("[%s] Poll attempt %d network error: %s", collector_name, attempt, exc)
            time.sleep(wait)
            elapsed += wait
            wait = min(wait * 2, POLL_WAIT_MAX)
            continue

        if resp.status_code == 429:
            log.warning("[%s] Rate limited (HTTP 429). Waiting %ds...",
                        collector_name, wait)
            time.sleep(wait)
            elapsed += wait
            wait = min(wait * 2, POLL_WAIT_MAX)
            continue

        if resp.status_code not in (200, 202):
            log.error("[%s] Dataset poll returned HTTP %d: %s",
                      collector_name, resp.status_code, resp.text[:300])
            return None

        try:
            data = resp.json()
        except ValueError:
            log.warning("[%s] Poll response not JSON on attempt %d; retrying...",
                        collector_name, attempt)
            time.sleep(wait)
            elapsed += wait
            continue

        if _is_building(data):
            msg = data.get("message", "still building") if isinstance(data, dict) else "empty list"
            log.info("[%s] Not ready yet (attempt %d): %s. Waiting %ds...",
                     collector_name, attempt, msg, wait)
            time.sleep(wait)
            elapsed += wait
            wait = min(wait * 2, POLL_WAIT_MAX)
            continue

        # If it's a non-empty list: results are ready
        if isinstance(data, list) and len(data) > 0:
            log.info("[%s] Results ready. %d records received.", collector_name, len(data))
            return data

        # Unexpected response shape
        log.error("[%s] Unexpected response from /dca/dataset: %s", collector_name, str(data)[:300])
        return None

    log.error("[%s] Timed out waiting for collection_id=%s after %ds.",
              collector_name, collection_id, max_wait_seconds)
    return None


# ---------------------------------------------------------------------------
# Save raw result
# ---------------------------------------------------------------------------

def save_raw_result(
    collector_name: str,
    collection_id: str,
    records: list[dict],
    scraped_at: str,
) -> Path:
    """
    Save the raw API result as a JSON file compatible with the existing
    ingest.py format:
      [{
          "scraped_at": "<ISO timestamp>",
          "stories":    [<story records>],
          "_api_collection_id": "<collection_id>",
          "_collector_name":    "<collector_name>"
      }]

    File: data/raw/{collector_name}/api_{collection_id}.json
    The existing snapshot format uses this exact top-level structure.
    Metadata fields prefixed with '_' are extra and won't break ingest.py
    since flatten_raw_file accesses only 'scraped_at' and 'stories'.
    """
    output_dir = Path(COLLECTORS[collector_name]["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sanitise collection_id for use as a filename
    safe_id = collection_id.replace("/", "_").replace("\\", "_")
    out_path = output_dir / f"api_{safe_id}.json"

    payload = [{
        "scraped_at":            scraped_at,
        "stories":               records,
        "_api_collection_id":    collection_id,
        "_collector_name":       collector_name,
        "input": {"url": COLLECTORS[collector_name]["url"]},
    }]

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    log.info("[%s] Saved %d records -> %s", collector_name, len(records), out_path)
    return out_path


# ---------------------------------------------------------------------------
# High-level: run one collector sync cycle
# ---------------------------------------------------------------------------

def run_once(
    session: requests.Session,
    state: dict,
    collector_name: str,
    run_ingest: bool = False,
) -> bool:
    """
    Trigger, poll, download, and optionally ingest one collector cycle.
    Returns True on success, False on failure.
    """
    # 1. Trigger
    collection_id = trigger_collection(session, collector_name)
    if not collection_id:
        return False

    # 2. Deduplication guard
    if _already_downloaded(state, collector_name, collection_id):
        log.info("[%s] collection_id=%s already downloaded. Skipping.",
                 collector_name, collection_id)
        return True

    _mark_triggered(state, collector_name, collection_id)

    # 3. Poll for results
    records = fetch_result(session, collector_name, collection_id)
    if records is None:
        _mark_failed(state, collector_name, collection_id, "fetch_result returned None")
        return False

    # 4. Save
    scraped_at = datetime.now(timezone.utc).isoformat()
    out_path = save_raw_result(collector_name, collection_id, records, scraped_at)
    _mark_downloaded(state, collector_name, collection_id, str(out_path))

    # 5. Optional ingestion
    if run_ingest:
        _run_ingestion()

    return True


def _run_ingestion() -> None:
    """Call the existing ingest.py pipeline in-process."""
    log.info("Running ingestion pipeline (src.ingest)...")
    try:
        from src.ingest import main as ingest_main
        ingest_main()
        log.info("Ingestion complete.")
    except Exception as exc:
        log.error("Ingestion failed: %s", exc)


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

_shutdown_requested = False


def _handle_signal(signum, frame):  # noqa: ANN001
    global _shutdown_requested
    log.info("Shutdown signal received. Finishing current cycle and stopping.")
    _shutdown_requested = True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="collector_sync",
        description="Trigger Bright Data Scraper Studio collectors and download results.",
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--once",
        action="store_true",
        help="Trigger each selected collector once and retrieve results.",
    )
    mode.add_argument(
        "--poll",
        action="store_true",
        help="Repeatedly trigger and retrieve on a fixed interval.",
    )
    p.add_argument(
        "--collector",
        choices=list(COLLECTORS.keys()),
        default=None,
        help="Run only this collector. Omit to run all.",
    )
    p.add_argument(
        "--interval",
        type=int,
        default=480,
        help="Seconds between poll cycles when using --poll (default: 480).",
    )
    p.add_argument(
        "--ingest",
        action="store_true",
        help="Run src.ingest after each successful retrieval.",
    )
    return p


def _get_token() -> str:
    token = os.environ.get("BRIGHTDATA_API_TOKEN", "").strip()
    if not token:
        log.error(
            "BRIGHTDATA_API_TOKEN environment variable is not set. "
            "Set it before running: export BRIGHTDATA_API_TOKEN=<your_token>"
        )
        sys.exit(1)
    return token


def main() -> None:
    parser = _build_parser()
    args   = parser.parse_args()

    token   = _get_token()
    session = _build_session(token)
    state   = _load_state()

    collectors_to_run = (
        [args.collector] if args.collector else list(COLLECTORS.keys())
    )

    signal.signal(signal.SIGINT,  _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    if args.once:
        for name in collectors_to_run:
            run_once(session, state, name, run_ingest=args.ingest)

    elif args.poll:
        log.info("Starting poll loop. Collectors: %s | Interval: %ds | Ctrl-C to stop.",
                 collectors_to_run, args.interval)
        while not _shutdown_requested:
            for name in collectors_to_run:
                if _shutdown_requested:
                    break
                run_once(session, state, name, run_ingest=args.ingest)
            if _shutdown_requested:
                break
            log.info("Sleeping %ds until next cycle...", args.interval)
            # Sleep in small chunks so Ctrl-C is responsive
            for _ in range(args.interval):
                if _shutdown_requested:
                    break
                time.sleep(1)
        log.info("Collector sync stopped.")


if __name__ == "__main__":
    main()
