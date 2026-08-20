"""
schema.py

Pydantic request / response models for the Virality Forensics API.

All feature fields are Optional[float] so the pipeline's MedianImputer
handles any missing values gracefully — callers do not need to fill gaps
before calling the API.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Feature inputs
# ---------------------------------------------------------------------------

class StoryFeatures(BaseModel):
    """
    Early-engagement features for a single Hacker News story measured at the
    15-minute prediction horizon.  All fields are optional; missing values are
    imputed with training-set medians by the model pipeline.
    """

    early_points: Optional[float] = Field(
        default=None, description="Point count at or before the prediction cutoff"
    )
    early_comments: Optional[float] = Field(
        default=None, description="Comment count at or before the prediction cutoff"
    )
    early_rank: Optional[float] = Field(
        default=None, description="Story rank at the last observed snapshot before cutoff"
    )
    points_velocity: Optional[float] = Field(
        default=None, description="Points gained per hour since the previous snapshot"
    )
    comments_velocity: Optional[float] = Field(
        default=None, description="Comments added per hour since the previous snapshot"
    )
    rank_change: Optional[float] = Field(
        default=None,
        description="prev_rank - current_rank (positive = moved toward rank 1)",
    )
    observation_count_early: Optional[float] = Field(
        default=None,
        description="Number of scraper observations within the prediction window",
    )
    title_length: Optional[float] = Field(
        default=None, description="Character length of the story title"
    )
    title_word_count: Optional[float] = Field(
        default=None, description="Word count of the story title"
    )
    title_has_question_mark: Optional[float] = Field(
        default=None, description="1 if title contains '?', else 0"
    )
    title_has_number: Optional[float] = Field(
        default=None, description="1 if title contains any digit, else 0"
    )
    engagement_ratio: Optional[float] = Field(
        default=None,
        description="early_comments / early_points (NaN when early_points == 0)",
    )

    model_config = {"json_schema_extra": {
        "example": {
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
    }}


class StoryFeaturesWithId(BaseModel):
    """StoryFeatures with an optional story_id for batch requests."""

    story_id: Optional[str] = Field(default=None, description="HN story ID (echoed in response)")
    features: StoryFeatures


# ---------------------------------------------------------------------------
# Prediction outputs
# ---------------------------------------------------------------------------

class PredictionResponse(BaseModel):
    """Prediction result for a single story."""

    story_id: Optional[str] = Field(default=None, description="Echoed from request if provided")
    p_viral: float = Field(
        description="Probability that the story reaches top-20% eventual engagement (Label B)"
    )
    prediction_default: bool = Field(
        description="Binary prediction at threshold = 0.50"
    )
    prediction_f1_optimal: bool = Field(
        description="Binary prediction at F1-optimal threshold = 0.778"
    )
    horizon: str = Field(default="15 min", description="Prediction window used")
    model_version: str = Field(default="v1", description="Model artifact version")
    note: str = Field(
        default="Label B: quota-based top-20% by eventual max points. "
                "Positive rate ≈ 19%. Use p_viral for ranking; thresholds are illustrative.",
    )


class BatchRequest(BaseModel):
    """Up to 500 stories for a single batch prediction call."""

    stories: list[StoryFeaturesWithId] = Field(
        description="List of stories to score (max 500)"
    )

    model_config = {"json_schema_extra": {
        "example": {
            "stories": [
                {
                    "story_id": "49366792",
                    "features": {
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
                    },
                }
            ]
        }
    }}


class BatchResponse(BaseModel):
    predictions: list[PredictionResponse]


# ---------------------------------------------------------------------------
# Collect trigger
# ---------------------------------------------------------------------------

class CollectRequest(BaseModel):
    collector: str = Field(
        description="Collector name to trigger. One of: 'newest', 'front_page'"
    )

    model_config = {"json_schema_extra": {"example": {"collector": "newest"}}}


class CollectResponse(BaseModel):
    collector: str
    collection_id: str
    status: str = "triggered"
    message: str
