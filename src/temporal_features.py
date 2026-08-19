"""
temporal_features.py

Computes RAW temporal/observational features for each story_id, using only
information available AT or BEFORE each observation's own scraped_at
timestamp. No future information is used, and no label/target is computed
here.

Features computed per observation row:
    story_age_at_snapshot          -- hours since submission_time_est
    points                         -- carried through unchanged
    comment_count                  -- carried through unchanged
    rank                           -- carried through unchanged
    elapsed_time_since_previous_snapshot   -- hours since this story_id's
                                               previous observation (NaN for
                                               the first observation)
    points_change_since_previous_snapshot
    comments_change_since_previous_snapshot
    points_velocity                -- points_change / elapsed_time (per hour)
    comments_velocity              -- comments_change / elapsed_time (per hour)
    rank_change                    -- previous_rank - current_rank
                                       (positive = moved toward rank 1 / up)

All "previous" values are the immediately preceding observation of the SAME
story_id, ordered by scraped_at. This is a strictly backward-looking window,
so these features are safe to use for early-prediction modeling later.
"""

from __future__ import annotations

import pandas as pd


def compute_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["story_id", "scraped_at"]).copy()

    grouped = df.groupby("story_id", group_keys=False)

    df["story_age_at_snapshot"] = (
        df["scraped_at"] - df["submission_time_est"]
    ).dt.total_seconds() / 3600.0

    df["prev_scraped_at"] = grouped["scraped_at"].shift(1)
    df["prev_points"] = grouped["points"].shift(1)
    df["prev_comment_count"] = grouped["comment_count"].shift(1)
    df["prev_rank"] = grouped["rank"].shift(1)

    df["elapsed_time_since_previous_snapshot"] = (
        df["scraped_at"] - df["prev_scraped_at"]
    ).dt.total_seconds() / 3600.0

    df["points_change_since_previous_snapshot"] = df["points"] - df["prev_points"]
    df["comments_change_since_previous_snapshot"] = (
        df["comment_count"] - df["prev_comment_count"]
    )

    # rank_change: positive means the story moved UP the page (toward rank 1)
    df["rank_change"] = df["prev_rank"] - df["rank"]

    # Velocities are undefined (NaN) when there is no previous observation,
    # or when elapsed_time is zero (guards a div-by-zero if a collector ever
    # fires twice at the identical timestamp for some reason).
    safe_elapsed = df["elapsed_time_since_previous_snapshot"].replace(0, pd.NA)

    df["points_velocity"] = df["points_change_since_previous_snapshot"] / safe_elapsed
    df["comments_velocity"] = df["comments_change_since_previous_snapshot"] / safe_elapsed

    output_columns = [
        "story_id",
        "source_scraper",
        "scraped_at",
        "submission_time_est",
        "story_age_at_snapshot",
        "points",
        "comment_count",
        "rank",
        "elapsed_time_since_previous_snapshot",
        "points_change_since_previous_snapshot",
        "comments_change_since_previous_snapshot",
        "points_velocity",
        "comments_velocity",
        "rank_change",
        "title",
        "story_type",
    ]

    return df[output_columns].reset_index(drop=True)
