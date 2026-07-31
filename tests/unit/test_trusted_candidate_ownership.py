"""Stable ownership and exact trusted-candidate repair controls."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from readme_agent.errors import LLMError
from readme_agent.facts.trusted_readme_extraction import extract_trusted_readme_fact_graph
from readme_agent.gitsafety._git import run_git
from readme_agent.readme.trusted_candidate_ownership import build_candidate_span_ownership_map
from readme_agent.readme.trusted_composition import finalize_trusted_composition
from readme_agent.readme.trusted_composition_models import (
    TrustedCompositionEnvelopeV1,
    TrustedReadmeDraftSegmentV1,
    TrustedReadmeSectionDraftV1,
    TrustedReadmeSectionToolDraftV1,
    TrustedSourceInventoryDecisionV1,
)
from readme_agent.readme.trusted_exact_repair import apply_grounded_exact_removal
from readme_agent.registry.loader import load_products
from readme_agent.repository_snapshot import capture_repository_snapshot

ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
_HASH = "a" * 64


def test_ownership_map_covers_normalized_candidate_and_exact_removal_needs_no_llm(
    tmp_path: Path,
) -> None:
    source = "# Widget\n\nUseful inherited product detail.\n"
    duplicate = "This paragraph is a duplicated promotional addition."
    graph = _graph(tmp_path, source)
    composition = _composition(graph, source, f"{source.rstrip()}\n\n{duplicate}\n")

    ownership = composition.ownership_map
    assert ownership.candidate_byte_length == len(composition.candidate_markdown.encode("utf-8"))
    assert ownership.records[0].byte_start == 0
    assert ownership.records[-1].byte_end == ownership.candidate_byte_length
    assert any(record.owner_kind == "authored" for record in ownership.records)

    repaired, action = apply_grounded_exact_removal(
        graph,
        source,
        composition,
        finding_id="duplicate-promotion",
        quoted_candidate_span=duplicate,
        instruction="Remove the duplicated promotional paragraph.",
    )

    assert duplicate not in repaired.candidate_markdown
    assert "Useful inherited product detail." in repaired.candidate_markdown
    assert action.action == "remove_exact"
    assert action.llm_author_calls == 0
    assert repaired.llm_call_count == composition.llm_call_count
    assert repaired.plan.repair_actions == (action,)
    assert repaired.ownership_map.candidate_sha256 == repaired.candidate_sha256


def test_exact_removal_fails_closed_when_quote_is_not_unique(tmp_path: Path) -> None:
    source = "# Widget\n\nUseful inherited product detail.\n"
    repeated = "Repeated paragraph."
    graph = _graph(tmp_path, source)
    composition = _composition(
        graph,
        source,
        f"{source.rstrip()}\n\n{repeated}\n\n{repeated}\n",
    )

    with pytest.raises(LLMError, match="one unique literal"):
        apply_grounded_exact_removal(
            graph,
            source,
            composition,
            finding_id="ambiguous",
            quoted_candidate_span=repeated,
            instruction="Remove the duplicated paragraph.",
        )


def test_exact_removal_fails_closed_for_structural_heading_quote(tmp_path: Path) -> None:
    source = "# Widget\n\nUseful inherited product detail.\n"
    candidate = f"{source.rstrip()}\n\n## Quick start\n\nDuplicated overview.\n"
    graph = _graph(tmp_path, source)
    composition = _composition(graph, source, candidate)

    with pytest.raises(LLMError, match="complete prose paragraph"):
        apply_grounded_exact_removal(
            graph,
            source,
            composition,
            finding_id="misgrounded-duplicate",
            quoted_candidate_span="## Quick start",
            instruction="Remove the duplicated overview paragraph.",
        )


def test_normalized_heading_retains_unique_source_batch_lineage(tmp_path: Path) -> None:
    source = "# Widget\n\n## 🚀 Examples\n\nUseful inherited product detail.\n"
    graph = _graph(tmp_path, source)
    composition = _composition(graph, source, source)
    candidate = composition.candidate_markdown.replace("## 🚀 Examples", "## Examples")

    ownership = build_candidate_span_ownership_map(
        graph,
        candidate,
        composition.plan.section_drafts,
    )
    candidate_bytes = candidate.encode("utf-8")
    heading_records = [
        record
        for record in ownership.records
        if b"## Examples" in candidate_bytes[record.byte_start : record.byte_end]
    ]

    assert len(heading_records) == 1
    assert heading_records[0].owner_kind == "normalizer"
    assert heading_records[0].batch_id == "batch-0001"
    assert heading_records[0].producer_segment_id == "model-proposed-segment"


def _graph(tmp_path: Path, source: str):
    root = tmp_path / "source"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Trusted Ownership Test")
    _git(root, "config", "user.email", "trusted-ownership@example.invalid")
    (root / "README.md").write_text(source, encoding="utf-8", newline="")
    _git(root, "add", "README.md")
    _git(root, "commit", "-m", "seed")
    entry = next(item for item in load_products() if item.org_repo == ORG_REPO)
    snapshot = capture_repository_snapshot(entry, root)
    return extract_trusted_readme_fact_graph(snapshot)


def _composition(graph, source: str, candidate: str):
    fact_ids = tuple(fact.fact_id for fact in graph.inherited_facts)
    inventory = tuple(
        TrustedSourceInventoryDecisionV1(
            fact_id=fact_id,
            action="rewrite",
            rationale="Retain the inherited unit in the candidate.",
        )
        for fact_id in fact_ids
    )
    segment = TrustedReadmeDraftSegmentV1(
        segment_id="model-proposed-segment",
        kind="authored",
        markdown=candidate,
        inherited_fact_ids=fact_ids,
    )
    tool = TrustedReadmeSectionToolDraftV1(
        editorial_summary="Compose the complete bounded candidate.",
        complete=True,
        source_inventory=inventory,
        segments=(segment,),
    )
    bound = TrustedReadmeSectionDraftV1(
        batch_id="batch-0001",
        editorial_summary=tool.editorial_summary,
        source_inventory=inventory,
        segments=(segment,),
        prompt_sha256=_HASH,
        tool_schema_sha256=_HASH,
        input_sha256=hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
        model="fixture-author",
        attempt_count=1,
    )
    return finalize_trusted_composition(
        graph,
        source,
        TrustedCompositionEnvelopeV1(),
        [tool],
        [bound],
        llm_call_count=1,
    )


def _git(root: Path, *args: str) -> None:
    result = run_git(list(args), cwd=root)
    assert result.returncode == 0, result.stderr
