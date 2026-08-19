"""
analysis.py

Dataset diagnostics for the ingested observation-level dataset. Prints a
report and writes a story_id_overlap.csv showing which story_ids were seen
by both the newest and front_page collectors.

Nothing here computes a label or target variable.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SUBMISSION_TIME_DRIFT_THRESHOLD_MINUTES = 10


def validate_submission_time_consistency(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each story_id, submission_time_est should be roughly constant across
    repeated observations (it's derived from age_hours at each snapshot, so
    small variation is expected from rounding, but large drift usually means
    a parse error or -- more rarely -- a story_id being reused).

    Returns a DataFrame of story_ids whose submission_time_est standard
    deviation exceeds the threshold, for manual inspection.
    """
    valid = df.dropna(subset=["submission_time_est"])
    grouped = valid.groupby("story_id")["submission_time_est"]

    stats = grouped.agg(["std", "count"]).reset_index()
    stats = stats[stats["count"] >= 2]
    stats["std_minutes"] = stats["std"].dt.total_seconds() / 60.0

    flagged = stats[stats["std_minutes"] > SUBMISSION_TIME_DRIFT_THRESHOLD_MINUTES]
    return flagged.sort_values("std_minutes", ascending=False)


def compute_story_id_overlap(df: pd.DataFrame) -> pd.DataFrame:
    """
    Find story_ids observed by BOTH the newest and front_page collectors,
    and report the first-seen timestamp from each. This is the backbone of
    the early-signal -> later-outcome pairing this project needs, so it's
    written out as its own file rather than just a count.
    """
    first_seen = (
        df.dropna(subset=["scraped_at"])
        .groupby(["story_id", "source_scraper"])["scraped_at"]
        .min()
        .unstack("source_scraper")
    )

    for col in ("newest", "front_page"):
        if col not in first_seen.columns:
            first_seen[col] = pd.NaT

    overlap = first_seen.dropna(subset=["newest", "front_page"]).reset_index()
    overlap = overlap.rename(
        columns={"newest": "first_seen_newest", "front_page": "first_seen_front_page"}
    )
    overlap["hours_from_newest_to_front_page"] = (
        overlap["first_seen_front_page"] - overlap["first_seen_newest"]
    ).dt.total_seconds() / 3600.0

    return overlap.sort_values("first_seen_newest")


def run_diagnostics(
    df: pd.DataFrame,
    temporal_df: pd.DataFrame,
    num_files: int,
    overlap_output_path: Path,
) -> None:
    n_obs = len(df)
    n_unique_stories = df["story_id"].nunique()

    obs_per_story = df.groupby("story_id").size()

    time_span = None
    if df["scraped_at"].notna().any():
        time_span = df["scraped_at"].max() - df["scraped_at"].min()

    missing_counts = df[["points", "comment_count", "rank", "age_hours"]].isna().sum()

    n_observed_2plus = (obs_per_story >= 2).sum()
    n_observed_3plus = (obs_per_story >= 3).sum()
    n_observed_5plus = (obs_per_story >= 5).sum()

    drift_flags = validate_submission_time_consistency(df)

    overlap = compute_story_id_overlap(df)
    overlap.to_csv(overlap_output_path, index=False)

    points_desc = df["points"].describe()
    comments_desc = df["comment_count"].describe()

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("VIRALITY FORENSICS -- INGESTION REPORT")
    print("=" * 70)

    print(f"\nRaw files loaded:           {num_files}")
    print(f"Total observations:         {n_obs}")
    print(f"Unique story_ids:           {n_unique_stories}")
    if time_span is not None:
        print(f"Time span covered:          {time_span}")
    else:
        print("Time span covered:          N/A (no valid scraped_at values)")

    print("\n--- Observations per story ---")
    print(f"Stories observed >= 2 times: {n_observed_2plus}")
    print(f"Stories observed >= 3 times: {n_observed_3plus}")
    print(f"Stories observed >= 5 times: {n_observed_5plus}")
    print(f"Max observations for a single story: {obs_per_story.max() if len(obs_per_story) else 'N/A'}")

    print("\n--- Missing values ---")
    for col, count in missing_counts.items():
        pct = 100 * count / n_obs if n_obs else 0
        print(f"  {col:15s}: {count} missing ({pct:.1f}%)")

    print("\n--- submission_time_est consistency ---")
    if drift_flags.empty:
        print("  No story_ids exceeded the "
              f"{SUBMISSION_TIME_DRIFT_THRESHOLD_MINUTES}-minute drift threshold. Good.")
    else:
        print(f"  {len(drift_flags)} story_id(s) exceeded "
              f"{SUBMISSION_TIME_DRIFT_THRESHOLD_MINUTES} min drift -- inspect these:")
        print(drift_flags.to_string(index=False))

    print("\n--- points distribution ---")
    print(points_desc.to_string())

    print("\n--- comment_count distribution ---")
    print(comments_desc.to_string())

    print("\n--- Cross-collector overlap (newest -> front_page) ---")
    print(f"  story_ids seen in BOTH collectors: {len(overlap)}")
    if not overlap.empty:
        print(f"  Written to: {overlap_output_path}")
        print(overlap.head(10).to_string(index=False))
    else:
        print("  None found yet. This is expected with a short collection "
              "window -- a story needs enough time to travel from /newest "
              "to the front page. This is the key metric to watch as more "
              "snapshots accumulate.")

    print("\n--- Readiness assessment ---")
    if n_observed_3plus < 5:
        print("  NOT YET sufficient for label/target design: fewer than 5 "
              "story_ids currently have 3+ observations. Temporal features "
              "(velocity, acceleration) are unreliable with this little "
              "repeated coverage. Keep collecting before defining a "
              "'high-growth' label or training anything.")
    else:
        print("  Baseline repeated-observation coverage looks reasonable. "
              "Still recommend waiting for meaningful newest -> front_page "
              "overlap before defining the high-growth label, since that's "
              "what the early-prediction target depends on.")

    print("=" * 70 + "\n")
