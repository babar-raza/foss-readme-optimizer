"""K3-3: `readme/idea_candidate.py::prepare_idea_fidelity_candidate` must
make the authoritative post-render `build_knowledge_application_report`
call with the real, final `document_plan` in scope -- the second,
superseding call `facts/knowledge_application_evidence.py`'s own module
docstring promises, and the one production call site that has operations,
candidate_content_provenance, and rendered candidate bytes all in scope
together (`supervisor/product_truth.py`'s own call happens pre-render, with
`document_plan=None`)."""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

from readme_agent.facts.migration import migrate_product_facts_v1
from readme_agent.facts.schema import ProductFactsV1
from readme_agent.readme import idea_candidate
from readme_agent.readme.document_plan import PresentationSpanAdoptionV1, ReadmeDocumentPlanV1


def _real_document_plan(candidate: str) -> ReadmeDocumentPlanV1:
    source = "# Immutable source\n"
    source_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return ReadmeDocumentPlanV1(
        org_repo="acme/widget",
        immutable_base_revision="a" * 40,
        facts_hash=hashlib.sha256(b"facts").hexdigest(),
        template_sha256=hashlib.sha256(b"template").hexdigest(),
        source_sha256=source_sha,
        adoption=PresentationSpanAdoptionV1(
            already_adopted=True,
            source_document_sha256=source_sha,
            source_inner_sha256=source_sha,
            source_inner_bytes=len(source.encode("utf-8")),
            preservation_check="byte_identical",
        ),
        operations=[],
        candidate_sha256=hashlib.sha256(candidate.encode("utf-8")).hexdigest(),
    )


def _wire_common_mocks(monkeypatch, tmp_path, *, candidate: str, document_plan):
    revision = "a" * 40
    snapshot_root = tmp_path / "snapshot"
    snapshot_root.mkdir()
    immutable_source = "# Immutable source\n"
    (snapshot_root / "README.md").write_text(immutable_source, encoding="utf-8")
    work_root = tmp_path / "work"
    work_root.mkdir()
    (work_root / "README.md").write_text(immutable_source, encoding="utf-8")
    snapshot = SimpleNamespace(
        root_path=snapshot_root,
        readme_path="README.md",
        source_revision=revision,
    )
    entry = SimpleNamespace(org="acme", repo_name="widget", family="widget", platform="java")
    facts = migrate_product_facts_v1(
        ProductFactsV1(
            org_repo="acme/widget",
            family="widget",
            platform="java",
            ecosystem="java",
        ),
        source_revision=revision,
    )

    monkeypatch.setattr(idea_candidate, "require_listed", lambda org_repo: entry)
    monkeypatch.setattr(idea_candidate, "current_repository_snapshot", lambda org_repo: snapshot)
    monkeypatch.setattr(idea_candidate, "verify_repository_snapshot", lambda value: None)
    monkeypatch.setattr(
        idea_candidate, "compute_tracked_content_hash", lambda root: "fresh-fingerprint"
    )
    monkeypatch.setattr(idea_candidate.paths, "work_dir", lambda org, repo: work_root)
    monkeypatch.setattr(idea_candidate, "ensure_work_clone", lambda *args, **kwargs: work_root)
    monkeypatch.setattr(idea_candidate, "neuter_push", lambda root: None)
    monkeypatch.setattr(idea_candidate, "install_pre_push_hook", lambda root: None)
    monkeypatch.setattr(
        idea_candidate, "verify_push_blocked", lambda root: SimpleNamespace(ok=True, detail="")
    )
    monkeypatch.setattr(idea_candidate, "load_runtime_link_inputs", lambda org_repo: (None, None))
    monkeypatch.setattr(
        idea_candidate,
        "build_readme_document_candidate",
        lambda *args, **kwargs: (candidate, document_plan),
    )
    monkeypatch.setattr(
        idea_candidate,
        "assess_readme_document",
        lambda *args, **kwargs: SimpleNamespace(model_dump=lambda mode: {}),
    )
    monkeypatch.setattr(
        idea_candidate,
        "build_readme_claim_map",
        lambda *args, **kwargs: SimpleNamespace(model_dump=lambda mode: {}),
    )
    return facts


def test_prepare_idea_fidelity_candidate_calls_report_with_the_real_document_plan(
    monkeypatch, tmp_path
):
    candidate = "# Immutable source\n\nVerified presentation.\n"
    document_plan = _real_document_plan(candidate)
    facts = _wire_common_mocks(
        monkeypatch, tmp_path, candidate=candidate, document_plan=document_plan
    )

    captured: dict = {}
    real_builder = idea_candidate.build_knowledge_application_report

    def spy(*args, **kwargs):
        captured["document_plan"] = kwargs.get("document_plan")
        captured["candidate_text"] = kwargs.get("candidate_text")
        captured["status"] = kwargs.get("status")
        return real_builder(*args, **kwargs)

    monkeypatch.setattr(idea_candidate, "build_knowledge_application_report", spy)

    idea_candidate.prepare_idea_fidelity_candidate("acme/widget", facts)

    assert captured["document_plan"] is document_plan
    assert captured["candidate_text"] == candidate
    assert captured["status"] == "final"


def test_prepare_idea_fidelity_candidate_return_dict_includes_final_knowledge_application(
    monkeypatch, tmp_path
):
    candidate = "# Immutable source\n\nVerified presentation.\n"
    document_plan = _real_document_plan(candidate)
    facts = _wire_common_mocks(
        monkeypatch, tmp_path, candidate=candidate, document_plan=document_plan
    )

    result = idea_candidate.prepare_idea_fidelity_candidate("acme/widget", facts)

    assert "knowledge_application" in result
    assert result["knowledge_application"]["status"] == "final"
    assert result["knowledge_application"]["candidate_sha256"] == document_plan.candidate_sha256
    assert result["knowledge_application"]["facts_hash"] == document_plan.facts_hash
