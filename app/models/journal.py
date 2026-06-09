from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class JournalEntryBase(BaseModel):
    """Base schema shared by create and response models."""

    mood: int = Field(
        ...,
        ge=1,
        le=10,
        description="Self-reported mood on a 1 (lowest) to 10 (highest) scale.",
    )
    text: str = Field(
        ...,
        min_length=1,
        description="Free-form journal entry text.",
    )
    date: Optional[datetime] = Field(
        default=None,
        description="Optional user-supplied date for the entry. "
        "Defaults to server time when not provided.",
    )


class JournalEntryCreate(JournalEntryBase):
    """Schema used when creating a new journal entry."""

    pass


class JournalEntryUpdate(BaseModel):
    """Schema used when updating an existing journal entry.

    All fields are optional so the client can send a partial patch.
    """

    mood: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Updated mood value (1-10).",
    )
    text: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Updated journal text.",
    )
    date: Optional[datetime] = None


class JournalEntryResponse(JournalEntryBase):
    """Full journal entry returned to the client, including emotion analysis.

    Field naming follows MongoDB document structure with UUID string IDs.
    """

    id: str = Field(..., description="UUID string identifier of the journal entry.")
    user_id: str = Field(..., description="UUID string identifier of the owning user.")
    date: datetime = Field(..., description="Date associated with the journal entry.")
    created_at: datetime = Field(..., description="Server timestamp when the entry was created.")
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Server timestamp of the last update, if any.",
    )

    # --- Emotion analysis fields ------------------------------------------
    emotion_label: Optional[str] = Field(
        default=None,
        description="Dominant emotion label (e.g. 'joy', 'sadness').",
    )
    emotion_confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence score for the dominant emotion (0.0 – 1.0).",
    )
    emotion_scores: Optional[dict] = Field(
        default=None,
        description="Full emotion probability distribution, e.g. {'joy': 0.85, 'sadness': 0.05, …}.",
    )
    emotion_analyzed: bool = Field(
        default=False,
        description="Whether emotion analysis has been attempted for this entry.",
    )

    model_config = {"from_attributes": True}

class MoodHistoryPoint(BaseModel):
    date: datetime
    mood: float


class MoodHistoryResponse(BaseModel):
    user_id: str
    period_days: int
    average_mood: Optional[float] = None
    entries: List[MoodHistoryPoint]

    model_config = {"from_attributes": True}


# Alias for backward compatibility with journal service
JournalEntry = JournalEntryResponse
