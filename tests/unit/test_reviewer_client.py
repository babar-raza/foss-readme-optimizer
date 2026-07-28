"""Independent-review client uses the proven forced-tool transport."""

import json as json_module

from readme_agent.llm import verifier_client
from readme_agent.llm.reviewer_client import (
    LiveBlindQualityReviewClient,
    LiveFactualPlanReviewClient,
    LiveIndependentReviewClient,
)
from readme_agent.llm.verification_prompts import (
    BLIND_QUALITY_REVIEW_TOOL_SCHEMA,
    FACTUAL_PLAN_REVIEW_TOOL_SCHEMA,
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
                                                    "findings": [],
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


def test_role_tool_schemas_require_grounded_acceptance_fields():
    blind_finding = BLIND_QUALITY_REVIEW_TOOL_SCHEMA["function"]["parameters"]["properties"][
        "findings"
    ]["items"]
    factual_finding = FACTUAL_PLAN_REVIEW_TOOL_SCHEMA["function"]["parameters"]["properties"][
        "findings"
    ]["items"]

    assert {"disposition", "quoted_candidate_span", "evidence_location"} <= set(
        blind_finding["required"]
    )
    assert blind_finding["properties"]["kind"]["enum"] == ["quality"]
    assert factual_finding["properties"]["kind"]["enum"] == ["factual"]
    assert "supports_acceptance" in factual_finding["properties"]["disposition"]["enum"]
