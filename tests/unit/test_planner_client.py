"""Mirrors `test_llm_client.py`'s pattern for the planner's Live/Fixture
client pair."""

import pytest
import requests

from readme_agent.errors import LLMError
from readme_agent.llm import planner_client
from readme_agent.llm.planner_client import FixturePlannerClient, LivePlannerClient, PlannerTurn
from readme_agent.llm.schema import LLMResponseMeta

TOOL_CALL = {"id": "call1", "function": {"name": "inspect_repository", "arguments": "{}"}}


class FakeResponse:
    def __init__(self, status_code, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text or (body and __import__("json").dumps(body)) or text

    def json(self):
        return self._body


class TestLivePlannerClientHappyPath:
    def test_plan_returns_the_tool_call(self, monkeypatch):
        body = {
            "id": "chatcmpl-1",
            "created": 123,
            "model": "qwen3-next",
            "choices": [{"message": {"tool_calls": [TOOL_CALL], "content": None}}],
        }

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(planner_client.requests, "post", fake_post)
        client = LivePlannerClient("https://example/v1", "key", "qwen3-next")

        turn = client.plan([{"role": "user", "content": "go"}], [])

        assert turn.tool_call == TOOL_CALL
        assert turn.content is None
        assert turn.meta.request_id == "chatcmpl-1"

    def test_plan_returns_content_when_no_tool_call(self, monkeypatch):
        body = {"choices": [{"message": {"content": "Nothing more to do.", "tool_calls": []}}]}

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(planner_client.requests, "post", fake_post)
        client = LivePlannerClient("https://example/v1", "key", "qwen3-next")

        turn = client.plan([{"role": "user", "content": "go"}], [])

        assert turn.tool_call is None
        assert turn.content == "Nothing more to do."

    def test_only_first_tool_call_kept(self, monkeypatch):
        """One capability per planning turn (decision #27/L7) -- a second
        tool call in the same response, if the gateway ever returned one,
        is not consumed."""
        second_call = {"id": "call2", "function": {"name": "detect_readme_gaps", "arguments": "{}"}}
        body = {"choices": [{"message": {"tool_calls": [TOOL_CALL, second_call]}}]}

        def fake_post(url, json, headers, timeout):
            return FakeResponse(200, body)

        monkeypatch.setattr(planner_client.requests, "post", fake_post)
        client = LivePlannerClient("https://example/v1", "key", "qwen3-next")

        turn = client.plan([], [])
        assert turn.tool_call == TOOL_CALL


class TestLivePlannerClientRetry:
    def test_retries_on_503_then_succeeds(self, monkeypatch):
        calls = {"n": 0}
        body = {"choices": [{"message": {"tool_calls": [TOOL_CALL]}}]}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            if calls["n"] < 2:
                return FakeResponse(503, text="unavailable")
            return FakeResponse(200, body)

        monkeypatch.setattr(planner_client.requests, "post", fake_post)
        monkeypatch.setattr(planner_client.time, "sleep", lambda _: None)
        client = LivePlannerClient("https://example/v1", "key", "qwen3-next")

        turn = client.plan([], [])
        assert calls["n"] == 2
        assert turn.tool_call == TOOL_CALL

    def test_gives_up_after_max_retries(self, monkeypatch):
        def fake_post(url, json, headers, timeout):
            return FakeResponse(503, text="unavailable")

        monkeypatch.setattr(planner_client.requests, "post", fake_post)
        monkeypatch.setattr(planner_client.time, "sleep", lambda _: None)
        client = LivePlannerClient("https://example/v1", "key", "qwen3-next")

        with pytest.raises(LLMError):
            client.plan([], [])

    def test_never_retries_on_plain_400(self, monkeypatch):
        calls = {"n": 0}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            return FakeResponse(400, text="bad request")

        monkeypatch.setattr(planner_client.requests, "post", fake_post)
        client = LivePlannerClient("https://example/v1", "key", "qwen3-next")

        with pytest.raises(LLMError):
            client.plan([], [])
        assert calls["n"] == 1

    def test_retries_on_connection_error(self, monkeypatch):
        calls = {"n": 0}
        body = {"choices": [{"message": {"tool_calls": [TOOL_CALL]}}]}

        def fake_post(url, json, headers, timeout):
            calls["n"] += 1
            if calls["n"] < 2:
                raise requests.ConnectionError("boom")
            return FakeResponse(200, body)

        monkeypatch.setattr(planner_client.requests, "post", fake_post)
        monkeypatch.setattr(planner_client.time, "sleep", lambda _: None)
        client = LivePlannerClient("https://example/v1", "key", "qwen3-next")

        turn = client.plan([], [])
        assert turn.tool_call == TOOL_CALL


class TestFixturePlannerClient:
    def test_returns_seeded_turns_in_order(self):
        turns = [
            PlannerTurn(tool_call=TOOL_CALL, meta=LLMResponseMeta()),
            PlannerTurn(content="done", meta=LLMResponseMeta()),
        ]
        client = FixturePlannerClient(turns)

        assert client.plan([], []).tool_call == TOOL_CALL
        assert client.plan([], []).content == "done"

    def test_exhausted_fixture_fails_closed(self):
        client = FixturePlannerClient([PlannerTurn(content="done", meta=LLMResponseMeta())])
        client.plan([], [])
        with pytest.raises(LLMError):
            client.plan([], [])
