"""
HuggingFace Inference API emotion analysis service.

Provides async text emotion detection via the j-hartmann/emotion-english-distilroberta-base
model hosted on HuggingFace. Designed to be fail-open: never blocks journal saves, returns
None on any failure.
"""

import asyncio
from typing import Optional

import httpx
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("huggingface_emotion")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_MODEL_URL = (
    "https://api-inference.huggingface.co/models/"
    "j-hartmann/emotion-english-distilroberta-base"
)
_REQUEST_TIMEOUT_SECONDS = 10.0
_MAX_TEXT_LENGTH = 512


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------
class EmotionAnalysisResult(BaseModel):
    """Structured result of an emotion analysis call.

    Attributes:
        label: The dominant emotion label (e.g. "joy", "anger", "sadness").
        confidence: Confidence score for the dominant emotion (0-1).
        scores: Mapping of every emotion label to its confidence score.
    """

    label: str = Field(..., description="Dominant emotion label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Dominant emotion confidence")
    scores: dict[str, float] = Field(
        default_factory=dict,
        description="All emotion labels mapped to their confidence scores",
    )

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------
class HuggingFaceEmotionService:
    """Async service for emotion detection via the HuggingFace Inference API.

    Design principles:
    * **Fail-open** – any error returns ``None`` so journal saves are never blocked.
    * **Single retry on 503** – the HF API returns 503 while a model is loading;
      we honour the ``estimated_time`` hint and retry once.
    * **Rate-limit awareness** – a 429 response logs a warning and returns ``None``.
    * **Text truncation** – input is truncated to 512 characters before sending.
    """

    def __init__(self) -> None:
        self._api_key: Optional[str] = settings.HUGGINGFACE_API_KEY
        self._client: Optional[httpx.AsyncClient] = None

    # -- internal helpers ---------------------------------------------------

    def _get_headers(self) -> dict[str, str]:
        """Build authorisation headers for the HuggingFace API."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Lazily create (and reuse) a shared ``httpx.AsyncClient``."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(_REQUEST_TIMEOUT_SECONDS),
            )
            logger.debug("Created new httpx.AsyncClient for HuggingFace API")
        return self._client

    @staticmethod
    def _truncate(text: str) -> str:
        """Truncate *text* to ``_MAX_TEXT_LENGTH`` characters."""
        if len(text) > _MAX_TEXT_LENGTH:
            return text[:_MAX_TEXT_LENGTH]
        return text

    @staticmethod
    def _parse_response(data: list) -> EmotionAnalysisResult:
        """Parse the raw HuggingFace API response into an ``EmotionAnalysisResult``.

        The API returns a list of lists:
        ``[[{"label": "joy", "score": 0.98}, ...]]``

        We flatten the inner list, find the top-scoring label, and build the
        result object.
        """
        # The response is [[{label, score}, ...]] – grab the inner list.
        emotion_list: list[dict] = data[0] if data else []

        scores: dict[str, float] = {
            item["label"]: round(float(item["score"]), 6) for item in emotion_list
        }

        if not scores:
            raise ValueError("Empty emotion scores received from HuggingFace API")

        dominant_label = max(scores, key=scores.get)  # type: ignore[arg-type]
        dominant_confidence = scores[dominant_label]

        return EmotionAnalysisResult(
            label=dominant_label,
            confidence=dominant_confidence,
            scores=scores,
        )

    # -- public API ---------------------------------------------------------

    async def analyze(self, text: str) -> Optional[EmotionAnalysisResult]:
        """Analyse *text* for emotions via the HuggingFace Inference API.

        Args:
            text: The input text to classify.

        Returns:
            An ``EmotionAnalysisResult`` on success, or ``None`` when the
            analysis could not be completed (missing API key, rate-limited,
            network error, etc.).
        """

        # --- guard: API key ---------------------------------------------------
        if not self._api_key:
            logger.warning(
                "HUGGINGFACE_API_KEY is not configured – skipping emotion analysis"
            )
            return None

        # --- guard: empty text ------------------------------------------------
        if not text or not text.strip():
            logger.warning("Empty text provided for emotion analysis – skipping")
            return None

        truncated_text = self._truncate(text.strip())
        payload = {"inputs": truncated_text}

        logger.debug(
            "Sending emotion analysis request (text length: %d chars, truncated: %d chars)",
            len(text),
            len(truncated_text),
        )

        try:
            client = await self._ensure_client()
            headers = self._get_headers()

            response = await client.post(_MODEL_URL, json=payload, headers=headers)

            # -- handle model loading (503) with retry -----------------------
            if response.status_code == 503:
                try:
                    body = response.json()
                except Exception:
                    body = {}

                estimated_time = body.get("estimated_time", 5.0)
                # Clamp wait to a reasonable ceiling so we don't hang.
                wait_seconds = min(float(estimated_time), 30.0)

                logger.info(
                    "HuggingFace model is loading – retrying in %.1f seconds",
                    wait_seconds,
                )
                await asyncio.sleep(wait_seconds)

                # --- single retry -------------------------------------------
                response = await client.post(
                    _MODEL_URL, json=payload, headers=headers
                )

                if response.status_code == 503:
                    logger.warning(
                        "HuggingFace model still loading after retry – giving up"
                    )
                    return None

            # -- handle rate limiting (429) -----------------------------------
            if response.status_code == 429:
                logger.warning(
                    "HuggingFace API rate limit hit (429) – skipping emotion analysis"
                )
                return None

            # -- handle other non-success codes -------------------------------
            if response.status_code != 200:
                logger.error(
                    "HuggingFace API returned unexpected status %d: %s",
                    response.status_code,
                    response.text[:500],
                )
                return None

            # -- parse successful response ------------------------------------
            data = response.json()
            result = self._parse_response(data)

            logger.info(
                "Emotion analysis complete – dominant: %s (%.4f)",
                result.label,
                result.confidence,
            )
            return result

        except httpx.TimeoutException:
            logger.error(
                "HuggingFace API request timed out after %.0f seconds",
                _REQUEST_TIMEOUT_SECONDS,
            )
            return None

        except httpx.RequestError as exc:
            logger.error(
                "Network error while calling HuggingFace API: %s", str(exc)
            )
            return None

        except Exception as exc:
            logger.error(
                "Unexpected error during emotion analysis: %s",
                str(exc),
                exc_info=True,
            )
            return None

    # -- lifecycle ----------------------------------------------------------

    async def close(self) -> None:
        """Close the underlying HTTP client gracefully."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.debug("httpx.AsyncClient closed")


# ---------------------------------------------------------------------------
# Global singleton instance
# ---------------------------------------------------------------------------
hf_emotion_service = HuggingFaceEmotionService()
