"""LiveSectionClusterAuthorClient: bounded transport retry, identical bytes, no semantic retry."""

import json

import pytest

from readme_agent.errors import LLMInfrastructureError
from readme_agent.llm import verifier_client
from readme_agent.llm.section_author_client import (
    MAX_OUTPUT_TOKENS,
    TRANSPORT_MAX_ATTEMPTS,
    LiveSectionClusterAuthorClient,
)

TOOL_SCHEMA_FACT_IDS = ["F.CAP.01", "F.CAP.02"]


class FakeResponse:
    def __init__(self, status_code, body=None, text=""):
        self.status_code = status_code
        self._body = body
        self.text = text or (body and json.dumps(body)) or text

    def json(self):
        return self._body


def _success_body():
    return {
        "id": "chatcmpl-1",
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "tool_calls": [
                        {
                            "id": "call1",
                            "function": {
                                "name": "submit_section_cluster",
                                "arguments": json.dumps(
                                    {
                                        "units": [
                                            {
                                                "heading": "Overview",
                                                "text": "Imports OBJ and GLTF files.",
                                                "fact_ids": ["F.CAP.01", "F.CAP.02"],
                                            }
                                        ],
                                        "omitted": [],
                                    }
                                ),
                            },
                        }
                    ]
                },
            }
        ],
    }


def test_transport_max_attempts_is_two():
    assert TRANSPORT_MAX_ATTEMPTS == 2


def test_transient_500_retries_once_with_identical_bytes_then_succeeds(monkeypatch):
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append(json)
        if len(calls) == 1:
            return FakeResponse(500, text="Cannot connect to host text-model.vllm-qwen")
        return FakeResponse(200, _success_body())

    monkeypatch.setattr(verifier_client.requests, "post", fake_post)
    monkeypatch.setattr(verifier_client.time, "sleep", lambda _: None)
    client = LiveSectionClusterAuthorClient("https://example/v1", "key", "qwen3-next")

    result = client.analyze_section_cluster(
        [{"role": "user", "content": "go"}], TOOL_SCHEMA_FACT_IDS
    )

    assert len(calls) == 2
    assert calls[0] == calls[1]  # identical request bytes on transport retry
    assert result.parsed["units"][0]["fact_ids"] == ["F.CAP.01", "F.CAP.02"]


def test_two_consecutive_500s_exhaust_the_bounded_retry_and_raise(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, json, headers, timeout):
        calls["n"] += 1
        return FakeResponse(500, text="Cannot connect to host text-model.vllm-qwen")

    monkeypatch.setattr(verifier_client.requests, "post", fake_post)
    monkeypatch.setattr(verifier_client.time, "sleep", lambda _: None)
    client = LiveSectionClusterAuthorClient("https://example/v1", "key", "qwen3-next")

    with pytest.raises(LLMInfrastructureError):
        client.analyze_section_cluster([{"role": "user", "content": "go"}], TOOL_SCHEMA_FACT_IDS)

    # bounded: never more than TRANSPORT_MAX_ATTEMPTS physical attempts for one authoring call
    assert calls["n"] == TRANSPORT_MAX_ATTEMPTS


def test_schema_invalid_response_is_not_transport_retried(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, json, headers, timeout):
        calls["n"] += 1
        return FakeResponse(
            200,
            {
                "choices": [
                    {
                        "finish_reason": "tool_calls",
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "call1",
                                    "function": {
                                        "name": "submit_section_cluster",
                                        "arguments": "{not valid json",
                                    },
                                }
                            ]
                        },
                    }
                ]
            },
        )

    monkeypatch.setattr(verifier_client.requests, "post", fake_post)
    client = LiveSectionClusterAuthorClient("https://example/v1", "key", "qwen3-next")

    with pytest.raises(Exception):  # noqa: B017 - either LLMError or LLMTruncatedResponseError
        client.analyze_section_cluster([{"role": "user", "content": "go"}], TOOL_SCHEMA_FACT_IDS)

    # response_max_attempts=1: no retry for factual/schema failure at this client layer -- the
    # specialist owns the bounded semantic-correction retry instead (test_section_cluster_
    # authoring.py::test_unsupported_fact_id_triggers_one_semantic_retry_then_succeeds).
    assert calls["n"] == 1


def test_max_output_tokens_default_matches_the_production_budget():
    assert MAX_OUTPUT_TOKENS == 2048
