"""Freeform-structured-analysis client family (Wave 8.6, items G/H --
comparison capabilities and vision-model integration).

Neither `llm/live_client.py` (hardcoded to the one narrow
`LLMBlockResponse` schema) nor `llm/planner_client.py` (tool-calling only)
fit a freeform structured-JSON analysis call with its own, per-capability
response shape -- this is a third sibling file, matching this project's own
established convention ("extensible families grow by adding a file, never
a parallel package"). Duplicates the bounded-retry/fence-unwrap shape
rather than sharing it privately, same as every other client in this
family.

Returns the raw parsed JSON dict, not a fixed pydantic response model --
each capability validates the shape it actually expects itself (mirrors how
`verify_readme_candidate`'s own capability does its own validation rather
than the client doing it), since a single shared response schema across
"presentation-standard compliance" and "visual-asset accuracy" would force
an artificial least-common-denominator shape onto both.

`messages`' `content` may be a plain string (text-only analysis, e.g. item
G) or an OpenAI-style vision content-parts list (`[{"type": "text", ...},
{"type": "image_url", ...}]`, item H) -- `requests.post()` just serializes
whatever is given, so no client-side change is needed for either case."""

import json
import re
import time
from typing import Any

import requests
from pydantic import BaseModel

from readme_agent.errors import LLMError
from readme_agent.llm.schema import LLMResponseMeta, Usage
from readme_agent.retry import RetryableOperationError, run_http_with_retry

DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 1000
_RETRYABLE_STATUS = {429, 502, 503, 504}

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _unwrap_fence(text: str) -> str:
    stripped = text.strip()
    match = _FENCE_RE.match(stripped)
    return match.group(1) if match else stripped


class AnalysisResult(BaseModel):
    parsed: dict
    meta: LLMResponseMeta


class LiveAnalysisClient:
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

    def _post_once(self, messages: list[dict]) -> requests.Response:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
        }
        return requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        try:
            resp = run_http_with_retry(
                "llm_call",
                lambda: self._post_once(messages),
                retryable_statuses=_RETRYABLE_STATUS,
                sleep=time.sleep,
            )
        except RetryableOperationError as exc:
            raise LLMError(f"analysis call failed after retries: {exc}") from exc
        if resp.status_code != 200:
            raise LLMError(f"analysis call failed: HTTP {resp.status_code}: {resp.text[:500]}")
        return self._parse_response(resp)

    def _parse_response(self, resp: requests.Response) -> AnalysisResult:
        try:
            body = resp.json()
        except ValueError as exc:
            raise LLMError(f"analysis response was not valid JSON: {exc}") from exc

        choices = body.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise LLMError("analysis response missing 'choices[0]'")
        content = choices[0].get("message", {}).get("content")
        if content is None:
            raise LLMError("analysis response missing choices[0].message.content")

        json_text = _unwrap_fence(str(content))
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"analysis content was not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise LLMError("analysis content did not parse to a JSON object")

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
        return AnalysisResult(parsed=parsed, meta=meta)


class FixtureAnalysisClient:
    """Returns a pre-seeded sequence of results, one per call -- mirrors
    `FixturePlannerClient`'s test-parity role."""

    def __init__(self, results: list[AnalysisResult]):
        self._results = list(results)
        self._index = 0

    def analyze(self, messages: list[dict]) -> AnalysisResult:
        if self._index >= len(self._results):
            raise LLMError(
                f"FixtureAnalysisClient exhausted: {len(self._results)} results seeded, "
                f"call {self._index + 1} requested"
            )
        result = self._results[self._index]
        self._index += 1
        return result
