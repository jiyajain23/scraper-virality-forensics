"""
title_intelligence.py

Corpus-based title analysis for HN content writers.

Upgraded with:
  - N-gram (unigrams, bigrams, trigrams) keyphrase extraction
  - TF-IDF cosine semantic similarity against the high-engagement corpus
  - Multi-dimensional structural pattern scoring
  - Best posting time integration

Produces:
    data/processed/title_corpus.json   — cached corpus stats (refresh with build_corpus())
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PROCESSED_DIR  = Path("data/processed")
OBS_CSV        = PROCESSED_DIR / "all_observations.csv"
OVERLAP_CSV    = PROCESSED_DIR / "story_id_overlap.csv"
CORPUS_CACHE   = PROCESSED_DIR / "title_corpus.json"

HIGH_ENGAGEMENT_PERCENTILE = 0.75

_STOP = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "is","are","was","were","be","been","has","have","had","do","does","did",
    "i","my","we","our","you","your","its","it","this","that","these","those",
    "from","by","as","up","how","what","why","when","who","which","use","using",
    "can","will","new","get","make","show","hn","ask","launch","tell",
    "about","than","more","into","after","over","also","just","not","no",
    "vs","via","—","-",":","|","all","some","one","two","three","first","second",
    "every","find","part","way","itself","own","may","could","would","should",
    "like","good","bad","best","simple","easy","better","world","today",
}

_WORD_RE = re.compile(r"[A-Za-z0-9+#\.\-]{2,}")


def _extract_phrases(title: str) -> list[str]:
    """Extract salient unigrams, bigrams, and trigrams from title text."""
    if not title:
        return []
    clean = re.sub(r"^(show hn|ask hn|launch hn)\s*[:\-]?\s*", "", str(title), flags=re.I)
    raw_words = _WORD_RE.findall(clean)
    words = [w.lower().strip(".,:;()[]\"'") for w in raw_words]
    words = [w for w in words if w and len(w) >= 2]

    phrases: list[str] = []
    # Bigrams
    for i in range(len(words) - 1):
        w1, w2 = words[i], words[i+1]
        if w1 not in _STOP and w2 not in _STOP and not w1.isdigit() and not w2.isdigit():
            phrases.append(f"{w1} {w2}")

    # Trigrams
    for i in range(len(words) - 2):
        w1, w2, w3 = words[i], words[i+1], words[i+2]
        if w1 not in _STOP and w3 not in _STOP and not (w1.isdigit() and w3.isdigit()):
            phrases.append(f"{w1} {w2} {w3}")

    # Unigrams
    for w in words:
        if w not in _STOP and len(w) >= 4 and not w.isdigit():
            phrases.append(w)

    return list(set(phrases))


def _title_features(title: str) -> dict:
    t = str(title) if title else ""
    return {
        "length_chars":          len(t),
        "word_count":            len(t.split()),
        "has_question_mark":     "?" in t,
        "has_number":            bool(re.search(r"\d", t)),
        "has_colon":             ":" in t,
        "has_brackets":          bool(re.search(r"[\[\(]", t)),
        "starts_with_show_ask":  bool(re.match(r"^(Show HN|Ask HN|Launch HN)", t, re.I)),
        "all_caps_word":         bool(re.search(r"\b[A-Z]{3,}\b", t)),
    }


# ---------------------------------------------------------------------------
# Corpus builder
# ---------------------------------------------------------------------------

def build_corpus() -> dict:
    """
    Read all_observations.csv, extract features and n-grams for high/low engagement groups,
    and save summary statistics to title_corpus.json.
    """
    if not OBS_CSV.exists():
        raise FileNotFoundError(f"Run src.ingest first: {OBS_CSV} not found.")

    obs = pd.read_csv(OBS_CSV, dtype={"story_id": str})

    # Peak points per story
    peak = obs.groupby("story_id").agg(
        peak_points=("points", "max"),
        title=("title", "first"),
        story_url=("story_url", "first"),
        story_type=("story_type", "first"),
    ).reset_index().dropna(subset=["title"])

    # Label A: actual front-page crossovers
    label_a_ids: set[str] = set()
    if OVERLAP_CSV.exists():
        overlap = pd.read_csv(OVERLAP_CSV, dtype={"story_id": str})
        label_a_ids = set(overlap["story_id"].unique())

    threshold = float(peak["peak_points"].quantile(HIGH_ENGAGEMENT_PERCENTILE))
    peak["high_engagement"] = peak["peak_points"] >= threshold
    peak["label_a"] = peak["story_id"].isin(label_a_ids)

    # Compute features
    feat_rows = []
    for _, row in peak.iterrows():
        f = _title_features(row["title"])
        f.update({
            "story_id":        row["story_id"],
            "title":           row["title"],
            "story_url":       row.get("story_url", ""),
            "peak_points":     float(row["peak_points"]),
            "high_engagement": bool(row["high_engagement"]),
            "label_a":         bool(row["label_a"]),
        })
        feat_rows.append(f)
    feat_df = pd.DataFrame(feat_rows)

    high = feat_df[feat_df["high_engagement"]]
    low  = feat_df[~feat_df["high_engagement"]]

    numeric_features = ["length_chars", "word_count"]
    bool_features    = ["has_question_mark", "has_number", "has_colon",
                        "has_brackets", "starts_with_show_ask", "all_caps_word"]

    stats: dict = {
        "corpus_size":        int(len(feat_df)),
        "high_engagement_n":  int(len(high)),
        "low_engagement_n":   int(len(low)),
        "threshold_points":   float(threshold),
        "label_a_n":          int(feat_df["label_a"].sum()),
        "numeric": {},
        "boolean": {},
        "top_phrases_high":   [],
        "top_phrases_low":    [],
        "successful_titles":  [],
    }

    for feat in numeric_features:
        stats["numeric"][feat] = {
            "high_mean": round(float(high[feat].mean()), 2),
            "high_std":  round(float(high[feat].std()),  2),
            "low_mean":  round(float(low[feat].mean()),  2),
            "low_std":   round(float(low[feat].std()),   2),
            "high_p25":  round(float(high[feat].quantile(0.25)), 1),
            "high_p75":  round(float(high[feat].quantile(0.75)), 1),
        }

    for feat in bool_features:
        stats["boolean"][feat] = {
            "high_rate": round(float(high[feat].mean()), 4),
            "low_rate":  round(float(low[feat].mean()),  4),
        }

    # Top keyphrases in high-engagement vs low-engagement titles
    high_phrases = Counter()
    for t in high["title"]:
        for p in _extract_phrases(str(t)):
            high_phrases[p] += 1

    low_phrases = Counter()
    for t in low["title"]:
        for p in _extract_phrases(str(t)):
            low_phrases[p] += 1

    stats["top_phrases_high"] = [p for p, _ in high_phrases.most_common(50)]
    stats["top_phrases_low"]  = [p for p, _ in low_phrases.most_common(30)]

    # Successful title examples
    stats["successful_titles"] = (
        high[["story_id", "title", "story_url", "peak_points"]]
        .sort_values("peak_points", ascending=False)
        .head(100)
        .to_dict(orient="records")
    )

    CORPUS_CACHE.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    return stats


def _load_corpus() -> dict:
    """Load cached corpus, building it if not present."""
    if not CORPUS_CACHE.exists():
        return build_corpus()
    return json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# In-memory TF-IDF semantic matcher
# ---------------------------------------------------------------------------

_tfidf_vectorizer: Optional[TfidfVectorizer] = None
_tfidf_matrix = None
_corpus_titles: list[dict] = []


def _get_tfidf_engine():
    global _tfidf_vectorizer, _tfidf_matrix, _corpus_titles
    if _tfidf_vectorizer is None or not _corpus_titles:
        corpus = _load_corpus()
        _corpus_titles = corpus.get("successful_titles", [])
        if not _corpus_titles:
            return None, None, []
        titles_text = [s["title"] for s in _corpus_titles]
        _tfidf_vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            min_df=1,
            sublinear_tf=True,
        )
        _tfidf_matrix = _tfidf_vectorizer.fit_transform(titles_text)
    return _tfidf_vectorizer, _tfidf_matrix, _corpus_titles


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_title(title: str) -> dict:
    """
    Score a draft title against the HN corpus using N-grams, structural patterns,
    and TF-IDF semantic matching against top-performing titles.
    """
    corpus = _load_corpus()
    feats  = _title_features(title)
    flags: list[str] = []
    score  = 0.0
    max_score = 0.0

    # 1. Length & Cadence
    lc = feats["length_chars"]
    num_stats = corpus["numeric"]
    h_mean_len  = num_stats["length_chars"]["high_mean"]
    h_p25_len   = num_stats["length_chars"]["high_p25"]
    h_p75_len   = num_stats["length_chars"]["high_p75"]
    max_score += 2.0
    if h_p25_len <= lc <= h_p75_len:
        score += 2.0
        flags.append(f"✅ Length sweet spot ({lc} chars — top stories average {int(h_p25_len)}–{int(h_p75_len)} chars)")
    elif lc < h_p25_len:
        score += 0.7
        flags.append(f"⚠️ Short title ({lc} chars). Top performers average {h_mean_len:.0f} chars. Adding a differentiator helps.")
    else:
        score += 0.7
        flags.append(f"⚠️ Long title ({lc} chars). Top performers average {h_mean_len:.0f} chars. Consider trimming filler.")

    # 2. Word Count
    wc = feats["word_count"]
    h_mean_wc = num_stats["word_count"]["high_mean"]
    h_p25_wc  = num_stats["word_count"]["high_p25"]
    h_p75_wc  = num_stats["word_count"]["high_p75"]
    max_score += 1.5
    if h_p25_wc <= wc <= h_p75_wc:
        score += 1.5
        flags.append(f"✅ Word count ({wc} words — typical range {int(h_p25_wc)}–{int(h_p75_wc)})")
    else:
        score += 0.5
        flags.append(f"💡 Word count is {wc}. High-engagement titles average {h_mean_wc:.1f} words.")

    # 3. Structural & Format Markers
    bool_stats = corpus["boolean"]
    checks = [
        ("has_number", 1.5,
         "✅ Specific metric / number present (seen in {hr:.0%} of top titles)",
         "💡 Numbers (benchmarks, versions, scale) appear in {hr:.0%} of top titles"),
        ("has_colon", 1.0,
         "✅ Colon structure (e.g. 'Project: Value Prop') signals clear technical focus",
         "💡 A colon structure ('Product: One-line explanation') is common in {hr:.0%} of top posts"),
        ("starts_with_show_ask", 1.0,
         "✅ Show/Ask HN prefix detected — targets dedicated community discovery channels",
         None),
        ("has_brackets", 0.5,
         "✅ Technical bracket tag like [pdf] or [video] provides helpful context",
         None),
        ("has_question_mark", 0.5,
         "✅ Question format (seen in {hr:.0%} of top discussion posts)",
         None),
    ]
    for feat, weight, pos_msg, neg_msg in checks:
        hr = bool_stats[feat]["high_rate"]
        max_score += weight
        if feats[feat]:
            score += weight
            flags.append(pos_msg.format(hr=hr))
        elif neg_msg:
            flags.append(neg_msg.format(hr=hr))

    # 4. Multi-word Phrase & Keyphrase Matching
    title_phrases = set(_extract_phrases(title))
    top_phrases   = set(corpus.get("top_phrases_high", []))
    matched_phrases = sorted(title_phrases & top_phrases)

    max_score += 2.0
    phrase_score = min(len(matched_phrases) * 0.7, 2.0)
    score += phrase_score

    multi_word_matches = [p for p in matched_phrases if " " in p]
    single_word_matches = [p for p in matched_phrases if " " not in p]

    if multi_word_matches:
        flags.append(f"🔥 Strong topic phrases matched: {', '.join(multi_word_matches[:4])}")
    elif single_word_matches:
        flags.append(f"✅ Relevant tech terms matched: {', '.join(single_word_matches[:5])}")
    else:
        flags.append("💡 Title uses uncommon phrasing for HN. Framing around clear tech concepts (e.g., 'open source', 'Rust', 'local AI', 'compiler') improves discoverability.")

    # 5. Semantic Matcher via TF-IDF Cosine Similarity
    similar_successful: list[dict] = []
    try:
        vec, mat, stories_ref = _get_tfidf_engine()
        if vec is not None and mat is not None and stories_ref:
            q_vec = vec.transform([title])
            sims = cosine_similarity(q_vec, mat)[0]
            # Top 3 matches with similarity > 0.08
            top_idx = sims.argsort()[::-1]
            for idx in top_idx[:5]:
                if sims[idx] >= 0.08:
                    s_item = dict(stories_ref[idx])
                    s_item["similarity_score"] = round(float(sims[idx]), 2)
                    s_item["match_percentage"] = f"{int(sims[idx] * 100)}%"
                    similar_successful.append(s_item)
                if len(similar_successful) >= 3:
                    break
    except Exception:
        pass

    # Fallback to phrase overlap if TF-IDF gave zero matches
    if not similar_successful:
        for s in corpus.get("successful_titles", []):
            s_phrases = set(_extract_phrases(str(s.get("title", ""))))
            if title_phrases & s_phrases:
                s_copy = dict(s)
                s_copy["similarity_score"] = 0.15
                s_copy["match_percentage"] = "15%"
                similar_successful.append(s_copy)
            if len(similar_successful) >= 3:
                break

    # Normalise score to 0–10
    pattern_score = round(min(score / max_score * 10, 10.0), 1)

    # 6. Best Posting Time
    try:
        from src.live_feed import best_posting_time
        timing = best_posting_time()
        rec = timing.get("recommendation", {})
        best_time = {
            "best_day":      rec.get("best_day"),
            "best_hour_utc": rec.get("best_hour_utc"),
            "note":          rec.get("note", ""),
            "data_note":     timing.get("data_note", ""),
        }
    except Exception:
        best_time = {"note": "Timing analysis unavailable."}

    return {
        "title":                      title,
        "pattern_score":              pattern_score,
        "raw_features":               feats,
        "matched_keyphrases":         matched_phrases,
        "flags":                      flags,
        "similar_successful_titles":  similar_successful,
        "best_posting_time":          best_time,
        "corpus_info": {
            "total_stories":      corpus["corpus_size"],
            "high_engagement_n":  corpus["high_engagement_n"],
            "threshold_points":   corpus["threshold_points"],
        },
        "disclaimer": (
            "Pattern-based analysis derived from "
            f"{corpus['corpus_size']} Hacker News stories using N-Gram & TF-IDF similarity. "
            "This is not a guarantee of virality — it shows how closely your title aligns "
            "with successful historical conventions on Hacker News."
        ),
    }
