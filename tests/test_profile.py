import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _register_and_login(email: str, name: str = "Profile User"):
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "name": name,
            "password": "testpassword123",
            "role": "user",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "testpassword123"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_profile():
    headers = _register_and_login("profile-get@example.com", "Sofie dsouza")
    response = client.get("/api/v1/auth/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "profile-get@example.com"
    assert data["name"] == "Sofie dsouza"
    assert data["emergency_contacts"] == []


def test_update_profile_name_and_emergency_contact():
    headers = _register_and_login("profile-update@example.com")
    response = client.put(
        "/api/v1/auth/profile",
        headers=headers,
        json={
            "name": "Updated Name",
            "emergency_contacts": [
                {
                    "name": "Jordan Lee",
                    "phone": "1234567890",
                    "email": "jordan@example.com",
                    "relationship": "friend",
                }
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert len(data["emergency_contacts"]) == 1
    assert data["emergency_contacts"][0]["name"] == "Jordan Lee"

    refreshed = client.get("/api/v1/auth/profile", headers=headers)
    assert refreshed.json()["name"] == "Updated Name"


def test_upload_profile_picture():
    headers = _register_and_login("profile-picture@example.com")

    image = Image.new("RGB", (100, 100), color=(73, 109, 137))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    response = client.post(
        "/api/v1/auth/profile/picture",
        headers=headers,
        files={"file": ("avatar.jpg", buffer, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["profile_picture_url"].startswith("/uploads/profile_pictures/")


def test_upload_profile_picture_rejects_invalid_type():
    headers = _register_and_login("profile-invalid@example.com")
    response = client.post(
        "/api/v1/auth/profile/picture",
        headers=headers,
        files={"file": ("notes.txt", io.BytesIO(b"not an image"), "text/plain")},
    )
    assert response.status_code == 400
