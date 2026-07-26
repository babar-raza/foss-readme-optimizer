"""Embeddings client (Wave 8.6, item I -- `LLM-017`, batch-only, deliberately
never wired into the per-run supervisor planner loop). Same bounded-retry
convention as `llm/live_client.py`, a new sibling file per this project's
own "extensible families grow by adding a file" convention."""

import time
from typing import Any

from readme_agent.errors import LLMError
from readme_agent.llm.call_transport import ProviderCallSession
from readme_agent.retry import RetryableOperationError, run_http_with_retry

_RETRYABLE_STATUS = {429, 502, 503, 504}


def get_embedding(
    text: str, model: str, base_url: str, api_key: str | None, timeout: float = 90
) -> list[float]:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload: dict[str, Any] = {"model": model, "input": text}
    session = ProviderCallSession(
        job="embeddings",
        prompt_id="embeddings",
        prompt_sha256=None,
        provider="configured_gateway",
        model=model,
        prompt_required=False,
    )

    try:
        resp = run_http_with_retry(
            "llm_call",
            lambda: session.post(
                f"{base_url.rstrip('/')}/embeddings",
                payload=payload,
                headers=headers,
                timeout=timeout,
            ),
            retryable_statuses=_RETRYABLE_STATUS,
            sleep=time.sleep,
        )
    except RetryableOperationError as exc:
        raise LLMError(f"embedding call failed after retries: {exc}") from exc
    if resp.status_code != 200:
        raise LLMError(f"embedding call failed: HTTP {resp.status_code}: {resp.text[:500]}")

    try:
        body = resp.json()
        data = body.get("data") or []
        if not data or not isinstance(data[0], dict) or "embedding" not in data[0]:
            raise LLMError("embedding response missing 'data[0].embedding'")
    except ValueError as exc:
        session.finalize(resp, "response_invalid")
        raise LLMError(f"embedding response was not valid JSON: {exc}") from exc
    except LLMError:
        session.finalize(resp, "response_invalid")
        raise
    session.finalize(resp, "success")
    return list(data[0]["embedding"])
