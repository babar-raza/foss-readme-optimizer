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
from readme_agent.llm.call_ledger import known_prompt_hash, record_non_provider_call
from readme_agent.llm.call_transport import ProviderCallSession
from readme_agent.llm.schema import LLMResponseMeta, Usage
from readme_agent.retry import RetryableOperationError, run_http_with_retry

DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 300
_RETRYABLE_STATUS = {429, 502, 503, 504}
_MAX_RESPONSE_ATTEMPTS = 2
_RETRYABLE_RESPONSE_ERRORS = (
    "forced tool call response was not valid JSON",
    "forced tool call response missing 'choices[0]'",
    "forced tool call response contained no tool_calls",
    "forced tool call response must contain exactly one tool call",
    "forced tool call response used unexpected function",
    "forced tool call arguments were not valid JSON",
)


class ForcedToolResult(BaseModel):
    arguments: dict
    meta: LLMResponseMeta


class ForcedToolClient(Protocol):
    def call(self, messages: list[dict], tool_schema: dict) -> ForcedToolResult: ...


class LiveForcedToolClient:
    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout: float = 90,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        *,
        job: str = "forced_tool_call",
        prompt_id: str | None = None,
    ):
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.job = job
        self.prompt_id = prompt_id or job

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post_once(
        self,
        messages: list[dict],
        tool_schema: dict,
        session: ProviderCallSession,
    ) -> requests.Response:
        function_name = tool_schema["function"]["name"]
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": [tool_schema],
            "tool_choice": {"type": "function", "function": {"name": function_name}},
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": self.max_tokens,
        }
        return session.post(
            f"{self.base_url}/chat/completions",
            payload=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )

    def call(self, messages: list[dict], tool_schema: dict) -> ForcedToolResult:
        function_name = tool_schema["function"]["name"]
        last_error: LLMError | None = None
        session = ProviderCallSession(
            job=self.job,
            prompt_id=self.prompt_id,
            prompt_sha256=known_prompt_hash(self.prompt_id),
            provider="configured_gateway",
            model=self.model,
        )
        for attempt in range(_MAX_RESPONSE_ATTEMPTS):
            response: requests.Response | None = None
            try:
                response = self._request(messages, tool_schema, session)
                result = self._parse_response(response, expected_function_name=function_name)
            except LLMError as exc:
                if response is not None:
                    session.finalize(response, "response_invalid")
                if not str(exc).startswith(_RETRYABLE_RESPONSE_ERRORS):
                    raise
                last_error = exc
                if attempt + 1 == _MAX_RESPONSE_ATTEMPTS:
                    break
            else:
                session.finalize(response, "success")
                return result
        assert last_error is not None
        raise LLMError(
            "forced tool call returned an invalid structured response "
            f"after {_MAX_RESPONSE_ATTEMPTS} attempts: {last_error}"
        ) from last_error

    def _request(
        self,
        messages: list[dict],
        tool_schema: dict,
        session: ProviderCallSession,
    ) -> requests.Response:
        try:
            resp = run_http_with_retry(
                "llm_call",
                lambda: self._post_once(messages, tool_schema, session),
                retryable_statuses=_RETRYABLE_STATUS,
                sleep=time.sleep,
            )
        except RetryableOperationError as exc:
            raise LLMError(f"forced tool call failed after retries: {exc}") from exc
        if resp.status_code != 200:
            raise LLMError(f"forced tool call failed: HTTP {resp.status_code}: {resp.text[:500]}")
        return resp

    def _parse_response(
        self,
        resp: requests.Response,
        *,
        expected_function_name: str,
    ) -> ForcedToolResult:
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
        if len(tool_calls) != 1:
            raise LLMError("forced tool call response must contain exactly one tool call")
        function = tool_calls[0].get("function", {})
        if function.get("name") != expected_function_name:
            raise LLMError(
                "forced tool call response used unexpected function "
                f"{function.get('name')!r}; expected {expected_function_name!r}"
            )
        try:
            arguments = json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError as exc:
            finish_reason = choices[0].get("finish_reason")
            completion_tokens = (body.get("usage") or {}).get("completion_tokens")
            raise LLMError(
                "forced tool call arguments were not valid JSON: "
                f"{exc}; finish_reason={finish_reason!r}; "
                f"completion_tokens={completion_tokens!r}"
            ) from exc

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

    def __init__(
        self,
        results: list[ForcedToolResult],
        *,
        job: str = "forced_tool_call",
        prompt_id: str | None = None,
    ):
        self._results = list(results)
        self._index = 0
        self.job = job
        self.prompt_id = prompt_id or job

    def call(self, messages: list[dict], tool_schema: dict) -> ForcedToolResult:
        if self._index >= len(self._results):
            raise LLMError(
                f"FixtureForcedToolClient exhausted: {len(self._results)} results seeded, "
                f"call {self._index + 1} requested"
            )
        result = self._results[self._index]
        self._index += 1
        record_non_provider_call(
            job=self.job,
            prompt_id=self.prompt_id,
            prompt_sha256=known_prompt_hash(self.prompt_id),
            model=result.meta.model or "fixture",
            disposition="fixture",
            request={"messages": messages, "tool_schema": tool_schema},
        )
        return result
