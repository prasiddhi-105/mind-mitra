from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from typing import Optional

class EmotionRequest(BaseModel):
    text: Optional[str] = None
    image_base64: Optional[str] = None

class EmotionResponse(BaseModel):
    emotion: str
    confidence: float

router = APIRouter()

@router.post(
    '/emotion',
    summary="Detect emotion from text or image",
    response_model=EmotionResponse,
    responses={
        200: {
            "description": "Emotion detection result",
            "content": {
                "application/json": {
                    "example": {
                        "emotion": "sad",
                        "confidence": 0.95
                    }
                }
            }
        }
    }
)
def detect_emotion(request: EmotionRequest = Body(
    ...,
    examples={
        "textExample": {
            "summary": "Text emotion detection",
            "value": {
                "text": "I feel so sad and hopeless",
                "image_base64": None
            }
        },
        "imageExample": {
            "summary": "Image emotion detection",
            "value": {
                "text": None,
                "image_base64": "iVBORw0KGgoAAAANSUhE..."
            }
        }
    }
), current_user: User = Depends(get_current_user)):
    """Detect emotion from provided text or base64-encoded image.

    Enter the follwoing paramteres while sending the request
    text: Optional- string
    image_base64: Optional- string

    Response model: `EmotionResponse`
    emotion: string
    confidence: float

    
    """
    # If image is provided, stub: always return 'happy' for demo
    if request.image_base64:
        return EmotionResponse(emotion='happy', confidence=0.92)
    # Dummy logic for text
    if request.text and 'sad' in request.text.lower():
        return EmotionResponse(emotion='sad', confidence=0.95)
    return EmotionResponse(emotion='calm', confidence=0.80) 