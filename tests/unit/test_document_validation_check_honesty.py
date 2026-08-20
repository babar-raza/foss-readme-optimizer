"""`validate_readme_document_candidate` must fail closed on a classified-
blocking aspose check that errored (raised, or returned an uninterpretable
result) -- previously invisible to every one of this function's 5 call sites
except the one local-POC acceptance path that separately re-derived this
from persisted check-coverage evidence after the fact. Deliberately
error-only, not skip: `check_banner_present`'s family/platform derivation
gap (GOV-014, `plans/backlog-post-poc.md`) makes it skip in nearly every
non-full-portfolio run, and gating on skip broke dozens of unrelated
synthetic-fixture tests when tried before."""

from __future__ import annotations

import json
from pathlib import Path

import readme_agent.readme.document_validation as document_validation_module
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.validation.aspose_checks_bridge import AsposeCheckResultV1

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROOF_PATH = (
    PROJECT_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-local-immutable-snapshot-and-facts-corrected-acquisition-2026-07-24"
    / "immutable-snapshot-and-product-facts-proof.json"
)


def _facts(org_repo: str) -> tuple[ProductFactsV2, str]:
    proof = json.loads(PROOF_PATH.read_text(encoding="utf-8"))
    pilot = next(item for item in proof["current_pilots"] if item["org_repo"] == org_repo)
    return (
        ProductFactsV2.model_validate(pilot["product_facts_v2"]),
        pilot["snapshot"]["source_revision"],
    )


def test_errored_blocking_check_fails_closed_in_the_shared_validator(monkeypatch):
    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _facts(org_repo)
    source = "# Aspose.Cells FOSS for Java\n\nSpreadsheet library for Java developers.\n"
    candidate, plan = build_readme_document_candidate(
        org_repo, source, facts, base_revision=revision
    )

    # A real, currently-classified-blocking check name, forced into
    # checks_errored -- proves the shared validator itself now reacts,
    # without depending on any one specific check's real invocation logic.
    from readme_agent.validation.aspose_checks_bridge import load_blocking_check_names

    blocking_name = sorted(load_blocking_check_names())[0]

    def _fake_run_aspose_checks(candidate_text, facts_arg):
        return AsposeCheckResultV1(
            valid=True,
            checks_run=(),
            checks_skipped=(),
            checks_errored=(blocking_name,),
            findings=(),
        )

    monkeypatch.setattr(document_validation_module, "run_aspose_checks", _fake_run_aspose_checks)

    decision = validate_readme_document_candidate(source, candidate, plan, facts)

    assert decision.valid is False
    assert decision.checks["aspose_checks_no_blocking_errors"] is False
    assert any(blocking_name in error for error in decision.errors)


def test_skipped_blocking_check_alone_does_not_fail_the_shared_validator(monkeypatch):
    """Regression guard: skip stays deliberately non-blocking here (unlike
    error) -- matches the existing, empirically-required precedent."""

    org_repo = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"
    facts, revision = _facts(org_repo)
    source = "# Aspose.Cells FOSS for Java\n\nSpreadsheet library for Java developers.\n"
    candidate, plan = build_readme_document_candidate(
        org_repo, source, facts, base_revision=revision
    )

    from readme_agent.validation.aspose_checks_bridge import load_blocking_check_names

    blocking_name = sorted(load_blocking_check_names())[0]

    def _fake_run_aspose_checks(candidate_text, facts_arg):
        return AsposeCheckResultV1(
            valid=True,
            checks_run=(),
            checks_skipped=(blocking_name,),
            checks_errored=(),
            findings=(),
        )

    monkeypatch.setattr(document_validation_module, "run_aspose_checks", _fake_run_aspose_checks)

    decision = validate_readme_document_candidate(source, candidate, plan, facts)

    assert decision.checks["aspose_checks_no_blocking_errors"] is True
    assert not any(blocking_name in error for error in decision.errors)
