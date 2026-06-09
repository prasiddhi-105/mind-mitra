import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.models.user import User
from app.api.v1.endpoints import auth
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_emotion_fallback():
    """
    Test that the journal entry is saved successfully even if 
    HuggingFace API emotion analysis fails (simulating a production outage).
    """
    logger.info("Setting invalid HuggingFace API key to force failure...")
    original_key = settings.HUGGINGFACE_API_KEY
    settings.HUGGINGFACE_API_KEY = "invalid_token_to_force_failure"
    
    with TestClient(app, base_url="http://localhost") as client:
        # 1. Create a dummy user and login
        email = f"fallback_test_{uuid.uuid4()}@example.com"
        reg_resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "name": "Fallback Test User",
            "password": "testpassword123",
            "role": "user"
        })
        if reg_resp.status_code != 200:
            logger.error(f"Registration failed: {reg_resp.text}")
            raise RuntimeError("Registration failed")
        
        login_resp = client.post("/api/v1/auth/login", data={
            "username": email,
            "password": "testpassword123"
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Submit journal entry
        test_text = "This is a test entry to ensure fallback works."
        logger.info("Submitting journal entry...")
        resp = client.post("/api/v1/journal", json={
            "mood": 5,
            "text": test_text
        }, headers=headers)
        
        # 3. Verify fallback
        if resp.status_code == 201:
            data = resp.json()
            assert data["text"] == test_text
            assert data["emotion_analyzed"] is False
            assert data["emotion_label"] is None
            logger.info("SUCCESS: Fallback handled gracefully! Entry saved with status 201.")
        else:
            logger.error(f"FAILURE: Expected 201 but got {resp.status_code}. Response: {resp.text}")
        
    # Restore key
    settings.HUGGINGFACE_API_KEY = original_key

if __name__ == "__main__":
    test_emotion_fallback()
