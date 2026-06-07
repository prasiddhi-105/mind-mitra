"""Tests for the HuggingFace emotion analysis service.

Uses httpx mock responses to test all service behaviors without making
real API calls.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.huggingface_emotion import (
    EmotionAnalysisResult,
    HuggingFaceEmotionService,
    _MODEL_URL,
    _MAX_TEXT_LENGTH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hf_response(emotions: dict[str, float] | None = None) -> list:
    """Build a mock HuggingFace API response payload."""
    if emotions is None:
        emotions = {
            "joy": 0.85,
            "sadness": 0.05,
            "anger": 0.03,
            "fear": 0.02,
            "disgust": 0.02,
            "surprise": 0.01,
            "neutral": 0.02,
        }
    return [[{"label": label, "score": score} for label, score in emotions.items()]]


def _mock_response(status_code: int = 200, json_data=None, text: str = "") -> httpx.Response:
    """Create a mock httpx.Response."""
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    response.text = text
    return response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestEmotionAnalysisResult:
    """Tests for the result Pydantic model."""

    def test_valid_result(self):
        result = EmotionAnalysisResult(
            label="joy",
            confidence=0.85,
            scores={"joy": 0.85, "sadness": 0.05},
        )
        assert result.label == "joy"
        assert result.confidence == 0.85
        assert result.scores["joy"] == 0.85

    def test_confidence_bounds(self):
        """Confidence must be between 0 and 1."""
        with pytest.raises(Exception):
            EmotionAnalysisResult(label="joy", confidence=1.5, scores={})

        with pytest.raises(Exception):
            EmotionAnalysisResult(label="joy", confidence=-0.1, scores={})


class TestHuggingFaceEmotionService:
    """Tests for the main service class."""

    @pytest.fixture
    def service(self):
        """Create a fresh service instance with a test API key."""
        svc = HuggingFaceEmotionService()
        svc._api_key = "test-api-key"
        return svc

    @pytest.mark.asyncio
    async def test_analyze_success(self, service):
        """Successful emotion analysis returns structured result."""
        mock_resp = _mock_response(200, _make_hf_response())

        with patch.object(service, "_ensure_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = client

            result = await service.analyze("I'm having a wonderful day!")

            assert result is not None
            assert isinstance(result, EmotionAnalysisResult)
            assert result.label == "joy"
            assert result.confidence == 0.85
            assert "sadness" in result.scores

    @pytest.mark.asyncio
    async def test_analyze_no_api_key(self):
        """Returns None when API key is not configured."""
        svc = HuggingFaceEmotionService()
        svc._api_key = None

        result = await svc.analyze("test text")
        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_empty_api_key(self):
        """Returns None when API key is empty string."""
        svc = HuggingFaceEmotionService()
        svc._api_key = ""

        result = await svc.analyze("test text")
        assert result is None

    @pytest.mark.asyncio
    async def test_analyze_empty_text(self, service):
        """Returns None for empty or whitespace-only text."""
        assert await service.analyze("") is None
        assert await service.analyze("   ") is None

    @pytest.mark.asyncio
    async def test_analyze_text_truncation(self, service):
        """Long text is truncated to MAX_TEXT_LENGTH before sending."""
        long_text = "x" * 1000
        mock_resp = _mock_response(200, _make_hf_response())

        with patch.object(service, "_ensure_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = client

            await service.analyze(long_text)

            # Verify the payload was truncated
            call_args = client.post.call_args
            payload = call_args.kwargs.get("json") or call_args[1].get("json")
            assert len(payload["inputs"]) == _MAX_TEXT_LENGTH

    @pytest.mark.asyncio
    async def test_analyze_rate_limited_429(self, service):
        """Returns None on 429 rate limit response."""
        mock_resp = _mock_response(429, text="Rate limit exceeded")

        with patch.object(service, "_ensure_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = client

            result = await service.analyze("test text")
            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_503_retry_success(self, service):
        """Retries once on 503 and succeeds."""
        loading_resp = _mock_response(503, {"estimated_time": 0.1})
        success_resp = _mock_response(200, _make_hf_response())

        with patch.object(service, "_ensure_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=[loading_resp, success_resp])
            mock_client.return_value = client

            result = await service.analyze("test text")

            assert result is not None
            assert result.label == "joy"
            assert client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_analyze_503_retry_still_loading(self, service):
        """Returns None when model still loading after retry."""
        loading_resp = _mock_response(503, {"estimated_time": 0.1})

        with patch.object(service, "_ensure_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=loading_resp)
            mock_client.return_value = client

            result = await service.analyze("test text")
            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_timeout(self, service):
        """Returns None on request timeout."""
        with patch.object(service, "_ensure_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.return_value = client

            result = await service.analyze("test text")
            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_network_error(self, service):
        """Returns None on network error."""
        with patch.object(service, "_ensure_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client.return_value = client

            result = await service.analyze("test text")
            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_unexpected_status(self, service):
        """Returns None on unexpected HTTP status codes."""
        mock_resp = _mock_response(500, text="Internal Server Error")

        with patch.object(service, "_ensure_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = client

            result = await service.analyze("test text")
            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_malformed_response(self, service):
        """Returns None when API returns unexpected JSON structure."""
        mock_resp = _mock_response(200, {"unexpected": "format"})

        with patch.object(service, "_ensure_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = client

            result = await service.analyze("test text")
            assert result is None

    @pytest.mark.asyncio
    async def test_analyze_sadness_dominant(self, service):
        """Correctly identifies sadness as dominant emotion."""
        sad_response = _make_hf_response({
            "sadness": 0.92,
            "joy": 0.02,
            "anger": 0.01,
            "fear": 0.02,
            "neutral": 0.03,
        })
        mock_resp = _mock_response(200, sad_response)

        with patch.object(service, "_ensure_client") as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_resp)
            mock_client.return_value = client

            result = await service.analyze("I feel terrible and hopeless")

            assert result is not None
            assert result.label == "sadness"
            assert result.confidence == 0.92


class TestParseResponse:
    """Tests for the static _parse_response method."""

    def test_standard_response(self):
        data = _make_hf_response({"joy": 0.8, "sadness": 0.2})
        result = HuggingFaceEmotionService._parse_response(data)
        assert result.label == "joy"
        assert result.confidence == 0.8
        assert len(result.scores) == 2

    def test_empty_response(self):
        with pytest.raises(ValueError, match="Empty emotion scores"):
            HuggingFaceEmotionService._parse_response([[]])

    def test_single_emotion(self):
        data = [[{"label": "neutral", "score": 1.0}]]
        result = HuggingFaceEmotionService._parse_response(data)
        assert result.label == "neutral"
        assert result.confidence == 1.0
