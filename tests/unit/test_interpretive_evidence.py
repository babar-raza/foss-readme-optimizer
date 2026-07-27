"""Groundedness/citation gate for the free-text `product.audience`/`product.problems_solved`
fields -- the two REQUIRED_PRODUCT_FIELDS with no existing mechanical evidence check."""

from readme_agent.facts.interpretive_evidence import (
    InterpretiveClaimV1,
    groundedness_fact_candidate,
)
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)


def _source(source_type="mechanical_repository"):
    return FactSourceV2(
        source_type=source_type,
        location="repository://acme/widget",
        source_revision="abc123",
    )


def _established_fact(field_name, value, qualifier="established", state="verified"):
    return FactRecordV2(
        fact_id=descriptive_fact_id(field_name, qualifier),
        field=field_name,
        value=value,
        source=_source(),
        verification_state=state,
        authoritative_owner="repository-owner",
        confidence=1.0 if state in {"verified", "policy_approved"} else 0.0,
        affected_surfaces=["readme.capabilities"],
    )


def _facts_so_far(*established):
    records = list(established)
    seen_fields = {fact.field for fact in records}
    for field_name in REQUIRED_PRODUCT_FIELDS:
        if field_name in seen_fields:
            continue
        records.append(
            FactRecordV2(
                fact_id=descriptive_fact_id(field_name, "missing"),
                field=field_name,
                value=None,
                source=_source(),
                verification_state="missing",
                authoritative_owner="repository-owner",
                confidence=0.0,
                affected_surfaces=["readme"],
            )
        )
    selected = {}
    for fact in records:
        selected.setdefault(fact.field, fact.fact_id)
    return ProductFactsV2(org_repo="acme/widget", facts=records, selected_fact_ids=selected)


_IDENTITY = _established_fact(
    "product.identity",
    {
        "family": "widget",
        "platform": "java",
        "ecosystem": "java",
        "repository": "acme/widget",
    },
    "identity",
)
_CAPABILITIES = _established_fact(
    "product.capabilities",
    "Convert and merge PDF documents without any external dependency.",
    "capabilities",
)


def test_all_claims_pass_yields_verified_agent_drafted_fact():
    facts_so_far = _facts_so_far(_IDENTITY, _CAPABILITIES)
    claim = InterpretiveClaimV1(
        claim_id="audience-1",
        text="Developers using Java.",
        supporting_fact_ids=[_IDENTITY.fact_id],
    )

    fact = groundedness_fact_candidate(
        "product.audience",
        [claim],
        facts_so_far,
        source_revision="abc123",
        observed_at=None,
    )

    assert fact.verification_state == "verified"
    assert fact.source.source_type == "agent_drafted"
    assert fact.confidence == 1.0
    assert fact.value == [claim.text]
    assert fact.supporting_fact_ids == [_IDENTITY.fact_id]


def test_audience_allows_only_a_cited_platform_in_the_bounded_scaffold():
    facts_so_far = _facts_so_far(_IDENTITY, _CAPABILITIES)
    claim = InterpretiveClaimV1(
        claim_id="audience-1",
        text="Developers using java.",
        supporting_fact_ids=[_IDENTITY.fact_id],
    )

    fact = groundedness_fact_candidate(
        "product.audience",
        [claim],
        facts_so_far,
        source_revision="abc123",
        observed_at=None,
    )

    assert fact.verification_state == "verified"


def test_audience_rejects_capability_text_appended_as_an_ungrammatical_for_phrase():
    facts_so_far = _facts_so_far(_IDENTITY, _CAPABILITIES)
    claim = InterpretiveClaimV1(
        claim_id="audience-1",
        text="Developers using Java for Convert and merge PDF documents.",
        supporting_fact_ids=[_IDENTITY.fact_id, _CAPABILITIES.fact_id],
    )

    fact = groundedness_fact_candidate(
        "product.audience",
        [claim],
        facts_so_far,
        source_revision="abc123",
        observed_at=None,
    )

    assert fact.verification_state == "blocked"
    assert any(
        "audience must be exactly" in reason for reason in fact.value["groundedness_failures"]
    )


def test_audience_scaffolding_does_not_allow_unsupported_positioning():
    facts_so_far = _facts_so_far(_IDENTITY, _CAPABILITIES)
    claim = InterpretiveClaimV1(
        claim_id="audience-1",
        text="Developers using a powerful free alternative.",
        supporting_fact_ids=[_IDENTITY.fact_id, _CAPABILITIES.fact_id],
    )

    fact = groundedness_fact_candidate(
        "product.audience",
        [claim],
        facts_so_far,
        source_revision="abc123",
        observed_at=None,
    )

    assert fact.verification_state == "blocked"
    failures = fact.value["groundedness_failures"]
    assert any("audience must be exactly" in reason for reason in failures)


def test_problems_solved_does_not_receive_audience_scaffolding():
    facts_so_far = _facts_so_far(_IDENTITY, _CAPABILITIES)
    claim = InterpretiveClaimV1(
        claim_id="problem-1",
        text="Developers using a backend document processing engine.",
        supporting_fact_ids=[_IDENTITY.fact_id],
    )

    fact = groundedness_fact_candidate(
        "product.problems_solved",
        [claim],
        facts_so_far,
        source_revision="abc123",
        observed_at=None,
    )

    assert fact.verification_state == "blocked"
    assert any("using" in reason for reason in fact.value["groundedness_failures"])


def test_empty_supporting_fact_ids_blocks_the_whole_field():
    facts_so_far = _facts_so_far(_IDENTITY, _CAPABILITIES)
    claim = InterpretiveClaimV1(
        claim_id="audience-1",
        text="Enterprise developers who convert PDF documents.",
        supporting_fact_ids=[],
    )

    fact = groundedness_fact_candidate(
        "product.audience",
        [claim],
        facts_so_far,
        source_revision="abc123",
        observed_at=None,
    )

    assert fact.verification_state == "blocked"
    assert fact.confidence == 0.0
    assert any("no supporting_fact_ids" in reason for reason in fact.value["groundedness_failures"])


def test_unresolvable_citation_id_blocks_the_whole_field():
    facts_so_far = _facts_so_far(_IDENTITY, _CAPABILITIES)
    claim = InterpretiveClaimV1(
        claim_id="audience-1",
        text="Enterprise developers who convert PDF documents.",
        supporting_fact_ids=["product.audience:does-not-exist"],
    )

    fact = groundedness_fact_candidate(
        "product.audience",
        [claim],
        facts_so_far,
        source_revision="abc123",
        observed_at=None,
    )

    assert fact.verification_state == "blocked"
    assert any("does not resolve" in reason for reason in fact.value["groundedness_failures"])


def test_low_lexical_coverage_blocks_the_whole_field():
    facts_so_far = _facts_so_far(_IDENTITY, _CAPABILITIES)
    claim = InterpretiveClaimV1(
        claim_id="audience-1",
        text="Cloud-native Kubernetes orchestration for machine learning pipelines.",
        supporting_fact_ids=[_IDENTITY.fact_id, _CAPABILITIES.fact_id],
    )

    fact = groundedness_fact_candidate(
        "product.audience",
        [claim],
        facts_so_far,
        source_revision="abc123",
        observed_at=None,
    )

    assert fact.verification_state == "blocked"
    assert any(
        "audience must be exactly" in reason for reason in fact.value["groundedness_failures"]
    )


def test_mixed_pass_and_fail_claims_block_the_whole_field_not_partial_credit():
    facts_so_far = _facts_so_far(_IDENTITY, _CAPABILITIES)
    passing = InterpretiveClaimV1(
        claim_id="problem-1",
        text="Convert and merge PDF documents.",
        supporting_fact_ids=[_CAPABILITIES.fact_id],
    )
    failing = InterpretiveClaimV1(
        claim_id="problem-2",
        text="Real-time video transcoding at massive scale.",
        supporting_fact_ids=[_IDENTITY.fact_id, _CAPABILITIES.fact_id],
    )

    fact = groundedness_fact_candidate(
        "product.problems_solved",
        [passing, failing],
        facts_so_far,
        source_revision="abc123",
        observed_at=None,
    )

    assert fact.verification_state == "blocked"
    assert fact.confidence == 0.0
    reasons = fact.value["groundedness_failures"]
    assert any(reason.startswith("problem-2") for reason in reasons)
    assert not any(reason.startswith("problem-1") for reason in reasons)


def test_agentic_problem_selection_keeps_only_fully_grounded_sibling_claims():
    facts_so_far = _facts_so_far(_IDENTITY, _CAPABILITIES)
    passing = InterpretiveClaimV1(
        claim_id="problem-1",
        text="Convert and merge PDF documents.",
        supporting_fact_ids=[_CAPABILITIES.fact_id],
    )
    failing = InterpretiveClaimV1(
        claim_id="problem-2",
        text="Real-time video transcoding at massive scale.",
        supporting_fact_ids=[_IDENTITY.fact_id, _CAPABILITIES.fact_id],
    )

    fact = groundedness_fact_candidate(
        "product.problems_solved",
        [passing, failing],
        facts_so_far,
        source_revision="abc123",
        observed_at=None,
        allow_partial=True,
    )

    assert fact.verification_state == "verified"
    assert fact.value == [passing.text]
    assert fact.supporting_fact_ids == [_CAPABILITIES.fact_id]


def test_citation_to_a_fact_outside_the_accepted_verification_states_is_rejected():
    conflicting_capabilities = _established_fact(
        "product.capabilities",
        "Convert and merge PDF documents without any external dependency.",
        "capabilities",
        state="conflicting",
    )
    facts_so_far = _facts_so_far(_IDENTITY, conflicting_capabilities)
    claim = InterpretiveClaimV1(
        claim_id="audience-1",
        text="Enterprise developers who convert and merge PDF documents.",
        supporting_fact_ids=[_IDENTITY.fact_id, conflicting_capabilities.fact_id],
    )

    fact = groundedness_fact_candidate(
        "product.audience",
        [claim],
        facts_so_far,
        source_revision="abc123",
        observed_at=None,
    )

    assert fact.verification_state == "blocked"
