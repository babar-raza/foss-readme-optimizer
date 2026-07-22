"""Mirrors `test_llm_client.py`'s pattern for `llm/embeddings_client.py`
(Wave 8.6, item I)."""

import pytest
import requests

from readme_agent.errors import LLMError
from readme_agent.llm import embeddings_client
from readme_agent.llm.embeddings_client import get_embedding


class FakeResponse:
    def __init__(self, status_code, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text

    def json(self):
        return self._body


class TestGetEmbeddingHappyPath:
    def test_returns_the_embedding_vector(self, monkeypatch):
        body = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(embeddings_client.requests, "post", fake_post)

        result = get_embedding("some text", "qwen3-embedding-8b", "https://example/v1", "key")

        assert result == [0.1, 0.2, 0.3]

    def test_missing_data_raises(self, monkeypatch):
        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, {"data": []})

        monkeypatch.setattr(embeddings_client.requests, "post", fake_post)

        with pytest.raises(LLMError):
            get_embedding("some text", "qwen3-embedding-8b", "https://example/v1", "key")


class TestGetEmbeddingRetry:
    def test_retries_on_503_then_succeeds(self, monkeypatch):
        calls = {"n": 0}
        body = {"data": [{"embedding": [0.1]}]}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            if calls["n"] < 2:
                return FakeResponse(503, text="unavailable")
            return FakeResponse(200, body)

        monkeypatch.setattr(embeddings_client.requests, "post", fake_post)
        monkeypatch.setattr(embeddings_client.time, "sleep", lambda _: None)

        result = get_embedding("text", "model", "https://example/v1", "key")
        assert calls["n"] == 2
        assert result == [0.1]

    def test_gives_up_after_max_retries(self, monkeypatch):
        def fake_post(url, json, headers, timeout):
            return FakeResponse(503, text="unavailable")

        monkeypatch.setattr(embeddings_client.requests, "post", fake_post)
        monkeypatch.setattr(embeddings_client.time, "sleep", lambda _: None)

        with pytest.raises(LLMError):
            get_embedding("text", "model", "https://example/v1", "key")

    def test_retries_on_connection_error(self, monkeypatch):
        calls = {"n": 0}
        body = {"data": [{"embedding": [0.1]}]}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            if calls["n"] < 2:
                raise requests.ConnectionError("boom")
            return FakeResponse(200, body)

        monkeypatch.setattr(embeddings_client.requests, "post", fake_post)
        monkeypatch.setattr(embeddings_client.time, "sleep", lambda _: None)

        result = get_embedding("text", "model", "https://example/v1", "key")
        assert result == [0.1]

    def test_never_retries_on_plain_400(self, monkeypatch):
        calls = {"n": 0}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            return FakeResponse(400, text="bad request")

        monkeypatch.setattr(embeddings_client.requests, "post", fake_post)

        with pytest.raises(LLMError):
            get_embedding("text", "model", "https://example/v1", "key")
        assert calls["n"] == 1
