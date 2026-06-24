import pytest
from httpx import AsyncClient, ASGITransport
from mongomock_motor import AsyncMongoMockClient
from app.main import app
from app.core.middleware import limiter
from app.core.config import settings
from app.core import database as db_module
from limits.storage import MemoryStorage

@pytest.fixture(autouse=True)
def setup_mock_db():
    db_module.client = AsyncMongoMockClient()
    db_module.database = db_module.client[settings.DATABASE_NAME]
    from app.services.auth import auth_service
    auth_service._users_collection = None
    auth_service._reset_tokens_collection = None
    yield
    db_module.client.close()
    db_module.client = None
    db_module.database = None
    auth_service._users_collection = None
    auth_service._reset_tokens_collection = None


@pytest.fixture(autouse=True)
def reset_limiter():
    limiter._storage.reset()
    if hasattr(limiter, "limiter") and hasattr(limiter.limiter, "storage"):
        limiter.limiter.storage.reset()
    yield

@pytest.mark.asyncio
async def test_login_rate_limit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        payload = {"username": "test@example.com", "password": "wrongpass"}
        responses = []
        for _ in range(10):
            r = await client.post("/api/v1/auth/login", data=payload)
            responses.append(r.status_code)
        print(f"Responses: {responses}")
        assert 429 in responses, f"Expected 429 in responses, got: {responses}"

@pytest.mark.asyncio
async def test_register_rate_limit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        responses = []
        for i in range(10):
            r = await client.post("/api/v1/auth/register", json={
                "email": f"newuser{i}@ratelimitest.com",
                "password": "Test@1234",
                "name": f"User {i}"
            })
            responses.append(r.status_code)
        print(f"Responses: {responses}")
        assert 429 in responses, f"Expected 429 in responses, got: {responses}"

@pytest.mark.asyncio
async def test_refresh_rate_limit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        responses = []
        for _ in range(15):
            r = await client.post("/api/v1/auth/refresh", json="faketoken")
            responses.append(r.status_code)
        print(f"Responses: {responses}")
        assert 429 in responses, f"Expected 429 in responses, got: {responses}"

@pytest.mark.asyncio
async def test_429_response_structure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        payload = {"username": "structure@test.com", "password": "x"}
        r = None
        for _ in range(10):
            r = await client.post("/api/v1/auth/login", data=payload)
            if r.status_code == 429:
                break
        assert r.status_code == 429, f"Expected 429, got {r.status_code}"
        body = r.json()
        assert body["error"] == "rate_limit_exceeded"
        assert "message" in body
        assert "retry_after" in body
        assert "Retry-After" in r.headers


async def get_user_headers(client, email: str, password: str = "Test@1234") -> dict:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "name": "Rate Limit Tester"
    })
    r = await client.post("/api/v1/auth/login", data={
        "username": email,
        "password": password
    })
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_audio_analyze_rate_limit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        headers = await get_user_headers(client, "audio-user@test.com")
        payload = {
            "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
            "audio_format": "wav"
        }
        
        responses = []
        for _ in range(10):
            r = await client.post("/api/v1/analyze/audio", json=payload, headers=headers)
            responses.append(r.status_code)
            
        assert all(status == 200 for status in responses)
        
        # 11th request gets 429
        r = await client.post("/api/v1/analyze/audio", json=payload, headers=headers)
        assert r.status_code == 429
        assert "Retry-After" in r.headers
        
        body = r.json()
        assert body["error"] == "rate_limit_exceeded"
        assert "retry_after" in body


@pytest.mark.asyncio
async def test_image_analyze_rate_limit():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        headers = await get_user_headers(client, "image-user@test.com")
        payload = {
            "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "image_format": "jpeg"
        }
        
        responses = []
        for _ in range(10):
            r = await client.post("/api/v1/analyze/image", json=payload, headers=headers)
            responses.append(r.status_code)
            
        assert all(status == 200 for status in responses)
        
        # 11th request gets 429
        r = await client.post("/api/v1/analyze/image", json=payload, headers=headers)
        assert r.status_code == 429
        assert "Retry-After" in r.headers
        
        body = r.json()
        assert body["error"] == "rate_limit_exceeded"
        assert "retry_after" in body


@pytest.mark.asyncio
async def test_rate_limit_is_per_user_not_global():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
        headers_a = await get_user_headers(client, "user-a@test.com")
        headers_b = await get_user_headers(client, "user-b@test.com")
        
        payload = {
            "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
            "audio_format": "wav"
        }
        
        for _ in range(10):
            r = await client.post("/api/v1/analyze/audio", json=payload, headers=headers_a)
            assert r.status_code == 200
            
        r_a = await client.post("/api/v1/analyze/audio", json=payload, headers=headers_a)
        assert r_a.status_code == 429
        
        r_b = await client.post("/api/v1/analyze/audio", json=payload, headers=headers_b)
        assert r_b.status_code == 200


@pytest.mark.asyncio
async def test_rate_limit_env_override():
    from app.core.config import settings
    original_limit = settings.RATE_LIMIT_PER_MINUTE
    settings.RATE_LIMIT_PER_MINUTE = 3
    
    try:
        limiter._storage.reset()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as client:
            headers = await get_user_headers(client, "override-user@test.com")
            payload = {
                "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=",
                "audio_format": "wav"
            }
            
            for _ in range(3):
                r = await client.post("/api/v1/analyze/audio", json=payload, headers=headers)
                assert r.status_code == 200
                
            r = await client.post("/api/v1/analyze/audio", json=payload, headers=headers)
            assert r.status_code == 429
    finally:
        settings.RATE_LIMIT_PER_MINUTE = original_limit

