"""Independent quality and inheritance-fidelity review for trusted transforms."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from readme_agent import env
from readme_agent.capabilities.dispatcher import dispatch_tool_call
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
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
from readme_agent.registry.loader import load_products
from readme_agent.repository_snapshot import capture_repository_snapshot, repository_snapshot_scope
from readme_agent.specialists.trusted_fidelity_context import build_trusted_fidelity_context
from readme_agent.specialists.trusted_fidelity_execution import (
    partition_fidelity_fact_ids,
    run_batched_trusted_fidelity_review,
)
from readme_agent.specialists.trusted_fidelity_validation import (
    normalize_trusted_fidelity_output,
)
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
    candidate = "# Widget\n\nProduct — Enterprise Edition.\n\n```python\n\nrun()\n```\n"
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
                "quoted_candidate_span": "Product — Enterprise Edition.",
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
    assert messages[1]["content"].startswith("/no_think")


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
        "max_tokens": 8_000,
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
        "max_tokens": 8_000,
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
