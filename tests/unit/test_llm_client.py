import json

import pytest
import requests

from readme_agent.errors import ConfigError, LLMError
from readme_agent.llm import live_client
from readme_agent.llm.fixture_client import FixtureLLMClient
from readme_agent.llm.live_client import LiveLLMClient, _unwrap_fence

VALID_CONTENT = json.dumps(
    {
        "relationship_paragraph": "This is the free FOSS edition; commercial adds more.",
        "talking_points_covered": ["open_source_scope", "commercial_upgrade_path"],
        "claims": {
            "license_name": "MIT",
            "commercial_link_url": "https://products.aspose.com/3d/java/",
        },
    }
)


class FakeResponse:
    def __init__(self, status_code, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text or json.dumps(body) if body else text

    def json(self):
        return self._body


class TestUnwrapFence:
    def test_plain_json_not_touched(self):
        text, fenced = _unwrap_fence('{"a": 1}')
        assert text == '{"a": 1}'
        assert not fenced

    def test_fenced_json_unwrapped_and_flagged(self):
        text, fenced = _unwrap_fence('```json\n{"a": 1}\n```')
        assert text == '{"a": 1}'
        assert fenced


class TestLiveClientHappyPath:
    def test_generate_parses_valid_response(self, monkeypatch):
        body = {
            "id": "chatcmpl-abc123",
            "created": 1784307225,
            "model": "gpt-oss",
            "choices": [{"message": {"content": VALID_CONTENT}}],
        }

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(live_client.requests, "post", fake_post)
        client = LiveLLMClient("https://example/v1", "key", "gpt-oss")

        result = client.generate([{"role": "user", "content": "go"}])

        assert result.mode == "live"
        assert not result.was_fenced
        assert result.response.claims.license_name == "MIT"
        assert result.meta.request_id == "chatcmpl-abc123"
        assert result.meta.model == "gpt-oss"

    def test_generate_unwraps_fenced_response(self, monkeypatch):
        body = {
            "choices": [{"message": {"content": f"```json\n{VALID_CONTENT}\n```"}}],
        }

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(live_client.requests, "post", fake_post)
        client = LiveLLMClient("https://example/v1", "key", "gpt-oss")

        result = client.generate([{"role": "user", "content": "go"}])

        assert result.was_fenced


class TestLiveClientRetry:
    def test_retries_on_503_then_succeeds(self, monkeypatch):
        calls = {"n": 0}
        body = {"choices": [{"message": {"content": VALID_CONTENT}}]}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            if calls["n"] < 2:
                return FakeResponse(503, text="unavailable")
            return FakeResponse(200, body)

        monkeypatch.setattr(live_client.requests, "post", fake_post)
        monkeypatch.setattr(live_client.time, "sleep", lambda _: None)
        client = LiveLLMClient("https://example/v1", "key", "gpt-oss")

        result = client.generate([{"role": "user", "content": "go"}])

        assert calls["n"] == 2
        assert result.mode == "live"

    def test_gives_up_after_max_retries(self, monkeypatch):
        def fake_post(url, json, headers, timeout):
            return FakeResponse(503, text="unavailable")

        monkeypatch.setattr(live_client.requests, "post", fake_post)
        monkeypatch.setattr(live_client.time, "sleep", lambda _: None)
        client = LiveLLMClient("https://example/v1", "key", "gpt-oss")

        with pytest.raises(LLMError):
            client.generate([{"role": "user", "content": "go"}])

    def test_never_retries_on_plain_400(self, monkeypatch):
        calls = {"n": 0}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            return FakeResponse(400, text="bad request")

        monkeypatch.setattr(live_client.requests, "post", fake_post)
        client = LiveLLMClient("https://example/v1", "key", "gpt-oss")

        with pytest.raises(LLMError):
            client.generate([{"role": "user", "content": "go"}])
        assert calls["n"] == 1

    def test_never_retries_on_schema_validation_failure(self, monkeypatch):
        calls = {"n": 0}
        body = {"choices": [{"message": {"content": '{"not_the_right_field": true}'}}]}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            return FakeResponse(200, body)

        monkeypatch.setattr(live_client.requests, "post", fake_post)
        client = LiveLLMClient("https://example/v1", "key", "gpt-oss")

        with pytest.raises(LLMError):
            client.generate([{"role": "user", "content": "go"}])
        assert calls["n"] == 1

    def test_retries_on_connection_error(self, monkeypatch):
        calls = {"n": 0}
        body = {"choices": [{"message": {"content": VALID_CONTENT}}]}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            if calls["n"] < 2:
                raise requests.ConnectionError("boom")
            return FakeResponse(200, body)

        monkeypatch.setattr(live_client.requests, "post", fake_post)
        monkeypatch.setattr(live_client.time, "sleep", lambda _: None)
        client = LiveLLMClient("https://example/v1", "key", "gpt-oss")

        result = client.generate([{"role": "user", "content": "go"}])
        assert result.mode == "live"


class TestFixtureClient:
    def test_loads_valid_fixture(self, tmp_path):
        fixture = tmp_path / "response.json"
        fixture.write_text(VALID_CONTENT, encoding="utf-8")

        result = FixtureLLMClient(fixture).generate([])

        assert result.mode == "fixture"
        assert result.response.claims.license_name == "MIT"

    def test_malformed_fixture_fails_closed(self, tmp_path):
        fixture = tmp_path / "response.json"
        fixture.write_text('{"not_the_right_field": true}', encoding="utf-8")

        with pytest.raises(ConfigError):
            FixtureLLMClient(fixture).generate([])

    def test_missing_fixture_fails_closed(self, tmp_path):
        with pytest.raises(ConfigError):
            FixtureLLMClient(tmp_path / "nope.json").generate([])
