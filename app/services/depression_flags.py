from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import uuid

from app.core.config import settings
from app.core.database import get_collection
from app.core.logging import get_logger
from app.models.depression_flag import DepressionFlag, DepressionFlagStatus
from app.models.user import User
from app.services.notifications import NotificationService

logger = get_logger("depression_flags")


class DepressionFlagService:
    """Records depression-related emotion flags and sends threshold notifications."""

    def __init__(self):
        self.flags_collection = get_collection("depression_flags")
        self.users_collection = get_collection("users")
        self.notification_service = NotificationService()

    async def process_emotion(
        self,
        user_id: str,
        emotion_data: Dict[str, Any],
        source: str = "emotion_detection",
    ) -> DepressionFlagStatus:
        """Record a qualifying flag and send email when the threshold is crossed."""
        emotion = (emotion_data.get("dominant_emotion") or emotion_data.get("emotion") or "").lower()
        confidence = float(emotion_data.get("confidence", 0.0))

        if emotion in settings.DEPRESSION_FLAG_EMOTIONS:
            await self._record_flag(user_id, emotion, confidence, source)

        return await self._evaluate_and_notify(user_id)

    async def get_flag_count(self, user_id: str) -> int:
        """Count depression flags in the configured rolling window."""
        window_start = self._window_start()
        return await self.flags_collection.count_documents({
            "user_id": user_id,
            "created_at": {"$gte": window_start},
        })

    async def get_status(self, user_id: str) -> DepressionFlagStatus:
        """Return current flag count and notification state for a user."""
        flag_count = await self.get_flag_count(user_id)
        user_doc = await self.users_collection.find_one({"id": user_id})
        last_notified_at = user_doc.get("depression_threshold_notified_at") if user_doc else None
        notified_in_window = self._is_notified_in_window(last_notified_at)

        return DepressionFlagStatus(
            flag_count=flag_count,
            threshold=settings.DEPRESSION_FLAG_THRESHOLD,
            threshold_exceeded=flag_count >= settings.DEPRESSION_FLAG_THRESHOLD,
            window_hours=settings.DEPRESSION_FLAG_WINDOW_HOURS,
            notified_in_window=notified_in_window,
            last_notified_at=last_notified_at,
        )

    async def _record_flag(
        self,
        user_id: str,
        emotion: str,
        confidence: float,
        source: str,
    ) -> DepressionFlag:
        now = datetime.utcnow()
        flag_doc = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "emotion": emotion,
            "confidence": confidence,
            "source": source,
            "created_at": now,
        }
        await self.flags_collection.insert_one(flag_doc)
        logger.info(f"Recorded depression flag for user {user_id}: {emotion}")
        return DepressionFlag(**flag_doc)

    async def _evaluate_and_notify(self, user_id: str) -> DepressionFlagStatus:
        status = await self.get_status(user_id)

        if (
            status.threshold_exceeded
            and not status.notified_in_window
            and await self._claim_notification_slot(user_id)
        ):
            try:
                await self._send_threshold_notifications(user_id)
            except Exception as e:
                logger.error(f"Notification failed for {user_id}:{e}")
                user_doc = await self.users_collection.find_one({"id": user_id})
                saved_time = user_doc.get("depression_threshold_notified_at") if user_doc else None
                if saved_time:
                    await self.users_collection.update_one(
                    {'id':user_id,"depression_threshold_notified_at": saved_time},
                    {"$set": {"depression_threshold_notified_at": None}}
                )
                raise e
            status = await self.get_status(user_id)

        return status

    async def _claim_notification_slot(self, user_id: str) -> bool:
        """Atomically claim the notification slot to prevent duplicate emails."""
        window_start = self._window_start()
        result = await self.users_collection.update_one(
            {
                "id": user_id,
                "$or": [
                    {"depression_threshold_notified_at": {"$exists": False}},
                    {"depression_threshold_notified_at": None},
                    {"depression_threshold_notified_at": {"$lt": window_start}},
                ],
            },
            {"$set": {"depression_threshold_notified_at": datetime.utcnow()}},
        )
        return result.modified_count > 0

    async def _send_threshold_notifications(self, user_id: str) -> None:
        user_doc = await self.users_collection.find_one({"id": user_id})
        if not user_doc:
            logger.error(f"User not found for threshold notification: {user_id}")
            return

        user = User(**user_doc)
        flag_count = await self.get_flag_count(user_id)
        resources = self._support_resources()

        await self.notification_service.send_depression_threshold_user_email(
            user_email=user.email,
            user_name=user.name,
            flag_count=flag_count,
            threshold=settings.DEPRESSION_FLAG_THRESHOLD,
            resources=resources,
        )

        for contact in user.emergency_contacts:
            if contact.email:
                await self.notification_service.send_depression_threshold_contact_email(
                    contact_email=contact.email,
                    contact_name=contact.name,
                    user_name=user.name,
                    flag_count=flag_count,
                    threshold=settings.DEPRESSION_FLAG_THRESHOLD,
                    resources=resources,
                )

        logger.info(f"Depression threshold notifications sent for user {user_id}")

    def _window_start(self) -> datetime:
        return datetime.utcnow() - timedelta(hours=settings.DEPRESSION_FLAG_WINDOW_HOURS)

    def _is_notified_in_window(self, last_notified_at: Optional[datetime]) -> bool:
        if not last_notified_at:
            return False
        return last_notified_at >= self._window_start()

    def _support_resources(self) -> List[str]:
        return [
            "National Suicide Prevention Lifeline: 988 (US)",
            "Crisis Text Line: Text HOME to 741741",
            "International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/",
        ]


class _DepressionFlagServiceProxy:
    _instance: Optional[DepressionFlagService] = None

    def __getattr__(self, name: str):
        if self._instance is None:
            self._instance = DepressionFlagService()
        return getattr(self._instance, name)


depression_flag_service = _DepressionFlagServiceProxy()
