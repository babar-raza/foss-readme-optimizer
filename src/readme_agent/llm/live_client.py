"""Live LLM client. Request/response shape adapted from aspose.org's
professionalize_client.py; defaults matched exactly to its llm_registry.yaml
(default_temperature=0.0, default_timeout=90, default_max_tokens=8000).

Unlike the upstream client (single attempt, no retry -- that lives in their
separate router), this adds its own bounded retry: max 2 retries, backoff
1s/2s, only on connection errors/timeouts and HTTP 429/502/503/504. Never
retried: other 4xx (masks bugs) or local JSON-schema validation failures
(resending an identical request rarely fixes a malformed response and risks
silently accepting a second, differently-wrong one).
"""

import json
import re
import time
from typing import Any

import requests
from pydantic import ValidationError

from readme_agent.errors import LLMError
from readme_agent.llm.client import GeneratedResult
from readme_agent.llm.schema import LLMBlockResponse, LLMResponseMeta

DEFAULT_TEMPERATURE = 0.0
DEFAULT_MAX_TOKENS = 8000
_RETRYABLE_STATUS = {429, 502, 503, 504}
_MAX_RETRIES = 2
_BACKOFF_SECONDS = [1, 2]

_FENCE_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


def _unwrap_fence(text: str) -> tuple[str, bool]:
    stripped = text.strip()
    match = _FENCE_RE.match(stripped)
    if match:
        return match.group(1), True
    return stripped, False


class LiveLLMClient:
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

    def _post_once(self, messages: list[dict[str, str]]) -> requests.Response:
        payload: dict[str, Any] = {
            "messages": messages,
            "model": self.model,
            "temperature": DEFAULT_TEMPERATURE,
            "max_tokens": DEFAULT_MAX_TOKENS,
        }
        return requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )

    def generate(self, messages: list[dict[str, str]]) -> GeneratedResult:
        last_error: str | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = self._post_once(messages)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_error = f"network error: {exc}"
                if attempt < _MAX_RETRIES:
                    time.sleep(_BACKOFF_SECONDS[attempt])
                    continue
                raise LLMError(f"LLM call failed after retries: {last_error}") from exc

            if resp.status_code in _RETRYABLE_STATUS:
                last_error = f"HTTP {resp.status_code}"
                if attempt < _MAX_RETRIES:
                    time.sleep(_BACKOFF_SECONDS[attempt])
                    continue
                raise LLMError(f"LLM call failed after retries: {last_error}")

            if resp.status_code != 200:
                # Any other 4xx/5xx: never retried, masks bugs (auth/schema).
                raise LLMError(f"LLM call failed: HTTP {resp.status_code}: {resp.text[:500]}")

            return self._parse_response(resp)

        raise LLMError(f"LLM call failed after retries: {last_error}")  # pragma: no cover

    def _parse_response(self, resp: requests.Response) -> GeneratedResult:
        try:
            body = resp.json()
        except ValueError as exc:
            raise LLMError(f"LLM response was not valid JSON: {exc}") from exc

        choices = body.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise LLMError("LLM response missing 'choices[0]'")
        content = choices[0].get("message", {}).get("content")
        if content is None:
            raise LLMError("LLM response missing choices[0].message.content")

        json_text, was_fenced = _unwrap_fence(str(content))
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM content was not valid JSON: {exc}") from exc

        try:
            block = LLMBlockResponse.model_validate(parsed)
        except ValidationError as exc:
            raise LLMError(f"LLM content did not match the required schema: {exc}") from exc

        meta = LLMResponseMeta(
            request_id=body.get("id"),
            created=body.get("created"),
            model=body.get("model"),
        )
        return GeneratedResult(response=block, meta=meta, mode="live", was_fenced=was_fenced)
