"""Embeddings client (Wave 8.6, item I -- `LLM-017`, batch-only, deliberately
never wired into the per-run supervisor planner loop). Same bounded-retry
convention as `llm/live_client.py`, a new sibling file per this project's
own "extensible families grow by adding a file" convention."""

import time
from typing import Any

import requests

from readme_agent.errors import LLMError

_RETRYABLE_STATUS = {429, 502, 503, 504}
_MAX_RETRIES = 2
_BACKOFF_SECONDS = [1, 2]


def get_embedding(
    text: str, model: str, base_url: str, api_key: str | None, timeout: float = 90
) -> list[float]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload: dict[str, Any] = {"model": model, "input": text}

    last_error: str | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = requests.post(
                f"{base_url.rstrip('/')}/embeddings",
                json=payload,
                headers=headers,
                timeout=timeout,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = f"network error: {exc}"
            if attempt < _MAX_RETRIES:
                time.sleep(_BACKOFF_SECONDS[attempt])
                continue
            raise LLMError(f"embedding call failed after retries: {last_error}") from exc

        if resp.status_code in _RETRYABLE_STATUS:
            last_error = f"HTTP {resp.status_code}"
            if attempt < _MAX_RETRIES:
                time.sleep(_BACKOFF_SECONDS[attempt])
                continue
            raise LLMError(f"embedding call failed after retries: {last_error}")

        if resp.status_code != 200:
            raise LLMError(f"embedding call failed: HTTP {resp.status_code}: {resp.text[:500]}")

        try:
            body = resp.json()
        except ValueError as exc:
            raise LLMError(f"embedding response was not valid JSON: {exc}") from exc

        data = body.get("data") or []
        if not data or not isinstance(data[0], dict) or "embedding" not in data[0]:
            raise LLMError("embedding response missing 'data[0].embedding'")
        return list(data[0]["embedding"])

    raise LLMError(f"embedding call failed after retries: {last_error}")  # pragma: no cover
