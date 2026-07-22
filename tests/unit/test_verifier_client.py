"""Mirrors `test_planner_client.py`'s pattern for the forced-tool-call
client pair (Wave 8.6, `VER-006` reversal)."""

import json

import pytest
import requests

from readme_agent.errors import LLMError
from readme_agent.llm import verifier_client
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verifier_client import (
    FixtureForcedToolClient,
    ForcedToolResult,
    LiveForcedToolClient,
)

TOOL_SCHEMA = {
    "type": "function",
    "function": {"name": "report_prose_quality_finding", "parameters": {"type": "object"}},
}


class FakeResponse:
    def __init__(self, status_code, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text or (body and json.dumps(body)) or text

    def json(self):
        return self._body


class TestLiveForcedToolClientHappyPath:
    def test_call_forces_the_named_tool_and_returns_its_arguments(self, monkeypatch):
        body = {
            "id": "chatcmpl-1",
            "created": 123,
            "model": "qwen3-next",
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call1",
                                "function": {
                                    "name": "report_prose_quality_finding",
                                    "arguments": json.dumps({"flagged": False, "reason": "fine"}),
                                },
                            }
                        ]
                    }
                }
            ],
        }
        captured = {}

        def fake_post(url, json, headers, timeout):
            captured["payload"] = json
            return FakeResponse(200, body)

        monkeypatch.setattr(verifier_client.requests, "post", fake_post)
        client = LiveForcedToolClient("https://example/v1", "key", "qwen3-next")

        result = client.call([{"role": "user", "content": "go"}], TOOL_SCHEMA)

        assert result.arguments == {"flagged": False, "reason": "fine"}
        assert result.meta.request_id == "chatcmpl-1"
        assert captured["payload"]["tool_choice"] == {
            "type": "function",
            "function": {"name": "report_prose_quality_finding"},
        }

    def test_no_tool_calls_in_response_raises(self, monkeypatch):
        body = {"choices": [{"message": {"content": "I decline to answer", "tool_calls": []}}]}

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(verifier_client.requests, "post", fake_post)
        client = LiveForcedToolClient("https://example/v1", "key", "qwen3-next")

        with pytest.raises(LLMError):
            client.call([], TOOL_SCHEMA)

    def test_malformed_arguments_json_raises(self, monkeypatch):
        body = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call1",
                                "function": {
                                    "name": "report_prose_quality_finding",
                                    "arguments": "{not valid json",
                                },
                            }
                        ]
                    }
                }
            ]
        }

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(verifier_client.requests, "post", fake_post)
        client = LiveForcedToolClient("https://example/v1", "key", "qwen3-next")

        with pytest.raises(LLMError):
            client.call([], TOOL_SCHEMA)


class TestLiveForcedToolClientRetry:
    def test_retries_on_503_then_succeeds(self, monkeypatch):
        calls = {"n": 0}
        body = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call1",
                                "function": {
                                    "name": "report_prose_quality_finding",
                                    "arguments": "{}",
                                },
                            }
                        ]
                    }
                }
            ]
        }

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            if calls["n"] < 2:
                return FakeResponse(503, text="unavailable")
            return FakeResponse(200, body)

        monkeypatch.setattr(verifier_client.requests, "post", fake_post)
        monkeypatch.setattr(verifier_client.time, "sleep", lambda _: None)
        client = LiveForcedToolClient("https://example/v1", "key", "qwen3-next")

        result = client.call([], TOOL_SCHEMA)
        assert calls["n"] == 2
        assert result.arguments == {}

    def test_gives_up_after_max_retries(self, monkeypatch):
        def fake_post(url, json, headers, timeout):
            return FakeResponse(503, text="unavailable")

        monkeypatch.setattr(verifier_client.requests, "post", fake_post)
        monkeypatch.setattr(verifier_client.time, "sleep", lambda _: None)
        client = LiveForcedToolClient("https://example/v1", "key", "qwen3-next")

        with pytest.raises(LLMError):
            client.call([], TOOL_SCHEMA)

    def test_retries_on_connection_error(self, monkeypatch):
        calls = {"n": 0}
        body = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call1",
                                "function": {
                                    "name": "report_prose_quality_finding",
                                    "arguments": "{}",
                                },
                            }
                        ]
                    }
                }
            ]
        }

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            if calls["n"] < 2:
                raise requests.ConnectionError("boom")
            return FakeResponse(200, body)

        monkeypatch.setattr(verifier_client.requests, "post", fake_post)
        monkeypatch.setattr(verifier_client.time, "sleep", lambda _: None)
        client = LiveForcedToolClient("https://example/v1", "key", "qwen3-next")

        result = client.call([], TOOL_SCHEMA)
        assert result.arguments == {}


class TestFixtureForcedToolClient:
    def test_returns_seeded_results_in_order(self):
        results = [
            ForcedToolResult(arguments={"flagged": False, "reason": "a"}, meta=LLMResponseMeta()),
            ForcedToolResult(arguments={"flagged": True, "reason": "b"}, meta=LLMResponseMeta()),
        ]
        client = FixtureForcedToolClient(results)

        assert client.call([], TOOL_SCHEMA).arguments == {"flagged": False, "reason": "a"}
        assert client.call([], TOOL_SCHEMA).arguments == {"flagged": True, "reason": "b"}

    def test_exhausted_fixture_fails_closed(self):
        client = FixtureForcedToolClient(
            [ForcedToolResult(arguments={"flagged": False, "reason": "a"}, meta=LLMResponseMeta())]
        )
        client.call([], TOOL_SCHEMA)
        with pytest.raises(LLMError):
            client.call([], TOOL_SCHEMA)
