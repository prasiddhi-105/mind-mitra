"""
Emotion analysis endpoints for audio and image inputs.

Exposes rate-limited POST routes utilizing the pre-trained models via
the emotion analysis service. Rate limits are applied per-user.
"""

from fastapi import APIRouter, Body, Depends, Request
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.models.analysis import AudioAnalysisRequest, AudioAnalysisResponse, ImageAnalysisRequest, ImageAnalysisResponse
from app.services.emotion_analysis import emotion_service
from app.core.middleware import limiter
from app.core.config import settings

router = APIRouter()


def get_rate_limit() -> str:
    return f"{settings.RATE_LIMIT_PER_MINUTE}/minute"


@router.post(
    "/audio",
    summary="Analyze audio for emotion detection",
    response_model=AudioAnalysisResponse,
    responses={
        200: {"description": "Audio analysis emotion result"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(get_rate_limit)
async def analyze_audio(
    request: Request,
    payload: AudioAnalysisRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> AudioAnalysisResponse:
    """Analyze audio tone for emotion detection.

    Allows a configurable number of requests per minute per user.
    """
    return emotion_service.analyze_audio(payload.audio_data, payload.audio_format)


@router.post(
    "/image",
    summary="Analyze image for facial emotion detection",
    response_model=ImageAnalysisResponse,
    responses={
        200: {"description": "Image analysis emotion result"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(get_rate_limit)
async def analyze_image(
    request: Request,
    payload: ImageAnalysisRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> ImageAnalysisResponse:
    """Analyze facial expressions from image for emotion detection.

    Allows a configurable number of requests per minute per user.
    """
    return emotion_service.analyze_image(payload.image_data, payload.image_format)
