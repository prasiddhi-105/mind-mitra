
import asyncio
import pytest
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import auth_service

client = TestClient(app)

PASSWORD_RESET_MESSAGE = (
    "If an account exists for this email, a reset link has been sent."
)


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


def _register_user(email: str, password: str = "testpassword123"):
    user_data = {
        "email": email,
        "name": "Reset Test User",
        "password": password,
        "role": "user",
    }
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    return user_data


def _extract_token_from_link(reset_link: str) -> str:
    query = parse_qs(urlparse(reset_link).query)
    return query["token"][0]


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "mindmitra-backend"


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Welcome to MindMitra API"
    assert data["version"] == "1.0.0"


def test_register_user():
    """Test user registration"""
    user_data = {
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpassword123",
        "role": "user"
    }
    
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]
    assert data["role"] == user_data["role"]
    assert "id" in data


def test_register_duplicate_user():
    """Test registering duplicate user"""
    user_data = {
        "email": "duplicate@example.com",
        "name": "Duplicate User",
        "password": "testpassword123",
        "role": "user"
    }
    
    # Register first time
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    
    # Try to register again
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_user():
    """Test user login"""
    # First register a user
    user_data = {
        "email": "login@example.com",
        "name": "Login User",
        "password": "testpassword123",
        "role": "user"
    }
    
    client.post("/api/v1/auth/register", json=user_data)
    
    # Then login
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    login_data = {
        "username": "nonexistent@example.com",
        "password": "wrongpassword"
    }
    
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_protected_endpoint_without_token():
    """Test accessing protected endpoint without token"""
    response = client.get("/api/v1/auth/profile")
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]


def test_protected_endpoint_with_token():
    """Test accessing protected endpoint with valid token"""
    # Register and login to get token
    user_data = {
        "email": "protected@example.com",
        "name": "Protected User",
        "password": "testpassword123",
        "role": "user"
    }
    
    client.post("/api/v1/auth/register", json=user_data)
    
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    
    login_response = client.post("/api/v1/auth/login", data=login_data)
    token = login_response.json()["access_token"]
    
    # Access protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/profile", headers=headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["name"] == user_data["name"]


def test_forgot_password_known_email(mock_password_reset_email):
    """Test password reset request for a registered email."""
    email = "forgot-known@example.com"
    _register_user(email)

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )
    assert response.status_code == 200
    assert response.json()["message"] == PASSWORD_RESET_MESSAGE
    assert len(mock_password_reset_email) == 1
    assert mock_password_reset_email[0]["email"] == email


def test_forgot_password_unknown_email(mock_password_reset_email):
    """Test password reset request does not reveal unknown emails."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "unknown@example.com"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == PASSWORD_RESET_MESSAGE
    assert len(mock_password_reset_email) == 0


def test_reset_password_success(mock_password_reset_email):
    """Test successful password reset and login with new password."""
    email = "reset-success@example.com"
    old_password = "testpassword123"
    new_password = "newpassword456"
    _register_user(email, old_password)

    forgot_response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": email},
    )
    assert forgot_response.status_code == 200

    token = _extract_token_from_link(mock_password_reset_email[0]["reset_link"])

    validate_response = client.get(
        "/api/v1/auth/reset-password/validate",
        params={"token": token},
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["valid"] is True

    reset_response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert reset_response.status_code == 200
    assert reset_response.json()["message"] == "Password reset successfully"

    old_login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": old_password},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": new_password},
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


def test_reset_password_expired_token(mock_password_reset_email):
    """Test reset fails when token has expired."""
    email = "reset-expired@example.com"
    _register_user(email)

    client.post("/api/v1/auth/forgot-password", json={"email": email})
    token = _extract_token_from_link(mock_password_reset_email[0]["reset_link"])

    token_hash = auth_service._hash_reset_token(token)
    past = datetime.utcnow() - timedelta(minutes=1)

    async def expire_token():
        await auth_service.reset_tokens_collection.update_one(
            {"token_hash": token_hash},
            {"$set": {"expires_at": past}},
        )

    asyncio.run(expire_token())

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "newpassword456"},
    )
    assert response.status_code == 400
    assert "Invalid or expired reset token" in response.json()["detail"]


def test_reset_password_reused_token(mock_password_reset_email):
    """Test reset token cannot be used twice."""
    email = "reset-reuse@example.com"
    _register_user(email)

    client.post("/api/v1/auth/forgot-password", json={"email": email})
    token = _extract_token_from_link(mock_password_reset_email[0]["reset_link"])

    first_reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "newpassword456"},
    )
    assert first_reset.status_code == 200

    second_reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "new_password": "anotherpassword789"},
    )
    assert second_reset.status_code == 400
    assert "Invalid or expired reset token" in second_reset.json()["detail"] 