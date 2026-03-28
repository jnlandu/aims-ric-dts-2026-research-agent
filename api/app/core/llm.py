"""Shared LLM client — single place for Groq API calls.

Eliminates the duplicated _get_client / _chat / _extract_json across agents.
"""

from __future__ import annotations

import json
import logging
import re
import time

from groq import Groq

from app.core import config

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF = (1, 3, 10)  # seconds to wait between retries


def get_client() -> Groq:
    """Return a configured Groq client."""
    return Groq(api_key=config.GROQ_API_KEY)


def chat(client: Groq, system: str, user: str) -> str:
    """Send a chat completion request with exponential back-off on transient errors."""
    logger.debug("LLM request | model=%s | system=%s...", config.GROQ_MODEL, system[:80])
    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=config.GROQ_MODEL,
                temperature=config.TEMPERATURE,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            content = resp.choices[0].message.content or ""
            logger.debug("LLM response | length=%d", len(content))
            return content
        except Exception as exc:
            last_exc = exc
            # Only retry on transient / rate-limit errors
            status = getattr(exc, "status_code", None) or getattr(exc, "status", 0)
            if status in (429, 500, 502, 503, 504) and attempt < _MAX_RETRIES - 1:
                wait = _RETRY_BACKOFF[attempt]
                logger.warning("LLM call failed (attempt %d/%d, status %s), retrying in %ds…",
                               attempt + 1, _MAX_RETRIES, status, wait)
                time.sleep(wait)
            else:
                raise
    raise last_exc  # type: ignore[misc]


def extract_json(text: str) -> str:
    """Pull a JSON block out of an LLM response (fenced or raw)."""
    m = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def chat_json(client: Groq, system: str, user: str) -> list | dict:
    """Send a chat request and parse the response as JSON.

    Returns an empty list on failure.
    """
    raw = chat(client, system, user)
    try:
        return json.loads(extract_json(raw))
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM JSON response: %s...", raw[:120])
        return []
