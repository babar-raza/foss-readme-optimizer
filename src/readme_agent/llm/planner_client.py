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
from readme_agent.llm.schema import LLMResponseMeta, Usage

DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 300  # one capability per turn (decision #27/L7) -- a short response
_RETRYABLE_STATUS = {429, 502, 503, 504}
_MAX_RETRIES = 2
_BACKOFF_SECONDS = [1, 2]


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

    def _post_once(self, messages: list[dict], tools: list[dict]) -> requests.Response:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
        }
        return requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )

    def plan(self, messages: list[dict], tools: list[dict]) -> PlannerTurn:
        last_error: str | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = self._post_once(messages, tools)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = f"network error: {exc}"
                if attempt < _MAX_RETRIES:
                    time.sleep(_BACKOFF_SECONDS[attempt])
                    continue
                raise LLMError(f"planner call failed after retries: {last_error}") from exc

            if resp.status_code in _RETRYABLE_STATUS:
                last_error = f"HTTP {resp.status_code}"
                if attempt < _MAX_RETRIES:
                    time.sleep(_BACKOFF_SECONDS[attempt])
                    continue
                raise LLMError(f"planner call failed after retries: {last_error}")

            if resp.status_code != 200:
                raise LLMError(f"planner call failed: HTTP {resp.status_code}: {resp.text[:500]}")

            return self._parse_response(resp)

        raise LLMError(f"planner call failed after retries: {last_error}")  # pragma: no cover

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

    def __init__(self, turns: list[PlannerTurn]):
        self._turns = list(turns)
        self._index = 0

    def plan(self, messages: list[dict], tools: list[dict]) -> PlannerTurn:
        if self._index >= len(self._turns):
            raise LLMError(
                f"FixturePlannerClient exhausted: {len(self._turns)} turns seeded, "
                f"call {self._index + 1} requested"
            )
        turn = self._turns[self._index]
        self._index += 1
        return turn
