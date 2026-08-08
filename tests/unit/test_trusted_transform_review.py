"""Independent quality and inheritance-fidelity review for trusted transforms."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from readme_agent import env
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.errors import LLMError, LLMInfrastructureError, StateBackendError
from readme_agent.facts.trusted_readme_extraction import (
    bind_configured_standards,
    configured_standard_addition,
    extract_trusted_readme_fact_graph,
)
from readme_agent.gitsafety._git import run_git
from readme_agent.llm import prompt_registry
from readme_agent.llm.analysis_client import AnalysisResult, FixtureAnalysisClient
from readme_agent.llm.call_ledger import (
    bind_llm_repository_revision,
    current_llm_accounting_summary,
    start_llm_call_accounting,
)
from readme_agent.llm.call_schema import LlmAccountingSummaryV1
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.llm.verification_prompts import (
    build_blind_quality_review_messages,
    build_trusted_fidelity_review_messages,
)
from readme_agent.llm.verifier_client import FixtureForcedToolClient, ForcedToolResult
from readme_agent.readme.trusted_composition import compose_trusted_readme
from readme_agent.readme.trusted_exact_repair import apply_grounded_exact_removal
from readme_agent.registry.loader import load_products
from readme_agent.repository_snapshot import capture_repository_snapshot, repository_snapshot_scope
from readme_agent.specialists import trusted_fidelity_cache
from readme_agent.specialists import trusted_fidelity_validation as fidelity_validation
from readme_agent.specialists.review_finding_grounding import (
    GroundedReviewFindingV1,
    validate_review_findings,
)
from readme_agent.specialists.trusted_fidelity_context import build_trusted_fidelity_context
from readme_agent.specialists.trusted_fidelity_delta import (
    derive_fidelity_after_exact_removal,
)
from readme_agent.specialists.trusted_fidelity_execution import (
    _render_review_candidates,
    partition_fidelity_fact_ids,
    run_batched_trusted_fidelity_review,
)
from readme_agent.specialists.trusted_fidelity_validation import (
    normalize_trusted_fidelity_output,
    validate_trusted_fidelity_result,
)
from readme_agent.specialists.trusted_transform_review import run_trusted_transform_review
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedFidelityReviewResultV1,
    TrustedReviewActorIdentityV1,
    TrustedReviewCacheIdentityV1,
    TrustedReviewExecutionV1,
    TrustedReviewRoleRecordV1,
    TrustedTransformReviewV1,
)
from readme_agent.specialists.trusted_transform_review_repair import (
    run_trusted_review_with_repair,
)
from readme_agent.state.readme_poc_lifecycle import (
    record_repository_profile,
    record_repository_snapshot,
    switch_content_assurance,
    transition_trusted_readme_poc_status,
)
from readme_agent.supervisor.trusted_readme_pipeline import run_trusted_readme_pipeline
from readme_agent.supervisor.trusted_readme_stage_execution import (
    live_trusted_review_clients,
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
    source_text: str = SOURCE,
):
    root = tmp_path / root_name
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Trusted Review Test")
    _git(root, "config", "user.email", "trusted-review@example.invalid")
    (root / "README.md").write_text(source_text, encoding="utf-8", newline="")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "seed")
    entry = next(item for item in load_products() if item.org_repo == ORG_REPO)
    snapshot = capture_repository_snapshot(entry, root)
    graph = extract_trusted_readme_fact_graph(snapshot)
    graph = bind_configured_standards(
        graph,
        [
            configured_standard_addition(
                standard_id,
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"authorized-transform-test",
            )
            for standard_id in (
                "readme.no_comments",
                "readme.contextual_links",
                "readme.enterprise_edition_terminology",
            )
        ],
    )
    fact_ids = [fact.fact_id for fact in graph.inherited_facts]
    composition = compose_trusted_readme(
        graph,
        source_text,
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


def _accepted_fidelity_record(
    graph,
    composition,
    *,
    candidate_quote_overrides: dict[str, str] | None = None,
) -> TrustedReviewRoleRecordV1:
    overrides = candidate_quote_overrides or {}
    result = TrustedFidelityReviewResultV1(
        verdict="ACCEPT",
        reasoning="Every inherited source unit is represented.",
        source_checks=tuple(
            {
                "fact_id": fact.fact_id,
                "outcome": "preserved_or_represented",
                "source_quote": fact.value,
                "candidate_quote": overrides.get(fact.fact_id, fact.value),
                "section": "source",
                "required_repair": "",
            }
            for fact in graph.inherited_facts
        ),
    )
    return TrustedReviewRoleRecordV1(
        identity=TrustedReviewActorIdentityV1(
            actor_id="fixture-fidelity-reviewer",
            role="inheritance_fidelity_reviewer",
            prompt_id="trusted_readme_fidelity_review",
            prompt_sha256="1" * 64,
            model_route="fixture-fidelity",
        ),
        candidate_sha256=composition.candidate_sha256,
        input_sha256="2" * 64,
        verdict=result.verdict,
        result=result.model_dump(mode="json"),
    )


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


def _blind_remove(quote: str) -> dict:
    return {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "One unsupported promotional paragraph must be removed.",
        "failed_criteria": ["hierarchy"],
        "sections_affected": ["README"],
        "required_repair": "Remove the unsupported promotional paragraph.",
        "findings": [
            {
                "finding_id": "quality.unsupported-promotion",
                "kind": "quality",
                "criterion": "hierarchy",
                "section": "README",
                "claim": "The final paragraph is unsupported promotional prose.",
                "quoted_candidate_span": quote,
                "disposition": "requires_repair",
                "fact_id": None,
                "evidence_excerpt": None,
                "evidence_location": None,
                "expected_polarity": None,
                "observed_polarity": None,
                "polarity_result": "not_applicable",
                "required_repair": "Remove the unsupported promotional paragraph.",
            }
        ],
    }


def test_blind_finding_ids_are_normalized_before_validation(tmp_path) -> None:
    graph, composition, _ = _composition(tmp_path)
    blind = _blind_accept()
    blind["findings"][0]["finding_id"] = "Header-Badge-Nav-EE"
    blind_client, fidelity_client = _review_clients(graph, blind=blind)
    _start_accounting(graph, "trusted-review-normalized-finding-id")

    execution = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind_client,
        fidelity_client=fidelity_client,
    )

    assert execution.review.blind_quality.verdict == "ACCEPT"
    assert (
        execution.review.blind_quality.result["findings"][0]["finding_id"] == "header-badge-nav-ee"
    )


def test_fidelity_accepts_only_authorized_source_transformations(tmp_path) -> None:
    source = (
        "# Widget\n\n"
        "[Product](https://products.aspose.com/widget) — commercial On-Premise edition.\n\n"
        "```python\n# Explain\nrun()\n```\n"
    )
    root = tmp_path / "authorized-transform"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Trusted Review Test")
    _git(root, "config", "user.email", "trusted-review@example.invalid")
    (root / "README.md").write_text(source, encoding="utf-8", newline="")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "seed")
    entry = next(item for item in load_products() if item.org_repo == ORG_REPO)
    snapshot = capture_repository_snapshot(entry, root)
    graph = extract_trusted_readme_fact_graph(snapshot)
    graph = bind_configured_standards(
        graph,
        [
            configured_standard_addition(
                standard_id,
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"authorized-transform-test",
            )
            for standard_id in (
                "readme.no_comments",
                "readme.contextual_links",
                "readme.enterprise_edition_terminology",
            )
        ],
    )
    candidate = "# Widget\n\nEnterprise Edition — Enterprise Edition.\n\n```python\n\nrun()\n```\n"
    checks = [
        {
            "fact_id": fact.fact_id,
            "outcome": "lost_or_distorted",
            "source_quote": fact.value,
            "candidate_quote": "",
            "section": "README",
            "required_repair": "Restore the source.",
        }
        for fact in graph.inherited_facts
    ]
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "Links, terminology, and comments changed.",
        "source_checks": checks,
        "unsupported_additions": [
            {
                "finding_id": "enterprise",
                "section": "README",
                "quoted_candidate_span": "Enterprise Edition — Enterprise Edition.",
                "reason": "The source used legacy terminology.",
                "required_repair": "Restore the legacy terminology.",
            }
        ],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["README"],
        "required_repair": "Restore the source.",
    }

    normalized = normalize_trusted_fidelity_output(value, graph=graph, candidate_text=candidate)

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["unsupported_additions"] == []
    outcomes = {item["fact_id"]: item["outcome"] for item in normalized["source_checks"]}
    for fact in graph.inherited_facts:
        if fact.material_kind in {"heading", "paragraph", "code"}:
            assert outcomes[fact.fact_id] == "preserved_or_represented"

    unconfigured = normalize_trusted_fidelity_output(
        value,
        graph=graph.model_copy(update={"configured_standards": ()}),
        candidate_text=candidate,
    )
    assert unconfigured["verdict"] == "REJECT_REPAIRABLE"


def test_fidelity_accepts_governed_paragraph_consolidation(tmp_path) -> None:
    source = (
        "# Widget\n\n"
        "This repository provides a focused Python API.\n\n"
        "It is inspired by "
        "[Aspose.Widget for .NET](https://products.aspose.com/widget/net/).\n"
    )
    candidate = (
        "# Widget\n\n"
        "This repository provides a focused practical Python API. It is inspired by "
        "Aspose.Widget Enterprise Edition for .NET.\n"
    )
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate=candidate,
        root_name="consolidated-prose",
    )
    graph = bind_configured_standards(
        graph,
        [
            configured_standard_addition(
                "readme.contextual_links",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"consolidated-prose-links",
            ),
            configured_standard_addition(
                "readme.enterprise_edition_terminology",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"consolidated-prose-enterprise",
            ),
        ],
    )
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The source paragraphs were consolidated.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "lost_or_distorted",
                "source_quote": fact.value,
                "candidate_quote": "",
                "section": "Opening",
                "required_repair": "Restore the source paragraph.",
            }
            for fact in graph.inherited_facts
        ],
        "unsupported_additions": [],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["Opening"],
        "required_repair": "Restore the source paragraphs.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert all(
        item["outcome"] == "preserved_or_represented" for item in normalized["source_checks"]
    )


def test_fidelity_accepts_conservative_no_emoji_value_proposition_rewrite(tmp_path) -> None:
    source = (
        "# Widget\n\n"
        "\u2705 **Official Aspose project** — **100% free & open-source**. "
        "Provides an Aspose.Note-compatible Python API for working with OneNote `.one` files.\n"
    )
    candidate_quote = (
        "This repository provides a 100% free and open-source Python library for reading "
        "Microsoft OneNote (.one) files. It offers a familiar API surface inspired by "
        "Aspose.Note for .NET, backed by a built-in MS-ONE/OneStore parser."
    )
    candidate = f"# Widget\n\n{candidate_quote}\n"
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate=candidate,
        root_name="no-emoji-value-proposition",
    )
    graph = bind_configured_standards(
        graph,
        [
            configured_standard_addition(
                "readme.header",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"global-no-emoji",
                parameters={"emoji_policy": "none"},
            )
        ],
    )
    paragraph = next(fact for fact in graph.inherited_facts if fact.material_kind == "paragraph")
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The paragraph was rewritten.",
        "source_checks": [
            {
                "fact_id": paragraph.fact_id,
                "outcome": "lost_or_distorted",
                "source_quote": paragraph.value,
                "candidate_quote": "",
                "section": "readme.value_proposition",
                "required_repair": "Restore exact phrasing and emoji.",
            }
        ],
        "unsupported_additions": [],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["readme.value_proposition"],
        "required_repair": "Restore exact phrasing and emoji.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["source_checks"][0]["outcome"] == "preserved_or_represented"


def test_fidelity_dismisses_structure_owned_by_a_valid_global_brand_contract(
    tmp_path,
    monkeypatch,
) -> None:
    source = "# Widget\n\nSource paragraph.\n"
    candidate = "# Widget\n\nNavigation block\n\nMermaid block\n"
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate=candidate,
        root_name="global-brand-owned-structure",
    )
    graph = bind_configured_standards(
        graph,
        [
            configured_standard_addition(
                "readme.header",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"global-brand-contract",
                parameters={"brand_contract_version": "repository-presentation-brand-v1"},
            )
        ],
    )
    monkeypatch.setattr(
        fidelity_validation,
        "validate_trusted_portfolio_brand",
        lambda candidate_text, candidate_graph: None,
    )
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The reviewer treated configured structure as unsupported.",
        "source_checks": [],
        "unsupported_additions": [
            {
                "finding_id": "navigation",
                "section": "readme.navigation",
                "quoted_candidate_span": "Navigation block",
                "reason": "Navigation is an addition.",
                "required_repair": "Remove Navigation.",
            },
            {
                "finding_id": "mermaid",
                "section": "readme.at_a_glance",
                "quoted_candidate_span": "Mermaid block",
                "reason": "Mermaid is an addition.",
                "required_repair": "Remove Mermaid.",
            },
        ],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["readme.navigation", "readme.at_a_glance"],
        "required_repair": "Remove configured structure.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["unsupported_additions"] == []


def test_fidelity_accepts_navigation_composed_from_source_and_brand_headings(tmp_path) -> None:
    source = "# Widget\n\n## Architecture\n\nDetails.\n\n## License\n\nMIT.\n"
    navigation = (
        "- [Architecture](#architecture)\n"
        "- [License](#license)\n"
        "- [Scope and limitations](#scope-and-limitations)"
    )
    candidate = f"{source}\n## Navigation\n\n{navigation}\n"
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate=candidate,
        root_name="composed-navigation",
    )
    graph = bind_configured_standards(
        graph,
        [
            configured_standard_addition(
                "readme.header",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"composed-navigation-header",
                parameters={
                    "brand_contract_version": "repository-presentation-brand-v1",
                    "required_h2_prefix": ["Navigation"],
                },
            ),
            configured_standard_addition(
                "readme.navigation",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"composed-navigation-standard",
            ),
        ],
    )
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The navigation block was treated as one addition.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "preserved_or_represented",
                "source_quote": fact.value,
                "candidate_quote": fact.value,
                "section": "README",
                "required_repair": "",
            }
            for fact in graph.inherited_facts
        ],
        "unsupported_additions": [
            {
                "finding_id": "composed-navigation",
                "section": "Navigation",
                "quoted_candidate_span": navigation,
                "reason": "Multiple source headings were linked together.",
                "required_repair": "Remove the navigation links.",
            }
        ],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["Navigation"],
        "required_repair": "Remove the navigation links.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["unsupported_additions"] == []


def test_fidelity_accepts_governed_promotional_blockquote_relocation(tmp_path) -> None:
    source = (
        "# Aspose.3D FOSS\n\n"
        "> **Aspose.3D FOSS** lives on "
        "[aspose.org](https://products.aspose.org/3d/python/). "
        "The commercial edition, "
        "[Aspose.3D for Python via .NET]"
        "(https://products.aspose.com/3d/python-net/), "
        "is available on [aspose.com](https://products.aspose.com/3d/).\n"
    )
    candidate = (
        "# Aspose.3D FOSS\n\n"
        "Aspose.3D for Python via .NET is the Enterprise Edition.\n\n"
        "## Resources\n\n"
        "Aspose.3D FOSS resources are maintained on aspose.org; "
        "Enterprise resources are on aspose.com.\n"
    )
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate=candidate,
        root_name="blockquote-source",
    )
    fact = next(item for item in graph.inherited_facts if item.material_kind == "blockquote")
    graph = bind_configured_standards(
        graph.model_copy(update={"inherited_facts": (fact,)}),
        [
            configured_standard_addition(
                "readme.contextual_links",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"blockquote-relocation",
                parameters={"forbid_blockquotes": True},
            ),
            configured_standard_addition(
                "readme.enterprise_edition_terminology",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"enterprise-terminology",
            ),
        ],
    )
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The promotional callout was removed.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "lost_or_distorted",
                "source_quote": fact.value,
                "candidate_quote": "",
                "section": "Opening",
                "required_repair": "Restore the callout.",
            }
        ],
        "unsupported_additions": [],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["Opening"],
        "required_repair": "Restore the callout.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["source_checks"][0]["outcome"] == "preserved_or_represented"


def test_fidelity_navigation_addition_is_derived_from_source_heading(tmp_path) -> None:
    source = "# Widget\n\n## Architecture\n\nDetails.\n"
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate=source,
        root_name="navigation-source",
    )
    fact = next(item for item in graph.inherited_facts if item.value == "## Architecture\n")
    graph = bind_configured_standards(
        graph.model_copy(update={"inherited_facts": (fact,)}),
        [
            configured_standard_addition(
                "readme.navigation",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"navigation-standard",
            )
        ],
    )
    candidate = "# Widget\n\n## Navigation\n\n- [Architecture](#architecture)\n\n## Architecture\n"
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The navigation entry is unsupported.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "preserved_or_represented",
                "source_quote": fact.value,
                "candidate_quote": "## Architecture\n",
                "section": "Architecture",
                "required_repair": "",
            }
        ],
        "unsupported_additions": [
            {
                "finding_id": "navigation-architecture",
                "section": "Navigation",
                "quoted_candidate_span": "- [Architecture](#architecture)",
                "reason": "No source exists.",
                "required_repair": "Remove the entry.",
            }
        ],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["Navigation"],
        "required_repair": "Remove the entry.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["unsupported_additions"] == []


def test_fidelity_navigation_addition_can_come_from_configured_required_label(tmp_path) -> None:
    source = "# Widget\n\nUseful product detail.\n"
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate=source,
        root_name="configured-navigation",
    )
    fact = next(item for item in graph.inherited_facts if item.material_kind == "paragraph")
    graph = bind_configured_standards(
        graph.model_copy(update={"inherited_facts": (fact,)}),
        [
            configured_standard_addition(
                "readme.navigation",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"configured-navigation-label",
                parameters={"required_labels": ["At a glance"]},
            ),
            configured_standard_addition(
                "readme.at_a_glance_mermaid",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"configured-at-a-glance",
                parameters={"heading": "At a glance", "diagram_kind": "flowchart"},
            ),
        ],
    )
    candidate = (
        "# Widget\n\n"
        "## Navigation\n\n"
        "- [At a glance](#at-a-glance)\n\n"
        "## At a glance\n\n"
        "Useful product detail.\n"
    )
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The configured navigation entry was called unsupported.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "preserved_or_represented",
                "source_quote": fact.value,
                "candidate_quote": fact.value,
                "section": "At a glance",
                "required_repair": "",
            }
        ],
        "unsupported_additions": [
            {
                "finding_id": "navigation-at-a-glance",
                "section": "Navigation",
                "quoted_candidate_span": "- [At a glance](#at-a-glance)",
                "reason": "No inherited heading exists.",
                "required_repair": "Remove the configured navigation entry.",
            }
        ],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["Navigation"],
        "required_repair": "Remove the configured navigation entry.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["unsupported_additions"] == []


def test_fidelity_accepts_configured_badge_variant_and_row_consolidation(tmp_path) -> None:
    source = (
        "# Widget\n\n"
        "[![PyPI version](https://badge.example/pypi.svg)](https://pypi.org/project/widget/)\n"
        "[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]"
        "(https://opensource.org/licenses/MIT)\n"
    )
    candidate = (
        "# Widget\n\n"
        "[![PyPI version](https://badge.example/pypi.svg)]"
        "(https://pypi.org/project/widget/) "
        "[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)]"
        "(https://opensource.org/licenses/MIT)\n"
    )
    root = tmp_path / "configured-badges"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Trusted Review Test")
    _git(root, "config", "user.email", "trusted-review@example.invalid")
    (root / "README.md").write_text(source, encoding="utf-8", newline="")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "seed")
    entry = next(item for item in load_products() if item.org_repo == ORG_REPO)
    snapshot = capture_repository_snapshot(entry, root)
    graph = extract_trusted_readme_fact_graph(snapshot)
    fact = next(item for item in graph.inherited_facts if "PyPI version" in item.value)
    graph = bind_configured_standards(
        graph.model_copy(update={"inherited_facts": (fact,)}),
        [
            configured_standard_addition(
                "readme.badges",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"configured-badge-variant",
                parameters={
                    "required_fragments": [
                        "![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)"
                    ]
                },
            )
        ],
    )
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "Badge layout and color changed.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "lost_or_distorted",
                "source_quote": fact.value,
                "candidate_quote": candidate.split("\n\n", maxsplit=1)[1],
                "section": "Header",
                "required_repair": "Restore the original badge lines and color.",
            }
        ],
        "unsupported_additions": [],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["Header"],
        "required_repair": "Restore the original badge lines and color.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["source_checks"][0]["outcome"] == "preserved_or_represented"
    assert normalized["source_checks"][0]["required_repair"] == ""


def test_fidelity_accepts_configured_core_license_badge_in_place_of_source_link(
    tmp_path,
) -> None:
    source = (
        "# Widget\n\n"
        "[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)\n"
    )
    core_license = "![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)"
    candidate = f"# Widget\n\n{core_license}\n"
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate=source,
        root_name="configured-core-license",
    )
    fact = next(item for item in graph.inherited_facts if "License: MIT" in item.value)
    graph = bind_configured_standards(
        graph.model_copy(update={"inherited_facts": (fact,)}),
        [
            configured_standard_addition(
                "readme.badges",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"configured-core-license",
                parameters={"required_fragments": [core_license]},
            )
        ],
    )
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The linked source license badge changed.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "lost_or_distorted",
                "source_quote": fact.value,
                "candidate_quote": "",
                "section": "Header",
                "required_repair": "Restore the linked source license badge.",
            }
        ],
        "unsupported_additions": [],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["Header"],
        "required_repair": "Restore the linked source license badge.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["source_checks"][0]["outcome"] == "preserved_or_represented"


def test_fidelity_accepts_configured_removal_of_decorative_heading_emoji(tmp_path) -> None:
    source = "# Widget\n\n## 🚀 Quick start\n\nRun it.\n"
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate="# Widget\n\n## Quick start\n\nRun it.\n",
        root_name="heading-style",
    )
    fact = next(item for item in graph.inherited_facts if item.material_kind == "heading")
    graph = bind_configured_standards(
        graph.model_copy(update={"inherited_facts": (fact,)}),
        [
            configured_standard_addition(
                "readme.header",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"repository-presentation-brand-v1",
                parameters={
                    "brand_contract_version": "repository-presentation-brand-v1",
                    "emoji_policy": "none",
                },
            )
        ],
    )
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The heading lost its decorative marker.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "lost_or_distorted",
                "source_quote": fact.value,
                "candidate_quote": "## Quick start",
                "section": "Quick start",
                "required_repair": "Restore the decorative heading marker.",
            }
        ],
        "unsupported_additions": [],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["Quick start"],
        "required_repair": "Restore the decorative heading marker.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text="# Widget\n\n## Quick start\n\nRun it.\n",
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["source_checks"][0]["outcome"] == "preserved_or_represented"


def test_fidelity_accepts_configured_removal_of_emojis_from_source_prose(tmp_path) -> None:
    source = "# Widget\n\nUse Widget to convert files quickly. ✨\n"
    candidate = "# Widget\n\nUse Widget to convert files quickly.\n"
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate=candidate,
        root_name="candidate-wide-emoji-policy",
    )
    fact = next(item for item in graph.inherited_facts if item.material_kind == "paragraph")
    graph = bind_configured_standards(
        graph.model_copy(update={"inherited_facts": (fact,)}),
        [
            configured_standard_addition(
                "readme.header",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"repository-presentation-brand-v1-no-emojis",
                parameters={
                    "brand_contract_version": "repository-presentation-brand-v1",
                    "emoji_policy": "none",
                },
            )
        ],
    )
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The source emoji was removed.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "lost_or_distorted",
                "source_quote": fact.value,
                "candidate_quote": candidate.splitlines()[2],
                "section": "Opening",
                "required_repair": "Restore the source emoji.",
            }
        ],
        "unsupported_additions": [],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["Opening"],
        "required_repair": "Restore the source emoji.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["source_checks"][0]["outcome"] == "preserved_or_represented"


def test_fidelity_accepts_the_configured_features_heading_alias(tmp_path) -> None:
    source = "# Widget\n\n## ✨ Features\n\n- Read files.\n"
    candidate = "# Widget\n\n## Key capabilities\n\n- Read files.\n"
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate=candidate,
        root_name="heading-alias",
    )
    fact = next(
        item
        for item in graph.inherited_facts
        if item.material_kind == "heading" and "Features" in item.value
    )
    graph = bind_configured_standards(
        graph.model_copy(update={"inherited_facts": (fact,)}),
        [
            configured_standard_addition(
                "readme.header",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"trusted-heading-alias",
                parameters={
                    "brand_contract_version": "repository-presentation-brand-v1",
                    "heading_aliases": {"Features": "Key capabilities"},
                },
            )
        ],
    )
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The Features heading changed.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "lost_or_distorted",
                "source_quote": fact.value,
                "candidate_quote": "",
                "section": "Key capabilities",
                "required_repair": "Restore the Features heading.",
            }
        ],
        "unsupported_additions": [],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["Key capabilities"],
        "required_repair": "Restore the Features heading.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["source_checks"][0]["outcome"] == "preserved_or_represented"


def test_fidelity_accepts_configured_product_specific_examples_suffix(tmp_path) -> None:
    source = "# Widget\n\n## MS OneNote Examples\n\nRun it.\n"
    candidate = "# Widget\n\n## Examples\n\nRun it.\n"
    graph, _, _ = _composition(
        tmp_path,
        source_text=source,
        candidate=candidate,
        root_name="heading-suffix-alias",
    )
    fact = next(
        item
        for item in graph.inherited_facts
        if item.material_kind == "heading" and "Examples" in item.value
    )
    graph = bind_configured_standards(
        graph.model_copy(update={"inherited_facts": (fact,)}),
        [
            configured_standard_addition(
                "readme.header",
                configuration_source="config/policies/test.yml",
                configuration_bytes=b"trusted-heading-suffix-alias",
                parameters={
                    "brand_contract_version": "repository-presentation-brand-v1",
                    "heading_suffix_aliases": {"examples": "Examples"},
                },
            )
        ],
    )
    value = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The product-specific prefix was simplified.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "lost_or_distorted",
                "source_quote": fact.value,
                "candidate_quote": "## Examples",
                "section": "Examples",
                "required_repair": "Restore the product-specific prefix.",
            }
        ],
        "unsupported_additions": [],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["Examples"],
        "required_repair": "Restore the product-specific prefix.",
    }

    normalized = normalize_trusted_fidelity_output(
        value,
        graph=graph,
        candidate_text=candidate,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["source_checks"][0]["outcome"] == "preserved_or_represented"


def test_blind_grounding_rejects_a_missing_h1_premise_when_h1_is_visible() -> None:
    candidate = "# Widget\n\nCore content.\n"
    finding = GroundedReviewFindingV1(
        finding_id="quality.missing-h1",
        kind="quality",
        criterion="hierarchy",
        section="Header",
        claim="The README is missing an H1.",
        quoted_candidate_span="# Widget",
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Add the H1.",
    )

    grounding = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.header",
                    "parameters": {"brand_contract_version": "repository-presentation-brand-v1"},
                }
            ]
        },
    )

    assert not grounding.valid
    assert grounding.errors == ["quality.missing-h1:H1 premise contradicts visible candidate"]


def test_blind_grounding_rejects_required_blank_line_premise_when_quote_has_it() -> None:
    candidate = "## At a glance\n\n```mermaid\nflowchart LR\n```\n"
    finding = GroundedReviewFindingV1(
        finding_id="quality.at-a-glance-spacing",
        kind="quality",
        criterion="hierarchy",
        section="At a glance",
        claim=("The At a glance section is missing the required blank line after the heading."),
        quoted_candidate_span="## At a glance\n\n```mermaid",
        disposition="requires_repair",
        polarity_result="not_applicable",
        required_repair="Insert a blank line after the heading before the Mermaid block.",
    )

    grounding = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=(finding,),
    )

    assert not grounding.valid
    assert grounding.errors == [
        "quality.at-a-glance-spacing:blank-line premise contradicts quoted span"
    ]


def test_blind_grounding_rejects_header_and_enterprise_premises_contradicted_by_contract() -> None:
    core_row = (
        "![Platform: Python](https://img.shields.io/badge/Platform-Python-3776AB.svg) "
        "![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)"
    )
    enterprise_url = "https://products.aspose.com/note/"
    candidate = (
        f"# Widget\n\n{core_row}\n\n"
        "[![Build](https://example.test/build.svg)](https://example.test/build)\n\n"
        "Widget provides a focused API for document workflows.\n\n"
        "## At a glance\n\n"
        "```mermaid\n"
        "flowchart LR\n"
        "  subgraph Inputs\n"
        '    I1["Widget document file"]\n'
        "  end\n"
        '  PRODUCT["Widget API"]\n'
        "  subgraph Capabilities\n"
        '    C1["Parse document structure"]\n'
        '    C2["Extract embedded content"]\n'
        "  end\n"
        "  subgraph Outputs\n"
        '    O1["Structured document content"]\n'
        "  end\n"
        "  I1 --> PRODUCT\n"
        "  PRODUCT --> C1\n"
        "  PRODUCT --> C2\n"
        "  C1 --> O1\n"
        "```\n\n"
        "## Navigation\n\n"
        "- [At a glance](#at-a-glance)\n"
        "- [Key capabilities](#key-capabilities)\n"
        "- [Installation](#installation)\n"
        "- [Quick start](#quick-start)\n"
        "- [License](#license)\n\n"
        "## Scope and limitations\n\n"
        "For advanced requirements, evaluate the "
        f"[Widget Enterprise Edition]({enterprise_url}).\n\n"
        "## Build and Test (Developers)\n"
    )
    findings = [
        GroundedReviewFindingV1(
            finding_id="quality.h1-emoji",
            kind="quality",
            criterion="clarity",
            section="Header",
            claim="H1 title contains emoji.",
            quoted_candidate_span="# Widget",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Remove emoji from the H1.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.header-spacing",
            kind="quality",
            criterion="hierarchy",
            section="Header",
            claim="Missing blank line between H1 title and badge row.",
            quoted_candidate_span="# Widget",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Insert a blank line after the H1.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.badge-duplication",
            kind="quality",
            criterion="visible_duplication",
            section="Header",
            claim="Badge row appears twice.",
            quoted_candidate_span=core_row,
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Remove the duplicated badge row.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.extra-badges",
            kind="quality",
            criterion="clarity",
            section="Header",
            claim="Header contains an extra CI badge row.",
            quoted_candidate_span="[![Build](https://example.test/build.svg)]",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Keep only the two required core badges.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.opening-visual-duplication",
            kind="quality",
            criterion="clarity",
            section="Header",
            claim=(
                "The first paragraph after badges duplicates the value proposition already "
                "present in the At a glance section."
            ),
            quoted_candidate_span="Widget provides a focused API for document workflows.",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Remove the paragraph or merge it into At a glance.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.enterprise-link",
            kind="quality",
            criterion="promotional_balance",
            section="Resources",
            claim="Missing required Enterprise Edition link.",
            quoted_candidate_span="Widget Enterprise Edition",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Replace placeholder text with the required Enterprise Edition link.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.navigation-labels",
            kind="quality",
            criterion="navigation",
            section="Navigation",
            claim="Navigation includes sections not in the required set.",
            quoted_candidate_span="- [License](#license)",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Trim the Navigation section to the required labels.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.navigation-duplicate",
            kind="quality",
            criterion="visible_duplication",
            section="Navigation",
            claim="Navigation section appears twice.",
            quoted_candidate_span="## Navigation",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Remove the duplicate Navigation section.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.mermaid-contract",
            kind="quality",
            criterion="markdown_integrity",
            section="At a glance",
            claim="Mermaid exceeds the max_nodes limit and must be rendered without subgraphs.",
            quoted_candidate_span="```mermaid",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Reduce the Mermaid nodes and remove subgraphs.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.mermaid-detail",
            kind="quality",
            criterion="hierarchy",
            section="At a glance",
            claim="Mermaid PRODUCT node label is generic and not product-specific.",
            quoted_candidate_span="flowchart LR",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair=(
                "Use short labels and show a clear inputs->product->capabilities->outputs flow."
            ),
        ),
        GroundedReviewFindingV1(
            finding_id="quality.bare-enterprise-url",
            kind="quality",
            criterion="promotional_balance",
            section="Scope and limitations",
            claim="Enterprise Edition appears as a link label instead of the configured URL.",
            quoted_candidate_span="Widget Enterprise Edition",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Replace the link label with the configured URL.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.enterprise-wrong-section",
            kind="quality",
            criterion="promotional_balance",
            section="Quick start",
            claim="Enterprise Edition link appears in the middle of Quick start.",
            quoted_candidate_span="Widget Enterprise Edition",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Move the Enterprise Edition link below the opening.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.enterprise-duplicate-link",
            kind="quality",
            criterion="promotional_balance",
            section="Other platforms",
            claim="Enterprise Edition labels appear without the required Enterprise Edition link.",
            quoted_candidate_span="Widget Enterprise Edition",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Add the Enterprise Edition link to each label.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.heading-alias",
            kind="quality",
            criterion="hierarchy",
            section="Scope and limitations",
            claim="This heading should be renamed according to the heading_alias.",
            quoted_candidate_span="## Scope and limitations",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Rename this section to Key capabilities.",
        ),
        GroundedReviewFindingV1(
            finding_id="quality.heading-parentheses",
            kind="quality",
            criterion="markdown_integrity",
            section="Build and Test (Developers)",
            claim="The heading contains parentheses, which are not permitted.",
            quoted_candidate_span="## Build and Test (Developers)",
            disposition="requires_repair",
            polarity_result="not_applicable",
            required_repair="Remove the parenthetical phrase from the heading.",
        ),
    ]

    grounding = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=findings,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.header",
                    "parameters": {
                        "brand_contract_version": "repository-presentation-brand-v1",
                        "heading_style": "sentence_case_without_emoji",
                        "required_h2_prefix": [
                            "At a glance",
                            "Navigation",
                            "Key capabilities",
                            "Installation",
                            "Quick start",
                        ],
                        "heading_aliases": {"Features": "Key capabilities"},
                    },
                },
                {
                    "standard_id": "readme.badges",
                    "parameters": {
                        "required_core_row": core_row,
                        "allow_inherited_badges_after_core": True,
                    },
                },
                {
                    "standard_id": "readme.contextual_links",
                    "parameters": {
                        "required_enterprise_url": enterprise_url,
                        "required_aspose_com_occurrences": 1,
                    },
                },
                {
                    "standard_id": "readme.navigation",
                    "parameters": {
                        "required_labels": [
                            "At a glance",
                            "Key capabilities",
                            "Installation",
                            "Quick start",
                        ]
                    },
                },
                {
                    "standard_id": "readme.at_a_glance_mermaid",
                    "parameters": {
                        "visual_grammar": "inputs-product-capabilities-outputs",
                        "max_nodes": 12,
                        "max_label_characters": 52,
                    },
                },
            ]
        },
    )

    assert not grounding.valid
    assert grounding.errors == [
        "quality.h1-emoji:H1 emoji premise contradicts visible candidate",
        "quality.header-spacing:header-spacing premise contradicts configured header",
        "quality.badge-duplication:badge-duplication premise contradicts configured header",
        "quality.extra-badges:inherited-badge premise contradicts configured header",
        "quality.opening-visual-duplication:"
        "opening-versus-visual premise contradicts global contract",
        "quality.enterprise-link:quoted span is outside the named candidate section",
        "quality.enterprise-link:Enterprise link premise contradicts configured candidate",
        "quality.navigation-labels:navigation prefix-only premise is unconfigured",
        "quality.navigation-duplicate:heading-only quote cannot prove the claimed section content",
        "quality.navigation-duplicate:navigation-duplication premise contradicts candidate",
        "quality.navigation-duplicate:"
        "mechanical premise lacks required typed check document.duplicate_h2_headings",
        "quality.mermaid-contract:Mermaid subgraph prohibition is unconfigured",
        "quality.mermaid-contract:Mermaid node-count premise contradicts candidate",
        "quality.mermaid-detail:Mermaid-product-label premise contradicts visible candidate label",
        "quality.bare-enterprise-url:bare-URL premise contradicts configured candidate",
        "quality.enterprise-wrong-section:quoted span is outside the named candidate section",
        "quality.enterprise-wrong-section:Enterprise link placement contradicts configured scope",
        "quality.enterprise-duplicate-link:quoted span is outside the named candidate section",
        "quality.enterprise-duplicate-link:"
        "Enterprise link premise contradicts configured candidate",
        "quality.heading-alias:heading-alias premise is unconfigured",
    ]


def test_fidelity_discards_an_unsupported_addition_with_an_absent_candidate_quote(
    tmp_path,
) -> None:
    graph, composition, _ = _composition(tmp_path)
    fact = graph.inherited_facts[0]
    normalized = normalize_trusted_fidelity_output(
        {
            "verdict": "REJECT_REPAIRABLE",
            "reasoning": "A supposed addition is unsupported.",
            "source_checks": [
                {
                    "fact_id": fact.fact_id,
                    "outcome": "preserved_or_represented",
                    "source_quote": fact.value,
                    "candidate_quote": fact.value,
                    "section": "README",
                    "required_repair": "",
                }
            ],
            "unsupported_additions": [
                {
                    "finding_id": "unsupported-addition-1",
                    "section": "README",
                    "quoted_candidate_span": "Text that is not present.",
                    "reason": "No inherited unit supports this text.",
                    "required_repair": "Remove the absent text.",
                }
            ],
            "failed_criteria": ["inheritance_fidelity"],
            "sections_affected": ["README"],
            "required_repair": "Remove the absent text.",
        },
        graph=graph.model_copy(update={"inherited_facts": (fact,)}),
        candidate_text=composition.candidate_markdown,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["unsupported_additions"] == []


def test_fidelity_does_not_reject_the_required_descriptive_enterprise_link(
    tmp_path: Path,
) -> None:
    graph, _composition_output, _snapshot = _composition(tmp_path)
    enterprise_url = "https://products.aspose.com/note/"
    graph = graph.model_copy(
        update={
            "configured_standards": tuple(
                standard.model_copy(
                    update={
                        "parameters": {
                            "required_enterprise_url": enterprise_url,
                            "required_aspose_com_occurrences": 1,
                            "enterprise_product_name": (
                                "Aspose.Note for Python Enterprise Edition"
                            ),
                        }
                    }
                )
                if standard.standard_id == "readme.contextual_links"
                else standard
                for standard in graph.configured_standards
            )
        }
    )
    paragraph = (
        "For requirements outside this repository's scope, use "
        f"[Aspose.Note for Python Enterprise Edition]({enterprise_url})."
    )
    candidate = SOURCE + "\n" + paragraph + "\n"

    normalized = normalize_trusted_fidelity_output(
        {
            "verdict": "REJECT_REPAIRABLE",
            "reasoning": "The configured link was incorrectly classified as unsupported.",
            "source_checks": [
                {
                    "fact_id": fact.fact_id,
                    "outcome": "preserved_or_represented",
                    "source_quote": fact.value,
                    "candidate_quote": fact.value,
                    "section": "source",
                    "required_repair": "",
                }
                for fact in graph.inherited_facts
            ],
            "unsupported_additions": [
                {
                    "finding_id": "unsupported-enterprise-link",
                    "section": "Scope and limitations",
                    "quoted_candidate_span": paragraph,
                    "reason": "The Enterprise Edition link is supposedly unauthorized.",
                    "required_repair": "Remove the configured Enterprise Edition link.",
                }
            ],
            "failed_criteria": ["inheritance_fidelity"],
            "sections_affected": ["Scope and limitations"],
            "required_repair": "Remove the configured Enterprise Edition link.",
        },
        graph=graph,
        candidate_text=candidate,
    )
    result = TrustedFidelityReviewResultV1.model_validate(normalized)

    assert result.verdict == "ACCEPT"
    assert result.unsupported_additions == ()


def test_fidelity_requires_unsupported_addition_quote_to_exclude_inherited_material(
    tmp_path,
) -> None:
    candidate = f"{SOURCE}\nUnverified hosted service is included.\n"
    graph, composition, _ = _composition(tmp_path, candidate=candidate)
    fact = graph.inherited_facts[-1]
    normalized = normalize_trusted_fidelity_output(
        {
            "verdict": "REJECT_REPAIRABLE",
            "reasoning": "The cited block mixes source and unsupported prose.",
            "source_checks": [
                {
                    "fact_id": item.fact_id,
                    "outcome": "preserved_or_represented",
                    "source_quote": item.value,
                    "candidate_quote": item.value,
                    "section": "README",
                    "required_repair": "",
                }
                for item in graph.inherited_facts
            ],
            "unsupported_additions": [
                {
                    "finding_id": "unsupported-addition-mixed",
                    "section": "README",
                    "quoted_candidate_span": candidate.strip(),
                    "reason": "The final line is not inherited.",
                    "required_repair": "Remove only the unsupported line.",
                }
            ],
            "failed_criteria": ["inheritance_fidelity"],
            "sections_affected": ["README"],
            "required_repair": "Remove only the unsupported line.",
        },
        graph=graph,
        candidate_text=composition.candidate_markdown,
    )
    parsed = TrustedFidelityReviewResultV1.model_validate(normalized)

    assert fact.value in parsed.unsupported_additions[0].quoted_candidate_span
    assert validate_trusted_fidelity_result(
        parsed,
        graph,
        composition.candidate_markdown,
    ) == (
        "unsupported-addition-mixed: unsupported-addition quote mixes inherited material; "
        "cite only the exact unsupported bytes",
    )


def test_fidelity_shard_grounds_additions_against_complete_authorization_graph(
    tmp_path,
) -> None:
    candidate = f"{SOURCE}\nUnverified hosted service is included.\n"
    graph, composition, _ = _composition(tmp_path, candidate=candidate)
    paragraph = next(fact for fact in graph.inherited_facts if fact.material_kind == "paragraph")
    heading = next(fact for fact in graph.inherited_facts if fact.material_kind == "heading")
    batch_graph = graph.model_copy(update={"inherited_facts": (heading,)})
    payload = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "The cited block mixes source and unsupported prose.",
        "source_checks": [
            {
                "fact_id": heading.fact_id,
                "outcome": "preserved_or_represented",
                "source_quote": heading.value,
                "candidate_quote": heading.value,
                "section": "README",
                "required_repair": "",
            }
        ],
        "unsupported_additions": [
            {
                "finding_id": "unsupported-addition-cross-shard",
                "section": "README",
                "quoted_candidate_span": candidate.strip(),
                "reason": "The final line is not inherited.",
                "required_repair": "Remove only the unsupported line.",
            }
        ],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["README"],
        "required_repair": "Remove only the unsupported line.",
    }
    parsed = TrustedFidelityReviewResultV1.model_validate(payload)

    assert paragraph.fact_id not in {item.fact_id for item in batch_graph.inherited_facts}
    assert validate_trusted_fidelity_result(
        parsed,
        batch_graph,
        composition.candidate_markdown,
        authorization_graph=graph,
    ) == (
        "unsupported-addition-cross-shard: unsupported-addition quote mixes inherited material; "
        "cite only the exact unsupported bytes",
    )


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


def _repair_result(graph, markdown: str, *, segment_id: str = "complete") -> ForcedToolResult:
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
                    "segment_id": segment_id,
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


def test_fidelity_context_is_compact_and_source_complete(tmp_path) -> None:
    graph, composition, _ = _composition(tmp_path)

    graph_payload, plan_payload = build_trusted_fidelity_context(graph, composition.plan)

    assert [item["fact_id"] for item in graph_payload["inherited_units"]] == [
        fact.fact_id for fact in graph.inherited_facts
    ]
    assert [item["text"] for item in graph_payload["inherited_units"]] == [
        fact.value for fact in graph.inherited_facts
    ]
    assert "source_span" not in json.dumps(graph_payload)
    assert "editorial_summary" not in json.dumps(plan_payload)
    assert len(json.dumps(graph_payload)) < len(graph.model_dump_json())
    assert len(json.dumps(plan_payload)) < len(composition.plan.model_dump_json())


def test_fidelity_normalization_canonicalizes_empty_repair_sentinels() -> None:
    normalized = normalize_trusted_fidelity_output(
        {
            "verdict": "REJECT_REPAIRABLE",
            "required_repair": "N/A",
            "source_checks": [
                {
                    "fact_id": "readme.inherited:0123456789abcdef01234567",
                    "outcome": "preserved_or_represented",
                    "source_quote": "source",
                    "candidate_quote": "candidate",
                    "required_repair": "none",
                },
                {
                    "fact_id": "readme.inherited:89abcdef0123456789abcdef",
                    "outcome": "lost_or_distorted",
                    "source_quote": "source",
                    "candidate_quote": "",
                    "required_repair": "Restore this exact source unit.",
                },
            ],
        }
    )

    assert normalized["required_repair"] == "Restore this exact source unit."
    assert normalized["source_checks"][0]["required_repair"] == ""
    assert normalized["source_checks"][1]["required_repair"] == "Restore this exact source unit."


def test_exact_removal_delta_rebinds_source_check_to_surviving_representation(
    tmp_path: Path,
) -> None:
    removable = "This package is specifically designed for Python developers."
    candidate = f"{SOURCE}\n{removable}\n"
    graph, composition, _snapshot = _composition(tmp_path, candidate=candidate)
    paragraph = next(fact for fact in graph.inherited_facts if fact.material_kind == "paragraph")
    prior = _accepted_fidelity_record(
        graph,
        composition,
        candidate_quote_overrides={paragraph.fact_id: removable},
    )
    repaired, action = apply_grounded_exact_removal(
        graph,
        SOURCE,
        composition,
        finding_id="duplicate-prose",
        quoted_candidate_span=removable,
        instruction="Remove the duplicate product description.",
    )

    result = derive_fidelity_after_exact_removal(graph, repaired, prior, action)

    assert result.verdict == "ACCEPT"
    rebound = next(check for check in result.source_checks if check.fact_id == paragraph.fact_id)
    assert rebound.candidate_quote == paragraph.value


def test_exact_removal_delta_returns_repairable_rejection_for_actual_source_loss(
    tmp_path: Path,
) -> None:
    removable = "A specific package for Python developers."
    candidate = f"# Widget\n\n{removable}\n\nAdditional operational guidance.\n"
    graph, composition, _snapshot = _composition(tmp_path, candidate=candidate)
    paragraph = next(
        fact
        for fact in graph.inherited_facts
        if fact.material_kind == "paragraph" and "specific package" in fact.value
    )
    prior = _accepted_fidelity_record(graph, composition)
    repaired, action = apply_grounded_exact_removal(
        graph,
        SOURCE,
        composition,
        finding_id="remove-source",
        quoted_candidate_span=removable,
        instruction="Remove the product description.",
    )

    result = derive_fidelity_after_exact_removal(graph, repaired, prior, action)

    assert result.verdict == "REJECT_REPAIRABLE"
    lost = next(check for check in result.source_checks if check.fact_id == paragraph.fact_id)
    assert lost.outcome == "lost_or_distorted"
    assert paragraph.fact_id in lost.required_repair

    unresolved_prior = prior.model_copy(
        update={
            "verdict": result.verdict,
            "result": result.model_dump(mode="json"),
        }
    )
    repeated = derive_fidelity_after_exact_removal(
        graph,
        repaired,
        unresolved_prior,
        action,
    )

    assert repeated.verdict == "REJECT_REPAIRABLE"
    assert (
        next(
            check for check in repeated.source_checks if check.fact_id == paragraph.fact_id
        ).outcome
        == "lost_or_distorted"
    )


def test_fidelity_normalization_derives_only_redundant_rejection_fields() -> None:
    normalized = normalize_trusted_fidelity_output(
        {
            "verdict": "REJECT_REPAIRABLE",
            "reasoning": "One inherited unit was lost.",
            "source_checks": [
                {
                    "fact_id": "readme.inherited:0123456789abcdef01234567",
                    "outcome": "lost_or_distorted",
                    "source_quote": "source",
                    "candidate_quote": "",
                    "section": "Overview",
                    "required_repair": "",
                }
            ],
            "unsupported_additions": [],
            "failed_criteria": [],
            "sections_affected": [],
            "required_repair": "",
        }
    )

    assert normalized["failed_criteria"] == ["inheritance_fidelity"]
    assert normalized["sections_affected"] == ["Overview"]
    assert normalized["source_checks"][0]["required_repair"].startswith(
        "Restore or accurately represent inherited source unit"
    )
    assert normalized["required_repair"] == normalized["source_checks"][0]["required_repair"]


def test_fidelity_normalization_clears_accept_residue_outside_addition_scope(
    tmp_path,
) -> None:
    graph, composition, _ = _composition(tmp_path)
    fact = graph.inherited_facts[0]
    normalized = normalize_trusted_fidelity_output(
        {
            "verdict": "ACCEPT",
            "reasoning": "The source is represented.",
            "source_checks": [
                {
                    "fact_id": fact.fact_id,
                    "outcome": "preserved_or_represented",
                    "source_quote": fact.value,
                    "candidate_quote": fact.value,
                    "section": "README",
                    "required_repair": "Stale repair text.",
                }
            ],
            "unsupported_additions": [
                {
                    "finding_id": "out-of-scope-addition",
                    "section": "Navigation",
                    "quoted_candidate_span": composition.candidate_markdown.splitlines()[0],
                    "reason": "This shard was not assigned addition review.",
                    "required_repair": "Remove it.",
                }
            ],
            "failed_criteria": ["stale"],
            "sections_affected": ["Navigation"],
            "required_repair": "Stale repair text.",
        },
        graph=graph.model_copy(update={"inherited_facts": (fact,)}),
        candidate_text=composition.candidate_markdown,
        allow_unsupported_additions=False,
    )

    assert normalized["verdict"] == "ACCEPT"
    assert normalized["source_checks"][0]["required_repair"] == ""
    assert normalized["unsupported_additions"] == []
    assert normalized["failed_criteria"] == []
    assert normalized["sections_affected"] == []
    assert normalized["required_repair"] == ""


def test_fidelity_normalization_safely_downgrades_ungrounded_preservation(tmp_path) -> None:
    graph, _, _ = _composition(tmp_path)
    fact = graph.inherited_facts[0]
    normalized = normalize_trusted_fidelity_output(
        {
            "verdict": "ACCEPT",
            "reasoning": "The source was represented.",
            "source_checks": [
                {
                    "fact_id": fact.fact_id,
                    "outcome": "preserved_or_represented",
                    "source_quote": "paraphrased source",
                    "candidate_quote": "invented candidate quote",
                    "section": "Overview",
                    "required_repair": "",
                }
            ],
            "unsupported_additions": [],
            "failed_criteria": [],
            "sections_affected": [],
            "required_repair": "",
        },
        graph=graph.model_copy(update={"inherited_facts": (fact,)}),
        candidate_text="# Different\n",
    )

    assert normalized["verdict"] == "REJECT_REPAIRABLE"
    assert normalized["source_checks"][0]["source_quote"] == fact.value
    assert normalized["source_checks"][0]["candidate_quote"] == ""
    assert normalized["source_checks"][0]["outcome"] == "lost_or_distorted"
    assert normalized["failed_criteria"] == ["inheritance_fidelity"]


def test_fidelity_code_repair_cannot_restore_comments_when_standard_prohibits_them(
    tmp_path,
) -> None:
    graph, _, _ = _composition(tmp_path)
    code_fact = graph.inherited_facts[0].model_copy(update={"material_kind": "code"})
    no_comments = configured_standard_addition(
        "readme.no_comments",
        configuration_source="config/policies/test.yml",
        configuration_bytes=b"no-comments-test",
    )
    graph = graph.model_copy(
        update={
            "inherited_facts": (code_fact,),
            "configured_standards": (no_comments,),
        }
    )
    normalized = normalize_trusted_fidelity_output(
        {
            "verdict": "REJECT_REPAIRABLE",
            "reasoning": "The example was distorted.",
            "source_checks": [
                {
                    "fact_id": code_fact.fact_id,
                    "outcome": "lost_or_distorted",
                    "source_quote": code_fact.value,
                    "candidate_quote": "",
                    "section": "Quick Start",
                    "required_repair": "Restore valid Python comment syntax.",
                }
            ],
            "unsupported_additions": [],
            "failed_criteria": ["preservation"],
            "sections_affected": ["Quick Start"],
            "required_repair": "Restore valid Python comment syntax.",
        },
        graph=graph.model_copy(update={"inherited_facts": (code_fact,)}),
        candidate_text="# Different\n",
    )

    repair = normalized["source_checks"][0]["required_repair"]
    assert repair.endswith("while omitting all comments and docstrings.")
    assert normalized["required_repair"] == repair
    assert "valid Python comment syntax" not in repair


def test_fidelity_review_executes_each_source_batch_then_reduces_complete_coverage(
    tmp_path,
) -> None:
    graph, composition, _ = _composition(tmp_path)
    draft = composition.plan.section_drafts[0]
    first_fact, second_fact = graph.inherited_facts
    first_inventory, second_inventory = draft.source_inventory
    segment = draft.segments[0]
    first_draft = draft.model_copy(
        update={
            "batch_id": "batch-0001",
            "source_inventory": (first_inventory,),
            "segments": (
                segment.model_copy(
                    update={
                        "segment_id": "first",
                        "inherited_fact_ids": (first_fact.fact_id,),
                    }
                ),
            ),
        }
    )
    second_draft = draft.model_copy(
        update={
            "batch_id": "batch-0002",
            "source_inventory": (second_inventory,),
            "segments": (
                segment.model_copy(
                    update={
                        "segment_id": "second",
                        "inherited_fact_ids": (second_fact.fact_id,),
                    }
                ),
            ),
        }
    )
    plan = composition.plan.model_copy(update={"section_drafts": (first_draft, second_draft)})
    batched_composition = composition.model_copy(
        update={"plan": plan, "plan_hash": plan.canonical_hash()}
    )
    first_graph = graph.model_copy(update={"inherited_facts": (first_fact,)})
    second_graph = graph.model_copy(update={"inherited_facts": (second_fact,)})
    client = FixtureAnalysisClient(
        [
            _analysis(_fidelity_accept(first_graph), model="fixture-fidelity"),
            _analysis(_fidelity_accept(second_graph), model="fixture-fidelity"),
        ],
        job="trusted_readme_fidelity_review",
        prompt_id="trusted_readme_fidelity_review",
    )
    _start_accounting(graph, "trusted-review-batched-fidelity")
    calls_before = current_llm_accounting_summary().fixture_call_count or 0

    result, history = run_batched_trusted_fidelity_review(
        client=client,
        graph=graph,
        composition=batched_composition,
    )

    assert result.verdict == "ACCEPT"
    assert result.reasoning == (
        "All bounded fidelity shards passed deterministic grounding; every required "
        "source fact is preserved or represented and no in-scope unsupported addition remains."
    )
    assert [item.fact_id for item in result.source_checks] == [
        first_fact.fact_id,
        second_fact.fact_id,
    ]
    assert [item["batch_id"] for item in history] == [
        "batch-0001.part-0001",
        "batch-0002.part-0001",
    ]
    calls_after = current_llm_accounting_summary().fixture_call_count or 0
    assert calls_after - calls_before == 2


def test_fidelity_batches_review_the_owned_final_candidate_projection(tmp_path) -> None:
    graph, composition, _ = _composition(tmp_path)

    review_candidates = _render_review_candidates(composition, graph)

    assert review_candidates
    assert set(review_candidates) == {draft.batch_id for draft in composition.plan.section_drafts}
    assert {value.rstrip() for value in review_candidates.values()} == {
        composition.candidate_markdown.rstrip()
    }


def test_fidelity_call_partition_is_fact_and_source_byte_bounded() -> None:
    fact_ids = tuple(f"fact-{index:02d}" for index in range(25))
    values = {fact_id: "x" * 100 for fact_id in fact_ids}

    chunks = partition_fidelity_fact_ids(fact_ids, values)

    assert [len(chunk) for chunk in chunks] == [8, 8, 8, 1]
    large_values = {"one": "x" * 4_000, "two": "y" * 3_000, "three": "z"}
    assert partition_fidelity_fact_ids(("one", "two", "three"), large_values) == (
        ("one",),
        ("two", "three"),
    )


def test_fidelity_batch_cache_reuses_validated_result_without_client_call(tmp_path) -> None:
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-fidelity-batch-cache")
    first_client = FixtureAnalysisClient(
        [_analysis(_fidelity_accept(graph), model="fixture-fidelity")],
        job="trusted_readme_fidelity_review",
        prompt_id="trusted_readme_fidelity_review",
    )

    first, _ = run_batched_trusted_fidelity_review(
        client=first_client,
        graph=graph,
        composition=composition,
        cache_dir=tmp_path / "fidelity-cache",
    )
    before = current_llm_accounting_summary()
    second, _ = run_batched_trusted_fidelity_review(
        client=FixtureAnalysisClient([]),
        graph=graph,
        composition=composition,
        cache_dir=tmp_path / "fidelity-cache",
    )
    after = current_llm_accounting_summary()

    assert second == first
    assert (after.fixture_call_count or 0) == (before.fixture_call_count or 0)
    assert (after.cache_reuse_count or 0) - (before.cache_reuse_count or 0) == 1


def test_fidelity_batch_cache_migrates_one_exact_prior_contract(
    tmp_path,
    monkeypatch,
) -> None:
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-fidelity-batch-cache-migration")
    current_contract = trusted_fidelity_cache.FIDELITY_BATCH_CONTRACT_VERSION
    monkeypatch.setattr(
        trusted_fidelity_cache,
        "FIDELITY_BATCH_CONTRACT_VERSION",
        trusted_fidelity_cache.LEGACY_FIDELITY_BATCH_CONTRACT_VERSION,
    )
    run_batched_trusted_fidelity_review(
        client=FixtureAnalysisClient(
            [_analysis(_fidelity_accept(graph), model="fixture-fidelity")],
            job="trusted_readme_fidelity_review",
            prompt_id="trusted_readme_fidelity_review",
        ),
        graph=graph,
        composition=composition,
        cache_dir=tmp_path / "fidelity-migration-cache",
    )
    monkeypatch.setattr(
        trusted_fidelity_cache,
        "FIDELITY_BATCH_CONTRACT_VERSION",
        current_contract,
    )
    before = current_llm_accounting_summary()

    migrated, _ = run_batched_trusted_fidelity_review(
        client=FixtureAnalysisClient([]),
        graph=graph,
        composition=composition,
        cache_dir=tmp_path / "fidelity-migration-cache",
    )
    after = current_llm_accounting_summary()

    assert migrated.verdict == "ACCEPT"
    assert (after.fixture_call_count or 0) == (before.fixture_call_count or 0)
    assert (after.cache_reuse_count or 0) - (before.cache_reuse_count or 0) == 1


def test_blind_rubric_respects_governed_header_and_link_budget() -> None:
    manifest = prompt_registry.get("blind_readme_quality_review")

    assert manifest is not None
    assert "do not request badges before the title" in manifest.system
    assert "Do not demand restoration of any original hyperlink" in manifest.system
    assert "proven false and MUST be omitted" in manifest.turn_context_template
    messages = build_blind_quality_review_messages(
        ORG_REPO,
        SOURCE,
        SOURCE,
        '{"configured_standards":[{"standard_id":"readme.contextual_links"}]}',
    )
    assert "readme.contextual_links" in messages[1]["content"]
    assert not messages[1]["content"].startswith("/no_think")
    assert "Authoritative parser-derived mechanical observations:" in messages[1]["content"]


def test_trusted_fidelity_prompt_disables_unbounded_thinking() -> None:
    messages = build_trusted_fidelity_review_messages(
        ORG_REPO,
        '{"inherited_units":[]}',
        '{"required_source_check_fact_ids":[]}',
        SOURCE,
    )

    assert messages[1]["content"].startswith("/no_think")


def test_canonical_trusted_pipeline_persists_approval_then_exact_no_op(
    tmp_path,
    monkeypatch,
):
    graph, _, snapshot = _composition(tmp_path)
    backend = FakeStateBackend()
    record_repository_snapshot(
        backend,
        ORG_REPO,
        source_revision=snapshot.source_revision,
        evidence_refs=["snapshot"],
    )
    record_repository_profile(
        backend,
        ORG_REPO,
        source_revision=snapshot.source_revision,
        evidence_refs=["profile"],
    )
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr(
        "readme_agent.supervisor.trusted_product_truth.bind_trusted_presentation_standards",
        lambda org_repo, fact_graph, source_text: fact_graph,
    )
    monkeypatch.setattr(
        "readme_agent.capabilities.compose_trusted_readme.bind_trusted_presentation_standards",
        lambda org_repo, fact_graph, source_text: fact_graph,
    )
    fact_ids = [fact.fact_id for fact in graph.inherited_facts]
    author = FixtureForcedToolClient(
        [
            ForcedToolResult(
                arguments={
                    "editorial_summary": "Retain the source while proving the trusted lane.",
                    "complete": True,
                    "source_inventory": [
                        {
                            "fact_id": fact_id,
                            "action": "rewrite",
                            "rationale": "Represent the inherited source in the candidate.",
                        }
                        for fact_id in fact_ids
                    ],
                    "segments": [
                        {
                            "segment_id": "complete",
                            "kind": "authored",
                            "markdown": SOURCE,
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
    )
    blind, fidelity = _review_clients(graph)
    _start_accounting(graph, "trusted-pipeline-first")
    with repository_snapshot_scope(snapshot):
        first = run_trusted_readme_pipeline(
            ORG_REPO,
            snapshot,
            backend,
            target_stage="TRUSTED_TRANSFORM_APPROVED",
            author_client=author,
            blind_client=blind,
            fidelity_client=fidelity,
        )

    assert first.status == "TRUSTED_TRANSFORM_APPROVED"
    assert first.reached
    assert not first.cache_reused
    first_lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle
    assert first_lifecycle is not None
    assert first_lifecycle.content_assurance == "trusted_inherited"
    assert first_lifecycle.status == "TRUSTED_TRANSFORM_APPROVED"

    _start_accounting(graph, "trusted-pipeline-no-op")
    with repository_snapshot_scope(snapshot):
        second = run_trusted_readme_pipeline(
            ORG_REPO,
            snapshot,
            backend,
            target_stage="TRUSTED_NO_OP_PROVEN",
            author_client=FixtureForcedToolClient([]),
            blind_client=FixtureAnalysisClient([]),
            fidelity_client=FixtureAnalysisClient([]),
        )

    assert second.status == "TRUSTED_NO_OP_PROVEN"
    assert second.reached
    assert second.cache_reused
    final_lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle
    assert final_lifecycle is not None
    assert final_lifecycle.status == "TRUSTED_NO_OP_PROVEN"
    assert [item.to_status for item in final_lifecycle.history][-6:] == [
        "TRUSTED_PLAN_READY",
        "TRUSTED_CANDIDATE_GENERATED",
        "TRUSTED_DETERMINISTIC_VALIDATED",
        "TRUSTED_REVIEWING",
        "TRUSTED_TRANSFORM_APPROVED",
        "TRUSTED_NO_OP_PROVEN",
    ]


def test_canonical_pipeline_records_composition_failure_without_traceback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    graph, _composition_output, snapshot = _composition(tmp_path)
    backend = FakeStateBackend()
    record_repository_snapshot(
        backend,
        ORG_REPO,
        source_revision=snapshot.source_revision,
        evidence_refs=["snapshot"],
    )
    record_repository_profile(
        backend,
        ORG_REPO,
        source_revision=snapshot.source_revision,
        evidence_refs=["profile"],
    )
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr(
        "readme_agent.supervisor.trusted_product_truth.bind_trusted_presentation_standards",
        lambda org_repo, fact_graph, source_text: fact_graph,
    )
    monkeypatch.setattr(
        "readme_agent.capabilities.compose_trusted_readme.bind_trusted_presentation_standards",
        lambda org_repo, fact_graph, source_text: fact_graph,
    )

    def fail_composition(*args, **kwargs):
        raise LLMError("configured presentation contract was not satisfied")

    monkeypatch.setattr(
        "readme_agent.supervisor.trusted_readme_pipeline.dispatch_trusted_composition",
        fail_composition,
    )

    with repository_snapshot_scope(snapshot):
        result = run_trusted_readme_pipeline(
            ORG_REPO,
            snapshot,
            backend,
            target_stage="TRUSTED_TRANSFORM_APPROVED",
        )

    assert result.status == "SYSTEM_FAILURE"
    assert result.reached is False
    assert result.blocked_reason == (
        "trusted composition failed: configured presentation contract was not satisfied"
    )
    assert result.blocked_category == "agent_fixable"
    lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle
    assert lifecycle is not None
    assert lifecycle.status == "SYSTEM_FAILURE"


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
    history = execution.review.inheritance_fidelity.result["retry_history"]
    assert [item["attempt"] for item in history] == [1, 2]
    assert all(item["valid"] is False for item in history)


def test_repeated_ungrounded_blind_output_preserves_retry_evidence(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-blind-grounding-failure")
    invalid = _blind_reject()
    invalid["findings"][0]["quoted_candidate_span"] = "absent candidate wording"
    blind = FixtureAnalysisClient(
        [_analysis(invalid, model="fixture-blind") for _ in range(3)],
        job="blind_readme_quality_review",
        prompt_id="blind_readme_quality_review",
    )
    fidelity = _review_clients(graph)[1]

    execution = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
    )

    assert execution.review.verdict == "SYSTEM_FAILURE"
    history = execution.review.blind_quality.result["retry_history"]
    assert [item["attempt"] for item in history] == [1, 2, 3]
    assert all(item["valid"] is False for item in history)


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
    assert result.repair_history[0].approach == "bounded_llm_section_rewrite"
    assert result.repair_history[0].rereview_verdict == "TRUSTED_TRANSFORM_APPROVED"
    assert result.final_execution.review.blind_quality.verdict == "ACCEPT"
    assert result.final_execution.review.inheritance_fidelity.verdict == "ACCEPT"


def test_grounded_repair_preserves_segment_identity_after_candidate_normalization(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-normalized-ownership")
    draft = composition.plan.section_drafts[0]
    segment = draft.segments[0]
    normalized_source_draft = segment.model_copy(
        update={
            "markdown": (
                "# Widget\n\nA specific [package](https://example.invalid/package) "
                "for Python developers.\n"
            )
        }
    )
    changed_draft = draft.model_copy(update={"segments": (normalized_source_draft,)})
    changed_plan = composition.plan.model_copy(update={"section_drafts": (changed_draft,)})
    composition = composition.model_copy(update={"plan": changed_plan})
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
                graph,
                SOURCE.rstrip() + "\n\nThe purpose is explicit.\n",
                segment_id=segment.segment_id,
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
    assert result.repair_history[0].request.rejected_batch_id == draft.batch_id
    assert result.repair_history[0].candidate_changed


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


def test_repair_provider_outage_is_typed_as_external_infrastructure(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-provider-outage")
    blind, fidelity = _review_clients(graph, blind=_blind_reject())

    class ProviderDown:
        def call(self, messages, tool_schema):
            raise LLMInfrastructureError("HTTP 500: EngineCore encountered an issue")

    result = run_trusted_review_with_repair(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
        repair_client=ProviderDown(),
    )

    assert result.outcome == "system_failure"
    assert result.system_failure_category == "infra_external"
    assert "EngineCore encountered an issue" in result.system_failure_reason


def test_same_failed_boundary_cannot_repeat_the_same_repair_approach(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-approach-change")
    blind = FixtureAnalysisClient(
        [
            _analysis(_blind_reject(), model="fixture-blind"),
            _analysis(_blind_reject(), model="fixture-blind"),
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
                graph,
                "# Widget for Python\n\nA specific package for Python developers.\n",
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

    assert result.outcome == "system_failure"
    assert result.system_failure_reason == (
        "trusted repair approach repeated without resolving the same boundary; "
        "an upstream resolver or materially different mechanism is required"
    )
    assert len(result.repair_history) == 1
    assert result.repair_history[0].approach == "bounded_llm_section_rewrite"


def test_exact_removal_reuses_prior_fidelity_without_replaying_source_shards(tmp_path):
    unsupported = "Unverified hosted service is included."
    candidate = f"{SOURCE}\n{unsupported}\n"
    graph, composition, _ = _composition(tmp_path, candidate=candidate)
    _start_accounting(graph, "trusted-review-exact-removal-delta")
    blind = FixtureAnalysisClient(
        [
            _analysis(_blind_remove(unsupported), model="fixture-blind"),
            _analysis(_blind_accept(), model="fixture-blind"),
        ],
        job="blind_readme_quality_review",
        prompt_id="blind_readme_quality_review",
    )
    fidelity_reject = {
        "verdict": "REJECT_REPAIRABLE",
        "reasoning": "One exact paragraph is not inherited.",
        "source_checks": [
            {
                "fact_id": fact.fact_id,
                "outcome": "preserved_or_represented",
                "source_quote": fact.value,
                "candidate_quote": fact.value,
                "section": "README",
                "required_repair": "",
            }
            for fact in graph.inherited_facts
        ],
        "unsupported_additions": [
            {
                "finding_id": "unsupported-promotion",
                "section": "README",
                "quoted_candidate_span": unsupported,
                "reason": "The paragraph is absent from inherited source.",
                "required_repair": "Remove the unsupported promotional paragraph.",
            }
        ],
        "failed_criteria": ["inheritance_fidelity"],
        "sections_affected": ["README"],
        "required_repair": "Remove the unsupported promotional paragraph.",
    }
    fidelity = FixtureAnalysisClient(
        [_analysis(fidelity_reject, model="fixture-fidelity")],
        job="trusted_readme_fidelity_review",
        prompt_id="trusted_readme_fidelity_review",
    )
    unused_repair = FixtureForcedToolClient(
        [],
        job="trusted_readme_section_transform",
        prompt_id="trusted_readme_section_transform",
    )

    result = run_trusted_review_with_repair(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
        repair_client=unused_repair,
    )

    assert result.outcome == "accepted"
    assert result.final_composition.candidate_markdown.rstrip() == SOURCE.rstrip()
    assert len(result.repair_history) == 1
    assert result.repair_history[0].approach == "grounded_exact_removal"
    assert result.final_execution.review.inheritance_fidelity.verdict == "ACCEPT"
    assert (
        result.final_execution.review.inheritance_fidelity.result["retry_history"][0]["disposition"]
        == "exact_removal_delta_proof"
    )


def test_partial_paragraph_quote_routes_repair_through_bounded_llm(tmp_path):
    duplicate = "Duplicated overview paragraph that should be removed."
    candidate = f"{SOURCE.rstrip()}\n\n{duplicate}\n"
    repaired_candidate = f"{SOURCE.rstrip()}\n\n## Quick start\n"
    graph, composition, _ = _composition(tmp_path, candidate=candidate)
    _start_accounting(graph, "trusted-review-structural-quote-repair")
    blind = FixtureAnalysisClient(
        [
            _analysis(_blind_remove("Duplicated overview paragraph"), model="fixture-blind"),
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
        [_repair_result(graph, repaired_candidate)],
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
    assert duplicate not in result.final_composition.candidate_markdown
    assert "## Quick start" in result.final_composition.candidate_markdown
    assert result.repair_history[0].approach == "bounded_llm_section_rewrite"


def test_blind_grounding_rejects_heading_quote_for_paragraph_removal() -> None:
    candidate = "# Widget\n\n## Quick start\n\nDuplicated overview paragraph.\n"
    finding = GroundedReviewFindingV1.model_validate(
        {
            **_blind_remove("## Quick start")["findings"][0],
            "finding_id": "quality.misgrounded-duplicate",
        }
    )

    result = validate_review_findings(
        candidate_text=candidate,
        product_facts=None,
        findings=[finding],
    )

    assert not result.valid
    assert result.errors == [
        "quality.misgrounded-duplicate:repair quote identifies a heading instead of the prose "
        "to remove"
    ]


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


def test_live_trusted_review_uses_real_fact_coverage_envelope(tmp_path, monkeypatch):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-live-envelope")
    blind, fidelity = _review_clients(graph)
    captured: dict[str, object] = {}

    def build_clients(base_url, api_key, **kwargs):
        captured.update({"base_url": base_url, "api_key": api_key, **kwargs})
        return blind, fidelity

    monkeypatch.setattr(
        "readme_agent.specialists.trusted_transform_review.build_live_trusted_review_clients",
        build_clients,
    )
    monkeypatch.setattr(env, "llm_base_url", lambda: "https://gateway.example/v1")
    monkeypatch.setattr(env, "llm_api_key", lambda: "test-key")
    monkeypatch.setattr(env, "llm_timeout_seconds", lambda: 123.0)
    cache_dir = tmp_path / "live-fidelity-cache"
    monkeypatch.setattr(
        "readme_agent.specialists.trusted_transform_review.default_trusted_fidelity_cache_dir",
        lambda graph: cache_dir,
    )

    execution = run_trusted_transform_review(graph, SOURCE, composition)

    assert execution.review.verdict == "TRUSTED_TRANSFORM_APPROVED"
    assert [item.name for item in cache_dir.iterdir()] == ["batch-0001.part-0001.json"]
    assert captured == {
        "base_url": "https://gateway.example/v1",
        "api_key": "test-key",
        "timeout": 123.0,
        "max_tokens": 12_000,
    }


def test_explicit_canonical_review_clients_can_enable_fidelity_checkpoint(tmp_path, monkeypatch):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-explicit-live-cache")
    blind, fidelity = _review_clients(graph)
    cache_dir = tmp_path / "explicit-fidelity-cache"
    monkeypatch.setattr(
        "readme_agent.specialists.trusted_transform_review.default_trusted_fidelity_cache_dir",
        lambda graph: cache_dir,
    )

    execution = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=blind,
        fidelity_client=fidelity,
        enable_fidelity_batch_cache=True,
    )

    assert execution.review.verdict == "TRUSTED_TRANSFORM_APPROVED"
    assert [item.name for item in cache_dir.iterdir()] == ["batch-0001.part-0001.json"]


def test_stage_review_builder_does_not_fall_back_to_short_output_limit(monkeypatch):
    captured: dict[str, object] = {}
    sentinels = (object(), object())

    def build_clients(base_url, api_key, **kwargs):
        captured.update({"base_url": base_url, "api_key": api_key, **kwargs})
        return sentinels

    monkeypatch.setattr(
        "readme_agent.supervisor.trusted_readme_stage_execution.build_live_trusted_review_clients",
        build_clients,
    )
    monkeypatch.setattr(env, "llm_base_url", lambda: "https://gateway.example/v1")
    monkeypatch.setattr(env, "llm_api_key", lambda: "test-key")
    monkeypatch.setattr(env, "llm_timeout_seconds", lambda: 123.0)

    clients = live_trusted_review_clients()

    assert clients == sentinels
    assert captured == {
        "base_url": "https://gateway.example/v1",
        "api_key": "test-key",
        "timeout": 123.0,
        "max_tokens": 12_000,
    }


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


def test_interrupted_repair_resumes_at_candidate_revalidation(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-interrupted-repair")
    blind, fidelity = _review_clients(graph, blind=_blind_reject())
    rejected = run_trusted_transform_review(
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
        reason="exercise interrupted repair recovery",
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
    record_trusted_review_execution(
        backend,
        graph,
        composition,
        rejected,
        evidence_refs=["rejected-review.json"],
    )
    transition_trusted_readme_poc_status(
        backend,
        ORG_REPO,
        "TRUSTED_REPAIRING",
        observed_by="test",
        reason="simulate interruption after repair claim",
        source_revision=graph.source_revision,
        facts_hash=graph.canonical_hash(),
        candidate_hash=composition.candidate_sha256,
    )

    resumed = record_trusted_review_execution(
        backend,
        graph,
        composition,
        rejected,
        evidence_refs=["replayed-review.json"],
    )

    assert resumed.status == "TRUSTED_REVIEW_REJECTED"
    assert [item.to_status for item in resumed.history[-4:]] == [
        "TRUSTED_CANDIDATE_GENERATED",
        "TRUSTED_DETERMINISTIC_VALIDATED",
        "TRUSTED_REVIEWING",
        "TRUSTED_REVIEW_REJECTED",
    ]
    transition_trusted_readme_poc_status(
        backend,
        ORG_REPO,
        "TRUSTED_REPAIRING",
        observed_by="test",
        reason="retry the repair",
        source_revision=graph.source_revision,
        facts_hash=graph.canonical_hash(),
        candidate_hash=composition.candidate_sha256,
    )
    transition_trusted_readme_poc_status(
        backend,
        ORG_REPO,
        "SYSTEM_FAILURE",
        observed_by="test",
        reason="simulate agent-fixable repair machinery failure",
        source_revision=graph.source_revision,
        facts_hash=graph.canonical_hash(),
        candidate_hash=composition.candidate_sha256,
    )

    recovered = record_trusted_review_execution(
        backend,
        graph,
        composition,
        rejected,
        evidence_refs=["recovered-review.json"],
    )

    assert recovered.status == "TRUSTED_REVIEW_REJECTED"
    assert [item.to_status for item in recovered.history[-5:]] == [
        "TRUSTED_REPAIRING",
        "TRUSTED_CANDIDATE_GENERATED",
        "TRUSTED_DETERMINISTIC_VALIDATED",
        "TRUSTED_REVIEWING",
        "TRUSTED_REVIEW_REJECTED",
    ]


def test_changed_review_contract_requalifies_rejected_unchanged_candidate(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-old-rejection")
    rejected_blind, rejected_fidelity = _review_clients(graph, blind=_blind_reject())
    rejected = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=rejected_blind,
        fidelity_client=rejected_fidelity,
    )
    rejected_payload = rejected.model_dump(mode="json")
    old_identity_payload = rejected_payload["review"]["cache_identity"]
    old_identity_payload["review_contract_sha256"] = "0" * 64
    old_identity = TrustedReviewCacheIdentityV1.model_validate(old_identity_payload)
    rejected_payload["review"]["cache_identity"] = old_identity.model_dump(mode="json")
    rejected_payload["review"]["cache_identity_sha256"] = old_identity.canonical_hash()
    old_rejected = TrustedReviewExecutionV1.model_validate(rejected_payload)

    _start_accounting(graph, "trusted-review-new-acceptance")
    accepted_blind, accepted_fidelity = _review_clients(graph)
    accepted = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=accepted_blind,
        fidelity_client=accepted_fidelity,
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
        reason="exercise changed review contract requalification",
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
    rejected_state = record_trusted_review_execution(
        backend,
        graph,
        composition,
        old_rejected,
        evidence_refs=["old-review.json"],
    )

    approved_state = record_trusted_review_execution(
        backend,
        graph,
        composition,
        accepted,
        evidence_refs=["new-review.json"],
    )

    assert rejected_state.status == "TRUSTED_REVIEW_REJECTED"
    assert approved_state.status == "TRUSTED_TRANSFORM_APPROVED"
    assert [item.to_status for item in approved_state.history[-5:]] == [
        "TRUSTED_REPAIRING",
        "TRUSTED_CANDIDATE_GENERATED",
        "TRUSTED_DETERMINISTIC_VALIDATED",
        "TRUSTED_REVIEWING",
        "TRUSTED_TRANSFORM_APPROVED",
    ]


def test_unchanged_review_contract_cannot_replace_rejected_verdict(tmp_path):
    graph, composition, _ = _composition(tmp_path)
    _start_accounting(graph, "trusted-review-same-contract-rejection")
    rejected_blind, rejected_fidelity = _review_clients(graph, blind=_blind_reject())
    rejected = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=rejected_blind,
        fidelity_client=rejected_fidelity,
    )
    _start_accounting(graph, "trusted-review-same-contract-acceptance")
    accepted_blind, accepted_fidelity = _review_clients(graph)
    accepted = run_trusted_transform_review(
        graph,
        SOURCE,
        composition,
        blind_client=accepted_blind,
        fidelity_client=accepted_fidelity,
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
        reason="exercise same-contract rejection protection",
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
    record_trusted_review_execution(
        backend,
        graph,
        composition,
        rejected,
        evidence_refs=["rejected-review.json"],
    )

    with pytest.raises(StateBackendError, match="without changed review inputs"):
        record_trusted_review_execution(
            backend,
            graph,
            composition,
            accepted,
            evidence_refs=["accepted-review.json"],
        )
