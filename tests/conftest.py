"""Shared pytest fixtures for authentication API tests."""

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt

from mongomock_motor import AsyncMongoMockClient

from app.api.v1.endpoints import auth as auth_endpoints
from app.core import database as db_module
from app.core.config import settings
from app.services.auth import auth_service

PASSWORD_RESET_MESSAGE = (
    "If an account exists for this email, a reset link has been sent."
)


def _reset_auth_service_collections() -> None:
    auth_service._users_collection = None
    auth_service._reset_tokens_collection = None


@asynccontextmanager
async def _test_lifespan(app: FastAPI):
    db_module.client = AsyncMongoMockClient()
    db_module.database = db_module.client[settings.DATABASE_NAME]
    _reset_auth_service_collections()
    yield
    db_module.client.close()
    db_module.client = None
    db_module.database = None
    _reset_auth_service_collections()


@pytest.fixture(autouse=True)
def clean_collections():
    """Clear mock collections between tests for isolation."""
    _reset_auth_service_collections()
    if db_module.database is not None:
        async def _clean():
            for name in ("users", "password_reset_tokens"):
                await db_module.database[name].delete_many({})

        asyncio.run(_clean())
    yield
    _reset_auth_service_collections()


def create_test_app() -> FastAPI:
    """Minimal app with auth routes only — avoids heavy ML imports in full app."""
    app = FastAPI(lifespan=_test_lifespan)
    app.include_router(auth_endpoints.router, prefix="/api/v1/auth")

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "mindmitra-backend",
            "version": "1.0.0",
        }

    @app.get("/")
    async def root():
        return {
            "message": "Welcome to MindMitra API",
            "version": "1.0.0",
            "status": "healthy",
        }

    return app


@pytest.fixture
def app():
    return create_test_app()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def unique_email():
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture
def user_data(unique_email):
    return {
        "email": unique_email,
        "name": "Test User",
        "password": "Test@Pass123",
        "role": "user",
    }


@pytest.fixture
def registered_user(client, user_data):
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    return {**user_data, "id": response.json()["id"]}


@pytest.fixture
def auth_tokens(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def mock_password_reset_email(monkeypatch):
    sent_emails = []

    async def fake_send_password_reset_email(user_email, user_name, reset_link):
        sent_emails.append({
            "email": user_email,
            "name": user_name,
            "reset_link": reset_link,
        })
        return True

    monkeypatch.setattr(
        "app.api.v1.endpoints.auth.notification_service.send_password_reset_email",
        fake_send_password_reset_email,
    )
    return sent_emails


def extract_token_from_reset_link(reset_link: str) -> str:
    query = parse_qs(urlparse(reset_link).query)
    return query["token"][0]


def make_expired_refresh_token(user_id: str, email: str) -> str:
    payload = {
        "sub": email,
        "user_id": user_id,
        "role": "user",
        "type": "refresh",
        "exp": datetime.utcnow() - timedelta(minutes=1),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def set_user_active(email: str, is_active: bool) -> None:
    async def _update():
        await auth_service.users_collection.update_one(
            {"email": email},
            {"$set": {"is_active": is_active}},
        )

    asyncio.run(_update())


def expire_password_reset_token(raw_token: str) -> None:
    token_hash = auth_service._hash_reset_token(raw_token)
    past = datetime.utcnow() - timedelta(minutes=1)

    async def _expire():
        await auth_service.reset_tokens_collection.update_one(
            {"token_hash": token_hash},
            {"$set": {"expires_at": past}},
        )

    asyncio.run(_expire())
