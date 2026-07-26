"""Independent-review client uses the proven forced-tool transport."""

import json

from readme_agent.llm import verifier_client
from readme_agent.llm.reviewer_client import LiveIndependentReviewClient
from readme_agent.llm.verification_prompts import INDEPENDENT_README_REVIEW_TOOL_SCHEMA


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


def test_verdict_schema_encodes_fact_block_precedence():
    verdict = INDEPENDENT_README_REVIEW_TOOL_SCHEMA["function"]["parameters"]["properties"][
        "verdict"
    ]

    assert "absent from the supplied facts" in verdict["description"]
    assert "even when deleting it would be a bounded repair" in verdict["description"]
    assert "REJECT_REPAIRABLE is only" in verdict["description"]
    assert "document's own omissions or malformed markup" in verdict["description"]
