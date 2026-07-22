"""Mirrors `test_verifier_client.py`'s pattern for the freeform-structured-
analysis client pair (Wave 8.6, items G/H)."""

import json

import pytest
import requests

from readme_agent.errors import LLMError
from readme_agent.llm import analysis_client
from readme_agent.llm.analysis_client import (
    AnalysisResult,
    FixtureAnalysisClient,
    LiveAnalysisClient,
)


class FakeResponse:
    def __init__(self, status_code, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text or (body and json.dumps(body)) or text

    def json(self):
        return self._body


class TestLiveAnalysisClientHappyPath:
    def test_analyze_parses_plain_json_content(self, monkeypatch):
        content = json.dumps({"criteria_results": [], "overall_summary": "ok"})
        body = {
            "id": "chatcmpl-1",
            "created": 123,
            "model": "qwen3-next",
            "choices": [{"message": {"content": content}}],
        }

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(analysis_client.requests, "post", fake_post)
        client = LiveAnalysisClient("https://example/v1", "key", "qwen3-next")

        result = client.analyze([{"role": "user", "content": "go"}])

        assert result.parsed == {"criteria_results": [], "overall_summary": "ok"}
        assert result.meta.request_id == "chatcmpl-1"

    def test_analyze_unwraps_a_fenced_code_block(self, monkeypatch):
        fenced = '```json\n{"criteria_results": [], "overall_summary": "ok"}\n```'
        body = {"choices": [{"message": {"content": fenced}}]}

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(analysis_client.requests, "post", fake_post)
        client = LiveAnalysisClient("https://example/v1", "key", "qwen3-next")

        result = client.analyze([])
        assert result.parsed == {"criteria_results": [], "overall_summary": "ok"}

    def test_non_object_json_raises(self, monkeypatch):
        body = {"choices": [{"message": {"content": "[1, 2, 3]"}}]}

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(analysis_client.requests, "post", fake_post)
        client = LiveAnalysisClient("https://example/v1", "key", "qwen3-next")

        with pytest.raises(LLMError):
            client.analyze([])

    def test_malformed_json_raises(self, monkeypatch):
        body = {"choices": [{"message": {"content": "{not valid json"}}]}

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(analysis_client.requests, "post", fake_post)
        client = LiveAnalysisClient("https://example/v1", "key", "qwen3-next")

        with pytest.raises(LLMError):
            client.analyze([])


class TestLiveAnalysisClientRetry:
    def test_retries_on_503_then_succeeds(self, monkeypatch):
        calls = {"n": 0}
        body = {"choices": [{"message": {"content": "{}"}}]}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            if calls["n"] < 2:
                return FakeResponse(503, text="unavailable")
            return FakeResponse(200, body)

        monkeypatch.setattr(analysis_client.requests, "post", fake_post)
        monkeypatch.setattr(analysis_client.time, "sleep", lambda _: None)
        client = LiveAnalysisClient("https://example/v1", "key", "qwen3-next")

        result = client.analyze([])
        assert calls["n"] == 2
        assert result.parsed == {}

    def test_gives_up_after_max_retries(self, monkeypatch):
        def fake_post(url, json, headers, timeout):
            return FakeResponse(503, text="unavailable")

        monkeypatch.setattr(analysis_client.requests, "post", fake_post)
        monkeypatch.setattr(analysis_client.time, "sleep", lambda _: None)
        client = LiveAnalysisClient("https://example/v1", "key", "qwen3-next")

        with pytest.raises(LLMError):
            client.analyze([])

    def test_retries_on_connection_error(self, monkeypatch):
        calls = {"n": 0}
        body = {"choices": [{"message": {"content": "{}"}}]}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            if calls["n"] < 2:
                raise requests.ConnectionError("boom")
            return FakeResponse(200, body)

        monkeypatch.setattr(analysis_client.requests, "post", fake_post)
        monkeypatch.setattr(analysis_client.time, "sleep", lambda _: None)
        client = LiveAnalysisClient("https://example/v1", "key", "qwen3-next")

        result = client.analyze([])
        assert result.parsed == {}


class TestFixtureAnalysisClient:
    def test_returns_seeded_results_in_order(self):
        from readme_agent.llm.schema import LLMResponseMeta

        results = [
            AnalysisResult(parsed={"a": 1}, meta=LLMResponseMeta()),
            AnalysisResult(parsed={"b": 2}, meta=LLMResponseMeta()),
        ]
        client = FixtureAnalysisClient(results)

        assert client.analyze([]).parsed == {"a": 1}
        assert client.analyze([]).parsed == {"b": 2}

    def test_exhausted_fixture_fails_closed(self):
        from readme_agent.llm.schema import LLMResponseMeta

        client = FixtureAnalysisClient([AnalysisResult(parsed={"a": 1}, meta=LLMResponseMeta())])
        client.analyze([])
        with pytest.raises(LLMError):
            client.analyze([])
