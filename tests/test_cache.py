"""Tests for Redis cache service and journal cache-aside behavior.

Covers:
- CacheService unit tests (hit, miss, set, delete, delete_pattern, Redis errors)
- CACHE_ENABLED=False path
- JournalService cache-aside (list, mood-history, create/update/delete invalidation)
- Fallback to database when Redis is unavailable
- API-level tests with X-Cache response header
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis.exceptions import RedisError

from app.api.v1.endpoints import journal as journal_endpoints
from app.api.v1.endpoints import stats as stats_endpoints
from app.api.v1.endpoints import auth as auth_endpoints
from app.core import database as db_module
from app.core.config import settings
from app.models.journal import JournalEntryCreate
from app.services.auth import auth_service
from app.services.cache import (
    CacheService,
    cache_service,
    journal_list_cache_key,
    journal_list_cache_pattern,
    mood_history_cache_key,
    mood_history_cache_pattern,
)
from app.services.journal import journal_service
from mongomock_motor import AsyncMongoMockClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_auth_service_collections() -> None:
    auth_service._users_collection = None
    auth_service._reset_tokens_collection = None


def _reset_journal_service_collection() -> None:
    journal_service._collection = None


@asynccontextmanager
async def _journal_test_lifespan(app: FastAPI):
    db_module.client = AsyncMongoMockClient()
    db_module.database = db_module.client[settings.DATABASE_NAME]
    _reset_auth_service_collections()
    _reset_journal_service_collection()
    yield
    db_module.client.close()
    db_module.client = None
    db_module.database = None
    _reset_auth_service_collections()
    _reset_journal_service_collection()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def journal_client():
    app = FastAPI(lifespan=_journal_test_lifespan)
    app.include_router(auth_endpoints.router, prefix="/api/v1/auth")
    app.include_router(journal_endpoints.router, prefix="/api/v1")
    app.include_router(stats_endpoints.router, prefix="/api/v1")

    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_headers(journal_client):
    email = f"cache-user-{uuid.uuid4().hex[:8]}@example.com"
    password = "Test@Pass123"
    journal_client.post(
        "/api/v1/auth/register",
        json={"email": email, "name": "Cache User", "password": password, "role": "user"},
    )
    login = journal_client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_db():
    db_module.client = AsyncMongoMockClient()
    db_module.database = db_module.client[settings.DATABASE_NAME]
    _reset_journal_service_collection()
    yield
    db_module.client.close()
    db_module.client = None
    db_module.database = None
    _reset_journal_service_collection()


@pytest.fixture
def memory_cache(monkeypatch):
    """In-memory dict that replaces Redis for deterministic cache testing."""
    store: dict = {}

    async def get_json(key: str):
        return store.get(key)

    async def set_json(key: str, value, ttl: int):
        store[key] = value

    async def delete(key: str):
        store.pop(key, None)

    async def delete_pattern(pattern: str):
        prefix = pattern.replace("*", "")
        for key in list(store.keys()):
            if key.startswith(prefix):
                del store[key]

    monkeypatch.setattr(cache_service, "get_json", get_json)
    monkeypatch.setattr(cache_service, "set_json", set_json)
    monkeypatch.setattr(cache_service, "delete", delete)
    monkeypatch.setattr(cache_service, "delete_pattern", delete_pattern)
    return store


# ===========================================================================
# 1. CacheService unit tests
# ===========================================================================

class TestCacheServiceGetJson:
    """Tests for CacheService.get_json()."""

    @pytest.mark.asyncio
    async def test_hit(self):
        service = CacheService()
        mock_redis = AsyncMock()
        mock_redis.get.return_value = '{"value": 1}'

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: mock_redis)
            mp.setattr(settings, "CACHE_ENABLED", True)
            result = await service.get_json("test-key")

        assert result == {"value": 1}

    @pytest.mark.asyncio
    async def test_miss(self):
        service = CacheService()
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: mock_redis)
            mp.setattr(settings, "CACHE_ENABLED", True)
            result = await service.get_json("missing-key")

        assert result is None

    @pytest.mark.asyncio
    async def test_redis_error_returns_none(self):
        service = CacheService()
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = RedisError("connection refused")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: mock_redis)
            mp.setattr(settings, "CACHE_ENABLED", True)
            result = await service.get_json("error-key")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_cache_disabled(self):
        service = CacheService()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(settings, "CACHE_ENABLED", False)
            result = await service.get_json("any-key")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_redis_client_is_none(self):
        service = CacheService()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: None)
            mp.setattr(settings, "CACHE_ENABLED", True)
            result = await service.get_json("any-key")

        assert result is None


class TestCacheServiceSetJson:
    """Tests for CacheService.set_json()."""

    @pytest.mark.asyncio
    async def test_redis_error_does_not_raise(self):
        service = CacheService()
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = RedisError("connection refused")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: mock_redis)
            mp.setattr(settings, "CACHE_ENABLED", True)
            # Should not raise
            await service.set_json("error-key", {"ok": True}, 60)

    @pytest.mark.asyncio
    async def test_noop_when_cache_disabled(self):
        service = CacheService()
        mock_redis = AsyncMock()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: mock_redis)
            mp.setattr(settings, "CACHE_ENABLED", False)
            await service.set_json("any-key", {"data": 1}, 60)

        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_noop_when_redis_client_is_none(self):
        service = CacheService()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: None)
            mp.setattr(settings, "CACHE_ENABLED", True)
            # Should not raise
            await service.set_json("any-key", {"data": 1}, 60)


class TestCacheServiceDelete:
    """Tests for CacheService.delete()."""

    @pytest.mark.asyncio
    async def test_delete_calls_redis(self):
        service = CacheService()
        mock_redis = AsyncMock()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: mock_redis)
            mp.setattr(settings, "CACHE_ENABLED", True)
            await service.delete("my-key")

        mock_redis.delete.assert_awaited_once_with("my-key")

    @pytest.mark.asyncio
    async def test_delete_redis_error_does_not_raise(self):
        service = CacheService()
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = RedisError("connection refused")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: mock_redis)
            mp.setattr(settings, "CACHE_ENABLED", True)
            # Should not raise
            await service.delete("error-key")

    @pytest.mark.asyncio
    async def test_delete_noop_when_cache_disabled(self):
        service = CacheService()
        mock_redis = AsyncMock()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: mock_redis)
            mp.setattr(settings, "CACHE_ENABLED", False)
            await service.delete("any-key")

        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_noop_when_redis_client_is_none(self):
        service = CacheService()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: None)
            mp.setattr(settings, "CACHE_ENABLED", True)
            # Should not raise
            await service.delete("any-key")


class TestCacheServiceDeletePattern:
    """Tests for CacheService.delete_pattern()."""

    @pytest.mark.asyncio
    async def test_delete_pattern_redis_error_does_not_raise(self):
        service = CacheService()
        mock_redis = AsyncMock()

        async def _failing_scan_iter(**kwargs):
            raise RedisError("connection refused")
            # make it an async generator
            yield  # pragma: no cover

        mock_redis.scan_iter = _failing_scan_iter

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: mock_redis)
            mp.setattr(settings, "CACHE_ENABLED", True)
            # Should not raise
            await service.delete_pattern("mindmitra:journal:*")

    @pytest.mark.asyncio
    async def test_delete_pattern_noop_when_cache_disabled(self):
        service = CacheService()
        mock_redis = AsyncMock()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: mock_redis)
            mp.setattr(settings, "CACHE_ENABLED", False)
            await service.delete_pattern("mindmitra:journal:*")

        mock_redis.scan_iter.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_pattern_noop_when_redis_client_is_none(self):
        service = CacheService()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: None)
            mp.setattr(settings, "CACHE_ENABLED", True)
            # Should not raise
            await service.delete_pattern("mindmitra:journal:*")


# ===========================================================================
# 2. Cache key helpers
# ===========================================================================

class TestCacheKeyHelpers:
    """Tests for cache key generator functions."""

    def test_journal_list_cache_key_includes_user_id(self):
        key = journal_list_cache_key("user-42")
        assert "user-42" in key
        assert key.startswith("mindmitra:journal:list:")

    def test_mood_history_cache_key_includes_user_and_days(self):
        key = mood_history_cache_key("user-42", 7)
        assert "user-42" in key
        assert "days:7" in key
        assert key.startswith("mindmitra:mood:history:")

    def test_journal_list_cache_pattern_is_glob(self):
        pattern = journal_list_cache_pattern("user-42")
        assert pattern.endswith("*")
        assert "user-42" in pattern

    def test_mood_history_cache_pattern_is_glob(self):
        pattern = mood_history_cache_pattern("user-42")
        assert pattern.endswith("*")
        assert "user-42" in pattern

    def test_different_users_get_different_keys(self):
        assert journal_list_cache_key("alice") != journal_list_cache_key("bob")
        assert mood_history_cache_key("alice", 30) != mood_history_cache_key("bob", 30)

    def test_different_days_get_different_keys(self):
        assert mood_history_cache_key("user-1", 7) != mood_history_cache_key("user-1", 30)


# ===========================================================================
# 3. JournalService cache-aside integration tests
# ===========================================================================

class TestJournalServiceCacheAside:
    """Integration tests for journal service cache behavior using in-memory store."""

    @pytest.mark.asyncio
    async def test_list_entries_populates_cache(self, mock_db, memory_cache):
        user_id = "user-list-1"
        entry = JournalEntryCreate(mood=7, text="Cached day", date=datetime.utcnow())
        await journal_service.create_entry(user_id, entry)
        await journal_service.list_entries(user_id)

        list_key = journal_list_cache_key(user_id)
        assert list_key in memory_cache

    @pytest.mark.asyncio
    async def test_list_entries_serves_from_cache(self, mock_db, memory_cache):
        user_id = "user-list-2"
        entry = JournalEntryCreate(mood=7, text="Cached day", date=datetime.utcnow())
        created = await journal_service.create_entry(user_id, entry)
        await journal_service.list_entries(user_id)

        # Replace DB find with a function that should never be called
        original_find = journal_service.collection.find

        def failing_find(*args, **kwargs):
            raise AssertionError("Database should not be queried on cache hit")

        journal_service.collection.find = failing_find
        try:
            cached_entries = await journal_service.list_entries(user_id)
        finally:
            journal_service.collection.find = original_find

        assert len(cached_entries) == 1
        assert cached_entries[0].id == created.id

    @pytest.mark.asyncio
    async def test_create_entry_invalidates_cache(self, mock_db, memory_cache):
        user_id = "user-create-inv"
        await journal_service.create_entry(
            user_id,
            JournalEntryCreate(mood=5, text="First", date=datetime.utcnow()),
        )
        await journal_service.list_entries(user_id)
        list_key = journal_list_cache_key(user_id)
        assert list_key in memory_cache

        await journal_service.create_entry(
            user_id,
            JournalEntryCreate(mood=8, text="Second", date=datetime.utcnow()),
        )
        assert list_key not in memory_cache

        entries = await journal_service.list_entries(user_id)
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_update_entry_invalidates_cache(self, mock_db, memory_cache):
        """Updating an entry must clear both journal list and mood history caches."""
        user_id = "user-update-inv"
        from app.models.journal import JournalEntryUpdate

        created = await journal_service.create_entry(
            user_id,
            JournalEntryCreate(mood=4, text="Before update", date=datetime.utcnow()),
        )
        # Populate both caches
        await journal_service.list_entries(user_id)
        await journal_service.get_mood_history(user_id, days=7)

        list_key = journal_list_cache_key(user_id)
        mood_key = mood_history_cache_key(user_id, 7)
        assert list_key in memory_cache
        assert mood_key in memory_cache

        # Update entry
        await journal_service.update_entry(
            user_id,
            created.id,
            JournalEntryUpdate(mood=9, text="After update"),
        )

        # Both caches should be invalidated
        assert list_key not in memory_cache
        assert mood_key not in memory_cache

    @pytest.mark.asyncio
    async def test_delete_entry_invalidates_cache(self, mock_db, memory_cache):
        user_id = "user-delete-inv"
        created = await journal_service.create_entry(
            user_id,
            JournalEntryCreate(mood=6, text="To delete", date=datetime.utcnow()),
        )
        await journal_service.list_entries(user_id)
        await journal_service.get_mood_history(user_id, days=7)

        list_key = journal_list_cache_key(user_id)
        mood_key = mood_history_cache_key(user_id, 7)
        assert list_key in memory_cache
        assert mood_key in memory_cache

        await journal_service.delete_entry(user_id, created.id)
        assert list_key not in memory_cache
        assert mood_key not in memory_cache

    @pytest.mark.asyncio
    async def test_mood_history_cache_and_invalidation(self, mock_db, memory_cache):
        user_id = "user-mood-1"
        created = await journal_service.create_entry(
            user_id,
            JournalEntryCreate(mood=6, text="Mood log", date=datetime.utcnow()),
        )

        history = await journal_service.get_mood_history(user_id, days=7)
        history_key = mood_history_cache_key(user_id, 7)
        assert history_key in memory_cache
        assert history.average_mood == 6.0

        await journal_service.delete_entry(user_id, created.id)
        assert history_key not in memory_cache


# ===========================================================================
# 4. Fallback / resilience tests
# ===========================================================================

class TestCacheFallback:
    """Tests that the app works correctly when Redis is unavailable."""

    @pytest.mark.asyncio
    async def test_list_falls_back_to_db_when_redis_unavailable(self, mock_db):
        user_id = "user-fallback-1"
        await journal_service.create_entry(
            user_id,
            JournalEntryCreate(mood=4, text="Fallback", date=datetime.utcnow()),
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: None)
            entries = await journal_service.list_entries(user_id)

        assert len(entries) == 1
        assert entries[0].text == "Fallback"

    @pytest.mark.asyncio
    async def test_mood_history_falls_back_to_db_when_redis_unavailable(self, mock_db):
        user_id = "user-fallback-2"
        await journal_service.create_entry(
            user_id,
            JournalEntryCreate(mood=8, text="Mood fallback", date=datetime.utcnow()),
        )

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: None)
            history = await journal_service.get_mood_history(user_id, days=30)

        assert history.average_mood == 8.0
        assert len(history.entries) == 1

    @pytest.mark.asyncio
    async def test_create_entry_works_when_redis_unavailable(self, mock_db):
        """Cache invalidation should not break write operations."""
        user_id = "user-fallback-3"

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.services.cache.get_redis", lambda: None)
            entry = await journal_service.create_entry(
                user_id,
                JournalEntryCreate(mood=5, text="No Redis", date=datetime.utcnow()),
            )

        assert entry.text == "No Redis"


# ===========================================================================
# 5. API-level tests (X-Cache headers, end-to-end cache flow)
# ===========================================================================

class TestJournalAPICache:
    """API tests verifying X-Cache header and cache behavior through HTTP."""

    def test_first_request_is_cache_miss(self, journal_client, auth_headers, memory_cache):
        journal_client.post(
            "/api/v1/journal",
            json={"mood": 7, "text": "API cache test"},
            headers=auth_headers,
        )

        resp = journal_client.get("/api/v1/journal", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache") == "MISS"

    def test_second_request_is_cache_hit(self, journal_client, auth_headers, memory_cache):
        journal_client.post(
            "/api/v1/journal",
            json={"mood": 7, "text": "API cache test"},
            headers=auth_headers,
        )

        first = journal_client.get("/api/v1/journal", headers=auth_headers)
        second = journal_client.get("/api/v1/journal", headers=auth_headers)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.headers.get("X-Cache") == "MISS"
        assert second.headers.get("X-Cache") == "HIT"
        assert first.json() == second.json()

    def test_create_invalidates_and_next_get_is_miss(self, journal_client, auth_headers, memory_cache):
        # Create and GET to warm cache
        journal_client.post(
            "/api/v1/journal",
            json={"mood": 5, "text": "Warm up"},
            headers=auth_headers,
        )
        journal_client.get("/api/v1/journal", headers=auth_headers)

        # Create another entry (invalidates cache)
        journal_client.post(
            "/api/v1/journal",
            json={"mood": 9, "text": "New entry"},
            headers=auth_headers,
        )

        # Next GET should be a MISS
        resp = journal_client.get("/api/v1/journal", headers=auth_headers)
        assert resp.headers.get("X-Cache") == "MISS"
        assert len(resp.json()) == 2

    def test_update_invalidates_cache(self, journal_client, auth_headers, memory_cache):
        create_resp = journal_client.post(
            "/api/v1/journal",
            json={"mood": 5, "text": "Original"},
            headers=auth_headers,
        )
        entry_id = create_resp.json()["id"]

        # Warm cache
        journal_client.get("/api/v1/journal", headers=auth_headers)

        # Update
        journal_client.put(
            f"/api/v1/journal/{entry_id}",
            json={"mood": 10, "text": "Updated"},
            headers=auth_headers,
        )

        # Next GET should be MISS
        resp = journal_client.get("/api/v1/journal", headers=auth_headers)
        assert resp.headers.get("X-Cache") == "MISS"

    def test_delete_invalidates_cache(self, journal_client, auth_headers, memory_cache):
        create_resp = journal_client.post(
            "/api/v1/journal",
            json={"mood": 5, "text": "To delete"},
            headers=auth_headers,
        )
        entry_id = create_resp.json()["id"]

        # Warm cache
        journal_client.get("/api/v1/journal", headers=auth_headers)

        # Delete
        delete_resp = journal_client.delete(
            f"/api/v1/journal/{entry_id}",
            headers=auth_headers,
        )
        assert delete_resp.status_code == 204

        # Next GET should be MISS and return empty
        resp = journal_client.get("/api/v1/journal", headers=auth_headers)
        assert resp.headers.get("X-Cache") == "MISS"
        assert len(resp.json()) == 0


class TestMoodHistoryAPICache:
    """API tests verifying X-Cache header on the mood-history endpoint."""

    def test_first_request_is_cache_miss(self, journal_client, auth_headers, memory_cache):
        journal_client.post(
            "/api/v1/journal",
            json={"mood": 9, "text": "Great week"},
            headers=auth_headers,
        )

        resp = journal_client.get("/api/v1/stats/mood-history?days=14", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers.get("X-Cache") == "MISS"

    def test_second_request_is_cache_hit(self, journal_client, auth_headers, memory_cache):
        journal_client.post(
            "/api/v1/journal",
            json={"mood": 9, "text": "Great week"},
            headers=auth_headers,
        )

        first = journal_client.get("/api/v1/stats/mood-history?days=14", headers=auth_headers)
        second = journal_client.get("/api/v1/stats/mood-history?days=14", headers=auth_headers)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.headers.get("X-Cache") == "MISS"
        assert second.headers.get("X-Cache") == "HIT"
        assert first.json()["average_mood"] == 9.0
        assert first.json() == second.json()

    def test_different_days_are_separate_cache_entries(self, journal_client, auth_headers, memory_cache):
        journal_client.post(
            "/api/v1/journal",
            json={"mood": 7, "text": "Entry"},
            headers=auth_headers,
        )

        resp_7 = journal_client.get("/api/v1/stats/mood-history?days=7", headers=auth_headers)
        resp_30 = journal_client.get("/api/v1/stats/mood-history?days=30", headers=auth_headers)

        # Both should be MISS since they are different cache keys
        assert resp_7.headers.get("X-Cache") == "MISS"
        assert resp_30.headers.get("X-Cache") == "MISS"

        # Second request for each should be HIT
        resp_7_hit = journal_client.get("/api/v1/stats/mood-history?days=7", headers=auth_headers)
        resp_30_hit = journal_client.get("/api/v1/stats/mood-history?days=30", headers=auth_headers)
        assert resp_7_hit.headers.get("X-Cache") == "HIT"
        assert resp_30_hit.headers.get("X-Cache") == "HIT"


# ===========================================================================
# 6. JSON encoder edge cases
# ===========================================================================

class TestCacheJSONEncoder:
    """Tests for the custom JSON encoder used for cache serialization."""

    @pytest.mark.asyncio
    async def test_uuid_serialization(self):
        """UUIDs should be serialized as strings without error."""
        from app.services.cache import _CacheJSONEncoder
        import json

        test_uuid = uuid.uuid4()
        result = json.dumps({"id": test_uuid}, cls=_CacheJSONEncoder)
        assert str(test_uuid) in result

    @pytest.mark.asyncio
    async def test_datetime_serialization(self):
        """Datetimes should be serialized as ISO format strings."""
        from app.services.cache import _CacheJSONEncoder
        import json

        now = datetime(2025, 6, 15, 12, 30, 0)
        result = json.dumps({"ts": now}, cls=_CacheJSONEncoder)
        assert "2025-06-15" in result

    @pytest.mark.asyncio
    async def test_date_serialization(self):
        """Date objects should be serialized as ISO format strings."""
        from app.services.cache import _CacheJSONEncoder
        from datetime import date
        import json

        d = date(2025, 1, 1)
        result = json.dumps({"d": d}, cls=_CacheJSONEncoder)
        assert "2025-01-01" in result


# ===========================================================================
# 7. Edge cases: empty data, user isolation, days clamping
# ===========================================================================

class TestEdgeCases:
    """Edge-case tests for cache behavior."""

    @pytest.mark.asyncio
    async def test_empty_journal_list_is_cached(self, mock_db, memory_cache):
        """An empty journal list should still be cached (not treated as miss)."""
        user_id = "user-empty-1"
        entries = await journal_service.list_entries(user_id)
        assert entries == []

        list_key = journal_list_cache_key(user_id)
        assert list_key in memory_cache
        assert memory_cache[list_key] == []

    @pytest.mark.asyncio
    async def test_empty_mood_history_is_cached(self, mock_db, memory_cache):
        """Mood history with no entries should still be cached."""
        user_id = "user-empty-2"
        history = await journal_service.get_mood_history(user_id, days=7)
        assert history.entries == []
        assert history.average_mood is None

        mood_key = mood_history_cache_key(user_id, 7)
        assert mood_key in memory_cache

    @pytest.mark.asyncio
    async def test_user_cache_isolation(self, mock_db, memory_cache):
        """User A's cache should not leak into User B's responses."""
        user_a = "user-iso-a"
        user_b = "user-iso-b"

        await journal_service.create_entry(
            user_a,
            JournalEntryCreate(mood=9, text="User A private", date=datetime.utcnow()),
        )
        await journal_service.list_entries(user_a)

        entries_b = await journal_service.list_entries(user_b)
        assert entries_b == []

        entries_a = await journal_service.list_entries(user_a)
        assert len(entries_a) == 1
        assert entries_a[0].text == "User A private"

    @pytest.mark.asyncio
    async def test_mood_history_days_clamped_to_min_1(self, mock_db, memory_cache):
        """Days < 1 should be clamped to 1."""
        user_id = "user-clamp-1"
        history = await journal_service.get_mood_history(user_id, days=0)
        assert history.period_days == 1

    @pytest.mark.asyncio
    async def test_mood_history_days_clamped_to_max_365(self, mock_db, memory_cache):
        """Days > 365 should be clamped to 365."""
        user_id = "user-clamp-2"
        history = await journal_service.get_mood_history(user_id, days=999)
        assert history.period_days == 365

    @pytest.mark.asyncio
    async def test_delete_nonexistent_entry_does_not_invalidate(self, mock_db, memory_cache):
        """Deleting an entry that doesn't exist should not clear the cache."""
        user_id = "user-no-del"
        await journal_service.create_entry(
            user_id,
            JournalEntryCreate(mood=5, text="Keep me", date=datetime.utcnow()),
        )
        await journal_service.list_entries(user_id)
        list_key = journal_list_cache_key(user_id)
        assert list_key in memory_cache

        result = await journal_service.delete_entry(user_id, "nonexistent-id")
        assert result is False
        # Cache should still be intact since nothing was actually deleted
        assert list_key in memory_cache


# ===========================================================================
# 8. Redis lifecycle tests
# ===========================================================================

class TestRedisLifecycle:
    """Tests for Redis connection init/close/ping lifecycle."""

    @pytest.mark.asyncio
    async def test_ping_redis_returns_false_when_client_is_none(self):
        from app.core.redis import ping_redis
        import app.core.redis as redis_mod

        original = redis_mod.redis_client
        redis_mod.redis_client = None
        try:
            result = await ping_redis()
            assert result is False
        finally:
            redis_mod.redis_client = original

    @pytest.mark.asyncio
    async def test_close_redis_when_no_client(self):
        """close_redis should be a no-op when client is None."""
        from app.core.redis import close_redis
        import app.core.redis as redis_mod

        original = redis_mod.redis_client
        redis_mod.redis_client = None
        try:
            await close_redis()  # Should not raise
        finally:
            redis_mod.redis_client = original

    @pytest.mark.asyncio
    async def test_init_redis_skips_when_cache_disabled(self):
        """init_redis should be a no-op when CACHE_ENABLED is False."""
        from app.core.redis import init_redis
        import app.core.redis as redis_mod

        original = redis_mod.redis_client
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(settings, "CACHE_ENABLED", False)
            redis_mod.redis_client = None
            await init_redis()
            assert redis_mod.redis_client is None
        redis_mod.redis_client = original

    @pytest.mark.asyncio
    async def test_get_redis_returns_client(self):
        """get_redis should return whatever the module-level client is."""
        from app.core.redis import get_redis
        import app.core.redis as redis_mod

        original = redis_mod.redis_client
        sentinel = object()
        redis_mod.redis_client = sentinel
        try:
            assert get_redis() is sentinel
        finally:
            redis_mod.redis_client = original

