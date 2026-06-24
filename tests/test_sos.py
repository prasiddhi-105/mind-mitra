"""Comprehensive tests for SOS emergency alert feature.

Covers:
- SOS alert creation (happy path)
- Cooldown enforcement (30 min block)
- Cooldown status endpoint logic
- Cancel alert flow
- Alert history retrieval
- SMS/Email notification dispatch (mocked)
- Graceful handling when no emergency contacts
- API-level integration tests
"""

import pytest
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.core import database as db_module
from app.core.config import settings
from app.models.sos import SOSAlertCreate, AlertSeverity, AlertStatus, TriggerType
from app.services.sos import SOSService
from app.services.auth import auth_service
from app.api.v1.endpoints import auth as auth_endpoints
from app.api.v1.endpoints import sos as sos_endpoints
from app.api.v1.endpoints import user as user_endpoints


# ===========================================================================
# Lifespan and helpers
# ===========================================================================


def _reset_services():
    auth_service._users_collection = None
    auth_service._reset_tokens_collection = None
    from app.services.sos import sos_service
    sos_service._alerts = None
    sos_service._users = None


@asynccontextmanager
async def _sos_test_lifespan(app: FastAPI):
    from app.core.middleware import limiter
    limiter.enabled = False
    db_module.client = AsyncMongoMockClient()
    db_module.database = db_module.client[settings.DATABASE_NAME]
    _reset_services()
    yield
    db_module.client.close()
    db_module.client = None
    db_module.database = None
    _reset_services()
    limiter.enabled = True


def _make_alert_data(reason="I need help"):
    return SOSAlertCreate(
        trigger_type=TriggerType.MANUAL,
        severity=AlertSeverity.HIGH,
        reason=reason,
        emotion_data={},
    )


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def mock_db():
    """In-memory MongoDB via mongomock_motor."""
    db_module.client = AsyncMongoMockClient()
    db_module.database = db_module.client[settings.DATABASE_NAME]
    _reset_services()
    yield db_module.database
    db_module.client.close()
    db_module.client = None
    db_module.database = None
    _reset_services()


@pytest.fixture
def sos_service_instance(mock_db):
    """Fresh SOSService wired to the mock DB."""
    svc = SOSService()
    svc._alerts = None
    svc._users = None
    return svc


@pytest.fixture
def sos_client():
    """TestClient with auth + SOS + user routes."""
    app = FastAPI(lifespan=_sos_test_lifespan)
    app.include_router(auth_endpoints.router, prefix="/api/v1/auth")
    app.include_router(sos_endpoints.router, prefix="/api/v1/sos")
    app.include_router(user_endpoints.router, prefix="/api/v1/user")

    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_headers(sos_client):
    """Register + login a test user and return auth headers."""
    email = f"sos-{uuid.uuid4().hex[:8]}@example.com"
    password = "Test@Pass123"
    sos_client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "SOS Tester", "password": password, "role": "user"},
    )
    login = sos_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# Helper: insert a user doc directly into mock DB
async def _insert_user(db, user_id, name="Test User", contacts=None):
    now = datetime.utcnow()
    doc = {
        "id": user_id,
        "email": f"{user_id}@test.com",
        "name": name,
        "role": "user",
        "is_active": True,
        "hashed_password": "hashed",
        "emergency_contacts": contacts or [],
        "created_at": now,
        "updated_at": now,
    }
    await db["users"].insert_one(doc)
    return doc


# ===========================================================================
# 1. SOS Alert Creation (service level)
# ===========================================================================


class TestSOSAlertCreation:
    """Tests for creating SOS alerts."""

    @pytest.mark.asyncio
    async def test_create_alert_happy_path(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-create-1")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.create_alert(user["id"], _make_alert_data())

        assert alert is not None
        assert alert.user_id == user["id"]
        assert alert.status == AlertStatus.PENDING
        assert alert.severity == AlertSeverity.HIGH

    @pytest.mark.asyncio
    async def test_alert_id_is_uuid(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-uuid-1")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.create_alert(user["id"], _make_alert_data())

        uuid.UUID(alert.id)  # Should not raise

    @pytest.mark.asyncio
    async def test_alert_stored_in_db(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-stored-1")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.create_alert(user["id"], _make_alert_data())

        doc = await mock_db["sos_alerts"].find_one({"id": alert.id})
        assert doc is not None
        assert doc["user_id"] == user["id"]


# ===========================================================================
# 2. Cooldown Enforcement
# ===========================================================================


class TestSOSCooldown:
    """Tests for the 30-minute cooldown mechanism."""

    @pytest.mark.asyncio
    async def test_second_alert_blocked_by_cooldown(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-cd-1")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            first = await svc.create_alert(user["id"], _make_alert_data())
            second = await svc.create_alert(user["id"], _make_alert_data("Again"))

        assert first is not None
        assert second is None

    @pytest.mark.asyncio
    async def test_alert_allowed_after_cooldown_expires(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-cd-2")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            first = await svc.create_alert(user["id"], _make_alert_data())

        past = datetime.utcnow() - timedelta(minutes=settings.SOS_COOLDOWN_MINUTES + 1)
        await mock_db["sos_alerts"].update_one(
            {"id": first.id}, {"$set": {"created_at": past}}
        )

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            second = await svc.create_alert(user["id"], _make_alert_data("After"))

        assert second is not None

    @pytest.mark.asyncio
    async def test_cancelled_alert_does_not_block(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-cd-3")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            first = await svc.create_alert(user["id"], _make_alert_data())

        await svc.cancel_alert(first.id, user["id"])

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            second = await svc.create_alert(user["id"], _make_alert_data("After cancel"))

        assert second is not None


# ===========================================================================
# 3. Cooldown Status
# ===========================================================================


class TestCooldownStatus:

    @pytest.mark.asyncio
    async def test_no_prior_alerts_returns_inactive(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        status = await svc.get_cooldown_status("no-alerts-user")
        assert status["active"] is False
        assert status["remaining_seconds"] == 0
        assert status["last_alert_at"] is None

    @pytest.mark.asyncio
    async def test_recent_alert_returns_active(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-cs-1")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            await svc.create_alert(user["id"], _make_alert_data())

        status = await svc.get_cooldown_status(user["id"])
        assert status["active"] is True
        assert status["remaining_seconds"] > 0

    @pytest.mark.asyncio
    async def test_expired_alert_returns_inactive(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-cs-2")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.create_alert(user["id"], _make_alert_data())

        past = datetime.utcnow() - timedelta(minutes=settings.SOS_COOLDOWN_MINUTES + 1)
        await mock_db["sos_alerts"].update_one(
            {"id": alert.id}, {"$set": {"created_at": past}}
        )

        status = await svc.get_cooldown_status(user["id"])
        assert status["active"] is False
        assert status["remaining_seconds"] == 0


# ===========================================================================
# 4. Cancel Alert
# ===========================================================================


class TestCancelAlert:

    @pytest.mark.asyncio
    async def test_cancel_pending_alert(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-cancel-1")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.create_alert(user["id"], _make_alert_data())

        assert await svc.cancel_alert(alert.id, user["id"]) is True

    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self, sos_service_instance, mock_db):
        assert await sos_service_instance.cancel_alert("fake-id", "u") is False

    @pytest.mark.asyncio
    async def test_cannot_cancel_other_users_alert(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-cancel-2")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.create_alert(user["id"], _make_alert_data())

        assert await svc.cancel_alert(alert.id, "other-user") is False


# ===========================================================================
# 5. Alert History
# ===========================================================================


class TestAlertHistory:

    @pytest.mark.asyncio
    async def test_empty_history(self, sos_service_instance, mock_db):
        alerts = await sos_service_instance.get_user_alerts("no-alerts")
        assert alerts == []

    @pytest.mark.asyncio
    async def test_history_newest_first(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-hist-1")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            first = await svc.create_alert(user["id"], _make_alert_data("First"))

        past = datetime.utcnow() - timedelta(minutes=settings.SOS_COOLDOWN_MINUTES + 1)
        await mock_db["sos_alerts"].update_one(
            {"id": first.id}, {"$set": {"created_at": past}}
        )

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            await svc.create_alert(user["id"], _make_alert_data("Second"))

        alerts = await svc.get_user_alerts(user["id"])
        assert len(alerts) == 2
        assert alerts[0].reason == "Second"
        assert alerts[1].reason == "First"

    @pytest.mark.asyncio
    async def test_pagination(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        uid = "user-page-1"
        for i in range(5):
            await mock_db["sos_alerts"].insert_one({
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "trigger_type": TriggerType.MANUAL,
                "severity": AlertSeverity.HIGH,
                "reason": f"Alert {i}",
                "emotion_data": {},
                "status": AlertStatus.SENT,
                "created_at": datetime.utcnow() - timedelta(hours=i),
                "updated_at": datetime.utcnow(),
                "sent_at": None,
                "acknowledged_at": None,
            })

        assert len(await svc.get_user_alerts(uid, page=1, size=2)) == 2
        assert len(await svc.get_user_alerts(uid, page=2, size=2)) == 2


# ===========================================================================
# 6. Notification Dispatch
# ===========================================================================


class TestNotificationDispatch:

    @pytest.mark.asyncio
    async def test_sms_sent_to_contact(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        contacts = [{"name": "Mom", "phone": "+1234567890", "email": "mom@test.com", "relationship": "Mother"}]
        user = await _insert_user(mock_db, "user-notif-1", contacts=contacts)

        with patch("app.services.sos.notification_service") as mock_notif:
            mock_notif.send_sms = AsyncMock(return_value=True)
            mock_notif.send_email = AsyncMock(return_value=True)
            mock_notif.send_push_notification = AsyncMock(return_value=True)
            await svc.create_alert(user["id"], _make_alert_data())

        mock_notif.send_sms.assert_called_once()
        assert mock_notif.send_sms.call_args.kwargs["to"] == "+1234567890"
        assert "URGENT" in mock_notif.send_sms.call_args.kwargs["message"]

    @pytest.mark.asyncio
    async def test_user_gets_confirmation(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        contacts = [{"name": "Dad", "phone": "+1234567890", "email": "dad@test.com", "relationship": "Father"}]
        user = await _insert_user(mock_db, "user-notif-2", contacts=contacts)

        with patch("app.services.sos.notification_service") as mock_notif:
            mock_notif.send_sms = AsyncMock(return_value=True)
            mock_notif.send_email = AsyncMock(return_value=True)
            mock_notif.send_push_notification = AsyncMock(return_value=True)
            await svc.create_alert(user["id"], _make_alert_data())

        mock_notif.send_push_notification.assert_called_once()
        assert mock_notif.send_push_notification.call_args.kwargs["title"] == "SOS Alert Sent"

    @pytest.mark.asyncio
    async def test_no_contacts_still_creates_alert(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-notif-3", contacts=[])

        with patch("app.services.sos.notification_service") as mock_notif:
            mock_notif.send_sms = AsyncMock(return_value=True)
            mock_notif.send_email = AsyncMock(return_value=True)
            mock_notif.send_push_notification = AsyncMock(return_value=True)
            alert = await svc.create_alert(user["id"], _make_alert_data())

        assert alert is not None
        mock_notif.send_sms.assert_not_called()
        mock_notif.send_push_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_sms_failure_does_not_crash(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        contacts = [{"name": "X", "phone": "+999", "email": None, "relationship": "Friend"}]
        user = await _insert_user(mock_db, "user-notif-4", contacts=contacts)

        with patch("app.services.sos.notification_service") as mock_notif:
            mock_notif.send_sms = AsyncMock(side_effect=Exception("Twilio down"))
            mock_notif.send_email = AsyncMock(return_value=True)
            mock_notif.send_push_notification = AsyncMock(return_value=True)
            alert = await svc.create_alert(user["id"], _make_alert_data())

        assert alert is not None


# ===========================================================================
# 7. API Integration Tests
# ===========================================================================


class TestSOSAPI:
    """Full API-level tests via TestClient."""

    def test_send_sos_returns_201(self, sos_client, auth_headers, monkeypatch):
        monkeypatch.setattr(
            "app.services.sos.notification_service",
            type("M", (), {
                "send_sms": AsyncMock(return_value=True),
                "send_email": AsyncMock(return_value=True),
                "send_push_notification": AsyncMock(return_value=True),
            })(),
        )
        resp = sos_client.post(
            "/api/v1/sos/send",
            json={"reason": "Test emergency"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "alert_id" in data
        assert "notified" in data["message"].lower() or "sent" in data["message"].lower()

    def test_cooldown_returns_429(self, sos_client, auth_headers, monkeypatch):
        monkeypatch.setattr(
            "app.services.sos.notification_service",
            type("M", (), {
                "send_sms": AsyncMock(return_value=True),
                "send_email": AsyncMock(return_value=True),
                "send_push_notification": AsyncMock(return_value=True),
            })(),
        )
        resp1 = sos_client.post("/api/v1/sos/send", json={"reason": "First"}, headers=auth_headers)
        assert resp1.status_code == 201

        resp2 = sos_client.post("/api/v1/sos/send", json={"reason": "Second"}, headers=auth_headers)
        assert resp2.status_code == 429
        assert "cooldown" in resp2.json()["detail"].lower()

    def test_cooldown_status_after_send(self, sos_client, auth_headers, monkeypatch):
        monkeypatch.setattr(
            "app.services.sos.notification_service",
            type("M", (), {
                "send_sms": AsyncMock(return_value=True),
                "send_email": AsyncMock(return_value=True),
                "send_push_notification": AsyncMock(return_value=True),
            })(),
        )
        sos_client.post("/api/v1/sos/send", json={"reason": "check"}, headers=auth_headers)

        resp = sos_client.get("/api/v1/sos/cooldown-status", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["active"] is True
        assert resp.json()["remaining_seconds"] > 0

    def test_cooldown_status_no_alerts(self, sos_client, auth_headers):
        resp = sos_client.get("/api/v1/sos/cooldown-status", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["active"] is False

    def test_history_empty(self, sos_client, auth_headers):
        resp = sos_client.get("/api/v1/sos/history", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_after_send(self, sos_client, auth_headers, monkeypatch):
        monkeypatch.setattr(
            "app.services.sos.notification_service",
            type("M", (), {
                "send_sms": AsyncMock(return_value=True),
                "send_email": AsyncMock(return_value=True),
                "send_push_notification": AsyncMock(return_value=True),
            })(),
        )
        sos_client.post("/api/v1/sos/send", json={"reason": "For history"}, headers=auth_headers)

        resp = sos_client.get("/api/v1/sos/history", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_contacts_empty(self, sos_client, auth_headers):
        resp = sos_client.get("/api/v1/user/contacts", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_update_contacts(self, sos_client, auth_headers):
        new_contacts = [
            {"name": "Dad", "phone": "+9876543210", "email": "dad@test.com", "relationship": "Father"}
        ]
        resp = sos_client.put("/api/v1/user/contacts", json=new_contacts, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()[0]["name"] == "Dad"
        assert resp.json()[0]["phone"] == "+9876543210"


# ===========================================================================
# 8. Issue #71 - Additional Unit Tests
# ===========================================================================

class TestAutomaticAndTransitionSOS:
    """Additional unit tests for automatic triggers and status transitions."""

    @pytest.mark.asyncio
    async def test_automatic_trigger_three_modalities_critical(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-auto-1")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.evaluate_multimodal_critical(
                user_id=user["id"],
                text_emotion="depressed",
                text_confidence=0.85,
                audio_emotion="sad",
                audio_confidence=0.90,
                image_emotion="anxious",
                image_confidence=0.80,
            )

        assert alert is not None
        assert alert.trigger_type == TriggerType.AUTOMATIC
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.status == AlertStatus.PENDING

    @pytest.mark.asyncio
    async def test_automatic_trigger_modalities_not_all_critical(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-auto-2")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.evaluate_multimodal_critical(
                user_id=user["id"],
                text_emotion="depressed",
                text_confidence=0.85,
                audio_emotion="sad",
                audio_confidence=0.50,  # Below CRITICAL_EMOTION_THRESHOLD (0.8)
                image_emotion="joy",    # Not in DEPRESSION_FLAG_EMOTIONS
                image_confidence=0.80,
            )

        assert alert is None

    @pytest.mark.asyncio
    async def test_repeated_depression_flags_trigger(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-flags-1")

        # Insert 3 depression flags within the last 24 hours
        flags_collection = mock_db["depression_flags"]
        now = datetime.utcnow()
        for i in range(3):
            await flags_collection.insert_one({
                "id": f"flag-{i}",
                "user_id": user["id"],
                "emotion": "sad",
                "confidence": 0.85,
                "created_at": now - timedelta(hours=i),
            })

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.evaluate_depression_flags_trigger(user["id"])

        assert alert is not None
        assert alert.trigger_type == TriggerType.AUTOMATIC
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.PENDING

    @pytest.mark.asyncio
    async def test_repeated_depression_flags_below_threshold(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-flags-2")

        # Insert only 2 depression flags within the last 24 hours (threshold is 3)
        flags_collection = mock_db["depression_flags"]
        now = datetime.utcnow()
        for i in range(2):
            await flags_collection.insert_one({
                "id": f"flag-{i}",
                "user_id": user["id"],
                "emotion": "sad",
                "confidence": 0.85,
                "created_at": now - timedelta(hours=i),
            })

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.evaluate_depression_flags_trigger(user["id"])

        assert alert is None

    @pytest.mark.asyncio
    async def test_repeated_depression_flags_ignores_old_flags(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-flags-3")

        # Insert 3 depression flags, but 1 is older than 24 hours
        flags_collection = mock_db["depression_flags"]
        now = datetime.utcnow()
        await flags_collection.insert_one({
            "id": "flag-1", "user_id": user["id"], "emotion": "sad", "confidence": 0.85, "created_at": now
        })
        await flags_collection.insert_one({
            "id": "flag-2", "user_id": user["id"], "emotion": "sad", "confidence": 0.85, "created_at": now - timedelta(hours=2)
        })
        await flags_collection.insert_one({
            "id": "flag-3", "user_id": user["id"], "emotion": "sad", "confidence": 0.85, "created_at": now - timedelta(hours=25)
        })

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.evaluate_depression_flags_trigger(user["id"])

        assert alert is None

    @pytest.mark.asyncio
    async def test_status_transitions_sent_acknowledged_resolved(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-trans-1")

        # 1. PENDING -> SENT (create_alert will trigger _send_notifications which updates to SENT)
        alert = await svc.create_alert(user["id"], _make_alert_data())
        assert alert is not None
        doc = await mock_db["sos_alerts"].find_one({"id": alert.id})
        assert doc["status"] == AlertStatus.SENT

        # 2. SENT -> ACKNOWLEDGED
        acked = await svc.acknowledge_alert(alert.id)
        assert acked is True
        doc = await mock_db["sos_alerts"].find_one({"id": alert.id})
        assert doc["status"] == AlertStatus.ACKNOWLEDGED

        # 3. ACKNOWLEDGED -> RESOLVED
        resolved = await svc.resolve_alert(alert.id)
        assert resolved is True
        doc = await mock_db["sos_alerts"].find_one({"id": alert.id})
        assert doc["status"] == AlertStatus.RESOLVED

    @pytest.mark.asyncio
    async def test_resolve_invalid_status_fails(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        user = await _insert_user(mock_db, "user-trans-2")

        with patch.object(svc, "_send_notifications", new_callable=AsyncMock):
            alert = await svc.create_alert(user["id"], _make_alert_data())

        # Status is PENDING. Resolving it directly should fail (must be sent or acknowledged)
        assert await svc.resolve_alert(alert.id) is False

        # Cancel it
        await svc.cancel_alert(alert.id, user["id"])
        # Resolving cancelled alert should fail
        assert await svc.resolve_alert(alert.id) is False

        # Resolving non-existent alert should fail
        assert await svc.resolve_alert("fake-id") is False

    def test_api_resolve_alert(self, sos_client, auth_headers, monkeypatch):
        monkeypatch.setattr(
            "app.services.sos.notification_service",
            type("M", (), {
                "send_sms": AsyncMock(return_value=True),
                "send_email": AsyncMock(return_value=True),
                "send_push_notification": AsyncMock(return_value=True),
            })(),
        )
        # Send SOS
        resp = sos_client.post("/api/v1/sos/send", json={"reason": "Testing resolve"}, headers=auth_headers)
        assert resp.status_code == 201
        alert_id = resp.json()["alert_id"]

        # Call resolve endpoint. Note: alert is SENT status now, so it should resolve directly.
        resp_resolve = sos_client.post(f"/api/v1/sos/resolve/{alert_id}", headers=auth_headers)
        assert resp_resolve.status_code == 200
        assert "resolved successfully" in resp_resolve.json()["message"]

        # Try to resolve again (now it is RESOLVED, which is not in SENT/ACKNOWLEDGED, so it should fail)
        resp_resolve_again = sos_client.post(f"/api/v1/sos/resolve/{alert_id}", headers=auth_headers)
        assert resp_resolve_again.status_code == 404

    @pytest.mark.asyncio
    async def test_get_recent_emotion_data(self, sos_service_instance, mock_db):
        svc = sos_service_instance
        uid = "user-emotion-1"

        # Insert some journal entries
        now = datetime.utcnow()
        await mock_db["journal_entries"].insert_one({
            "user_id": uid,
            "emotion_labels": [{"label": "sad", "confidence": 0.9}],
            "mood_score": 0.2,
            "created_at": now,
        })
        await mock_db["journal_entries"].insert_one({
            "user_id": uid,
            "emotion_labels": [],
            "mood_score": 0.5,
            "created_at": now - timedelta(hours=2),
        })

        data = await svc._get_recent_emotion_data(uid)
        assert len(data) == 2
        assert data[0]["dominant_emotion"] == "sad"
        assert data[0]["mood_score"] == 0.2
        assert data[1]["dominant_emotion"] == "neutral"
        assert data[1]["mood_score"] == 0.5

        # Test exception branch
        with patch("app.services.sos.get_collection") as mock_get_col:
            mock_col = MagicMock()
            mock_col.find = MagicMock(side_effect=Exception("DB Error"))
            mock_get_col.return_value = mock_col
            empty_data = await svc._get_recent_emotion_data(uid)
            assert empty_data == []

    @pytest.mark.asyncio
    async def test_exceptions_in_sos_service(self, sos_service_instance, mock_db):
        svc = sos_service_instance

        # Mock collections to raise exceptions
        mock_alerts = MagicMock()
        mock_alerts.insert_one = AsyncMock(side_effect=Exception("DB Error"))
        mock_alerts.find = MagicMock(side_effect=Exception("DB Error"))
        mock_alerts.update_one = AsyncMock(side_effect=Exception("DB Error"))
        mock_alerts.find_one = AsyncMock(side_effect=Exception("DB Error"))

        old_alerts = svc._alerts
        svc._alerts = mock_alerts
        try:
            # 1. create_alert exception
            alert = await svc.create_alert("user-1", _make_alert_data())
            assert alert is None

            # 2. get_user_alerts exception
            alerts = await svc.get_user_alerts("user-1")
            assert alerts == []

            # 3. cancel_alert exception
            cancelled = await svc.cancel_alert("alert-1", "user-1")
            assert cancelled is False

            # 4. acknowledge_alert exception
            acked = await svc.acknowledge_alert("alert-1")
            assert acked is False

            # 5. resolve_alert exception
            resolved = await svc.resolve_alert("alert-1")
            assert resolved is False

            # 6. get_cooldown_status exception
            cooldown = await svc.get_cooldown_status("user-1")
            assert cooldown["active"] is False

            # 7. _has_recent_alert exception
            has_recent = await svc._has_recent_alert("user-1")
            assert has_recent is False
        finally:
            svc._alerts = old_alerts



