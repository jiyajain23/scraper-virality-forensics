"""
hn_api.py

Thin wrapper around the public HN / Algolia API.
No authentication required.

Endpoints used:
  - https://hn.algolia.com/api/v1/items/{story_id}
        → points, num_comments, title, url, created_at
  - https://hn.algolia.com/api/v1/search?tags=story,front_page&hitsPerPage=30
        → front-page rank approximation (position in results)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import requests

log = logging.getLogger("virality.hn_api")

ALGOLIA_ITEM_URL   = "https://hn.algolia.com/api/v1/items/{story_id}"
ALGOLIA_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
HN_ITEM_URL        = "https://hacker-news.firebaseio.com/v0/item/{story_id}.json"

REQUEST_TIMEOUT = 10  # seconds


def fetch_story(story_id: str) -> Optional[dict]:
    """
    Fetch current story data from Algolia HN API.

    Returns a normalised dict:
        story_id, title, url, author, points, comment_count,
        created_at (datetime UTC), story_age_seconds
    Returns None if the story is not found or the API call fails.
    """
    url = ALGOLIA_ITEM_URL.format(story_id=story_id)
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        log.warning("Algolia fetch failed for story_id=%s: %s", story_id, exc)
        return None

    if not data or data.get("type") not in ("story", None):
        # May be a comment, job, etc.
        pass

    created_str = data.get("created_at")
    created_at: Optional[datetime] = None
    story_age_seconds: Optional[float] = None

    if created_str:
        try:
            created_at = datetime.fromisoformat(created_str.rstrip("Z")).replace(tzinfo=timezone.utc)
            story_age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()
            story_age_seconds = max(60.0, story_age_seconds)
        except ValueError:
            pass

    return {
        "story_id":           str(data.get("objectID") or story_id),
        "title":              data.get("title") or "",
        "url":                data.get("url") or "",
        "author":             data.get("author") or "",
        "points":             int(data.get("points") or 0),
        "comment_count":      int(data.get("num_comments") or 0),
        "created_at":         created_at,
        "story_age_seconds":  story_age_seconds,
        "story_age_minutes":  round(story_age_seconds / 60, 2) if story_age_seconds else None,
    }


def fetch_newest_rank(story_id: str) -> Optional[int]:
    """
    Approximate the story's rank on /newest by searching Algolia for the
    story_id in the 'story' + 'front_page' tags and returning its position.
    Returns None if not found in the top 60 results (effectively unranked).

    NOTE: Algolia /newest != HN /newest exactly, but it's a close proxy.
    """
    try:
        resp = requests.get(
            ALGOLIA_SEARCH_URL,
            params={"tags": "story", "hitsPerPage": 60, "page": 0},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        for i, hit in enumerate(hits):
            if str(hit.get("objectID")) == str(story_id):
                return i + 1  # 1-indexed rank
    except requests.RequestException as exc:
        log.warning("Algolia rank fetch failed: %s", exc)
    return None


def fetch_story_with_rank(story_id: str) -> Optional[dict]:
    """
    Combines fetch_story + fetch_newest_rank into one call.
    Returns the story dict augmented with 'estimated_rank'.
    """
    story = fetch_story(story_id)
    if story is None:
        return None
    rank = fetch_newest_rank(story_id)
    story["estimated_rank"] = rank
    return story
