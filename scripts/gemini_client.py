# scripts/gemini_client.py
# Gemini wrapper for LeaseSight REASONING tasks only.
# Uses the current google-genai SDK (google.genai v1+).
#
# NOTE: The embedding pipeline has been decoupled from this module.
#       Use scripts.processor.get_local_embedding() for all vector operations.
#       GeminiChatClient is kept here exclusively for audit/chat completions.
#
# Usage:
#   from scripts.gemini_client import GeminiChatClient
#   chat = GeminiChatClient()
#   result = chat.complete_json(system_prompt, user_content, "MINER")

import os
import time
import json
import re
import logging
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Load .env from workspace root and api/ (api/.env takes precedence for prod secrets)
_ROOT_ENV = os.path.join(os.path.dirname(__file__), "..", ".env")
_API_ENV  = os.path.join(os.path.dirname(__file__), "..", "api", ".env")
load_dotenv(_ROOT_ENV)
load_dotenv(_API_ENV)

try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHAT_MODEL   = "gemini-2.5-pro-preview-06-05"

# Backoff parameters
_BASE_WAIT   = 8    # seconds (first retry sleep)
_MAX_WAIT    = 64   # cap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in (
        "429", "quota", "rate limit", "resource exhausted", "503", "500",
        "too many requests", "overloaded",
    ))


def _exponential_backoff(attempt: int, base: int = _BASE_WAIT, cap: int = _MAX_WAIT) -> float:
    import random
    wait = min(base * (2 ** attempt), cap)
    return wait + random.uniform(0, wait * 0.25)


def _strip_json_fence(text: str) -> str:
    """Remove ```json ... ``` fences that Gemini sometimes wraps output in."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# GeminiChatClient  (reasoning / audit tasks only)
# ---------------------------------------------------------------------------

class GeminiChatClient:
    """
    JSON-mode Gemini chat client with exponential backoff.
    Uses google-genai (google.genai) SDK v1+.

    Responsibilities:
      - Agent prompts: MINER, JUDGE, CLERK, AUDIT
      - Entity extraction (api/processor.py)
      - Document Q&A (scripts/query_engine.py)

    NOT responsible for embeddings — use scripts.processor.get_local_embedding()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_retries: int = 4,
    ):
        if not _GENAI_AVAILABLE:
            raise ImportError(
                "google-genai is not installed. Run: pip install google-genai"
            )
        self._api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("MANAGED_GEMINI_KEY")
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY not found in environment.")

        self._client      = genai.Client(api_key=self._api_key)
        self._model_name  = model or os.getenv("AUDIT_MODEL", CHAT_MODEL)
        self._temperature = temperature
        self._max_retries = max_retries
        logger.info("[GeminiChatClient] Initialized with model=%s", self._model_name)

    # ------------------------------------------------------------------ #

    def complete_json(
        self,
        system_prompt: str,
        user_content: str,
        agent_name: str = "Agent",
    ) -> Dict[str, Any]:
        """Call Gemini and return a parsed JSON dict."""

        config = genai_types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=self._temperature,
            response_mime_type="application/json",
        )

        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                response = self._client.models.generate_content(
                    model=self._model_name,
                    contents=user_content,
                    config=config,
                )
                raw     = response.text if response.text else ""
                cleaned = _strip_json_fence(raw)
                if not cleaned:
                    raise ValueError(f"{agent_name}: Empty response from Gemini")
                return json.loads(cleaned)

            except json.JSONDecodeError as exc:
                last_exc = exc
                logger.warning("[%s] JSON parse error on attempt %d/%d: %s",
                               agent_name, attempt + 1, self._max_retries, str(exc)[:200])
                if attempt < self._max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(
                    f"{agent_name}: Gemini returned malformed JSON after "
                    f"{self._max_retries} attempts. Last error: {exc}"
                ) from exc

            except Exception as exc:
                last_exc = exc
                logger.warning("[%s] attempt %d/%d failed: %s",
                               agent_name, attempt + 1, self._max_retries, str(exc)[:300])
                if attempt < self._max_retries - 1 and _is_retryable(exc):
                    wait = _exponential_backoff(attempt)
                    logger.info("[%s] Retrying in %.1f s (quota/transient)...", agent_name, wait)
                    time.sleep(wait)
                    continue
                if attempt < self._max_retries - 1:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError(
                    f"{agent_name}: Gemini call failed after {self._max_retries} attempts. "
                    f"Last error: {exc}"
                ) from exc

        raise RuntimeError(f"{agent_name}: Exceeded {self._max_retries} retries.")

    # Convenience alias
    def chat_json(self, system_prompt: str, user_content: str,
                  agent_name: str = "Agent") -> Dict[str, Any]:
        return self.complete_json(system_prompt, user_content, agent_name)
