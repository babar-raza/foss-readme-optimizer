"""Forced-tool-call client family (Wave 8.6, `VER-006` reversal).

Distinct from both `llm/live_client.py` (freeform JSON, forced onto the one
narrow `relationship_explained` schema) and `llm/planner_client.py`
(`tool_choice="auto"`, so the model can always choose not to call the one
tool it's offered) -- this family FORCES the model to call exactly one,
named tool every time (`tool_choice={"type": "function", "function":
{"name": ...}}`), so a verification or repair-selection call can never
silently degrade into a plain-text non-answer. Justified directly by this
project's own live evidence (`plans/investigations/llm-gateway-context-
ceiling-corrected.md`): forced native tool-calling is 5/5 reliable on both
routed models, while freeform-JSON validity alone swings 0.4-0.8 across
sessions on `gpt-oss`.

Same family-grows-by-adding-a-file convention as `llm/live_client.py`/
`llm/fixture_client.py`/`llm/planner_client.py` -- duplicates their bounded-
retry shape (max 2, 1s/2s backoff) rather than sharing it privately.
Callers (`verification/prose_quality.py`, `supervisor/repair.py`) MUST let
`LLMError` propagate on any gateway failure -- never mapped to accept/
reject or a specific repair action, so it flows into the existing
`execution_error`/dispatch-failure machinery unchanged.
"""

import json
import time
from typing import Any, Protocol

import requests
from pydantic import BaseModel

from readme_agent.errors import LLMError
from readme_agent.llm.schema import LLMResponseMeta, Usage
from readme_agent.retry import RetryableOperationError, run_http_with_retry

DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 300
_RETRYABLE_STATUS = {429, 502, 503, 504}


class ForcedToolResult(BaseModel):
    arguments: dict
    meta: LLMResponseMeta


class ForcedToolClient(Protocol):
    def call(self, messages: list[dict], tool_schema: dict) -> ForcedToolResult: ...


class LiveForcedToolClient:
    def __init__(self, base_url: str, api_key: str | None, model: str, timeout: float = 90):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post_once(self, messages: list[dict], tool_schema: dict) -> requests.Response:
        function_name = tool_schema["function"]["name"]
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": [tool_schema],
            "tool_choice": {"type": "function", "function": {"name": function_name}},
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
        }
        return requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )

    def call(self, messages: list[dict], tool_schema: dict) -> ForcedToolResult:
        try:
            resp = run_http_with_retry(
                "llm_call",
                lambda: self._post_once(messages, tool_schema),
                retryable_statuses=_RETRYABLE_STATUS,
                sleep=time.sleep,
            )
        except RetryableOperationError as exc:
            raise LLMError(f"forced tool call failed after retries: {exc}") from exc
        if resp.status_code != 200:
            raise LLMError(f"forced tool call failed: HTTP {resp.status_code}: {resp.text[:500]}")
        return self._parse_response(resp)

    def _parse_response(self, resp: requests.Response) -> ForcedToolResult:
        try:
            body = resp.json()
        except ValueError as exc:
            raise LLMError(f"forced tool call response was not valid JSON: {exc}") from exc

        choices = body.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise LLMError("forced tool call response missing 'choices[0]'")
        message = choices[0].get("message", {})

        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            raise LLMError("forced tool call response contained no tool_calls")
        function = tool_calls[0].get("function", {})
        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError as exc:
            raise LLMError(f"forced tool call arguments were not valid JSON: {exc}") from exc

        raw_usage = body.get("usage") or {}
        usage = (
            Usage(
                prompt_tokens=raw_usage.get("prompt_tokens"),
                completion_tokens=raw_usage.get("completion_tokens"),
            )
            if raw_usage
            else None
        )
        meta = LLMResponseMeta(
            request_id=body.get("id"),
            created=body.get("created"),
            model=body.get("model"),
            usage=usage,
        )
        return ForcedToolResult(arguments=arguments, meta=meta)


class FixtureForcedToolClient:
    """Returns a pre-seeded sequence of results, one per call -- mirrors
    `FixturePlannerClient`'s test-parity role."""

    def __init__(self, results: list[ForcedToolResult]):
        self._results = list(results)
        self._index = 0

    def call(self, messages: list[dict], tool_schema: dict) -> ForcedToolResult:
        if self._index >= len(self._results):
            raise LLMError(
                f"FixtureForcedToolClient exhausted: {len(self._results)} results seeded, "
                f"call {self._index + 1} requested"
            )
        result = self._results[self._index]
        self._index += 1
        return result
