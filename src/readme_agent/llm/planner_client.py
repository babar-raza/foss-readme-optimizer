"""Planner client -- promotes Wave 1 spike's proven `chat_raw()` logic
(`plans/investigations/tools/prove_agentic_loop.py`) into reusable, tested
production code, the same framing `capabilities/dispatcher.py`'s own
docstring already uses for its own promotion from the same spike.

Cannot reuse `llm/client.py`'s `LLMClient` as-is: `LiveLLMClient._post_once()`
hardcodes a payload with no `tools`/`tool_choice`, and `generate()` forces
every response through the strict `LLMBlockResponse` schema built for the one
narrow `relationship_explained` job -- a tool-call response has no `content`
field to validate against it. Same family as `llm/live_client.py`/
`llm/fixture_client.py` (this project's convention: extensible families grow
by adding a file, never a parallel package), same Live/Fixture test-parity
pattern, `llm/schema.py::LLMResponseMeta` reused verbatim (already generic).
"""

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
DEFAULT_MAX_TOKENS = 300  # one capability per turn (decision #27/L7) -- a short response
_RETRYABLE_STATUS = {429, 502, 503, 504}


class PlannerTurn(BaseModel):
    """One planning turn's result. Exactly one of `tool_call`/`content` is
    meaningful: a tool call feeds `dispatch_tool_call()`/`dispatch_gated_effect()`
    directly (OpenAI tool-call shape); `content` is a plain-text turn (e.g. a
    stop/converge rationale) when the model doesn't call a tool."""

    tool_call: dict | None = None
    content: str | None = None
    meta: LLMResponseMeta


class PlannerClient(Protocol):
    def plan(self, messages: list[dict], tools: list[dict]) -> PlannerTurn: ...


class LivePlannerClient:
    """Duplicates `LiveLLMClient`'s bounded-retry shape (max 2, 1s/2s
    backoff, connection errors/timeouts/429/5xx) rather than sharing it --
    that logic is private to `LiveLLMClient`. Flagged here rather than
    silently repeated uncredited."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None,
        model: str,
        timeout: float = 90,
        *,
        job: str = "supervisor_planning",
        prompt_id: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.job = job
        if prompt_id is None:
            from readme_agent.llm.prompt_registry import prompt_id_for_route

            prompt_id = prompt_id_for_route(job)
        self.prompt_id = prompt_id

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post_once(
        self,
        messages: list[dict],
        tools: list[dict],
        session: ProviderCallSession,
    ) -> requests.Response:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
        }
        return session.post(
            f"{self.base_url}/chat/completions",
            payload=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )

    def plan(self, messages: list[dict], tools: list[dict]) -> PlannerTurn:
        session = ProviderCallSession(
            job=self.job,
            prompt_id=self.prompt_id,
            prompt_sha256=known_prompt_hash(self.prompt_id),
            provider="configured_gateway",
            model=self.model,
        )
        try:
            resp = run_http_with_retry(
                "llm_call",
                lambda: self._post_once(messages, tools, session),
                retryable_statuses=_RETRYABLE_STATUS,
                sleep=time.sleep,
            )
        except RetryableOperationError as exc:
            raise LLMError(f"planner call failed after retries: {exc}") from exc
        if resp.status_code != 200:
            raise LLMError(f"planner call failed: HTTP {resp.status_code}: {resp.text[:500]}")
        try:
            result = self._parse_response(resp)
        except LLMError:
            session.finalize(resp, "response_invalid")
            raise
        session.finalize(resp, "success")
        return result

    def _parse_response(self, resp: requests.Response) -> PlannerTurn:
        try:
            body = resp.json()
        except ValueError as exc:
            raise LLMError(f"planner response was not valid JSON: {exc}") from exc

        choices = body.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise LLMError("planner response missing 'choices[0]'")
        message = choices[0].get("message", {})

        tool_calls = message.get("tool_calls") or []
        tool_call = tool_calls[0] if tool_calls else None  # one capability per turn, per L7

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
        return PlannerTurn(tool_call=tool_call, content=message.get("content"), meta=meta)


class FixturePlannerClient:
    """Returns a pre-seeded sequence of turns, one per call -- mirrors
    `FixtureLLMClient`'s test-parity role, but a planner needs a *sequence*
    of responses (one per round), not one canned response."""

    def __init__(
        self,
        turns: list[PlannerTurn],
        *,
        job: str = "supervisor_planning",
        prompt_id: str | None = None,
    ):
        self._turns = list(turns)
        self._index = 0
        self.job = job
        if prompt_id is None:
            from readme_agent.llm.prompt_registry import prompt_id_for_route

            prompt_id = prompt_id_for_route(job)
        self.prompt_id = prompt_id

    def plan(self, messages: list[dict], tools: list[dict]) -> PlannerTurn:
        if self._index >= len(self._turns):
            raise LLMError(
                f"FixturePlannerClient exhausted: {len(self._turns)} turns seeded, "
                f"call {self._index + 1} requested"
            )
        turn = self._turns[self._index]
        self._index += 1
        record_non_provider_call(
            job=self.job,
            prompt_id=self.prompt_id,
            prompt_sha256=known_prompt_hash(self.prompt_id),
            model=turn.meta.model or "fixture",
            disposition="fixture",
            request={"messages": messages, "tools": tools},
        )
        return turn
