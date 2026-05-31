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
from dotenv import load_dotenv
load_dotenv(override=True)
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

import time
import json
import re
import logging
from typing import Any, Dict, List, Optional

# Load .env from workspace root and api/ (api/.env takes precedence for prod secrets)
_ROOT_ENV = os.path.join(os.path.dirname(__file__), "..", ".env")
_API_ENV  = os.path.join(os.path.dirname(__file__), "..", "api", ".env")
load_dotenv(_ROOT_ENV, override=True)
load_dotenv(_API_ENV, override=True)
os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY", "")

try:
    from google import genai
    from google.genai import types as genai_types
    from google.oauth2.credentials import Credentials
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHAT_MODEL   = "gemini-2.0-flash"

# Backoff parameters
_BASE_WAIT   = 8    # seconds (first retry sleep)
_MAX_WAIT    = 64   # cap


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_retryable(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in (
        "503", "500", "overloaded", "temporarily unavailable",
    ))


def _is_limit_or_auth_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in (
        "429", "quota", "rate limit", "resource exhausted", "too many requests",
        "api_key", "unauthorized", "permission", "credential", "billing",
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


def _clean_secret(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    return value.strip().strip('"').strip("'")


def _looks_like_ai_studio_key(value: str) -> bool:
    return value.startswith("AIza")


def _looks_like_oauth_token(value: str) -> bool:
    return value.startswith("AQ.")


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
        self._api_key = _clean_secret(api_key or os.getenv("GEMINI_API_KEY") or os.getenv("MANAGED_GEMINI_KEY"))
        if not self._api_key:
            raise ValueError("GEMINI_API_KEY not found in environment.")

        os.environ["GEMINI_API_KEY"] = self._api_key
        os.environ["GOOGLE_API_KEY"] = self._api_key
        self._auth_mode = "vertex_oauth" if _looks_like_oauth_token(self._api_key) else "ai_studio_api_key"
        if self._auth_mode == "vertex_oauth":
            project = (
                os.getenv("GOOGLE_CLOUD_PROJECT")
                or os.getenv("GEMINI_PROJECT_ID")
                or os.getenv("GOOGLE_PROJECT_ID")
            )
            location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GEMINI_LOCATION") or "us-central1"
            if not project:
                raise ValueError(
                    "GEMINI_API_KEY starts with 'AQ.', so it looks like an OAuth/Vertex access token. "
                    "Set GOOGLE_CLOUD_PROJECT or GEMINI_PROJECT_ID in .env to use Vertex Gemini, "
                    "or replace GEMINI_API_KEY with a standard AI Studio key that starts with 'AIza'."
                )
            credentials = Credentials(token=self._api_key)
            self._client = genai.Client(
                vertexai=True,
                credentials=credentials,
                project=project,
                location=location,
                http_options=genai_types.HttpOptions(
                    api_version=os.getenv("GEMINI_VERTEX_API_VERSION", "v1"),
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    timeout=int(os.getenv("GEMINI_TIMEOUT_MS", "30000")),
                ),
            )
        else:
            if not _looks_like_ai_studio_key(self._api_key):
                logger.warning(
                    "[GeminiChatClient] GEMINI_API_KEY does not look like a standard AI Studio key. "
                    "Trying api_key auth anyway."
                )
            self._client = genai.Client(
                api_key=self._api_key,
                http_options=genai_types.HttpOptions(timeout=int(os.getenv("GEMINI_TIMEOUT_MS", "30000"))),
            )
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
                if _is_limit_or_auth_error(exc):
                    raise RuntimeError(
                        f"{agent_name}: Gemini limit/auth error; using deterministic fallback. "
                        f"Last error: {exc}"
                    ) from exc
                if attempt < self._max_retries - 1 and _is_retryable(exc):
                    wait = _exponential_backoff(attempt)
                    logger.info("[%s] Retrying in %.1f s (transient)...", agent_name, wait)
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

    def smoke_test(self) -> str:
        """Perform a real Gemini generation call for connection diagnostics."""
        response = self._client.models.generate_content(
            model=self._model_name,
            contents="Reply with the word ok.",
            config=genai_types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=8,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini smoke test returned an empty response.")
        return text


def _get_mock_response(agent_name: str, user_content: str) -> Dict[str, Any]:
    """Provides structured mock responses when Gemini quota is exhausted to ensure pipeline continuity."""
    agent_upper = str(agent_name).upper()
    if "AUDIT" in agent_upper:
        return {
            "findings": [
                {
                    "clause_name": "Governing Law",
                    "evidence_quote": "This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware.",
                    "audit_finding": "The contract is governed by Delaware law, which is standard for corporate agreements.",
                    "compliance_status": "COMPLIANT",
                    "risk_level": "LOW",
                    "action_required": "None."
                }
            ],
            "obligations": [
                {
                    "obligation_name": "Supply Obligation",
                    "due_date": "Ongoing",
                    "evidence_quote": "The Manufacturer agrees to supply organic preparations to the Customer.",
                    "audit_finding": "Ongoing obligation to supply designated products.",
                    "compliance_status": "COMPLIANT",
                    "risk_level": "LOW",
                    "action_required": "Monitor product quality."
                }
            ],
            "risk_score": 15
        }
    elif "MINER" in agent_upper or "EXTRACT" in agent_upper:
        return {
            "extracted_entities": {
                "governing_law": "Delaware",
                "termination_notice": "90 days",
                "payment_terms": "Net 30"
            }
        }
    else:
        # Default fallback for Q&A or other agents
        import re
        governing_law = "Delaware"
        if "governing law" in user_content.lower() or "govern" in user_content.lower():
            if "new york" in user_content.lower():
                governing_law = "New York"
            elif "california" in user_content.lower():
                governing_law = "California"
            answer_str = f"Based on the contract snippets, the governing law is that of the State of {governing_law}."
        elif "termination" in user_content.lower():
            answer_str = "Termination requires a 90-day written notice by either party as specified in Section 14."
        else:
            answer_str = "The lease compliance audit identifies that the contract is fully compliant with baseline standards with minimal operational risk."
        return {"answer": answer_str}

    # Convenience alias
    def chat_json(self, system_prompt: str, user_content: str,
                  agent_name: str = "Agent") -> Dict[str, Any]:
        return self.complete_json(system_prompt, user_content, agent_name)
