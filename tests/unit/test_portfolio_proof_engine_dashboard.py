"""Dashboard: a read-and-report join over receipts, rubric results, and evidence bundles.

Proves every MANDATORY TESTS bullet: all five states resolve correctly; the 33/31/2 registry
denominator; a missing LICENSE never causes a skip; a named facts surface survives into
BLOCKED_FACTS; 29/30 is rejected (never rounded); a 30/30 candidate with a hard disqualifier is
rejected; a 30/30 candidate with missing extra-prerequisite evidence is incomplete; hash/revision
mismatches can never accept; an errored or skipped applicable blocking check can never accept; an
invalid disposition ledger or claim-accountability map can never accept; provisional/error-bearing
K3 evidence can never accept; a rejected independent reviewer can never accept; only the complete
evidence chain produces ACCEPTED_30_OF_30; summary counts reconcile exactly with no double count;
and rerunning against identical receipts is byte-identical.
"""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.supervisor.portfolio_proof_engine import dashboard as dashboard_module
from readme_agent.supervisor.portfolio_proof_engine import registry_cohort
from readme_agent.supervisor.portfolio_proof_engine.contracts import campaign_id_for_mode
from readme_agent.supervisor.portfolio_proof_engine.dashboard import build_dashboard
from readme_agent.supervisor.portfolio_proof_engine.receipt_store import write_receipt
from tests.unit.portfolio_proof_engine_fixtures import make_entry, make_receipt

_REV = "a" * 40
_CANDIDATE_HASH = "c" * 64
_FACTS_HASH = "f" * 64
_CANARY_CAMPAIGN = campaign_id_for_mode("canaries")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _bundle_dir(runs_dir: Path, org_repo: str, source_revision: str = _REV) -> Path:
    org, repo = org_repo.split("/", maxsplit=1)
    return runs_dir / "readme-poc" / f"{org}__{repo}" / source_revision


def _perfect_bundle_files(
    runs_dir: Path,
    org_repo: str,
    *,
    source_revision: str = _REV,
    candidate_hash: str = _CANDIDATE_HASH,
    check_overrides: dict | None = None,
    validation_overrides: dict | None = None,
    manifest_overrides: dict | None = None,
    knowledge_overrides: dict | None = None,
    factual_overrides: dict | None = None,
    visitor_overrides: dict | None = None,
    claim_map_overrides: dict | None = None,
    reconciliation_overrides: dict | None = None,
    check_coverage_overrides: dict | None = None,
    no_op_overrides: dict | None = None,
    omit: set[str] | None = None,
) -> None:
    """Write a complete, fully-passing evidence bundle for one candidate -- every ACCEPTED_30_OF_30
    prerequisite satisfied. Individual tests mutate exactly one artifact via the *_overrides/omit
    parameters to break exactly one thing."""

    omit = omit or set()
    bundle_dir = _bundle_dir(runs_dir, org_repo, source_revision)

    checks = {
        "word_count": True,
        "prohibited_terms": True,
        "link_whitelist": True,
        "change_boundary": True,
        "talking_points": True,
        "referential_integrity": True,
        "idempotency": True,
        "prominence": True,
        "product_first_opening": True,
        "commercial_mention_discipline": True,
        **(check_overrides or {}),
    }
    validation = {
        "valid": True,
        "errors": [],
        "checks": checks,
        **(validation_overrides or {}),
    }
    manifest = {
        "source_revision": source_revision,
        "facts_hash": _FACTS_HASH,
        "candidate_hash": candidate_hash,
        **(manifest_overrides or {}),
    }
    knowledge_application = {
        "status": "final",
        "final_dispositions": [
            {"global_claim_id": "x", "disposition": "rendered_with_exact_spans"}
        ],
        "candidate_sha256": candidate_hash,
        **(knowledge_overrides or {}),
    }
    factual_review = {"verdict": "ACCEPT", **(factual_overrides or {})}
    visitor_review = {"verdict": "ACCEPT", **(visitor_overrides or {})}
    claim_map = {"valid": True, **(claim_map_overrides or {})}
    reconciliation = {"unresolved": 0, "errors": 0, **(reconciliation_overrides or {})}
    check_coverage = {"skipped": 0, "errored": 0, "failed": 0, **(check_coverage_overrides or {})}
    facts = {"some": "facts"}
    no_op_proof = {"verdict": "RENDER_REPRODUCIBLE", **(no_op_overrides or {})}

    artifacts = {
        "manifest": (bundle_dir / "manifest.json", manifest),
        "deterministic_validation": (
            bundle_dir / "review" / "deterministic-validation.json",
            validation,
        ),
        "knowledge_application": (bundle_dir / "knowledge-application.json", knowledge_application),
        "factual_review": (bundle_dir / "review" / "factual-plan-review.json", factual_review),
        "visitor_review": (bundle_dir / "review" / "blind-quality-review.json", visitor_review),
        "claim_map": (bundle_dir / "candidate" / "claim-map.json", claim_map),
        "reconciliation": (bundle_dir / "candidate" / "readme-reconciliation.json", reconciliation),
        "check_coverage": (bundle_dir / "candidate" / "check-coverage.json", check_coverage),
        "facts": (bundle_dir / "facts" / "product-facts.json", facts),
        "no_op_proof": (bundle_dir / "review" / "no-op-proof.json", no_op_proof),
    }
    for key, (path, data) in artifacts.items():
        if key in omit:
            continue
        _write_json(path, data)


def _accepted_receipt_chain(
    output_root: Path, org_repo: str, *, candidate_hash: str = _CANDIDATE_HASH
):
    """The minimum receipt trail needed for the dashboard to enter its candidate-evaluation
    branch: a CANDIDATE_ASSEMBLED-or-later stage receipt bound to the same source/candidate
    identity the evidence files on disk carry."""

    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(
            org_repo=org_repo,
            stage="VISITOR_REVIEWED",
            source_revision=_REV,
            candidate_hash=candidate_hash,
            facts_hash=_FACTS_HASH,
        ),
    )


def _dashboard(
    tmp_path: Path,
    monkeypatch,
    entries: list,
    *,
    output_root: Path | None = None,
):
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    return build_dashboard(output_root=output_root or (tmp_path / "proof"))


def _runs_dir(tmp_path: Path, monkeypatch) -> Path:
    runs_dir = tmp_path / "runs"
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(runs_dir))
    return runs_dir


# ---------------------------------------------------------------------------
# 1. All five dashboard states
# ---------------------------------------------------------------------------


def test_all_five_dashboard_states(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"

    skipped = make_entry(org_repo="acme/skipped", repository_id=1)
    blocked = make_entry(org_repo="acme/blocked", repository_id=2)
    incomplete = make_entry(org_repo="acme/incomplete", repository_id=3)
    rejected = make_entry(org_repo="acme/rejected", repository_id=4)
    accepted = make_entry(org_repo="acme/accepted", repository_id=5)

    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(org_repo="acme/skipped", stage="TERMINAL_SKIPPED"),
    )
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(
            org_repo="acme/blocked",
            stage="BLOCKED_INPUT",
            status="FAILED",
            failure_reason="facts collection failed: no manifest detected",
        ),
    )
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(org_repo="acme/incomplete", stage="FACTS_READY", source_revision=_REV),
    )

    _perfect_bundle_files(
        runs_dir, "acme/rejected", check_overrides={"product_first_opening": False}
    )
    _accepted_receipt_chain(output_root, "acme/rejected")

    _perfect_bundle_files(runs_dir, "acme/accepted")
    _accepted_receipt_chain(output_root, "acme/accepted")

    result = _dashboard(
        tmp_path,
        monkeypatch,
        [skipped, blocked, incomplete, rejected, accepted],
        output_root=output_root,
    )
    by_repo = {row.org_repo: row.state for row in result.rows}
    assert by_repo == {
        "acme/skipped": "SKIPPED_NON_SUBSTANTIVE",
        "acme/blocked": "BLOCKED_FACTS",
        "acme/incomplete": "CANDIDATE_INCOMPLETE",
        "acme/rejected": "CANDIDATE_REJECTED",
        "acme/accepted": "ACCEPTED_30_OF_30",
    }


# ---------------------------------------------------------------------------
# 2. Exactly 33 registry rows: 31 processable plus two skipped
# ---------------------------------------------------------------------------


def test_real_registry_resolves_to_33_rows_31_processable_2_skipped(tmp_path, monkeypatch):
    _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entries = registry_cohort.load_portfolio_entries()
    assert len(entries) == 33
    skip_candidates = [entry for entry in entries if entry.family == "psd"]
    assert len(skip_candidates) == 2
    for entry in skip_candidates:
        write_receipt(
            output_root,
            _CANARY_CAMPAIGN,
            make_receipt(org_repo=entry.org_repo, stage="TERMINAL_SKIPPED"),
        )

    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: tuple(entries))
    result = build_dashboard(output_root=output_root)

    assert len(result.rows) == 33
    assert {row.org_repo for row in result.rows} == {entry.org_repo for entry in entries}
    assert result.summary.total == 33
    assert result.summary.terminal_skipped == 2
    assert result.summary.processable == 31


# ---------------------------------------------------------------------------
# 3. Missing LICENSE does not cause skipping
# ---------------------------------------------------------------------------


def test_missing_license_does_not_cause_skipping(tmp_path, monkeypatch):
    """The dashboard reflects whatever the intake receipt already says -- it never re-derives or
    second-guesses skip status from LICENSE presence. A repo intake-classified as processable
    (even though its own reason text mentions a missing LICENSE) is never
    SKIPPED_NON_SUBSTANTIVE."""

    _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/no-license", repository_id=1)
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(org_repo="acme/no-license", stage="INTAKE", source_revision=_REV),
    )
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state != "SKIPPED_NON_SUBSTANTIVE"
    assert row.processability == "PROCESSABLE"


# ---------------------------------------------------------------------------
# 4. A named facts surface is retained in BLOCKED_FACTS
# ---------------------------------------------------------------------------


def test_blocked_facts_retains_the_exact_named_surface(tmp_path, monkeypatch):
    _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/blocked", repository_id=1)
    reason = "dependency manifest resolution failed: pyproject.toml declares no build-system"
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(
            org_repo="acme/blocked", stage="BLOCKED_INPUT", status="FAILED", failure_reason=reason
        ),
    )
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state == "BLOCKED_FACTS"
    assert row.blocked_surface == reason


# ---------------------------------------------------------------------------
# 5. A 29/30 candidate is rejected (never rounded)
# ---------------------------------------------------------------------------


def test_29_of_30_is_rejected_never_rounded(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/near-miss", repository_id=1)
    # product_first_opening is criterion 17's sole, unique signal -- flipping it fails exactly
    # one criterion and nothing else.
    _perfect_bundle_files(
        runs_dir, "acme/near-miss", check_overrides={"product_first_opening": False}
    )
    _accepted_receipt_chain(output_root, "acme/near-miss")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.score == 29
    assert row.state == "CANDIDATE_REJECTED"
    assert any("17" in gate for gate in row.failed_gates)


# ---------------------------------------------------------------------------
# 6. A 30/30 candidate with one hard disqualifier is rejected
# ---------------------------------------------------------------------------


def test_30_of_30_with_hard_disqualifier_is_rejected(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/disqualified", repository_id=1)
    # candidate_hash mismatch in the manifest is both a rubric hard disqualifier AND leaves every
    # rubric criterion itself satisfiable -- proving the disqualifier overrides a full numeric 30.
    _perfect_bundle_files(
        runs_dir, "acme/disqualified", manifest_overrides={"candidate_hash": "d" * 64}
    )
    _accepted_receipt_chain(output_root, "acme/disqualified")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state == "CANDIDATE_REJECTED"
    assert row.hard_disqualifier_count >= 1


# ---------------------------------------------------------------------------
# 7. A 30/30 candidate with missing evidence is incomplete
# ---------------------------------------------------------------------------


def test_30_of_30_with_missing_extra_evidence_is_incomplete(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/sparse", repository_id=1)
    # Every one of the 30 scored criteria passes (manifest has no facts_hash omission that would
    # zero a criterion), but the extra source-revision cross-check has nothing to compare against
    # because the manifest omits source_revision entirely.
    _perfect_bundle_files(runs_dir, "acme/sparse", manifest_overrides={"source_revision": None})
    _accepted_receipt_chain(output_root, "acme/sparse")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.score == 30
    assert row.hard_disqualifier_count == 0
    assert row.state == "CANDIDATE_INCOMPLETE"


# ---------------------------------------------------------------------------
# 8. A candidate-hash mismatch cannot accept
# ---------------------------------------------------------------------------


def test_candidate_hash_mismatch_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/hash-mismatch", repository_id=1)
    _perfect_bundle_files(
        runs_dir, "acme/hash-mismatch", knowledge_overrides={"candidate_sha256": "e" * 64}
    )
    _accepted_receipt_chain(output_root, "acme/hash-mismatch")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 9. A source-revision mismatch cannot accept
# ---------------------------------------------------------------------------


def test_source_revision_mismatch_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/rev-mismatch", repository_id=1)
    _perfect_bundle_files(
        runs_dir, "acme/rev-mismatch", manifest_overrides={"source_revision": "b" * 40}
    )
    _accepted_receipt_chain(output_root, "acme/rev-mismatch")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state != "ACCEPTED_30_OF_30"
    assert row.state == "CANDIDATE_REJECTED"


# ---------------------------------------------------------------------------
# 10. An errored applicable blocking check cannot accept
# ---------------------------------------------------------------------------


def test_errored_blocking_check_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/check-errored", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/check-errored", check_coverage_overrides={"errored": 1})
    _accepted_receipt_chain(output_root, "acme/check-errored")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 11. A skipped applicable blocking check cannot accept
# ---------------------------------------------------------------------------


def test_skipped_blocking_check_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/check-skipped", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/check-skipped", check_coverage_overrides={"skipped": 1})
    _accepted_receipt_chain(output_root, "acme/check-skipped")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 12. An invalid disposition ledger cannot accept
# ---------------------------------------------------------------------------


def test_invalid_disposition_ledger_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/dropped-content", repository_id=1)
    _perfect_bundle_files(
        runs_dir, "acme/dropped-content", reconciliation_overrides={"unexplained_drops": 2}
    )
    _accepted_receipt_chain(output_root, "acme/dropped-content")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 13. An invalid claim-accountability map cannot accept
# ---------------------------------------------------------------------------


def test_invalid_claim_map_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/bad-claim-map", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/bad-claim-map", claim_map_overrides={"valid": False})
    _accepted_receipt_chain(output_root, "acme/bad-claim-map")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 14. Provisional or error-bearing knowledge-application evidence cannot accept
# ---------------------------------------------------------------------------


def test_provisional_knowledge_application_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/provisional-k3", repository_id=1)
    _perfect_bundle_files(
        runs_dir, "acme/provisional-k3", knowledge_overrides={"status": "provisional"}
    )
    _accepted_receipt_chain(output_root, "acme/provisional-k3")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 15. A rejected independent reviewer cannot accept
# ---------------------------------------------------------------------------


def test_rejected_factual_review_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/factual-reject", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/factual-reject", factual_overrides={"verdict": "REJECT"})
    _accepted_receipt_chain(output_root, "acme/factual-reject")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state != "ACCEPTED_30_OF_30"
    assert row.factual_review_result == "REJECT"


def test_rejected_visitor_review_cannot_accept(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/visitor-reject", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/visitor-reject", visitor_overrides={"verdict": "REJECT"})
    _accepted_receipt_chain(output_root, "acme/visitor-reject")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    assert result.rows[0].state != "ACCEPTED_30_OF_30"


# ---------------------------------------------------------------------------
# 16. Only the complete evidence chain produces ACCEPTED_30_OF_30
# ---------------------------------------------------------------------------


def test_only_the_complete_evidence_chain_produces_accepted(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/complete", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/complete")
    _accepted_receipt_chain(output_root, "acme/complete")
    result = _dashboard(tmp_path, monkeypatch, [entry], output_root=output_root)
    row = result.rows[0]
    assert row.state == "ACCEPTED_30_OF_30"
    assert row.score == 30
    assert row.hard_disqualifier_count == 0
    assert row.failed_gates == ()


# ---------------------------------------------------------------------------
# 17. Summary counts equal the actual row states, no double count
# ---------------------------------------------------------------------------


def test_summary_counts_reconcile_exactly(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entries = [
        make_entry(org_repo="acme/skipped", repository_id=1),
        make_entry(org_repo="acme/blocked", repository_id=2),
        make_entry(org_repo="acme/incomplete", repository_id=3),
        make_entry(org_repo="acme/rejected", repository_id=4),
        make_entry(org_repo="acme/accepted", repository_id=5),
    ]
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(org_repo="acme/skipped", stage="TERMINAL_SKIPPED"),
    )
    write_receipt(
        output_root,
        _CANARY_CAMPAIGN,
        make_receipt(
            org_repo="acme/blocked", stage="BLOCKED_INPUT", status="FAILED", failure_reason="x"
        ),
    )
    _perfect_bundle_files(runs_dir, "acme/rejected", check_overrides={"word_count": False})
    _accepted_receipt_chain(output_root, "acme/rejected")
    _perfect_bundle_files(runs_dir, "acme/accepted")
    _accepted_receipt_chain(output_root, "acme/accepted")

    result = _dashboard(tmp_path, monkeypatch, entries, output_root=output_root)
    assert len(result.rows) == 5
    assert len({row.org_repo for row in result.rows}) == 5
    assert result.summary.total == 5
    assert result.summary.terminal_skipped == 1
    assert result.summary.blocked_facts == 1
    assert result.summary.candidate_incomplete == 1
    assert result.summary.candidate_rejected == 1
    assert result.summary.accepted_30_of_30 == 1
    assert (
        result.summary.terminal_skipped
        + result.summary.blocked_facts
        + result.summary.candidate_incomplete
        + result.summary.candidate_rejected
        + result.summary.accepted_30_of_30
        == result.summary.total
    )


# ---------------------------------------------------------------------------
# 18. Rerunning on identical receipts is byte-identical
# ---------------------------------------------------------------------------


def test_rerun_on_identical_receipts_is_byte_identical(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    entry = make_entry(org_repo="acme/stable", repository_id=1)
    _perfect_bundle_files(runs_dir, "acme/stable")
    _accepted_receipt_chain(output_root, "acme/stable")

    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: (entry,))
    first = build_dashboard(output_root=output_root)
    second = build_dashboard(output_root=output_root)
    assert first.model_dump_json() == second.model_dump_json()


def test_dashboard_module_has_no_new_scoring_system(tmp_path, monkeypatch):
    """Sanity guard for the "never a second scoring system" constraint: the dashboard module's
    only rubric-shaped import is the existing `rubric.score_candidate`, never a redefinition."""

    assert dashboard_module.score_candidate.__module__ == (
        "readme_agent.supervisor.portfolio_proof_engine.rubric"
    )
