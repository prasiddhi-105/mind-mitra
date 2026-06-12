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

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status

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
from app.services.cache import cache_service, journal_list_cache_key
from app.services.journal import journal_service

logger = get_logger("journal")
router = APIRouter()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _doc_to_response(doc: dict) -> JournalEntryResponse:
    doc.pop("_id", None)
    return JournalEntryResponse(**doc)

async def _get_owned_entry(entry_id: str, user_id: str) -> dict:
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
    try:
        result = await hf_emotion_service.analyze(text)

        if result is None:
            logger.warning("Emotion analysis returned None for entry %s", entry_id)
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
    description="Returns journal entries for the authenticated user. "
    "Responses include an `X-Cache` header (`HIT` or `MISS`) indicating "
    "whether the data was served from Redis.",
    response_model=List[JournalEntryResponse],
)
async def list_journal_entries(
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),  
    current_user: User = Depends(get_current_user),
) -> List[JournalEntryResponse]:
    """Retrieve journal entries for the authenticated user."""
    cache_key = journal_list_cache_key(current_user.id)
    cached = await cache_service.get_json(cache_key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        # Since cache contains basic models, we will load full response from db
        # Actually cache might not have emotion fields.
        pass
    
    # We fetch directly from DB to include emotion fields if they were missed by cache
    collection = get_collection("journal_entries")
    total_count = await collection.count_documents({"user_id": current_user.id}) #counting total entries
    cursor = (
        collection.find({"user_id": current_user.id})
        .sort("created_at", -1)
        .skip(offset)
        .limit(limit)
    )
    docs = await cursor.to_list(length=limit)
    
    response.headers["X-Cache"] = "MISS"

    #adding pagination to metadata
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["X-Has-Next"] = str(offset + limit < total_count)

    return [_doc_to_response(doc) for doc in docs]


@router.post(
    "/journal",
    summary="Create a journal entry",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_journal_entry(
    entry: JournalEntryCreate = Body(...),
    current_user: User = Depends(get_current_user),
) -> JournalEntryResponse:
    """Create a new journal entry for the authenticated user."""
    # Use journal_service to create the base entry and handle caching
    created_entry = await journal_service.create_entry(current_user.id, entry)
    
    # Get the raw doc
    doc = await _get_owned_entry(created_entry.id, current_user.id)
    
    # Run emotion analysis asynchronously
    emotion_fields = await _run_emotion_analysis(
        created_entry.id, entry.text, current_user.id
    )

    if emotion_fields:
        doc.update(emotion_fields)

    return _doc_to_response(doc)


@router.get(
    "/journal/{entry_id}",
    summary="Get a journal entry",
    description="Retrieve a single journal entry by ID. Ownership is verified.",
    response_model=JournalEntryResponse,
)
async def get_journal_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
) -> JournalEntryResponse:
    """Retrieve a single journal entry owned by the authenticated user."""
    doc = await _get_owned_entry(entry_id, current_user.id)
    return _doc_to_response(doc)


@router.put(
    "/journal/{entry_id}",
    summary="Update a journal entry",
    response_model=JournalEntryResponse,
)
async def update_journal_entry(
    entry_id: str,
    updates: JournalEntryUpdate = Body(...),
    current_user: User = Depends(get_current_user),
) -> JournalEntryResponse:
    """Update an existing journal entry for the authenticated user."""
    updated = await journal_service.update_entry(current_user.id, entry_id, updates)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")
        
    doc = await _get_owned_entry(entry_id, current_user.id)
    
    text_changed = updates.text is not None
    if text_changed:
        emotion_fields = await _run_emotion_analysis(
            entry_id, updates.text, current_user.id
        )
        if emotion_fields:
            doc.update(emotion_fields)
            
    return _doc_to_response(doc)


@router.delete(
    "/journal/{entry_id}",
    summary="Delete a journal entry",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_journal_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user),
):
    """Delete a journal entry for the authenticated user."""
    deleted = await journal_service.delete_entry(current_user.id, entry_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journal entry not found")

