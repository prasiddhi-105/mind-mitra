from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime

from app.models.chatbot import ChatMessage, ChatMessageCreate, ChatResponse
from app.core.database import get_collection
from app.core.logging import get_logger
from app.services.emotion_analysis import emotion_service

logger = get_logger("chatbot")


class ChatbotService:
    """CBT-based AI chatbot service"""
    
    def __init__(self):
        self._chat_collection = None

        # CBT techniques and responses
        self.cbt_techniques = {
            "cognitive_restructuring": {
                "name": "Cognitive Restructuring",
                "description": "Identify and challenge negative thoughts",
                "questions": [
                    "What facts or signs support this thought?",
                    "What facts or signs contradict this thought?",
                    "What would you tell your friend in this situation?",
                    "How might you view these thoughts differently in a week or month?"
                ]
            },
            "behavioral_activation": {
                "name": "Behavioral Activation",
                "description": "Increase positive activities and behaviors",
                "questions": [
                    "What are the activities which you usually used to enjoy?",
                    "What small step could you take today?",
                    "How might you reward yourself for trying?",
                    "What activity would make today a little better?"
                ]
            },
            "mindfulness": {
                "name": "Mindfulness",
                "description": "Practice present-moment awareness",
                "questions": [
                    "What are you noticing right now?",
                    "Can you describe your current emotions without any judgment?",
                    "What physical sensations do you feel right now?",
                    "How might you ground yourself in this moment?"
                ]
            },
            "problem_solving": {
                "name": "Problem Solving",
                "description": "Break down problems into manageable steps",
                "questions": [
                    "What specific problem are you facing?",
                    "What options do you have for addressing this problem?",
                    "What's the smallest step you could take?",
                    "How might you know if a solution is working?"
                ]
            }
        }
        
        # Crisis responses
        self.crisis_responses = {
            "suicidal": {
                "immediate": "I'm concerned about what you're sharing. Your life has value, and help is available. Please call the National Suicide Prevention Lifeline at 988 or text HOME to 741741 to reach the Crisis Text Line. You are not alone.",
                "follow_up": "It's important to talk to someone who can provide professional support. Would you be willing to reach out to a mental health professional or trusted person in your life?"
            },
            "self_harm": {
                "immediate": "I hear that you're in a lot of pain right now. You deserve support and care. Please consider reaching out to a crisis hotline or mental health professional who can help you through this difficult time.",
                "follow_up": "What might help you feel safer right now? Is there someone you trust who you could talk to?"
            },
            "panic": {
                "immediate": "I can see you're feeling very overwhelmed. Let's take a moment to breathe together. Try taking slow, deep breaths - inhale for 4 counts, hold for 4, exhale for 4. You are safe right now.",
                "follow_up": "What triggered these feelings? How might you ground yourself in this moment?"
            }
        }

    @property
    def chat_collection(self):
        if self._chat_collection is None:
            self._chat_collection = get_collection("chat_history")
        return self._chat_collection

    async def process_message(self, user_id: str, message_data: ChatMessageCreate) -> ChatResponse:
        """Process user message and generate CBT-based response"""
        try:
            # Analyze message for emotions
            emotion_analysis = emotion_service.analyze_text(message_data.content)
            
            # Check for crisis indicators
            crisis_response = self._check_crisis_indicators(message_data.content, emotion_analysis)
            if crisis_response:
                return await self._create_crisis_response(user_id, message_data, crisis_response)
            
            # Determine appropriate CBT technique
            technique = self._select_cbt_technique(emotion_analysis)
            
            # Generate response
            response_content = self._generate_cbt_response(message_data.content, technique, emotion_analysis)
            
            # Create response message
            response_message = await self._create_chat_message(
                user_id=user_id,
                content=response_content,
                is_user=False,
                emotion_data=emotion_analysis.dict()
            )
            
            # Save user message
            await self._create_chat_message(
                user_id=user_id,
                content=message_data.content,
                is_user=True,
                emotion_data=emotion_analysis.dict()
            )
            
            # Generate suggestions
            suggestions = self._generate_suggestions(technique, emotion_analysis)
            
            return ChatResponse(
                message=response_message,
                suggestions=suggestions,
                mood_analysis=emotion_analysis.dict()
            )
            
        except Exception as e:
            logger.error(f"Error processing chat message: {e}")
            return await self._create_fallback_response(user_id, message_data)
    
    async def get_chat_history(self, user_id: str, page: int = 1, size: int = 50) -> List[ChatMessage]:
        """Get chat history for user"""
        try:
            skip = (page - 1) * size
            cursor = self.chat_collection.find(
                {"user_id": user_id}
            ).sort("created_at", -1).skip(skip).limit(size)
            
            messages = []
            async for doc in cursor:
                messages.append(ChatMessage(**doc))
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            return []
    
    def _check_crisis_indicators(self, message: str, emotion_analysis) -> Optional[Dict[str, str]]:
        """Check for crisis indicators in message"""
        message_lower = message.lower()
        
        # Check for suicidal ideation
        if any(word in message_lower for word in ["kill myself", "suicide", "end it all", "don't want to live"]):
            return self.crisis_responses["suicidal"]
        
        # Check for self-harm
        if any(word in message_lower for word in ["hurt myself", "self-harm", "cut myself", "harm myself"]):
            return self.crisis_responses["self_harm"]
        
        # Check for panic/anxiety
        if any(word in message_lower for word in ["panic", "can't breathe", "overwhelmed", "losing control"]):
            return self.crisis_responses["panic"]
        
        return None
    
    def _select_cbt_technique(self, emotion_analysis) -> str:
        """Select appropriate CBT technique based on emotions"""
        dominant_emotion = emotion_analysis.dominant_emotion
        sentiment_score = emotion_analysis.sentiment_score
        
        if sentiment_score < -0.3:
            if dominant_emotion in ["sad", "depressed", "hopeless"]:
                return "behavioral_activation"
            elif dominant_emotion in ["anxious", "worried", "fearful"]:
                return "mindfulness"
            else:
                return "cognitive_restructuring"
        elif sentiment_score > 0.3:
            return "mindfulness"  # Positive emotions - maintain awareness
        else:
            return "problem_solving"  # Neutral - focus on practical solutions
    
    def _generate_cbt_response(self, user_message: str, technique: str, emotion_analysis) -> str:
        """Generate CBT-based response"""
        technique_info = self.cbt_techniques[technique]
        
        # Personalized response based on technique
        if technique == "cognitive_restructuring":
            response = f"I notice you're feeling {emotion_analysis.dominant_emotion}. "
            response += "Let us explore the thoughts behind these feelings. "
            response += technique_info["questions"][0]
        
        elif technique == "behavioral_activation":
            response = "I hear that you are struggling right now. "
            response += "Sometimes small actions can help shift our mood a lot. "
            response += technique_info["questions"][0]
        
        elif technique == "mindfulness":
            response = "It sounds like you're experiencing some intense emotions. "
            response += "Let's take a moment to observe what is happening. "
            response += technique_info["questions"][0]
        
        else:  # problem_solving
            response = "I can see you're dealing with a challenging situation. "
            response += "Let's break this down into small, manageable pieces. "
            response += technique_info["questions"][0]
        
        return response
    
    def _generate_suggestions(self, technique: str, emotion_analysis) -> List[str]:
        """Generate follow-up suggestions"""
        technique_info = self.cbt_techniques[technique]
        suggestions = []
        
        # Add technique-specific suggestions
        if technique == "cognitive_restructuring":
            suggestions.extend([
                "Write down your thoughts and challenge them - question if they are 100% true.",
                "Look for facts or signs that prove your negative thoughts are wrong.",
                "Take a step back and think: What would you tell your close friend who is feeling the same way as you?"
            ])
        elif technique == "behavioral_activation":
            suggestions.extend([
                "Pick 1 enjoyable activity to do today.",
                "Start small: Pick any activity and do it for just 5 minutes.",
                "Check in with yourself: Track your mood before and after doing activities."
            ])
        elif technique == "mindfulness":
            suggestions.extend([
                "Try a 3-minute deep breathing exercise.",
                "Look around you and name 5 things you can see, hear, and feel.",
                "Observe what you are feeling right now without trying to fix it or judge yourself."
            ])
        else:
            suggestions.extend([
                "Let's break the problem down into smaller, bite-sized pieces.",
                "List your options and analyze their pros/cons.",
                "Set 1 easy, achievable goal for yourself right now."
            ])
        
        # Add General wellness suggestions
        suggestions.extend([
            "Think about chatting with a [mental health professional](https://www.google.com/maps/search/mental+health+clinic) who can offer extra guidance.",
            "Reach out to a trusted friend or family member to talk things through.",
            "Spend time today doing an activity that brings you comfort."
        ])

        return suggestions[:5]  # Limit to 5 suggestions
    
    async def _create_crisis_response(self, user_id: str, message_data: ChatMessageCreate, crisis_response: Dict[str, str]) -> ChatResponse:
        """Create crisis response"""
        response_message = await self._create_chat_message(
            user_id=user_id,
            content=crisis_response["immediate"],
            is_user=False,
            emotion_data={"crisis": True}
        )
        
        # Save user message
        await self._create_chat_message(
            user_id=user_id,
            content=message_data.content,
            is_user=True,
            emotion_data={"crisis": True}
        )
        
        return ChatResponse(
            message=response_message,
            suggestions=[
                "Call a crisis hotline",
                "Reach out to a mental health professional",
                "Talk to a trusted person",
                "Consider emergency services if needed"
            ],
            mood_analysis={"crisis": True, "severity": "high"}
        )
    
    async def _create_fallback_response(self, user_id: str, message_data: ChatMessageCreate) -> ChatResponse:
        """Create fallback response when processing fails"""
        response_message = await self._create_chat_message(
            user_id=user_id,
            content="I'm here to listen and support you. Could you tell me more about what you're experiencing?",
            is_user=False,
            emotion_data={}
        )
        
        return ChatResponse(
            message=response_message,
            suggestions=[
                "Share more about your feelings",
                "Describe what's happening in your life",
                "Talk about what you need right now"
            ],
            mood_analysis={}
        )
    
    async def _create_chat_message(self, user_id: str, content: str, is_user: bool, emotion_data: Dict[str, Any]) -> ChatMessage:
        """Create and save chat message"""
        message_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        message_doc = {
            "id": message_id,
            "user_id": user_id,
            "content": content,
            "message_type": "text",
            "is_user": is_user,
            "emotion_data": emotion_data,
            "created_at": now
        }
        
        await self.chat_collection.insert_one(message_doc)
        return ChatMessage(**message_doc)


def get_ai_response(message: str) -> str:
    # Dummy AI response for now
    responses = [
        "I understand how you are feeling. Can you tell me more about what's troubling you?",
        "That sounds challenging. Let's work through this together. What thoughts are going through your mind right now?",
        "Thank you for sharing. Have you noticed any patterns in when these feelings occur?",
        "I'm here to support you. What coping strategies have helped you with these felings in the past?"
    ]
    import random
    return random.choice(responses)


# Global chatbot service instance
chatbot_service = ChatbotService() 
