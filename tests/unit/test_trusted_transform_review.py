"""Independent quality and inheritance-fidelity review for trusted transforms."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from readme_agent import env
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.facts.trusted_readme_extraction import extract_trusted_readme_fact_graph
from readme_agent.gitsafety._git import run_git
from readme_agent.llm.analysis_client import AnalysisResult, FixtureAnalysisClient
from readme_agent.llm.call_ledger import (
    bind_llm_repository_revision,
    start_llm_call_accounting,
)
from readme_agent.llm.call_schema import LlmAccountingSummaryV1
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verifier_client import FixtureForcedToolClient, ForcedToolResult
from readme_agent.readme.trusted_composition import compose_trusted_readme
from readme_agent.registry.loader import load_products
from readme_agent.repository_snapshot import capture_repository_snapshot, repository_snapshot_scope
from readme_agent.specialists.trusted_transform_review import run_trusted_transform_review
from readme_agent.specialists.trusted_transform_review_models import TrustedTransformReviewV1
from readme_agent.specialists.trusted_transform_review_repair import (
    run_trusted_review_with_repair,
)
from readme_agent.state.readme_poc_lifecycle import (
    record_repository_profile,
    record_repository_snapshot,
    switch_content_assurance,
    transition_trusted_readme_poc_status,
)
from readme_agent.supervisor.trusted_review_state import record_trusted_review_execution
from tests.unit.test_state_backend import FakeStateBackend

ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
SOURCE = "# Widget\n\nA specific package for Python developers.\n"


def _git(root: Path, *args: str) -> None:
    result = run_git(list(args), cwd=root)
    assert result.returncode == 0, result.stderr


def _composition(
    tmp_path: Path,
    *,
    candidate: str = SOURCE,
    root_name: str = "source",
):
    root = tmp_path / root_name
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Trusted Review Test")
    _git(root, "config", "user.email", "trusted-review@example.invalid")
    (root / "README.md").write_text(SOURCE, encoding="utf-8", newline="")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "seed")
    entry = next(item for item in load_products() if item.org_repo == ORG_REPO)
    snapshot = capture_repository_snapshot(entry, root)
    graph = extract_trusted_readme_fact_graph(snapshot)
    fact_ids = [fact.fact_id for fact in graph.inherited_facts]
    composition = compose_trusted_readme(
        graph,
        SOURCE,
        client=FixtureForcedToolClient(
            [
                ForcedToolResult(
                    arguments={
                        "editorial_summary": "Retain the concise source.",
                        "complete": True,
                        "source_inventory": [
                            {
                                "fact_id": fact_id,
                                "action": "rewrite",
                                "rationale": "Retain the inherited material.",
                            }
                            for fact_id in fact_ids
                        ],
                        "segments": [
                            {
                                "segment_id": "complete",
                                "kind": "authored",
                                "markdown": candidate,
                                "inherited_fact_ids": fact_ids,
                                "configured_standard_ids": [],
                            }
                        ],
                    },
                    meta=LLMResponseMeta(model="fixture-author"),
                )
            ],
            job="trusted_readme_section_transform",
            prompt_id="trusted_readme_section_transform",
        ),
    )
    return graph, composition, snapshot


def _analysis(parsed: dict, *, model: str) -> AnalysisResult:
    return AnalysisResult(parsed=parsed, meta=LLMResponseMeta(model=model))


def _blind_accept() -> dict:
    return {
        "verdict": "ACCEPT",
        "reasoning": "The candidate is concise and specific.",
        "failed_criteria": [],
        "sections_affected": [],
        "required_repair": "",
        "findings": [
            {
                "finding_id": "quality.specific-opening",
                "kind": "quality",
                "criterion": "product_specificity",
                "section": "overview",
                "claim": "The opening identifies the audience.",
                "quoted_candidate_span": "A specific package for Python developers.",
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


def _blind_reject() -> dict:
    finding = _blind_accept()["findings"][0]
    return {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The opening needs a clearer purpose.",
        "failed_criteria": ["clarity"],
        "sections_affected": ["overview"],
        "required_repair": "Clarify the product purpose.",
        "findings": [
            {
                **finding,
                "finding_id": "quality.unclear-purpose",
                "criterion": "clarity",
                "claim": "The purpose is unclear.",
                "disposition": "requires_repair",
                "required_repair": "Clarify the product purpose.",
            }
        ],
    }


def _fidelity_accept(graph) -> dict:
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


def _review_clients(graph, *, blind: dict | None = None, fidelity: dict | None = None):
    return (
        FixtureAnalysisClient(
            [_analysis(blind or _blind_accept(), model="fixture-blind")],
            job="blind_readme_quality_review",
            prompt_id="blind_readme_quality_review",
        ),
        FixtureAnalysisClient(
            [_analysis(fidelity or _fidelity_accept(graph), model="fixture-fidelity")],
            job="trusted_readme_fidelity_review",
            prompt_id="trusted_readme_fidelity_review",
        ),
    )


def _repair_result(graph, markdown: str) -> ForcedToolResult:
    fact_ids = [fact.fact_id for fact in graph.inherited_facts]
    return ForcedToolResult(
        arguments={
            "editorial_summary": "Repair the opening without losing inherited content.",
            "complete": True,
            "source_inventory": [
                {
                    "fact_id": fact_id,
                    "action": "rewrite",
                    "rationale": "Represent the inherited source in the repaired opening.",
                }
                for fact_id in fact_ids
            ],
            "segments": [
                {
                    "segment_id": "repaired",
                    "kind": "authored",
                    "markdown": markdown,
                    "inherited_fact_ids": fact_ids,
                    "configured_standard_ids": [],
                }
            ],
        },
        meta=LLMResponseMeta(model="fixture-repair"),
    )


def _start_accounting(graph, run_id: str) -> None:
    start_llm_call_accounting(ORG_REPO, run_id, stage="TRUSTED_REVIEWING")
    bind_llm_repository_revision(graph.source_revision, stage="TRUSTED_REVIEWING")


def test_approval_requires_deterministic_validation_and_two_independent_roles(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-accept")
    blind, fidelity = _review_clients(graph)

    execution = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    )

    review = execution.review
    assert review.verdict == "TRUSTED_TRANSFORM_APPROVED"
    assert review.validation.passed
    assert review.identity_separation_valid
    assert review.factual_truth_verified is False
    assert review.content_assurance == "trusted_inherited"
    assert execution.fixture_calls_after - execution.fixture_calls_before == 2
    assert execution.new_provider_call_count == 0
    assert execution.accounting_status == "EXACT"
    assert execution.ledger_sha256
    assert review.blind_quality.identity.prompt_id == "blind_readme_quality_review"
    assert review.inheritance_fidelity.identity.prompt_id == "trusted_readme_fidelity_review"


def test_blind_rejection_vetoes_fidelity_acceptance(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-reject")
    blind, fidelity = _review_clients(graph, blind=_blind_reject())

    execution = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    )

    assert execution.review.verdict == "REJECT_REPAIRABLE"
    assert execution.review.blind_quality.verdict == "REJECT_REPAIRABLE"
    assert execution.review.inheritance_fidelity.verdict == "ACCEPT"


def test_content_loss_cannot_be_approved(tmp_path):
    candidate = "# Widget\n"
    graph, composition, _ = _composition(tmp_path, candidate=candidate)
    _start_accounting(graph, "trusted-review-content-loss")
    fidelity_result = _fidelity_accept(graph)
    fidelity_result["verdict"] = "REJECT_REPAIRABLE"
    fidelity_result["reasoning"] = "One inherited unit is absent from the candidate."
    fidelity_result["failed_criteria"] = ["inheritance_fidelity"]
    fidelity_result["sections_affected"] = ["overview"]
    fidelity_result["required_repair"] = "Restore the inherited product description."
    missing_index = next(
        index
        for index, check in enumerate(fidelity_result["source_checks"])
        if check["source_quote"] not in candidate
    )
    fidelity_result["source_checks"][missing_index] = {
        **fidelity_result["source_checks"][missing_index],
        "outcome": "lost_or_distorted",
        "candidate_quote": "",
        "required_repair": "Restore this inherited source unit.",
    }
    blind_result = _blind_accept()
    blind_result["findings"][0]["quoted_candidate_span"] = "# Widget"
    blind_result["findings"][0]["claim"] = "The candidate retains a product heading."
    blind, fidelity = _review_clients(
        graph,
        blind=blind_result,
        fidelity=fidelity_result,
    )

    execution = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    )

    assert execution.review.verdict == "REJECT_REPAIRABLE"
    assert execution.review.inheritance_fidelity.verdict == "REJECT_REPAIRABLE"
    assert execution.review.factual_truth_verified is False


def test_unsupported_addition_cannot_be_approved(tmp_path):
    candidate = SOURCE + "\nUnlimited hosted processing is included.\n"
    graph, composition, _ = _composition(tmp_path, candidate=candidate)
    _start_accounting(graph, "trusted-review-unsupported-addition")
    fidelity_result = _fidelity_accept(graph)
    fidelity_result.update(
        {
            "verdict": "REJECT_REPAIRABLE",
            "reasoning": "The candidate contains an unsupported product claim.",
            "failed_criteria": ["unsupported_addition"],
            "sections_affected": ["overview"],
            "required_repair": "Remove the unsupported sentence.",
        }
    )
    fidelity_result["unsupported_additions"] = [
        {
            "finding_id": "fidelity.unsupported-hosting",
            "section": "overview",
            "quoted_candidate_span": "Unlimited hosted processing is included.",
            "reason": "No README-derived fact or configured standard supports this claim.",
            "required_repair": "Remove the unsupported hosting claim.",
        }
    ]
    blind, fidelity = _review_clients(graph, fidelity=fidelity_result)

    execution = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    )

    assert execution.review.verdict == "REJECT_REPAIRABLE"
    assert execution.review.inheritance_fidelity.verdict == "REJECT_REPAIRABLE"


def test_missing_source_check_gets_one_grounding_retry(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-grounding-retry")
    incomplete = _fidelity_accept(graph)
    incomplete["source_checks"] = incomplete["source_checks"][:-1]
    fidelity = FixtureAnalysisClient(
        [
            _analysis(incomplete, model="fixture-fidelity"),
            _analysis(_fidelity_accept(graph), model="fixture-fidelity"),
        ],
        job="trusted_readme_fidelity_review",
        prompt_id="trusted_readme_fidelity_review",
    )
    blind = _review_clients(graph)[0]

    execution = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    )

    history = execution.review.inheritance_fidelity.result["retry_history"]
    assert history[0]["valid"] is False
    assert history[1]["valid"] is True
    assert execution.review.verdict == "TRUSTED_TRANSFORM_APPROVED"


def test_repeated_invalid_fidelity_output_becomes_visible_system_failure(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-truncation")
    blind = _review_clients(graph)[0]
    fidelity = FixtureAnalysisClient(
        [_analysis({}, model="fixture-fidelity"), _analysis({}, model="fixture-fidelity")],
        job="trusted_readme_fidelity_review",
        prompt_id="trusted_readme_fidelity_review",
    )

    execution = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    )

    assert execution.review.verdict == "SYSTEM_FAILURE"
    assert execution.review.inheritance_fidelity.verdict == "SYSTEM_FAILURE"
    assert "repeatedly returned ungrounded output" in str(
        execution.review.inheritance_fidelity.result["reasoning"]
    )


def test_accepted_cache_reuse_makes_no_new_reviewer_calls(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-cache")
    blind, fidelity = _review_clients(graph)
    first = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    )

    second = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=FixtureAnalysisClient([]),
        fidelity_client=FixtureAnalysisClient([]),
        cached_review=first.review,
    )

    assert second.cache_reused
    assert second.new_provider_call_count == 0
    assert second.fixture_calls_after == second.fixture_calls_before
    assert second.cache_reuses_after - second.cache_reuses_before == 1
    assert second.review == first.review


def test_changed_candidate_invalidates_accepted_review_cache(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-cache-invalidation")
    blind, fidelity = _review_clients(graph)
    accepted = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    )
    changed_candidate = SOURCE + "\nFocused workflows remain easy to discover.\n"
    changed_graph, changed_composition, _ = _composition(
        tmp_path,
        candidate=changed_candidate,
        root_name="changed-source",
    )
    changed_blind, changed_fidelity = _review_clients(changed_graph)

    result = run_trusted_transform_review(
        changed_graph,
        SOURCE,
        changed_composition,
        blind_client=changed_blind,
        fidelity_client=changed_fidelity,
        cached_review=accepted.review,
    )

    assert not result.cache_reused
    assert result.fixture_calls_after - result.fixture_calls_before == 2
    assert result.review.candidate_sha256 == changed_composition.candidate_sha256


def test_author_route_change_invalidates_accepted_review_cache(tmp_path, monkeypatch):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-author-route-invalidation")
    blind, fidelity = _review_clients(graph)
    accepted = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    )
    real_route = env.llm_model_for_job
    monkeypatch.setattr(
        "readme_agent.specialists.trusted_transform_review.env.llm_model_for_job",
        lambda job: (
            "changed-author-route" if job == "trusted_readme_section_transform" else real_route(job)
        ),
    )
    changed_blind, changed_fidelity = _review_clients(graph)

    result = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=changed_blind,
        fidelity_client=changed_fidelity,
        cached_review=accepted.review,
    )

    assert not result.cache_reused
    assert result.fixture_calls_after - result.fixture_calls_before == 2
    assert result.review.cache_identity.author_model_route == "changed-author-route"


def test_model_rejects_false_identity_separation_claim(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-identity")
    blind, fidelity = _review_clients(graph)
    accepted = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    ).review
    payload = accepted.model_dump(mode="python")
    payload["blind_quality"]["identity"]["actor_id"] = payload["author"]["actor_id"]

    with pytest.raises(ValidationError, match="identity-separation claim"):
        TrustedTransformReviewV1.model_validate(payload)


def test_same_client_cannot_act_as_both_reviewers(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-client-separation")
    shared = FixtureAnalysisClient(
        [_analysis(_blind_accept(), model="fixture-shared")],
        job="blind_readme_quality_review",
        prompt_id="blind_readme_quality_review",
    )

    with pytest.raises(ValueError, match="must be separate clients"):
        run_trusted_transform_review(
            graph,
            SOURCE,
            composition,
            blind_client=shared,
            fidelity_client=shared,
        )


def test_grounded_repair_changes_bytes_then_reruns_both_roles(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-repair")
    blind = FixtureAnalysisClient(
        [
            _analysis(_blind_reject(), model="fixture-blind"),
            _analysis(_blind_accept(), model="fixture-blind"),
        ],
        job="blind_readme_quality_review",
        prompt_id="blind_readme_quality_review",
    )
    fidelity = FixtureAnalysisClient(
        [
            _analysis(_fidelity_accept(graph), model="fixture-fidelity"),
            _analysis(_fidelity_accept(graph), model="fixture-fidelity"),
        ],
        job="trusted_readme_fidelity_review",
        prompt_id="trusted_readme_fidelity_review",
    )
    repair = FixtureForcedToolClient(
        [
            _repair_result(
                graph, "# Widget for Python\n\nA specific package for Python developers.\n"
            )
        ],
        job="trusted_readme_section_transform",
        prompt_id="trusted_readme_section_transform",
    )

    result = run_trusted_review_with_repair(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
        repair_client=repair,
    )

    assert result.outcome == "accepted"
    assert result.final_composition.candidate_sha256 != composition.candidate_sha256
    assert len(result.repair_history) == 1
    assert result.repair_history[0].candidate_changed
    assert result.repair_history[0].rereview_verdict == "TRUSTED_TRANSFORM_APPROVED"
    assert result.final_execution.review.blind_quality.verdict == "ACCEPT"
    assert result.final_execution.review.inheritance_fidelity.verdict == "ACCEPT"


def test_byte_identical_repair_becomes_visible_system_failure(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-unchanged-repair")
    blind, fidelity = _review_clients(graph, blind=_blind_reject())
    repair = FixtureForcedToolClient(
        [_repair_result(graph, SOURCE)],
        job="trusted_readme_section_transform",
        prompt_id="trusted_readme_section_transform",
    )

    result = run_trusted_review_with_repair(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
        repair_client=repair,
    )

    assert result.outcome == "system_failure"
    assert result.system_failure_reason == "trusted repair returned byte-identical candidate"
    assert len(result.repair_history) == 1
    assert not result.repair_history[0].candidate_changed


def test_registered_review_capability_requires_independent_domain_and_bound_snapshot(tmp_path):
    graph, composition, snapshot = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-capability")
    blind, fidelity = _review_clients(graph)
    tool_call = {
        "id": "trusted-review-test",
        "function": {
            "name": "review_trusted_readme",
            "arguments": f'{{"org_repo":"{ORG_REPO}"}}',
        },
    }
    with repository_snapshot_scope(snapshot):
        denied = dispatch_tool_call(
            tool_call,
            {"read_only_network"},
            caller_domain="readme_presentation",
        )
        accepted = dispatch_tool_call(
            tool_call,
            {"read_only_network"},
            caller_domain=INDEPENDENT_VERIFICATION,
            extra_kwargs={
                "fact_graph": graph.model_dump(mode="json"),
                "composition_output": composition.model_dump(mode="json"),
                "blind_client": blind,
                "fidelity_client": fidelity,
            },
        )

    assert denied.outcome == "rejected_domain_denied"
    assert accepted.outcome == "executed", accepted.error
    assert accepted.result is not None
    assert accepted.result["review"]["verdict"] == "TRUSTED_TRANSFORM_APPROVED"


def test_review_fails_closed_without_active_call_accounting(tmp_path, monkeypatch):
    graph, composition, _ = _composition(tmp_path)
    blind, fidelity = _review_clients(graph)
    monkeypatch.setattr(
        "readme_agent.specialists.trusted_transform_review.current_llm_accounting_summary",
        lambda: LlmAccountingSummaryV1(status="UNKNOWN_LEGACY"),
    )

    with pytest.raises(RuntimeError, match="active per-repository LLM call accounting"):
        run_trusted_transform_review(
            graph,
            SOURCE,
            composition,
            blind_client=blind,
            fidelity_client=fidelity,
        )


def test_identical_accepted_review_records_no_duplicate_lifecycle_event(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-lifecycle-no-op")
    blind, fidelity = _review_clients(graph)
    execution = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    )
    backend = FakeStateBackend()
    record_repository_snapshot(
        backend,
        ORG_REPO,
        source_revision=graph.source_revision,
        evidence_refs=["snapshot"],
    )
    record_repository_profile(
        backend,
        ORG_REPO,
        source_revision=graph.source_revision,
        evidence_refs=["profile"],
    )
    switch_content_assurance(
        backend,
        ORG_REPO,
        "trusted_inherited",
        observed_by="test",
        reason="exercise trusted review persistence",
    )
    for status in (
        "TRUSTED_FACTS_EXTRACTING",
        "TRUSTED_FACTS_EXTRACTED",
        "TRUSTED_PLAN_READY",
        "TRUSTED_CANDIDATE_GENERATED",
    ):
        transition_trusted_readme_poc_status(
            backend,
            ORG_REPO,
            status,
            observed_by="test",
            reason="advance trusted fixture",
            source_revision=graph.source_revision,
            facts_hash=graph.canonical_hash(),
            candidate_hash=(
                composition.candidate_sha256 if status == "TRUSTED_CANDIDATE_GENERATED" else None
            ),
        )

    first = record_trusted_review_execution(
        backend,
        graph,
        composition,
        execution,
        evidence_refs=["trusted-review.json"],
    )
    state_version = backend.load(ORG_REPO).state_version
    second = record_trusted_review_execution(
        backend,
        graph,
        composition,
        execution,
        evidence_refs=["trusted-review.json"],
    )

    assert first.status == "TRUSTED_TRANSFORM_APPROVED"
    assert second == first
    assert backend.load(ORG_REPO).state_version == state_version
    assert [item.to_status for item in second.history[-3:]] == [
        "TRUSTED_DETERMINISTIC_VALIDATED",
        "TRUSTED_REVIEWING",
        "TRUSTED_TRANSFORM_APPROVED",
    ]
