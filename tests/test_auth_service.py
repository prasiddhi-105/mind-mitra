"""Unit tests for AuthService helpers."""

from datetime import timedelta

import pytest

from app.models.user import UserCreate, UserRole
from app.services.auth import auth_service, get_current_user


class TestAuthServiceUnit:
    def test_password_hash_and_verify(self):
        hashed = auth_service.get_password_hash("Test@Pass123")
        assert auth_service.verify_password("Test@Pass123", hashed)
        assert not auth_service.verify_password("wrongpassword", hashed)

    def test_create_and_verify_access_token(self):
        token = auth_service.create_access_token(
            data={"sub": "test@example.com", "user_id": "uid-1", "role": "user"},
            expires_delta=timedelta(minutes=5),
        )
        token_data = auth_service.verify_token(token)
        assert token_data is not None
        assert token_data.email == "test@example.com"
        assert token_data.user_id == "uid-1"
        assert token_data.role == UserRole.USER

    def test_verify_invalid_token_returns_none(self):
        assert auth_service.verify_token("not.a.valid.token") is None

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self):
        user = await auth_service.get_user_by_email("does-not-exist@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, registered_user):
        user = await auth_service.authenticate_user(
            registered_user["email"],
            "wrongpassword",
        )
        assert user is None

    @pytest.mark.asyncio
    async def test_create_user_duplicate_returns_none(self, registered_user):
        duplicate = UserCreate(
            email=registered_user["email"],
            name="Duplicate",
            password="Test@Pass123",
            role=UserRole.USER,
        )
        result = await auth_service.create_user(duplicate)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_dependency_invalid_token(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="invalid.token.value")
        assert exc_info.value.status_code == 401
