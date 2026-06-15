"""Tests for journal endpoints with emotion analysis integration.

Tests the complete flow: create journal → emotion analysis → store result →
retrieve with emotion data. Uses mongomock for MongoDB and mocks the
HuggingFace emotion service.
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mongomock_motor import AsyncMongoMockClient

from app.api.v1.endpoints import auth as auth_endpoints
from app.api.v1.endpoints import journal as journal_endpoints
from app.core import database as db_module
from app.core.config import settings
from app.services.auth import auth_service


# ---------------------------------------------------------------------------
# App & fixtures — isolated from conftest.py (which has autouse=True clean)
# ---------------------------------------------------------------------------


def _reset_auth():
    auth_service._users_collection = None
    auth_service._reset_tokens_collection = None


@asynccontextmanager
async def _journal_lifespan(app: FastAPI):
    db_module.client = AsyncMongoMockClient()
    db_module.database = db_module.client["mindmitra_journal_test"]
    _reset_auth()
    yield
    db_module.client.close()
    db_module.client = None
    db_module.database = None
    _reset_auth()


def _create_app() -> FastAPI:
    app = FastAPI(lifespan=_journal_lifespan)
    app.include_router(auth_endpoints.router, prefix="/api/v1/auth")
    app.include_router(journal_endpoints.router, prefix="/api/v1", tags=["journal"])
    return app


@pytest.fixture
def journal_client():
    """Self-contained test client with its own DB — avoids conftest autouse conflicts."""
    app = _create_app()
    with TestClient(app) as c:
        yield c


def _register_and_login(client) -> dict:
    """Register a fresh user and return auth headers."""
    email = f"jtest-{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/v1/auth/register", json={
        "email": email, "name": "Journal Tester", "password": "Test@Pass123", "role": "user",
    })
    assert reg.status_code == 200, f"Register failed: {reg.text}"

    login = client.post("/api/v1/auth/login", data={
        "username": email, "password": "Test@Pass123",
    })
    assert login.status_code == 200, f"Login failed: {login.text}"
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _mock_emotion_result(label="joy", confidence=0.85, scores=None):
    from app.services.huggingface_emotion import EmotionAnalysisResult
    return EmotionAnalysisResult(
        label=label,
        confidence=confidence,
        scores=scores or {"joy": 0.85, "sadness": 0.05, "anger": 0.03,
                          "fear": 0.02, "disgust": 0.02, "surprise": 0.01, "neutral": 0.02},
    )


def _mock_flag_status():
    from app.models.depression_flag import DepressionFlagStatus
    return DepressionFlagStatus(
        flag_count=0, threshold=3, threshold_exceeded=False,
        window_hours=24, notified_in_window=False, last_notified_at=None,
    )


# ---------------------------------------------------------------------------
# Tests: POST /journal
# ---------------------------------------------------------------------------


class TestCreateJournalEntry:

    @patch("app.api.v1.endpoints.journal.depression_flag_service")
    @patch("app.api.v1.endpoints.journal.hf_emotion_service")
    def test_create_with_emotion_success(self, mock_hf, mock_dep, journal_client):
        headers = _register_and_login(journal_client)
        mock_hf.analyze = AsyncMock(return_value=_mock_emotion_result("joy", 0.92))
        mock_dep.process_emotion = AsyncMock(return_value=_mock_flag_status())

        resp = journal_client.post(
            "/api/v1/journal",
            json={"mood": 4, "text": "I had an amazing day today!"},
            headers=headers,
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["emotion_label"] == "joy"
        assert data["emotion_confidence"] == 0.92
        assert data["emotion_analyzed"] is True
        assert data["emotion_scores"] is not None
        assert data["mood"] == 4

    @patch("app.api.v1.endpoints.journal.depression_flag_service")
    @patch("app.api.v1.endpoints.journal.hf_emotion_service")
    def test_create_emotion_failure_still_saves(self, mock_hf, mock_dep, journal_client):
        headers = _register_and_login(journal_client)
        mock_hf.analyze = AsyncMock(return_value=None)
        mock_dep.process_emotion = AsyncMock(return_value=_mock_flag_status())

        resp = journal_client.post(
            "/api/v1/journal",
            json={"mood": 3, "text": "A regular day, nothing special"},
            headers=headers,
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["text"] == "A regular day, nothing special"
        assert data["emotion_analyzed"] is False
        assert data["emotion_label"] is None

    @patch("app.api.v1.endpoints.journal.depression_flag_service")
    @patch("app.api.v1.endpoints.journal.hf_emotion_service")
    def test_create_emotion_exception_still_saves(self, mock_hf, mock_dep, journal_client):
        headers = _register_and_login(journal_client)
        mock_hf.analyze = AsyncMock(side_effect=Exception("API crashed"))
        mock_dep.process_emotion = AsyncMock(return_value=_mock_flag_status())

        resp = journal_client.post(
            "/api/v1/journal",
            json={"mood": 2, "text": "Feeling terrible"},
            headers=headers,
        )

        assert resp.status_code == 201
        assert resp.json()["emotion_analyzed"] is False

    @patch("app.api.v1.endpoints.journal.depression_flag_service")
    @patch("app.api.v1.endpoints.journal.hf_emotion_service")
    def test_create_sadness_detected(self, mock_hf, mock_dep, journal_client):
        headers = _register_and_login(journal_client)
        mock_hf.analyze = AsyncMock(return_value=_mock_emotion_result(
            "sadness", 0.91,
            {"sadness": 0.91, "joy": 0.02, "anger": 0.03, "fear": 0.02, "neutral": 0.02},
        ))
        mock_dep.process_emotion = AsyncMock(return_value=_mock_flag_status())

        resp = journal_client.post(
            "/api/v1/journal",
            json={"mood": 1, "text": "I feel so sad and hopeless today"},
            headers=headers,
        )

        assert resp.status_code == 201
        assert resp.json()["emotion_label"] == "sadness"
        assert resp.json()["emotion_confidence"] == 0.91

    def test_create_unauthenticated(self, journal_client):
        resp = journal_client.post("/api/v1/journal", json={"mood": 3, "text": "Test"})
        assert resp.status_code == 401

    @patch("app.api.v1.endpoints.journal.depression_flag_service")
    @patch("app.api.v1.endpoints.journal.hf_emotion_service")
    def test_create_invalid_mood(self, mock_hf, mock_dep, journal_client):
        headers = _register_and_login(journal_client)
        resp = journal_client.post(
            "/api/v1/journal", json={"mood": 11, "text": "Test"}, headers=headers,
        )
        assert resp.status_code == 422

    @patch("app.api.v1.endpoints.journal.depression_flag_service")
    @patch("app.api.v1.endpoints.journal.hf_emotion_service")
    def test_create_empty_text(self, mock_hf, mock_dep, journal_client):
        headers = _register_and_login(journal_client)
        resp = journal_client.post(
            "/api/v1/journal", json={"mood": 3, "text": ""}, headers=headers,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests: GET /journal
# ---------------------------------------------------------------------------


class TestListJournalEntries:

    @patch("app.api.v1.endpoints.journal.depression_flag_service")
    @patch("app.api.v1.endpoints.journal.hf_emotion_service")
    def test_list_entries(self, mock_hf, mock_dep, journal_client):
        headers = _register_and_login(journal_client)
        mock_hf.analyze = AsyncMock(return_value=_mock_emotion_result())
        mock_dep.process_emotion = AsyncMock(return_value=_mock_flag_status())

        journal_client.post("/api/v1/journal", json={"mood": 4, "text": "Entry one"}, headers=headers)
        journal_client.post("/api/v1/journal", json={"mood": 2, "text": "Entry two"}, headers=headers)

        resp = journal_client.get("/api/v1/journal", headers=headers)
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) == 2
        assert entries[0]["text"] == "Entry two"  # newest first
        assert all(e["emotion_analyzed"] for e in entries)

    def test_list_empty(self, journal_client):
        headers = _register_and_login(journal_client)
        resp = journal_client.get("/api/v1/journal", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("app.api.v1.endpoints.journal.depression_flag_service")
    @patch("app.api.v1.endpoints.journal.hf_emotion_service")
    def test_list_with_limit(self, mock_hf, mock_dep, journal_client):
        headers = _register_and_login(journal_client)
        mock_hf.analyze = AsyncMock(return_value=_mock_emotion_result())
        mock_dep.process_emotion = AsyncMock(return_value=_mock_flag_status())

        for i in range(5):
            journal_client.post("/api/v1/journal", json={"mood": 3, "text": f"Entry {i}"}, headers=headers)

        resp = journal_client.get("/api/v1/journal?limit=2", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# Tests: DELETE /journal/{entry_id}
# ---------------------------------------------------------------------------


class TestDeleteJournalEntry:

    @patch("app.api.v1.endpoints.journal.depression_flag_service")
    @patch("app.api.v1.endpoints.journal.hf_emotion_service")
    def test_delete_entry(self, mock_hf, mock_dep, journal_client):
        headers = _register_and_login(journal_client)
        mock_hf.analyze = AsyncMock(return_value=_mock_emotion_result())
        mock_dep.process_emotion = AsyncMock(return_value=_mock_flag_status())

        create_resp = journal_client.post(
            "/api/v1/journal", json={"mood": 3, "text": "To be deleted"}, headers=headers,
        )
        entry_id = create_resp.json()["id"]

        del_resp = journal_client.delete(f"/api/v1/journal/{entry_id}", headers=headers)
        assert del_resp.status_code == 204

        # Verify it's gone
        assert len(journal_client.get("/api/v1/journal", headers=headers).json()) == 0

    def test_delete_nonexistent(self, journal_client):
        headers = _register_and_login(journal_client)
        resp = journal_client.delete(f"/api/v1/journal/{uuid.uuid4()}", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Tests: Depression flag integration
# ---------------------------------------------------------------------------


class TestDepressionFlagIntegration:

    @patch("app.api.v1.endpoints.journal.depression_flag_service")
    @patch("app.api.v1.endpoints.journal.hf_emotion_service")
    def test_depression_flag_called_on_save(self, mock_hf, mock_dep, journal_client):
        headers = _register_and_login(journal_client)
        mock_hf.analyze = AsyncMock(return_value=_mock_emotion_result("sadness", 0.9))
        mock_dep.process_emotion = AsyncMock(return_value=_mock_flag_status())

        journal_client.post(
            "/api/v1/journal", json={"mood": 1, "text": "Feeling very down"}, headers=headers,
        )

        mock_dep.process_emotion.assert_called_once()
        call_kwargs = mock_dep.process_emotion.call_args
        # Check positional or keyword args
        if call_kwargs.args:
            emotion_data = call_kwargs.args[1]
        else:
            emotion_data = call_kwargs.kwargs.get("emotion_data", {})
        assert emotion_data.get("dominant_emotion") == "sadness"

    @patch("app.api.v1.endpoints.journal.depression_flag_service")
    @patch("app.api.v1.endpoints.journal.hf_emotion_service")
    def test_depression_flag_not_called_on_failure(self, mock_hf, mock_dep, journal_client):
        headers = _register_and_login(journal_client)
        mock_hf.analyze = AsyncMock(return_value=None)
        mock_dep.process_emotion = AsyncMock(return_value=_mock_flag_status())

        journal_client.post(
            "/api/v1/journal", json={"mood": 2, "text": "Meh day"}, headers=headers,
        )

        mock_dep.process_emotion.assert_not_called()
