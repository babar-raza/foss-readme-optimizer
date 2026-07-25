"""Independent-review client uses the proven forced-tool transport."""

import json

from readme_agent.llm import verifier_client
from readme_agent.llm.reviewer_client import LiveIndependentReviewClient


class FakeResponse:
    status_code = 200
    text = ""

    def json(self):
        return {
            "id": "review-1",
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "report_independent_readme_review",
                                    "arguments": json.dumps(
                                        {
                                            "verdict": "ACCEPT",
                                            "reasoning": "Grounded.",
                                            "failed_criteria": [],
                                            "sections_affected": [],
                                            "required_repair": "",
                                            "preserve": [],
                                        }
                                    ),
                                }
                            }
                        ]
                    }
                }
            ],
        }


def test_live_reviewer_forces_the_governed_verdict_tool(monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured.update(json)
        return FakeResponse()

    monkeypatch.setattr(verifier_client.requests, "post", fake_post)

    result = LiveIndependentReviewClient("https://example/v1", "key", "model").analyze([])

    assert result.parsed["verdict"] == "ACCEPT"
    assert captured["tool_choice"]["function"]["name"] == "report_independent_readme_review"
    schema = captured["tools"][0]["function"]["parameters"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
