"""Independent-review client uses the proven forced-tool transport."""

import json as json_module

import pytest
import requests

from readme_agent.errors import LLMInfrastructureError
from readme_agent.llm import verifier_client
from readme_agent.llm.merged_readme_review import MERGED_README_REVIEW_TOOL_SCHEMA
from readme_agent.llm.reviewer_client import (
    FACTUAL_REVIEW_MAX_TOKENS,
    LiveBlindQualityReviewClient,
    LiveFactualPlanReviewClient,
    LiveIndependentReviewClient,
    LiveMergedReadmeReviewClient,
    LiveTrustedFidelityReviewClient,
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
    captured_requests = []

    def fake_post(url, json, headers, timeout):
        tool_name = json["tool_choice"]["function"]["name"]
        captured_requests.append((tool_name, json["max_tokens"]))

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
    assert captured_requests == [
        ("report_blind_readme_quality_review", 2400),
        ("report_factual_readme_plan_review", FACTUAL_REVIEW_MAX_TOKENS),
    ]


def test_merged_reviewer_forces_one_tool_with_two_required_facets(monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured.update(json)
        tool_name = json["tool_choice"]["function"]["name"]

        class MergedResponse(FakeResponse):
            def json(self):
                facet = {
                    "verdict": "ACCEPT",
                    "reasoning": "Grounded acceptance.",
                    "failed_criteria": [],
                    "sections_affected": [],
                    "required_repair": "",
                    "findings": [],
                }
                return {
                    "id": "merged-review-1",
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "function": {
                                            "name": tool_name,
                                            "arguments": json_module.dumps(
                                                {"quality": facet, "factual": facet}
                                            ),
                                        }
                                    }
                                ]
                            }
                        }
                    ],
                }

        return MergedResponse()

    monkeypatch.setattr(verifier_client.requests, "post", fake_post)

    result = LiveMergedReadmeReviewClient("https://example/v1", "key", "model").analyze([])

    assert set(result.parsed) == {"quality", "factual"}
    assert captured["tool_choice"]["function"]["name"] == "report_merged_readme_review"
    parameters = MERGED_README_REVIEW_TOOL_SCHEMA["function"]["parameters"]
    assert parameters["required"] == ["quality", "factual"]
    assert parameters["additionalProperties"] is False
    assert parameters["properties"]["quality"]["properties"]["findings"]["maxItems"] == 4
    assert parameters["properties"]["factual"]["properties"]["findings"]["maxItems"] == 4


def test_merged_reviewer_does_not_repeat_an_identical_timed_out_request(monkeypatch):
    calls = 0

    def timeout_once(url, json, headers, timeout):
        nonlocal calls
        calls += 1
        raise requests.Timeout("slow gateway")

    monkeypatch.setattr(verifier_client.requests, "post", timeout_once)
    monkeypatch.setattr(verifier_client.time, "sleep", lambda _: None)

    with pytest.raises(LLMInfrastructureError, match="slow gateway"):
        LiveMergedReadmeReviewClient("https://example/v1", "key", "model").analyze([])

    assert calls == 1


def test_role_tool_schemas_require_grounded_acceptance_fields():
    blind_findings = BLIND_QUALITY_REVIEW_TOOL_SCHEMA["function"]["parameters"]["properties"][
        "findings"
    ]
    blind_finding = blind_findings["items"]
    factual_finding = FACTUAL_PLAN_REVIEW_TOOL_SCHEMA["function"]["parameters"]["properties"][
        "findings"
    ]["items"]

    assert {"disposition", "quoted_candidate_span", "evidence_location"} <= set(
        blind_finding["required"]
    )
    assert blind_finding["properties"]["kind"]["enum"] == ["quality"]
    assert blind_finding["properties"]["disposition"]["enum"] == [
        "supports_acceptance",
        "requires_repair",
    ]
    assert blind_finding["properties"]["fact_id"] == {"type": "null"}
    assert blind_finding["properties"]["evidence_excerpt"] == {"type": "null"}
    assert blind_finding["properties"]["evidence_location"] == {"type": "null"}
    assert blind_finding["properties"]["expected_polarity"]["enum"] == [None]
    assert blind_finding["properties"]["observed_polarity"]["enum"] == [None]
    assert blind_finding["properties"]["polarity_result"]["enum"] == ["not_applicable"]
    assert blind_findings["maxItems"] == 8
    assert blind_finding["properties"]["quoted_candidate_span"]["maxLength"] == 1200
    assert factual_finding["properties"]["kind"]["enum"] == ["factual"]
    assert "supports_acceptance" in factual_finding["properties"]["disposition"]["enum"]
    assert (
        FACTUAL_PLAN_REVIEW_TOOL_SCHEMA["function"]["parameters"]["properties"]["findings"][
            "maxItems"
        ]
        == 8
    )


def test_trusted_fidelity_client_forces_exact_source_inventory(monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured.update(json)
        tool_name = json["tool_choice"]["function"]["name"]

        class FidelityResponse(FakeResponse):
            def json(self):
                return {
                    "id": "fidelity-1",
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
                                                    "reasoning": "All required units are present.",
                                                    "source_checks": [
                                                        {
                                                            "fact_id": "readme.inherited:abc",
                                                            "outcome": "preserved_or_represented",
                                                            "source_quote": "source",
                                                            "candidate_quote": "candidate",
                                                            "section": "README",
                                                            "required_repair": "",
                                                        }
                                                    ],
                                                    "unsupported_additions": [],
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

        return FidelityResponse()

    monkeypatch.setattr(verifier_client.requests, "post", fake_post)

    result = LiveTrustedFidelityReviewClient("https://example/v1", "key", "model").analyze_fidelity(
        [], ("readme.inherited:abc",)
    )

    assert result.parsed["verdict"] == "ACCEPT"
    source_checks = captured["tools"][0]["function"]["parameters"]["properties"]["source_checks"]
    assert source_checks["minItems"] == 1
    assert source_checks["maxItems"] == 1
    assert source_checks["items"]["properties"]["fact_id"]["enum"] == ["readme.inherited:abc"]
