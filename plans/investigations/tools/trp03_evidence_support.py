"""Fixture payloads for the TRP-03 assurance-separated evidence builder."""

from __future__ import annotations

from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.llm.analysis_client import AnalysisResult, FixtureAnalysisClient
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verifier_client import ForcedToolResult


def tool_result(
    graph: TrustedReadmeFactGraphV1,
    markdown: str,
    model: str,
) -> ForcedToolResult:
    fact_ids = [fact.fact_id for fact in graph.inherited_facts]
    return ForcedToolResult(
        arguments={
            "editorial_summary": "Represent every inherited source unit.",
            "complete": True,
            "source_inventory": [
                {
                    "fact_id": fact_id,
                    "action": "rewrite",
                    "rationale": "Represent the inherited source.",
                }
                for fact_id in fact_ids
            ],
            "segments": [
                {
                    "segment_id": "complete",
                    "kind": "authored",
                    "markdown": markdown,
                    "inherited_fact_ids": fact_ids,
                    "configured_standard_ids": [],
                }
            ],
        },
        meta=LLMResponseMeta(model=model),
    )


def blind_accept(candidate_quote: str) -> dict:
    return {
        "verdict": "ACCEPT",
        "reasoning": "The candidate is concise, clear, and repository-specific.",
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "findings": [
            {
                "finding_id": "quality.specific-opening",
                "kind": "quality",
                "criterion": "product_specificity",
                "section": "overview",
                "claim": "The opening is specific.",
                "quoted_candidate_span": candidate_quote,
                "disposition": "supports_acceptance",
                "fact_id": None,
                "evidence_excerpt": None,
                "evidence_location": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "not_applicable",
                "required_repair": "",
            }
        ],
    }


def fidelity_accept(graph: TrustedReadmeFactGraphV1) -> dict:
    return {
        "verdict": "ACCEPT",
        "reasoning": "Every inherited source unit is represented.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "preserved_or_represented",
                "source_quote": fact.value.strip(),
                "candidate_quote": fact.value.strip(),
                "section": "README",
                "required_repair": "",
            }
            for fact in graph.inherited_facts
        ],
        "unsupported_additions": [],
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
    }


def fidelity_loss(graph: TrustedReadmeFactGraphV1) -> dict:
    payload = fidelity_accept(graph)
    lost = graph.inherited_facts[-1]
    payload["verdict"] = "REJECT_REPAIRABLE"
    payload["reasoning"] = "One inherited audience statement was materially weakened."
    payload["source_checks"][-1] = {
        "fact_id": lost.fact_id,
        "outcome": "lost_or_distorted",
        "source_quote": lost.value.strip(),
        "candidate_quote": "",
        "section": "overview",
        "required_repair": "Restore the inherited Python-developer audience.",
    }
    payload["failed_criteria"] = ["inherited_content_fidelity"]
    payload["sections_affected"] = ["overview"]
    payload["required_repair"] = "Restore the inherited Python-developer audience."
    return payload


def review_clients(
    blind_payloads: list[dict],
    fidelity_payloads: list[dict],
) -> tuple[FixtureAnalysisClient, FixtureAnalysisClient]:
    return (
        FixtureAnalysisClient(
            [
                AnalysisResult(parsed=item, meta=LLMResponseMeta(model="fixture-blind"))
                for item in blind_payloads
            ],
            job="blind_readme_quality_review",
            prompt_id="blind_readme_quality_review",
        ),
        FixtureAnalysisClient(
            [
                AnalysisResult(parsed=item, meta=LLMResponseMeta(model="fixture-fidelity"))
                for item in fidelity_payloads
            ],
            job="trusted_readme_fidelity_review",
            prompt_id="trusted_readme_fidelity_review",
        ),
    )
