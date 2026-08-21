"""Offline portfolio knowledge qualification orchestration contracts."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from readme_agent.facts.knowledge_qualification_models import (
    RepositoryKnowledgeQualificationV1,
)
from readme_agent.facts.portfolio_knowledge_qualification import qualify_portfolio_knowledge
from readme_agent.facts.portfolio_knowledge_selection import (
    PortfolioKnowledgeSelectionEntryV1,
    PortfolioKnowledgeSelectionV1,
)
from readme_agent.registry.models import ProductEntry


def _entry(repo: str, *, family: str, platform: str) -> ProductEntry:
    return ProductEntry(
        family=family,
        platform=platform,
        repo_name=repo,
        repo_url=f"https://github.com/acme/{repo}",
        clone_url=f"https://github.com/acme/{repo}.git",
        active=True,
        discovered_via="test",
        mode="disabled",
        ecosystem=platform,
        policy_profile="test",
    )


def test_portfolio_qualification_accounts_for_current_and_typed_entries(
    tmp_path: Path, monkeypatch
):
    processable = _entry("Aspose.Widget-FOSS-for-Python", family="widget", platform="python")
    disposed = _entry("Aspose.PSD-FOSS-for-Python", family="psd", platform="python")
    revision = "a" * 40
    generator = "b" * 64
    selection = PortfolioKnowledgeSelectionV1(
        generator_sha256=generator,
        denominator=2,
        processable=1,
        typed_dispositions=1,
        failed=0,
        total_claims=2,
        total_selected=1,
        entries=(
            PortfolioKnowledgeSelectionEntryV1(
                org_repo=processable.org_repo,
                family="widget",
                platform="python",
                source_revision=revision,
                status="current",
                claim_count=2,
                disposition_count=2,
                selected_count=1,
                rejected_count=1,
                freshness="current",
                detail="current",
            ),
            PortfolioKnowledgeSelectionEntryV1(
                org_repo=disposed.org_repo,
                family="psd",
                platform="python",
                source_revision=None,
                status="non_processable_no_implementation",
                detail="source empty",
            ),
        ),
    )
    receipt = tmp_path / "selection.json"
    receipt.write_text(selection.model_dump_json(indent=2), encoding="utf-8")
    products_path = tmp_path / "products.json"
    products_path.write_text("[]\n", encoding="utf-8")

    monkeypatch.setattr(
        "readme_agent.facts.portfolio_knowledge_qualification.load_products",
        lambda: (processable, disposed),
    )
    monkeypatch.setattr(
        "readme_agent.facts.portfolio_knowledge_qualification.PRODUCTS_PATH", products_path
    )
    monkeypatch.setattr(
        "readme_agent.facts.portfolio_knowledge_qualification.current_repository_knowledge_generator_sha256",
        lambda: generator,
    )
    monkeypatch.setattr(
        "readme_agent.facts.portfolio_knowledge_qualification.capture_repository_snapshot",
        lambda _entry, _baseline: SimpleNamespace(source_revision=revision),
    )

    def _qualified(entry, _snapshot, *, expected_revision, output_dir):
        return RepositoryKnowledgeQualificationV1(
            org_repo=entry.org_repo,
            family=entry.family,
            platform=entry.platform,
            source_revision=expected_revision,
            status="qualified",
            detail="passed",
            artifact_root=str(output_dir),
            candidate_generated=True,
            document_valid=True,
        )

    monkeypatch.setattr(
        "readme_agent.facts.portfolio_knowledge_qualification.qualify_repository_knowledge",
        _qualified,
    )
    output = tmp_path / "qualification"

    report = qualify_portfolio_knowledge(receipt, output_root=output)

    assert report.denominator == 2
    assert report.processable == 1
    assert report.typed_dispositions == 1
    assert report.candidate_generated == 1
    assert report.qualified_current_contract == 1
    assert report.llm_provider_calls == 0
    assert report.product_effects == 0
    persisted = json.loads((output / "portfolio-summary.json").read_text(encoding="utf-8"))
    assert persisted["gate_a_satisfied"] is False
    assert (output / "portfolio-summary.md").is_file()
    assert (output / "sha256sums.txt").is_file()


def test_portfolio_qualification_rejects_a_stale_generator(tmp_path: Path, monkeypatch):
    entry = _entry("Aspose.Widget-FOSS-for-Python", family="widget", platform="python")
    selection = PortfolioKnowledgeSelectionV1(
        generator_sha256="a" * 64,
        denominator=1,
        processable=0,
        typed_dispositions=1,
        failed=0,
        total_claims=0,
        total_selected=0,
        entries=(
            PortfolioKnowledgeSelectionEntryV1(
                org_repo=entry.org_repo,
                family="widget",
                platform="python",
                source_revision=None,
                status="non_processable_no_implementation",
                detail="test",
            ),
        ),
    )
    receipt = tmp_path / "selection.json"
    receipt.write_text(selection.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(
        "readme_agent.facts.portfolio_knowledge_qualification.load_products", lambda: (entry,)
    )
    monkeypatch.setattr(
        "readme_agent.facts.portfolio_knowledge_qualification.current_repository_knowledge_generator_sha256",
        lambda: "b" * 64,
    )

    try:
        qualify_portfolio_knowledge(receipt, output_root=tmp_path / "out")
    except ValueError as exc:
        assert "generator identity is stale" in str(exc)
    else:  # pragma: no cover - explicit fail-closed assertion
        raise AssertionError("stale generator was accepted")
