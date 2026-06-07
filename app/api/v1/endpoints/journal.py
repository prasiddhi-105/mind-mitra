"""Journal entry CRUD endpoints.

Provides authenticated endpoints to create, read, update, and delete journal
entries stored in MongoDB.  After a journal entry is saved, emotion analysis is
run asynchronously via the HuggingFace emotion service and the result is fed
into the depression-flag pipeline.  Emotion analysis failures are logged but
**never** block a successful save.
"""

from datetime import datetime
from typing import Dict, List, Optional

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_collection
from app.core.logging import get_logger
from app.models.journal import (
    JournalEntryCreate,
    JournalEntryResponse,
    JournalEntryUpdate,
)
from app.models.user import User
from app.services.huggingface_emotion import hf_emotion_service
from app.services.depression_flags import depression_flag_service

logger = get_logger("journal")

router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc_to_response(doc: dict) -> JournalEntryResponse:
    """Convert a MongoDB document to a ``JournalEntryResponse``.

    Strips the internal ``_id`` field so Pydantic does not choke and maps
    the application-level ``id`` field instead.
    """
    doc.pop("_id", None)
    return JournalEntryResponse(**doc)


async def _get_owned_entry(entry_id: str, user_id: str) -> dict:
    """Fetch a journal entry and verify it belongs to *user_id*.

    Raises:
        HTTPException 404: entry does not exist.
        HTTPException 403: entry belongs to another user.
    """
    collection = get_collection("journal_entries")
    doc = await collection.find_one({"id": entry_id})

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Journal entry not found.",
        )

    if doc.get("user_id") != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this journal entry.",
        )

    return doc


async def _run_emotion_analysis(
    entry_id: str,
    text: str,
    user_id: str,
) -> Optional[Dict]:
    """Run emotion analysis and persist the result.

    Returns the emotion fields dict on success, ``None`` on failure.
    This helper is intentionally wrapped so callers can treat it as
    fire-and-forget.
    """
    try:
        result = await hf_emotion_service.analyze(text)

        if result is None:
            logger.warning(
                "Emotion analysis returned None for entry %s", entry_id
            )
            return None

        emotion_fields: Dict = {
            "emotion_label": result.label,
            "emotion_confidence": result.confidence,
            "emotion_scores": result.scores,
            "emotion_analyzed": True,
        }

        collection = get_collection("journal_entries")
        await collection.update_one(
            {"id": entry_id},
            {"$set": emotion_fields},
        )

        # Feed into the depression-flag pipeline
        emotion_data = {
            "dominant_emotion": emotion_fields["emotion_label"],
            "confidence": emotion_fields["emotion_confidence"],
        }
        await depression_flag_service.process_emotion(
            user_id, emotion_data, source="journal"
        )

        logger.info(
            "Emotion analysis completed for entry %s — %s (%.2f)",
            entry_id,
            emotion_fields["emotion_label"],
            emotion_fields["emotion_confidence"] or 0.0,
        )
        return emotion_fields

    except Exception:
        logger.exception(
            "Emotion analysis failed for entry %s — entry was saved "
            "successfully without emotion data",
            entry_id,
        )
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/journal",
    summary="List journal entries",
    description=(
        "Returns journal entries for the authenticated user, sorted by "
        "``created_at`` descending (newest first)."
    ),
    response_model=List[JournalEntryResponse],
    responses={
        200: {
            "description": "List of journal entries",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                            "user_id": "u1234567-89ab-cdef-0123-456789abcdef",
                            "mood": 4,
                            "text": "Had a great day at work today!",
                            "date": "2024-06-01T14:30:00Z",
                            "created_at": "2024-06-01T14:30:00Z",
                            "updated_at": None,
                            "emotion_label": "joy",
                            "emotion_confidence": 0.92,
                            "emotion_scores": {
                                "joy": 0.92,
                                "sadness": 0.02,
                                "anger": 0.01,
                            },
                            "emotion_analyzed": True,
                        }
                    ]
                }
            },
        }
    },
)
async def list_journal_entries(
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of entries to return.",
    ),
    current_user: User = Depends(get_current_user),
) -> List[JournalEntryResponse]:
    """Retrieve journal entries for the authenticated user.

    Results are ordered from newest to oldest and capped at *limit*.
    """
    collection = get_collection("journal_entries")

    cursor = (
        collection.find({"user_id": current_user.id})
        .sort("created_at", -1)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)

    logger.info(
        "Listed %d journal entries for user %s", len(docs), current_user.id
    )
    return [_doc_to_response(doc) for doc in docs]


@router.post(
    "/journal",
    summary="Create a journal entry",
    description=(
        "Create a new journal entry. Emotion analysis runs automatically "
        "after the entry is persisted and will **never** prevent a "
        "successful save."
    ),
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {
            "description": "Journal entry created successfully",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "user_id": "u1234567-89ab-cdef-0123-456789abcdef",
                        "mood": 4,
                        "text": "Today was amazing! I accomplished all my goals.",
                        "date": "2024-06-02T18:45:00Z",
                        "created_at": "2024-06-02T18:45:00Z",
                        "updated_at": None,
                        "emotion_label": "joy",
                        "emotion_confidence": 0.95,
                        "emotion_scores": {
                            "joy": 0.95,
                            "surprise": 0.03,
                            "neutral": 0.02,
                        },
                        "emotion_analyzed": True,
                    }
                }
            },
        }
    },
)
async def create_journal_entry(
    entry: JournalEntryCreate = Body(
        ...,
        openapi_examples={
            "happy_day": {
                "summary": "Positive journal entry",
                "value": {
                    "mood": 4,
                    "text": (
                        "Today was amazing! I accomplished all my goals "
                        "and felt very productive."
                    ),
                    "date": "2024-06-02T18:45:00Z",
                },
            },
            "tough_day": {
                "summary": "Entry without explicit date (server time used)",
                "value": {
                    "mood": 2,
                    "text": "Had a challenging day but learned something new.",
                },
            },
        },
    ),
    current_user: User = Depends(get_current_user),
) -> JournalEntryResponse:
    """Create a new journal entry for the authenticated user.

    The ``date`` field is optional; if omitted the server uses the current
    UTC time.  After the document is inserted, emotion analysis is
    executed and the results are merged back into the document.
    """
    now = datetime.utcnow()
    entry_id = str(uuid.uuid4())

    doc = {
        "id": entry_id,
        "user_id": current_user.id,
        "mood": entry.mood,
        "text": entry.text,
        "date": entry.date or now,
        "created_at": now,
        "updated_at": None,
        # Emotion fields — will be overwritten after analysis
        "emotion_label": None,
        "emotion_confidence": None,
        "emotion_scores": None,
        "emotion_analyzed": False,
    }

    collection = get_collection("journal_entries")
    await collection.insert_one(doc)
    logger.info("Created journal entry %s for user %s", entry_id, current_user.id)

    # Run emotion analysis (never blocks a successful save)
    emotion_fields = await _run_emotion_analysis(
        entry_id, entry.text, current_user.id
    )

    if emotion_fields:
        doc.update(emotion_fields)

    return _doc_to_response(doc)


@router.get(
    "/journal/{entry_id}",
    summary="Get a journal entry",
    description="Retrieve a single journal entry by ID. Ownership is verified.",
    response_model=JournalEntryResponse,
    responses={
        200: {
            "description": "Journal entry retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "user_id": "u1234567-89ab-cdef-0123-456789abcdef",
                        "mood": 3,
                        "text": "A regular day, nothing special.",
                        "date": "2024-06-01T10:00:00Z",
                        "created_at": "2024-06-01T10:00:00Z",
                        "updated_at": None,
                        "emotion_label": "neutral",
                        "emotion_confidence": 0.78,
                        "emotion_scores": {"neutral": 0.78, "joy": 0.12},
                        "emotion_analyzed": True,
                    }
                }
            },
        },
        404: {"description": "Journal entry not found"},
        403: {"description": "Not authorised to access this entry"},
    },
)
async def get_journal_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
) -> JournalEntryResponse:
    """Retrieve a single journal entry owned by the authenticated user."""
    doc = await _get_owned_entry(entry_id, current_user.id)
    logger.info("Retrieved journal entry %s for user %s", entry_id, current_user.id)
    return _doc_to_response(doc)


@router.put(
    "/journal/{entry_id}",
    summary="Update a journal entry",
    description=(
        "Partially update a journal entry. If the ``text`` field is changed "
        "emotion analysis is re-run automatically."
    ),
    response_model=JournalEntryResponse,
    responses={
        200: {
            "description": "Journal entry updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "user_id": "u1234567-89ab-cdef-0123-456789abcdef",
                        "mood": 5,
                        "text": "Updated: Today was the best day ever!",
                        "date": "2024-06-02T18:45:00Z",
                        "created_at": "2024-06-02T18:45:00Z",
                        "updated_at": "2024-06-02T19:00:00Z",
                        "emotion_label": "joy",
                        "emotion_confidence": 0.97,
                        "emotion_scores": {"joy": 0.97, "surprise": 0.02},
                        "emotion_analyzed": True,
                    }
                }
            },
        },
        404: {"description": "Journal entry not found"},
        403: {"description": "Not authorised to access this entry"},
    },
)
async def update_journal_entry(
    entry_id: str,
    updates: JournalEntryUpdate = Body(
        ...,
        openapi_examples={
            "update_mood": {
                "summary": "Update only the mood",
                "value": {"mood": 5},
            },
            "update_text": {
                "summary": "Update the text (triggers re-analysis)",
                "value": {"text": "Updated: Today was the best day ever!"},
            },
        },
    ),
    current_user: User = Depends(get_current_user),
) -> JournalEntryResponse:
    """Update an existing journal entry owned by the authenticated user.

    Only fields present in the request body are modified.  When ``text``
    is updated, emotion analysis is re-run and the old results are
    replaced.
    """
    doc = await _get_owned_entry(entry_id, current_user.id)

    # Build the $set payload from non-None fields
    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update.",
        )

    update_data["updated_at"] = datetime.utcnow()

    text_changed = "text" in update_data and update_data["text"] != doc.get("text")

    # If text changed, reset emotion fields before re-analysis
    if text_changed:
        update_data.update(
            {
                "emotion_label": None,
                "emotion_confidence": None,
                "emotion_scores": None,
                "emotion_analyzed": False,
            }
        )

    collection = get_collection("journal_entries")
    await collection.update_one({"id": entry_id}, {"$set": update_data})

    logger.info(
        "Updated journal entry %s for user %s (fields: %s)",
        entry_id,
        current_user.id,
        ", ".join(update_data.keys()),
    )

    # Re-run emotion analysis if text was changed
    if text_changed:
        emotion_fields = await _run_emotion_analysis(
            entry_id, update_data["text"], current_user.id
        )
        if emotion_fields:
            update_data.update(emotion_fields)

    # Merge updates into the original doc to build the response
    doc.update(update_data)
    return _doc_to_response(doc)


@router.delete(
    "/journal/{entry_id}",
    summary="Delete a journal entry",
    description="Permanently delete a journal entry. Ownership is verified.",
    responses={
        200: {
            "description": "Journal entry deleted",
            "content": {
                "application/json": {
                    "example": {"message": "Journal entry deleted"}
                }
            },
        },
        404: {"description": "Journal entry not found"},
        403: {"description": "Not authorised to access this entry"},
    },
)
async def delete_journal_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a journal entry owned by the authenticated user."""
    await _get_owned_entry(entry_id, current_user.id)

    collection = get_collection("journal_entries")
    await collection.delete_one({"id": entry_id})

    logger.info(
        "Deleted journal entry %s for user %s", entry_id, current_user.id
    )
    return {"message": "Journal entry deleted"}