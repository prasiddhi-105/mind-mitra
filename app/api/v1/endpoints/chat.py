from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from app.services.chatbot import get_ai_response
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

router = APIRouter()

@router.post(
    '/chat',
    summary="Send chat message to AI",
    response_model=ChatResponse,
    responses={
        200: {
            "description": "AI chat response",
            "content": {
                "application/json": {
                    "example": {
                        "response": "It sounds like your presentation is causing a lot of stress, but preparing gradually can help."
                    }
                }
            }
        }
    }
)
def chat_endpoint(request: ChatRequest = Body(
    ...,
    example={
        "message": "I'm feeling anxious about my upcoming presentation"
    }
), current_user: User = Depends(get_current_user)):
    """Send a chat message to the AI chatbot and return a generated response.

    Request model: 'ChatRequest'
    message: string

    Response model: 'ChatResponse'
    response: string
    """
    ai_response = get_ai_response(request.message)
    return ChatResponse(response=ai_response)