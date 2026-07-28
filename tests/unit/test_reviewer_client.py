"""Independent-review client uses the proven forced-tool transport."""

import json as json_module

from readme_agent.llm import verifier_client
from readme_agent.llm.reviewer_client import (
    LiveBlindQualityReviewClient,
    LiveFactualPlanReviewClient,
    LiveIndependentReviewClient,
)
from readme_agent.llm.verification_prompts import (
    INDEPENDENT_README_REVIEW_TOOL_SCHEMA,
)


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
                                    "arguments": json_module.dumps(
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


def test_separated_role_clients_force_distinct_governed_tools(monkeypatch):
    captured_tools = []

    def fake_post(url, json, headers, timeout):
        tool_name = json["tool_choice"]["function"]["name"]
        captured_tools.append(tool_name)

        class RoleResponse(FakeResponse):
            def json(self):
                return {
                    "id": f"{tool_name}-1",
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": tool_name,
                                            "arguments": json_module.dumps(
                                                {
                                                    "verdict": "ACCEPT",
                                                    "reasoning": "Role-specific acceptance.",
                                                    "failed_criteria": [],
                                                    "sections_affected": [],
                                                    "required_repair": "",
                                                }
                                            ),
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                }

        return RoleResponse()

    monkeypatch.setattr(verifier_client.requests, "post", fake_post)

    blind = LiveBlindQualityReviewClient("https://example/v1", "key", "model").analyze([])
    factual = LiveFactualPlanReviewClient("https://example/v1", "key", "model").analyze([])

    assert blind.parsed["verdict"] == "ACCEPT"
    assert factual.parsed["verdict"] == "ACCEPT"
    assert captured_tools == [
        "report_blind_readme_quality_review",
        "report_factual_readme_plan_review",
    ]
