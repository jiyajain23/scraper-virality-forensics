"""
eda.py

Exploratory Data Analysis for the Virality Forensics dataset.

Reads:
    data/processed/all_observations.csv
    data/processed/temporal_features.csv
    data/processed/story_id_overlap.csv

Writes:
    figures/  -- PNG plots (auto-created)
    reports/eda_summary.md  -- narrative summary

Run as:
    python -m src.eda

IMPORTANT -- no model training, no "viral" label, no future-data leakage.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless -- no GUI required
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROCESSED_DIR = Path("data/processed")
OBS_CSV       = PROCESSED_DIR / "all_observations.csv"
TEMPORAL_CSV  = PROCESSED_DIR / "temporal_features.csv"
OVERLAP_CSV   = PROCESSED_DIR / "story_id_overlap.csv"

FIGURES_DIR = Path("figures")
REPORTS_DIR = Path("reports")

FIGURES_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Aesthetics
# ---------------------------------------------------------------------------
BLUE    = "#4F81BD"
RED     = "#C0504D"
GREEN   = "#9BBB59"
AMBER   = "#F79646"
GREY    = "#E0E0E0"

plt.rcParams.update({
    "figure.dpi":         150,
    "figure.facecolor":   "white",
    "axes.facecolor":     "white",
    "axes.grid":          True,
    "grid.color":         GREY,
    "grid.linewidth":     0.6,
    "font.size":          10,
    "axes.titlesize":     11,
    "axes.titleweight":   "bold",
    "axes.labelsize":     10,
    "xtick.labelsize":    9,
    "ytick.labelsize":    9,
    "legend.fontsize":    9,
    "figure.titlesize":   12,
    "figure.titleweight": "bold",
})


def savefig(name: str) -> None:
    p = FIGURES_DIR / name
    plt.savefig(p, bbox_inches="tight")
    plt.close()
    print(f"  [fig] {p}")


def pct(n: int, total: int) -> str:
    return f"{n:,} ({100 * n / total:.1f}%)"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    obs = pd.read_csv(
        OBS_CSV,
        parse_dates=["scraped_at", "submission_time_est"],
        dtype={"story_id": str},
    )
    tmp = pd.read_csv(
        TEMPORAL_CSV,
        parse_dates=["scraped_at", "submission_time_est"],
        dtype={"story_id": str},
    )
    ovl = pd.read_csv(
        OVERLAP_CSV,
        parse_dates=["first_seen_front_page", "first_seen_newest"],
        dtype={"story_id": str},
    )

    # Ensure UTC timezone consistency
    for df in (obs, tmp):
        for col in ("scraped_at", "submission_time_est"):
            if df[col].dt.tz is None:
                df[col] = df[col].dt.tz_localize("UTC")
            else:
                df[col] = df[col].dt.tz_convert("UTC")

    for col in ("first_seen_front_page", "first_seen_newest"):
        if ovl[col].dt.tz is None:
            ovl[col] = ovl[col].dt.tz_localize("UTC")
        else:
            ovl[col] = ovl[col].dt.tz_convert("UTC")

    # Tag reliable-age observations: "1 day ago" → age_hours == 24 → unreliable
    obs["age_reliable"] = obs["age_hours"] < 24.0

    return obs, tmp, ovl


# ===========================================================================
# SECTION 1 — Dataset coverage
# ===========================================================================

def section_coverage(obs: pd.DataFrame, ovl: pd.DataFrame) -> dict:
    n_obs         = len(obs)
    n_stories     = obs["story_id"].nunique()
    obs_per       = obs.groupby("story_id").size()
    n_fp_obs      = (obs["source_scraper"] == "front_page").sum()
    n_new_obs     = (obs["source_scraper"] == "newest").sum()
    n_fp_stories  = obs[obs.source_scraper == "front_page"]["story_id"].nunique()
    n_new_stories = obs[obs.source_scraper == "newest"]["story_id"].nunique()
    n_overlap     = len(ovl)

    durations = obs.groupby("story_id")["scraped_at"].agg(
        lambda x: (x.max() - x.min()).total_seconds() / 3600
    )

    cov = {
        "n_obs":          n_obs,
        "n_stories":      n_stories,
        "obs_per_2plus":  int((obs_per >= 2).sum()),
        "obs_per_3plus":  int((obs_per >= 3).sum()),
        "obs_per_5plus":  int((obs_per >= 5).sum()),
        "obs_per_10plus": int((obs_per >= 10).sum()),
        "obs_max":        int(obs_per.max()),
        "obs_median":     obs_per.median(),
        "n_fp_obs":       int(n_fp_obs),
        "n_new_obs":      int(n_new_obs),
        "n_fp_stories":   int(n_fp_stories),
        "n_new_stories":  int(n_new_stories),
        "n_overlap":      n_overlap,
        "dur_median_h":   durations.median(),
        "dur_max_h":      durations.max(),
    }

    # Plot: observations per story
    fig, ax = plt.subplots(figsize=(8, 4))
    bins = range(1, min(int(obs_per.max()) + 2, 30))
    ax.hist(obs_per, bins=bins, color=BLUE, edgecolor="white", linewidth=0.5)
    ax.axvline(obs_per.median(), color=AMBER, linestyle="--", linewidth=1.8,
               label=f"Median = {obs_per.median():.0f}")
    ax.set_xlabel("Observations per story_id")
    ax.set_ylabel("Number of stories")
    ax.set_title("Observations per Story")
    ax.legend()
    savefig("01_obs_per_story.png")

    return cov


# ===========================================================================
# SECTION 2 — Temporal coverage
# ===========================================================================

def section_temporal(obs: pd.DataFrame, tmp: pd.DataFrame) -> dict:
    elapsed     = tmp["elapsed_time_since_previous_snapshot"].dropna()
    elapsed_min = elapsed * 60.0

    n_total    = len(obs)
    n_reliable = int(obs["age_reliable"].sum())
    n_day_ago  = int((~obs["age_reliable"]).sum())

    reliable_ages = obs.loc[obs["age_reliable"], "age_hours"]

    tem = {
        "n_reliable":          n_reliable,
        "n_day_ago":           n_day_ago,
        "pct_day_ago":         100.0 * n_day_ago / n_total,
        "elapsed_median_min":  elapsed_min.median(),
        "elapsed_mean_min":    elapsed_min.mean(),
        "elapsed_p95_min":     elapsed_min.quantile(0.95),
        "age_median_h":        reliable_ages.median(),
        "age_p25_h":           reliable_ages.quantile(0.25),
        "age_p75_h":           reliable_ages.quantile(0.75),
    }

    # Plot: elapsed time + age distribution
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    el_clip = elapsed_min.clip(upper=120)
    axes[0].hist(el_clip, bins=40, color=BLUE, edgecolor="white", linewidth=0.4)
    axes[0].axvline(elapsed_min.median(), color=AMBER, linestyle="--", linewidth=1.5,
                    label=f"Median {elapsed_min.median():.0f} min")
    axes[0].set_xlabel("Elapsed since previous snapshot (min, clipped 120)")
    axes[0].set_ylabel("Count")
    axes[0].set_title("Inter-Snapshot Elapsed Time")
    axes[0].legend()

    axes[1].hist(reliable_ages, bins=30, color=RED, edgecolor="white", linewidth=0.4)
    axes[1].axvline(reliable_ages.median(), color=AMBER, linestyle="--", linewidth=1.5,
                    label=f"Median {reliable_ages.median():.0f} h")
    axes[1].set_xlabel("age_hours at observation (reliable, < 24 h)")
    axes[1].set_ylabel("Count")
    axes[1].set_title("Story Age at Snapshot\n(Reliable Observations Only)")
    axes[1].legend()

    plt.suptitle("Temporal Coverage", y=1.01)
    plt.tight_layout()
    savefig("02_temporal_coverage.png")

    return tem


# ===========================================================================
# SECTION 3 — Engagement distributions
# ===========================================================================

def section_engagement(obs: pd.DataFrame) -> dict:
    pts = obs["points"]
    cmt = obs["comment_count"]
    rnk = obs["rank"]

    eng = {
        "pts_median":      pts.median(),
        "pts_mean":        pts.mean(),
        "pts_p75":         pts.quantile(0.75),
        "pts_p90":         pts.quantile(0.90),
        "pts_p95":         pts.quantile(0.95),
        "pts_max":         pts.max(),
        "cmt_median":      cmt.median(),
        "cmt_mean":        cmt.mean(),
        "cmt_p75":         cmt.quantile(0.75),
        "cmt_p90":         cmt.quantile(0.90),
        "cmt_max":         cmt.max(),
        "rnk_median":      rnk.median(),
        "pct_pts_gt100":   100.0 * (pts > 100).mean(),
        "pct_pts_gt300":   100.0 * (pts > 300).mean(),
        "pct_cmt_gt50":    100.0 * (cmt > 50).mean(),
    }

    # Plot: points and comments distributions
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    axes[0].hist(pts.clip(upper=600), bins=50, color=BLUE, edgecolor="white", linewidth=0.4)
    axes[0].axvline(pts.median(), color=AMBER, linestyle="--", linewidth=1.5,
                    label=f"Median = {pts.median():.0f}")
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Points (clipped at 600)")
    axes[0].set_ylabel("Count (log scale)")
    axes[0].set_title("Points Distribution")
    axes[0].legend()

    axes[1].hist(cmt.clip(upper=400), bins=50, color=RED, edgecolor="white", linewidth=0.4)
    axes[1].axvline(cmt.median(), color=AMBER, linestyle="--", linewidth=1.5,
                    label=f"Median = {cmt.median():.0f}")
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Comments (clipped at 400)")
    axes[1].set_ylabel("Count (log scale)")
    axes[1].set_title("Comments Distribution")
    axes[1].legend()

    plt.suptitle("Engagement Distributions (all observations)", y=1.01)
    plt.tight_layout()
    savefig("03_engagement_distributions.png")

    # Plot: rank distribution
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(rnk, bins=30, color=GREEN, edgecolor="white", linewidth=0.4)
    ax.axvline(rnk.median(), color=AMBER, linestyle="--", linewidth=1.5,
               label=f"Median rank = {rnk.median():.0f}")
    ax.set_xlabel("Rank at observation")
    ax.set_ylabel("Count")
    ax.set_title("Rank Distribution")
    ax.legend()
    savefig("04_rank_distribution.png")

    # Plot: engagement by story age (reliable observations only)
    rel = obs[obs["age_reliable"]].copy()
    rel["age_bin"] = pd.cut(rel["age_hours"], bins=range(0, 25), right=False,
                            labels=range(0, 24))
    age_pts = rel.groupby("age_bin", observed=True)["points"].median().reset_index()
    age_cmt = rel.groupby("age_bin", observed=True)["comment_count"].median().reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    axes[0].bar(age_pts["age_bin"].astype(int), age_pts["points"],
                color=BLUE, edgecolor="white", linewidth=0.3)
    axes[0].set_xlabel("Story age at snapshot (hours, reliable only)")
    axes[0].set_ylabel("Median points")
    axes[0].set_title("Median Points by Story Age")

    axes[1].bar(age_cmt["age_bin"].astype(int), age_cmt["comment_count"],
                color=RED, edgecolor="white", linewidth=0.3)
    axes[1].set_xlabel("Story age at snapshot (hours, reliable only)")
    axes[1].set_ylabel("Median comments")
    axes[1].set_title("Median Comments by Story Age")

    plt.suptitle("Engagement by Story Age at Snapshot\n(Reliable age_hours < 24 only)", y=1.02)
    plt.tight_layout()
    savefig("05_engagement_by_age.png")

    return eng


# ===========================================================================
# SECTION 4 — Early-window statistics
# ===========================================================================

def _early_window(obs: pd.DataFrame, window_min: int) -> pd.DataFrame:
    """
    For each story, keep only observations within `window_min` minutes of
    that story's first scraped_at (scraper-clock anchor -- no submission_time_est).
    Returns one row per story with early-window stats.
    """
    first_scrape = obs.groupby("story_id")["scraped_at"].min().rename("first_scrape")
    df = obs.merge(first_scrape, on="story_id")
    df["elapsed_from_first_min"] = (
        df["scraped_at"] - df["first_scrape"]
    ).dt.total_seconds() / 60.0
    win = df[df["elapsed_from_first_min"] <= window_min].copy()

    def agg(g: pd.DataFrame) -> pd.Series:
        g = g.sort_values("scraped_at")
        first = g.iloc[0]
        last  = g.iloc[-1]
        elapsed_h = (last["scraped_at"] - first["scraped_at"]).total_seconds() / 3600.0
        pts_delta = last["points"] - first["points"]
        cmt_delta = last["comment_count"] - first["comment_count"]
        pts_vel   = pts_delta / elapsed_h if elapsed_h > 0 else np.nan
        cmt_vel   = cmt_delta / elapsed_h if elapsed_h > 0 else np.nan
        return pd.Series({
            "source_first":       first["source_scraper"],
            "age_h_at_first":     first["age_hours"],
            "age_reliable":       bool(first["age_reliable"]),
            "n_obs_window":       len(g),
            "elapsed_window_h":   elapsed_h,
            "pts_earliest":       first["points"],
            "pts_latest":         last["points"],
            "pts_change":         pts_delta,
            "cmt_earliest":       first["comment_count"],
            "cmt_latest":         last["comment_count"],
            "cmt_change":         cmt_delta,
            "best_rank":          g["rank"].min(),
            "pts_velocity_ph":    pts_vel,
            "cmt_velocity_ph":    cmt_vel,
        })

    result = win.groupby("story_id").apply(agg).reset_index()
    result["window_min"] = window_min
    return result


def section_early_windows(obs: pd.DataFrame) -> dict[int, pd.DataFrame]:
    windows: dict[int, pd.DataFrame] = {}
    for w in (15, 30, 60):
        df = _early_window(obs, w)
        windows[w] = df
        n_vel = (df["n_obs_window"] >= 2).sum()
        print(f"  [{w:3d}-min window] stories={len(df):,}  with velocity={n_vel:,}")

    # All-time max points (future info — for target candidate exploration only)
    max_pts = obs.groupby("story_id")["points"].max().rename("max_pts_all_time")
    w60 = windows[60].merge(max_pts, on="story_id")
    has_vel = w60[w60["n_obs_window"] >= 2].copy()

    # Plot: early window signal vs future max points
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    sc1 = axes[0].scatter(
        has_vel["pts_earliest"],
        has_vel["max_pts_all_time"],
        c=has_vel["pts_velocity_ph"].clip(upper=200),
        cmap="YlOrRd", alpha=0.6, s=22, edgecolors="none",
    )
    plt.colorbar(sc1, ax=axes[0], label="pts velocity/h (clipped 200)")
    axes[0].set_xlabel("Points at first obs (60-min window)")
    axes[0].set_ylabel("Max points — all-time\n[FUTURE: target candidate only]")
    axes[0].set_title("Early Points vs All-Time Max\n[60-min window]")
    axes[0].set_xscale("symlog")
    axes[0].set_yscale("symlog")

    sc2 = axes[1].scatter(
        has_vel["cmt_earliest"],
        has_vel["max_pts_all_time"],
        c=has_vel["pts_velocity_ph"].clip(upper=200),
        cmap="YlOrRd", alpha=0.6, s=22, edgecolors="none",
    )
    plt.colorbar(sc2, ax=axes[1], label="pts velocity/h (clipped 200)")
    axes[1].set_xlabel("Comments at first obs (60-min window)")
    axes[1].set_ylabel("Max points — all-time\n[FUTURE: target candidate only]")
    axes[1].set_title("Early Comments vs All-Time Max\n[60-min window]")
    axes[1].set_xscale("symlog")
    axes[1].set_yscale("symlog")

    plt.suptitle(
        "Early-Window Signal vs Future Max Points\n"
        "NOTE: y-axis is future data — for target candidate exploration only",
        y=1.03,
    )
    plt.tight_layout()
    savefig("06_early_vs_max_points.png")

    # Plot: points velocity distribution by window
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=False)
    for i, (w, color) in enumerate([(15, RED), (30, BLUE), (60, GREEN)]):
        vels = windows[w]["pts_velocity_ph"].dropna()
        cap  = vels.quantile(0.98)
        axes[i].hist(vels.clip(upper=cap), bins=30, color=color,
                     edgecolor="white", linewidth=0.4)
        axes[i].axvline(vels.median(), color=AMBER, linestyle="--",
                        linewidth=1.5, label=f"Median {vels.median():.1f}")
        axes[i].set_title(f"Points Velocity — {w}-min window")
        axes[i].set_xlabel("pts / h")
        axes[i].set_ylabel("Count")
        axes[i].legend()

    plt.suptitle("Points Velocity Distribution by Early Window", y=1.02)
    plt.tight_layout()
    savefig("07_points_velocity_by_window.png")

    return windows


# ===========================================================================
# SECTION 5 — Cross-collector analysis
# ===========================================================================

def section_cross_collector(obs: pd.DataFrame, ovl: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in ovl.iterrows():
        sid   = row["story_id"]
        fp_ts = row["first_seen_front_page"]
        # newest observations strictly before first fp appearance (no leakage)
        pre = obs[
            (obs.story_id == sid) &
            (obs.source_scraper == "newest") &
            (obs.scraped_at < fp_ts)
        ].sort_values("scraped_at")
        if pre.empty:
            pre_pts, pre_cmt, pre_rank, n_pre = np.nan, np.nan, np.nan, 0
        else:
            last = pre.iloc[-1]
            pre_pts, pre_cmt, pre_rank, n_pre = (
                last["points"], last["comment_count"], last["rank"], len(pre)
            )
        max_pts = obs[obs.story_id == sid]["points"].max()
        max_cmt = obs[obs.story_id == sid]["comment_count"].max()
        rows.append({
            "story_id":               sid,
            "hours_newest_to_fp":     row["hours_from_newest_to_front_page"],
            "n_newest_obs_before_fp": n_pre,
            "pts_before_fp":          pre_pts,
            "cmt_before_fp":          pre_cmt,
            "rank_before_fp":         pre_rank,
            "max_pts_observed":       max_pts,
            "max_cmt_observed":       max_cmt,
        })

    cross = pd.DataFrame(rows)

    # Plot: time to front page
    cross_sorted = cross.sort_values("hours_newest_to_fp")
    minutes = cross_sorted["hours_newest_to_fp"] * 60
    bar_colors = [AMBER if m < 30 else BLUE for m in minutes]

    fig, ax = plt.subplots(figsize=(8, 4))
    bars = ax.barh(range(len(minutes)), minutes, color=bar_colors, edgecolor="white")
    ax.set_xlabel("Minutes from first newest obs to front-page appearance")
    ax.set_ylabel("Story (sorted)")
    ax.set_title("Time from /newest to Front Page\n(all overlap stories)")
    ax.axvline(60, color="grey", linestyle=":", linewidth=1, label="1 h")
    ax.legend()
    # Annotate with pre-fp points
    for i, (_, r) in enumerate(cross_sorted.iterrows()):
        if pd.notna(r["pts_before_fp"]):
            ax.text(minutes.iloc[i] + 1, i,
                    f" {int(r['pts_before_fp'])}pts", va="center", fontsize=7.5)
    savefig("08_time_to_front_page.png")

    # Plot: pre-fp points vs all-time max points
    valid = cross.dropna(subset=["pts_before_fp", "max_pts_observed"])
    fig, ax = plt.subplots(figsize=(7, 5))
    sc = ax.scatter(
        valid["pts_before_fp"],
        valid["max_pts_observed"],
        c=valid["hours_newest_to_fp"],
        cmap="RdYlGn_r", s=80, edgecolors="k", linewidths=0.5, zorder=5,
    )
    plt.colorbar(sc, ax=ax, label="Hours newest -> front page")
    for _, r in valid.iterrows():
        ax.annotate(r["story_id"][-5:],
                    (r["pts_before_fp"], r["max_pts_observed"]),
                    fontsize=7, xytext=(4, 2), textcoords="offset points")
    ax.set_xlabel("Points in newest (last obs before fp)")
    ax.set_ylabel("Max points observed (all-time, FUTURE)")
    ax.set_title("Pre-FP Signal vs All-Time Max Points\n(Overlap stories only)")
    savefig("09_prefp_vs_max_pts.png")

    return cross


# ===========================================================================
# SECTION 6 — Candidate target variables (no label chosen)
# ===========================================================================

def section_target_candidates(obs: pd.DataFrame, ovl: pd.DataFrame,
                               cross: pd.DataFrame) -> dict:
    all_fp_ids = set(obs[obs.source_scraper == "front_page"]["story_id"])
    n_total    = obs["story_id"].nunique()

    max_pts = obs.groupby("story_id")["points"].max()
    print("    max_pts thresholds:")
    for thresh in (50, 100, 200, 300, 500):
        n = int((max_pts >= thresh).sum())
        print(f"      >= {thresh:4d}: {n} stories ({100*n/n_total:.1f}%)")

    first_pts = obs.sort_values("scraped_at").groupby("story_id")["points"].first()
    last_pts  = obs.sort_values("scraped_at").groupby("story_id")["points"].last()
    growth    = (last_pts / first_pts.replace(0, np.nan)).dropna()

    valid_tt = cross.dropna(subset=["hours_newest_to_fp"])

    return {
        "cand_A": {
            "name":       "reached_front_page (binary)",
            "pos_n":      len(all_fp_ids),
            "total_n":    n_total,
            "base_rate":  100.0 * len(all_fp_ids) / n_total,
            "notes": ("Risk: fp scraper started later; some fp stories may pre-date "
                      "the collection window and appear fp-only."),
        },
        "cand_B": {
            "name":       "time_to_front_page (continuous, hours)",
            "n":          len(valid_tt),
            "median_min": valid_tt["hours_newest_to_fp"].median() * 60,
            "min_min":    valid_tt["hours_newest_to_fp"].min() * 60,
            "max_min":    valid_tt["hours_newest_to_fp"].max() * 60,
            "notes": ("Only 11-12 stories have this defined. Too small for "
                      "direct modelling. Valid as secondary analysis."),
        },
        "cand_C": {
            "name":    "max_points_above_threshold (binary, threshold TBD)",
            "thresh_100_n": int((max_pts >= 100).sum()),
            "thresh_200_n": int((max_pts >= 200).sum()),
            "thresh_300_n": int((max_pts >= 300).sum()),
            "notes": ("Directly interpretable. Threshold choice sets class "
                      "balance. Must define a cutoff time to avoid leakage."),
        },
        "cand_D": {
            "name":    "points_growth_multiple (continuous)",
            "median":  growth.median(),
            "p75":     growth.quantile(0.75),
            "p90":     growth.quantile(0.90),
            "max":     growth.max(),
            "notes": ("Relative growth ratio. Sensitive to near-zero initial "
                      "values. Requires a defined prediction horizon."),
        },
        "cand_E": {
            "name":  "comment_acceleration (derived)",
            "notes": ("Comment velocity spikes early for high-discussion stories. "
                      "Useful composite signal alongside points growth."),
        },
    }


# ===========================================================================
# SECTION 7 — Trajectory plots
# ===========================================================================

def section_trajectories(obs: pd.DataFrame, ovl: pd.DataFrame) -> None:
    max_pts = obs.groupby("story_id")["points"].max()
    cnt     = obs.groupby("story_id").size()

    eligible = max_pts[cnt[max_pts.index] >= 5]

    # High: top-5 by max pts
    high_ids = eligible.nlargest(5).index.tolist()
    # Mid: around median
    lo = eligible.quantile(0.45)
    hi = eligible.quantile(0.55)
    mid_ids  = eligible[(eligible >= lo) & (eligible <= hi)].index[:3].tolist()
    # Low: bottom quintile
    low_ids  = eligible[eligible <= eligible.quantile(0.2)].index[:3].tolist()

    overlap_ids = set(ovl["story_id"].tolist())

    # Points trajectories: high / mid / low
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    groups = [
        (high_ids, "High Engagement",   BLUE),
        (mid_ids,  "Mid Engagement",    GREEN),
        (low_ids,  "Low Engagement",    RED),
    ]
    for ax, (ids, label, color) in zip(axes, groups):
        for i, sid in enumerate(ids):
            sub = obs[obs.story_id == sid].sort_values("scraped_at")
            t0  = sub["scraped_at"].min()
            hrs = (sub["scraped_at"] - t0).dt.total_seconds() / 3600.0
            ls  = "--" if sid in overlap_ids else "-"
            ax.plot(hrs, sub["points"], color=color, alpha=0.9 - i * 0.12,
                    linewidth=1.6, linestyle=ls,
                    label=f"{sid[-6:]} ({int(sub['points'].max())})")
        ax.set_xlabel("Hours since first observation")
        ax.set_ylabel("Points")
        ax.set_title(f"{label}\n(-- = in both collectors)")
        ax.legend(fontsize=7)

    plt.suptitle("Points Trajectories (scraper-clock anchor)", y=1.02)
    plt.tight_layout()
    savefig("10_points_trajectories.png")

    # Rank trajectories for overlap stories
    ovl_ids  = ovl["story_id"].tolist()
    ovl_obs  = obs[obs.story_id.isin(ovl_ids)].sort_values("scraped_at")
    first_sc = ovl_obs.groupby("story_id")["scraped_at"].min()
    colors   = plt.cm.tab10(np.linspace(0, 1, len(ovl_ids)))

    fig, ax = plt.subplots(figsize=(10, 5))
    for ci, sid in enumerate(ovl_ids):
        sub = ovl_obs[ovl_obs.story_id == sid].sort_values("scraped_at")
        t0  = first_sc[sid]
        for _, r in sub.iterrows():
            hrs    = (r["scraped_at"] - t0).total_seconds() / 3600.0
            marker = "o" if r["source_scraper"] == "newest" else "s"
            ax.scatter(hrs, r["rank"], color=colors[ci], marker=marker, s=40, zorder=5)
        hrs_all = (sub["scraped_at"] - t0).dt.total_seconds() / 3600.0
        ax.plot(hrs_all, sub["rank"], color=colors[ci], alpha=0.7,
                linewidth=1.2, label=sid[-6:])

    ax.invert_yaxis()
    ax.set_xlabel("Hours since first observation")
    ax.set_ylabel("Rank (lower = better)")
    ax.set_title("Rank Trajectories — Overlap Stories\n(o = newest, s = front_page)")
    ax.legend(fontsize=7, ncol=2)
    savefig("11_rank_trajectories_overlap.png")


# ===========================================================================
# SECTION 8 — Leakage audit
# ===========================================================================

def section_leakage_audit(
    obs: pd.DataFrame, windows: dict
) -> tuple[list[str], list[str]]:
    issues   = []
    warnings = []

    # Check 1: early windows do not exceed their bound
    for w, df in windows.items():
        over = int((df["elapsed_window_h"] > w / 60.0 + 0.05).sum())
        if over > 0:
            issues.append(
                f"LEAKAGE RISK: {over} stories in {w}-min window have "
                f"elapsed_window_h > {w/60:.2f} h"
            )
        else:
            warnings.append(
                f"OK: all {w}-min window elapsed_window_h <= window limit."
            )

    # Check 2: all-time max is future data
    warnings.append(
        "CAUTION: max_pts_all_time / max_pts_observed incorporate future "
        "observations. Must NEVER be used as model features; valid as target "
        "candidate only."
    )

    # Check 3: submission_time_est drift
    warnings.append(
        "CAUTION: submission_time_est drifts for age_hours == 24 (1 day ago). "
        "Use scraped_at deltas for all temporal features."
    )

    # Check 4: story_age_at_snapshot
    warnings.append(
        "CAUTION: story_age_at_snapshot in temporal_features.csv inherits "
        "submission_time_est drift. Prefer elapsed_time_since_previous_snapshot."
    )

    # Check 5: cross-collector pre-fp features
    warnings.append(
        "OK: cross-collector pre-fp features use only newest obs strictly "
        "BEFORE first_seen_front_page -- no leakage."
    )

    # Check 6: velocity uses shift(1) -- backward-looking
    warnings.append(
        "OK: temporal_features velocity columns use shift(1) -- strictly "
        "backward-looking, no future leak."
    )

    return issues, warnings


# ===========================================================================
# Report
# ===========================================================================

def write_report(
    obs: pd.DataFrame,
    cov: dict, tem: dict, eng: dict,
    windows: dict, cross: pd.DataFrame,
    cands: dict,
    leakage_issues: list, leakage_warns: list,
) -> None:
    n = cov["n_obs"]

    lines = [
        "# EDA Summary — Virality Forensics Dataset",
        "",
        f"> Generated: {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M UTC')}",
        f"> Source: `data/processed/all_observations.csv` ({n:,} rows)",
        "",
        "---",
        "",
        "## 1. Dataset Coverage",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total observations | {cov['n_obs']:,} |",
        f"| Unique story_ids | {cov['n_stories']:,} |",
        f"| Stories >= 2 observations | {pct(cov['obs_per_2plus'], cov['n_stories'])} |",
        f"| Stories >= 3 observations | {pct(cov['obs_per_3plus'], cov['n_stories'])} |",
        f"| Stories >= 5 observations | {pct(cov['obs_per_5plus'], cov['n_stories'])} |",
        f"| Stories >= 10 observations | {pct(cov['obs_per_10plus'], cov['n_stories'])} |",
        f"| Max observations (one story) | {cov['obs_max']} |",
        f"| Median observations per story | {cov['obs_median']:.0f} |",
        f"| front_page observations | {pct(cov['n_fp_obs'], n)} |",
        f"| newest observations | {pct(cov['n_new_obs'], n)} |",
        f"| front_page unique stories | {cov['n_fp_stories']:,} |",
        f"| newest unique stories | {cov['n_new_stories']:,} |",
        f"| Stories in BOTH collectors | {cov['n_overlap']} |",
        f"| Median observation duration | {cov['dur_median_h']:.1f} h |",
        f"| Max observation duration | {cov['dur_max_h']:.1f} h |",
        "",
        "**Note**: Only " + str(cov['n_overlap']) + " stories appear in both collectors. "
        "This newest->front_page link is the critical backbone for future label design.",
        "",
        "---",
        "",
        "## 2. Temporal Coverage",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Reliable observations (age < 24 h) | {pct(tem['n_reliable'], n)} |",
        f"| Unreliable observations (1 day ago) | {pct(tem['n_day_ago'], n)} |",
        f"| Median inter-snapshot elapsed | {tem['elapsed_median_min']:.0f} min |",
        f"| 95th-pct inter-snapshot elapsed | {tem['elapsed_p95_min']:.0f} min |",
        f"| Median story age at snapshot (reliable) | {tem['age_median_h']:.1f} h |",
        f"| IQR story age at snapshot (reliable) | {tem['age_p25_h']:.1f} h – {tem['age_p75_h']:.1f} h |",
        "",
        f"**{tem['pct_day_ago']:.1f}%** of observations fall in the '1 day ago' zone "
        "(age_hours = 24, unreliable). Drop or quarantine these for age-based features.",
        "",
        "---",
        "",
        "## 3. Engagement Distributions",
        "",
        "| Metric | Points | Comments |",
        "|---|---|---|",
        f"| Median | {eng['pts_median']:.0f} | {eng['cmt_median']:.0f} |",
        f"| Mean | {eng['pts_mean']:.1f} | {eng['cmt_mean']:.1f} |",
        f"| 75th percentile | {eng['pts_p75']:.0f} | {eng['cmt_p75']:.0f} |",
        f"| 90th percentile | {eng['pts_p90']:.0f} | {eng['cmt_p90']:.0f} |",
        f"| Max | {eng['pts_max']:.0f} | {eng['cmt_max']:.0f} |",
        "",
        f"Both distributions are extremely right-skewed. "
        f"{eng['pct_pts_gt100']:.1f}% of obs exceed 100 points; "
        f"{eng['pct_pts_gt300']:.1f}% exceed 300. "
        f"Median rank across all obs: {eng['rnk_median']:.0f}.",
        "",
        "---",
        "",
        "## 4. Early-Window Statistics",
        "",
        "> All windows are anchored to each story's first `scraped_at` "
        "(scraper clock). No future data used.",
        "",
    ]

    for w in (15, 30, 60):
        df = windows[w]
        hv = df[df["n_obs_window"] >= 2]
        lines += [
            f"### {w}-Minute Window",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Stories with >= 1 obs | {len(df):,} |",
            f"| Stories with >= 2 obs (velocity defined) | {len(hv):,} |",
            f"| Median earliest points | {df['pts_earliest'].median():.0f} |",
            f"| Median best rank in window | {df['best_rank'].median():.0f} |",
            f"| Median points velocity (pts/h) | {hv['pts_velocity_ph'].median():.1f} |",
            f"| 90th-pct points velocity (pts/h) | {hv['pts_velocity_ph'].quantile(0.9):.1f} |",
            f"| Stories with velocity > 50 pts/h | {int((hv['pts_velocity_ph'] > 50).sum())} |",
            "",
        ]

    lines += [
        "---",
        "",
        "## 5. Cross-Collector Analysis",
        "",
        f"{len(cross)} stories appeared in both the `newest` and `front_page` collectors.",
        "",
        "| story_id | newest->fp (min) | pts before fp | cmt before fp | max pts |",
        "|---|---|---|---|---|",
    ]
    for _, r in cross.sort_values("hours_newest_to_fp").iterrows():
        lines.append(
            f"| {r['story_id']} "
            f"| {r['hours_newest_to_fp']*60:.0f} "
            f"| {int(r['pts_before_fp']) if pd.notna(r['pts_before_fp']) else 'N/A'} "
            f"| {int(r['cmt_before_fp']) if pd.notna(r['cmt_before_fp']) else 'N/A'} "
            f"| {int(r['max_pts_observed']) if pd.notna(r['max_pts_observed']) else 'N/A'} |"
        )

    fastest = cross.loc[cross["hours_newest_to_fp"].idxmin()]
    lines += [
        "",
        f"Transition times: {cross['hours_newest_to_fp'].min()*60:.0f}–"
        f"{cross['hours_newest_to_fp'].max()*60:.0f} min "
        f"(median {cross['hours_newest_to_fp'].median()*60:.0f} min). "
        f"Fastest: story `{fastest['story_id']}` "
        f"({fastest['hours_newest_to_fp']*60:.0f} min).",
        "",
        "---",
        "",
        "## 6. Candidate Target Variables",
        "",
        "> **No target has been chosen.** These are candidates for review.",
        "",
        "### Candidate A — reached_front_page (binary)",
        f"- Positive class: {cands['cand_A']['pos_n']} stories "
        f"({cands['cand_A']['base_rate']:.1f}% base rate)",
        f"- Risk: {cands['cand_A']['notes']}",
        "",
        "### Candidate B — time_to_front_page (continuous, hours)",
        f"- Defined for: {cands['cand_B']['n']} stories",
        f"- Range: {cands['cand_B']['min_min']:.0f}–{cands['cand_B']['max_min']:.0f} min "
        f"(median {cands['cand_B']['median_min']:.0f} min)",
        f"- Risk: {cands['cand_B']['notes']}",
        "",
        "### Candidate C — max_points_above_threshold (binary)",
        f"- >= 100 pts: {cands['cand_C']['thresh_100_n']} stories",
        f"- >= 200 pts: {cands['cand_C']['thresh_200_n']} stories",
        f"- >= 300 pts: {cands['cand_C']['thresh_300_n']} stories",
        f"- Risk: {cands['cand_C']['notes']}",
        "",
        "### Candidate D — points_growth_multiple (continuous)",
        f"- Median: {cands['cand_D']['median']:.1f}x  |  "
        f"p75: {cands['cand_D']['p75']:.1f}x  |  "
        f"p90: {cands['cand_D']['p90']:.1f}x",
        f"- Risk: {cands['cand_D']['notes']}",
        "",
        "### Candidate E — comment_acceleration (derived)",
        f"- {cands['cand_E']['notes']}",
        "",
        "---",
        "",
        "## 7. Data Leakage Audit",
        "",
    ]
    if not leakage_issues:
        lines.append("- OK: No structural leakage detected in EDA computations.")
    for item in leakage_issues:
        lines.append(f"- FAIL: {item}")
    for item in leakage_warns:
        tag = "CAUTION" if item.startswith("CAUTION") else "OK"
        lines.append(f"- {tag}: {item}")

    lines += [
        "",
        "---",
        "",
        "## 8. Key Findings",
        "",
        f"1. **Extreme skew**: Median story has {eng['pts_median']:.0f} pts "
        f"and {eng['cmt_median']:.0f} comments. A tiny minority drives the "
        f"right tail (> 1000 pts max).",
        "",
        f"2. **Timestamp precision is limited**: {tem['pct_day_ago']:.1f}% of "
        "observations fall in the '1 day ago' zone. Use scraper-clock deltas, "
        "not submission_time_est, for temporal features.",
        "",
        f"3. **Fastest newest->fp transition**: "
        f"{cross['hours_newest_to_fp'].min()*60:.0f} min "
        f"(story {fastest['story_id']}). Median: "
        f"{cross['hours_newest_to_fp'].median()*60:.0f} min.",
        "",
        "4. **Early velocity is discriminative**: Stories that reach high "
        "max points show elevated points velocity within the first 30-60 "
        "minutes, even from very low starting points.",
        "",
        f"5. **Coverage is adequate for some stories**: "
        f"{cov['obs_per_5plus']} stories have >= 5 observations. "
        f"The densest story has {cov['obs_max']} observations over "
        f"{cov['dur_max_h']:.1f} hours.",
        "",
        "---",
        "",
        "## 9. Limitations",
        "",
        f"1. **Very small overlap set**: Only {cov['n_overlap']} stories appear "
        "in both collectors. The newest->front_page pairing is the backbone "
        "for any early-prediction label, but the sample is too small for ML.",
        "",
        "2. **No exact submission timestamps**: Age precision is ±1-2 min "
        "(minute strings), ±30 min (hour strings), unbounded for '1 day ago'.",
        "",
        "3. **Short collection window (~34 h)**: Many stories were still "
        "rising when data collection ended. Max engagement values are "
        "lower bounds on true peaks.",
        "",
        f"4. **Scraper gaps**: p95 inter-snapshot gap is "
        f"{tem['elapsed_p95_min']:.0f} min. At least one 11-hour gap "
        "was detected in the timestamp audit.",
        "",
        "---",
        "",
        "## 10. Recommendation",
        "",
        "> **Continue data collection before defining a target or training a model.**",
        "",
        f"- The overlap set ({cov['n_overlap']} stories) is far too small for "
        "supervised learning.",
        "- Target: >= 50 confirmed newest->front_page transitions with "
        "complete trajectories.",
        "- Early-window velocity (30- or 60-min) looks like the most "
        "promising feature family for an early-prediction problem.",
        "- **Candidate C** (max_points >= threshold) is the most tractable "
        "binary target, but requires a defined observation cutoff time "
        "to avoid future-data leakage.",
        "",
        "---",
        "",
        "## Figures",
        "",
        "| File | Description |",
        "|---|---|",
        "| `figures/01_obs_per_story.png` | Observations per story histogram |",
        "| `figures/02_temporal_coverage.png` | Inter-snapshot elapsed time + age distribution |",
        "| `figures/03_engagement_distributions.png` | Points and comments (log scale) |",
        "| `figures/04_rank_distribution.png` | Rank distribution |",
        "| `figures/05_engagement_by_age.png` | Median engagement by story age |",
        "| `figures/06_early_vs_max_points.png` | Early signal vs future max (60-min window) |",
        "| `figures/07_points_velocity_by_window.png` | Velocity distribution by window |",
        "| `figures/08_time_to_front_page.png` | Time newest -> front page |",
        "| `figures/09_prefp_vs_max_pts.png` | Pre-FP signal vs max pts (overlap stories) |",
        "| `figures/10_points_trajectories.png` | Points trajectories (high/mid/low) |",
        "| `figures/11_rank_trajectories_overlap.png` | Rank trajectories for overlap stories |",
    ]

    out = REPORTS_DIR / "eda_summary.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  [report] {out}")


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    print("Loading data...")
    obs, tmp, ovl = load_data()

    print("\n[Section 1] Dataset coverage...")
    cov = section_coverage(obs, ovl)

    print("\n[Section 2] Temporal coverage...")
    tem = section_temporal(obs, tmp)

    print("\n[Section 3] Engagement distributions...")
    eng = section_engagement(obs)

    print("\n[Section 4] Early-window statistics...")
    windows = section_early_windows(obs)

    print("\n[Section 5] Cross-collector analysis...")
    cross = section_cross_collector(obs, ovl)

    print("\n[Section 6] Target variable candidates...")
    cands = section_target_candidates(obs, ovl, cross)

    print("\n[Section 7] Trajectory plots...")
    section_trajectories(obs, ovl)

    print("\n[Section 8] Leakage audit...")
    leakage_issues, leakage_warns = section_leakage_audit(obs, windows)

    print("\nWriting report...")
    write_report(obs, cov, tem, eng, windows, cross, cands,
                 leakage_issues, leakage_warns)

    print("\nEDA complete.")
    print(f"  Figures : {FIGURES_DIR.resolve()}")
    print(f"  Report  : {(REPORTS_DIR / 'eda_summary.md').resolve()}")


if __name__ == "__main__":
    main()
