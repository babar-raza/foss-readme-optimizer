"""Contracts and negative controls for separated independent README review roles."""

import hashlib

import pytest
from pydantic import ValidationError

from readme_agent.llm import prompt_registry
from readme_agent.llm.verification_prompts import (
    build_blind_quality_review_messages,
    build_factual_plan_review_messages,
)
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.specialists.readme_review_roles import (
    BlindQualityReviewInputV1,
    FactualPlanReviewInputV1,
    ReviewActorIdentityV1,
    RoleReviewRecordV1,
    combine_review_verdicts,
    input_hash,
    json_hash,
)

ORG_REPO = "example/example-foss"
ORIGINAL = "# Example\n\nOriginal content.\n"
CANDIDATE = "# Example\n\nSpecific, useful candidate.\n"
CANDIDATE_HASH = sha256_hex(CANDIDATE)


def _identity(actor: str, role: str, prompt: str) -> ReviewActorIdentityV1:
    return ReviewActorIdentityV1(
        actor_id=actor,
        role=role,
        prompt_id=prompt,
        prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
    )


def _record(
    actor: str,
    role: str,
    prompt: str,
    verdict: str,
    candidate_hash: str = CANDIDATE_HASH,
) -> RoleReviewRecordV1:
    failed = verdict not in {"ACCEPT", "SYSTEM_FAILURE"}
    finding_kind = "quality" if role == "blind_quality_reviewer" else "factual"
    polarity_result = (
        "not_applicable"
        if finding_kind == "quality"
        else ("missing" if verdict != "BLOCKED_FACT_CONFLICT" else "contradicts")
    )
    return RoleReviewRecordV1(
        identity=_identity(actor, role, prompt),
        candidate_sha256=candidate_hash,
        input_sha256=hashlib.sha256(f"{actor}:{candidate_hash}".encode()).hexdigest(),
        verdict=verdict,
        reasoning=f"{role} returned {verdict}",
        failed_criteria=["clarity" if finding_kind == "quality" else "factuality"]
        if failed
        else [],
        sections_affected=["Overview"] if failed else [],
        findings=(
            [
                {
                    "finding_id": f"{finding_kind}.finding",
                    "kind": finding_kind,
                    "criterion": "clarity" if finding_kind == "quality" else "factuality",
                    "section": "Overview",
                    "claim": "A grounded finding.",
                    "quoted_candidate_span": "Specific, useful candidate.",
                    "fact_id": "fact-1" if polarity_result == "contradicts" else None,
                    "evidence_excerpt": (
                        "contradicting evidence" if polarity_result == "contradicts" else None
                    ),
                    "expected_polarity": (
                        "positive_implementation" if polarity_result == "contradicts" else None
                    ),
                    "observed_polarity": (
                        "explicit_constraint" if polarity_result == "contradicts" else None
                    ),
                    "polarity_result": polarity_result,
                    "required_repair": "Repair it.",
                }
            ]
            if failed
            else []
        ),
    )


def test_blind_context_cannot_contain_producer_plan_or_acceptance_context() -> None:
    messages = build_blind_quality_review_messages(ORG_REPO, ORIGINAL, CANDIDATE)
    serialized = "\n".join(str(message["content"]) for message in messages)

    assert ORIGINAL in serialized
    assert CANDIDATE in serialized
    assert "deterministic validation result" not in serialized.casefold()
    assert "presentation plan used to produce" not in serialized.casefold()
    assert '"verdict": "accept"' not in serialized.casefold()


def test_factual_plan_context_has_no_deterministic_or_producer_verdict() -> None:
    messages = build_factual_plan_review_messages(
        ORG_REPO,
        CANDIDATE,
        '{"selected_fact_ids":{"product.identity":"fact-1"}}',
        '{"operations":[{"operation_id":"readme.overview"}]}',
    )
    serialized = str(messages)

    assert "fact-1" in serialized
    assert "readme.overview" in serialized
    assert "deterministic validation result" not in serialized.casefold()
    assert "producer verdict" not in serialized.casefold()
    assert '"verdict": "accept"' not in serialized.casefold()


def test_role_inputs_are_hash_bound_and_have_disjoint_fields() -> None:
    blind = BlindQualityReviewInputV1(
        org_repo=ORG_REPO,
        original_readme_text=ORIGINAL,
        candidate_readme_text=CANDIDATE,
        candidate_sha256=CANDIDATE_HASH,
        rubric_version="1",
    )
    facts = {"selected_fact_ids": {"product.identity": "fact-1"}}
    plan = {"operations": [{"operation_id": "readme.overview"}]}
    factual = FactualPlanReviewInputV1(
        org_repo=ORG_REPO,
        candidate_readme_text=CANDIDATE,
        candidate_sha256=CANDIDATE_HASH,
        product_facts=facts,
        product_facts_sha256=json_hash(facts),
        presentation_plan=plan,
        presentation_plan_sha256=json_hash(plan),
        rubric_version="1",
    )

    assert "product_facts" not in blind.model_fields_set
    assert "presentation_plan" not in blind.model_fields_set
    assert input_hash(blind) != input_hash(factual)

    with pytest.raises(ValidationError, match="candidate hash"):
        BlindQualityReviewInputV1(
            org_repo=ORG_REPO,
            original_readme_text=ORIGINAL,
            candidate_readme_text=CANDIDATE,
            candidate_sha256="0" * 64,
            rubric_version="1",
        )


@pytest.mark.parametrize(
    ("blind_verdict", "factual_verdict", "combined"),
    [
        ("ACCEPT", "ACCEPT", "ACCEPT"),
        ("REJECT_REPAIRABLE", "ACCEPT", "REJECT_REPAIRABLE"),
        ("ACCEPT", "REJECT_REPAIRABLE", "REJECT_REPAIRABLE"),
        ("ACCEPT", "BLOCKED_MISSING_EVIDENCE", "BLOCKED_MISSING_EVIDENCE"),
        ("REJECT_REPAIRABLE", "BLOCKED_FACT_CONFLICT", "BLOCKED_FACT_CONFLICT"),
        ("SYSTEM_FAILURE", "ACCEPT", "SYSTEM_FAILURE"),
    ],
)
def test_either_role_can_fail_the_combined_verdict(
    blind_verdict: str,
    factual_verdict: str,
    combined: str,
) -> None:
    result = combine_review_verdicts(
        author=_identity("author-1", "author", "plan_readme_composition"),
        blind_quality=_record(
            "reviewer-blind",
            "blind_quality_reviewer",
            "blind_readme_quality_review",
            blind_verdict,
        ),
        factual_plan=_record(
            "reviewer-factual",
            "factual_plan_reviewer",
            "factual_readme_plan_review",
            factual_verdict,
        ),
    )

    assert result.verdict == combined
    assert result.identity_separation_valid


def test_author_or_reviewer_identity_overlap_fails_closed() -> None:
    author = _identity("shared-actor", "author", "plan_readme_composition")
    result = combine_review_verdicts(
        author=author,
        blind_quality=_record(
            "shared-actor",
            "blind_quality_reviewer",
            "blind_readme_quality_review",
            "ACCEPT",
        ),
        factual_plan=_record(
            "reviewer-factual",
            "factual_plan_reviewer",
            "factual_readme_plan_review",
            "ACCEPT",
        ),
    )

    assert result.verdict == "SYSTEM_FAILURE"
    assert not result.identity_separation_valid


def test_prompt_identities_are_distinct_and_registered() -> None:
    blind_hash = prompt_registry.prompt_hash("blind_readme_quality_review")
    factual_hash = prompt_registry.prompt_hash("factual_readme_plan_review")

    assert blind_hash != factual_hash
    assert prompt_registry.get("blind_readme_quality_review") is not None
    assert prompt_registry.get("factual_readme_plan_review") is not None
