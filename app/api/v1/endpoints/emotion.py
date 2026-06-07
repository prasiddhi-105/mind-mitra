"""
Emotion detection endpoint.

Accepts text or base64-encoded image input, analyses the content for
emotional signals, and returns the dominant emotion with confidence
scores.  Text analysis is backed by the HuggingFace Inference API;
image analysis is planned but not yet implemented.

Depression-flag bookkeeping is performed on every request so that
threshold notifications can be triggered when warranted.
"""

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Optional

from app.api.v1.endpoints.auth import get_current_user
from app.core.logging import get_logger
from app.models.user import User
from app.services.depression_flags import depression_flag_service
from app.services.huggingface_emotion import hf_emotion_service

logger = get_logger("emotion_endpoint")

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class EmotionRequest(BaseModel):
    """Payload for emotion detection.

    Supply *either* ``text`` or ``image_base64`` (or both).  At least one
    field must be provided.
    """

    text: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=5000,
        description="Plain-text input to analyse for emotion.",
    )
    image_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded image for facial emotion detection (not yet implemented).",
    )


class EmotionResponse(BaseModel):
    """Result of emotion detection."""

    emotion: str = Field(
        ...,
        description="Dominant detected emotion (e.g. 'joy', 'sadness', 'anger').",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence for the dominant emotion.",
    )
    emotion_scores: Optional[Dict[str, float]] = Field(
        default=None,
        description=(
            "Full mapping of emotion labels to their confidence scores "
            "as returned by the model.  ``None`` when no model scores "
            "are available (e.g. image-only requests or fallback mode)."
        ),
    )
    depression_flag_count: int = Field(
        default=0,
        description="Number of depression-related flags in the current rolling window.",
    )
    threshold_exceeded: bool = Field(
        default=False,
        description="Whether the depression-flag threshold has been exceeded.",
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FALLBACK_EMOTION = "neutral"
_FALLBACK_CONFIDENCE = 0.5

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


@router.post(
    "/emotion",
    summary="Detect emotion from text or image",
    response_model=EmotionResponse,
    responses={
        200: {
            "description": "Emotion detection result",
            "content": {
                "application/json": {
                    "example": {
                        "emotion": "sadness",
                        "confidence": 0.95,
                        "emotion_scores": {
                            "sadness": 0.95,
                            "joy": 0.01,
                            "anger": 0.02,
                            "fear": 0.01,
                            "surprise": 0.005,
                            "disgust": 0.005,
                        },
                        "depression_flag_count": 2,
                        "threshold_exceeded": False,
                    }
                }
            },
        },
        400: {"description": "No input provided"},
        503: {"description": "Upstream emotion-analysis service unavailable"},
    },
)
async def detect_emotion(
    request: EmotionRequest = Body(
        ...,
        examples=[
            {
                "summary": "Text emotion detection",
                "value": {
                    "text": "I feel so sad and hopeless",
                    "image_base64": None,
                },
            },
            {
                "summary": "Image emotion detection (placeholder)",
                "value": {
                    "text": None,
                    "image_base64": "iVBORw0KGgoAAAANSUhE...",
                },
            },
        ],
    ),
    current_user: User = Depends(get_current_user),
) -> EmotionResponse:
    """Detect emotion from provided text or base64-encoded image.

    **Text input** is sent to the HuggingFace Inference API via
    ``hf_emotion_service``.  If the upstream service is unreachable or
    returns an error the endpoint falls back to a neutral / 0.5-confidence
    response rather than failing the request.

    **Image input** is accepted but not yet analysed — a placeholder
    neutral result is returned while image support is under development.

    The detected emotion is also forwarded to the depression-flag service
    so that rolling-window thresholds can be evaluated.
    """

    # ------------------------------------------------------------------
    # Validate that at least one input modality is present
    # ------------------------------------------------------------------
    if not request.text and not request.image_base64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'text' or 'image_base64' must be provided.",
        )

    emotion: str = _FALLBACK_EMOTION
    confidence: float = _FALLBACK_CONFIDENCE
    emotion_scores: Optional[Dict[str, float]] = None

    # ------------------------------------------------------------------
    # Text-based emotion analysis (HuggingFace Inference API)
    # ------------------------------------------------------------------
    if request.text:
        logger.info(
            "Analysing text emotion for user %s (length=%d)",
            current_user.id,
            len(request.text),
        )

        try:
            result = await hf_emotion_service.analyze(request.text)
        except Exception:
            logger.exception(
                "Unexpected error calling hf_emotion_service.analyze for user %s",
                current_user.id,
            )
            result = None

        if result is not None:
            emotion = result.label
            confidence = result.confidence
            emotion_scores = result.scores
            logger.info(
                "HF emotion result for user %s: emotion=%s confidence=%.3f",
                current_user.id,
                emotion,
                confidence,
            )
        else:
            # Service returned None → graceful fallback
            logger.warning(
                "HF emotion service returned None for user %s; "
                "falling back to %s/%.1f",
                current_user.id,
                _FALLBACK_EMOTION,
                _FALLBACK_CONFIDENCE,
            )

    # ------------------------------------------------------------------
    # Image-based emotion analysis (not yet implemented)
    # ------------------------------------------------------------------
    elif request.image_base64:
        # TODO: Integrate image-based facial emotion recognition.
        #       Possible approaches:
        #         • HuggingFace image-classification pipeline
        #         • A dedicated FER (Facial Expression Recognition) model
        #       For now, return a neutral placeholder so the API contract
        #       remains stable for front-end consumers.
        logger.info(
            "Image emotion analysis requested by user %s — returning "
            "placeholder (not yet implemented)",
            current_user.id,
        )
        emotion = _FALLBACK_EMOTION
        confidence = _FALLBACK_CONFIDENCE
        emotion_scores = None

    # ------------------------------------------------------------------
    # Depression-flag bookkeeping
    # ------------------------------------------------------------------
    try:
        flag_status = await depression_flag_service.process_emotion(
            user_id=current_user.id,
            emotion_data={"dominant_emotion": emotion, "confidence": confidence},
            source="emotion_api",
        )
    except Exception:
        logger.exception(
            "Depression-flag processing failed for user %s; "
            "returning zero-count stub",
            current_user.id,
        )
        # Non-critical — don't let a flag-service error break the
        # primary emotion response.
        from app.models.depression_flag import DepressionFlagStatus

        flag_status = DepressionFlagStatus(
            flag_count=0,
            threshold=0,
            threshold_exceeded=False,
            window_hours=24,
            notified_in_window=False,
            last_notified_at=None,
        )

    # ------------------------------------------------------------------
    # Build response
    # ------------------------------------------------------------------
    return EmotionResponse(
        emotion=emotion,
        confidence=confidence,
        emotion_scores=emotion_scores,
        depression_flag_count=flag_status.flag_count,
        threshold_exceeded=flag_status.threshold_exceeded,
    )
