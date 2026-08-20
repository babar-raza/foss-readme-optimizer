"""RUNTIME-TRUTH CLOSURE item B: the dashboard must never combine unrelated receipts merely
because each is the newest timestamp for its own stage.

Every scenario here writes a genuinely *incoherent* set of receipts (across campaigns, across
source revisions, across facts/candidate hashes, or with a broken predecessor chain) and asserts
acceptance is refused -- ACCEPTED_30_OF_30 must never be produced by silently splicing together
evidence that was never actually generated together.
"""

from __future__ import annotations

from readme_agent.supervisor.portfolio_proof_engine import registry_cohort
from readme_agent.supervisor.portfolio_proof_engine.contracts import campaign_id_for_mode
from readme_agent.supervisor.portfolio_proof_engine.dashboard import build_dashboard
from readme_agent.supervisor.portfolio_proof_engine.receipt_store import write_receipt
from tests.unit.portfolio_proof_engine_fixtures import make_entry, make_receipt
from tests.unit.test_portfolio_proof_engine_dashboard import (
    _CANDIDATE_HASH,
    _FACTS_HASH,
    _REV,
    _perfect_bundle_files,
    _runs_dir,
)

_CANARIES = campaign_id_for_mode("canaries")
_FLEET = campaign_id_for_mode("fleet")
_OLD_REV = "b" * 40
_NEW_REV = _REV
_OLD_TS = "2020-01-01T00:00:00+00:00"
_NEW_TS = "2026-01-01T00:00:00+00:00"


def _dashboard_for(tmp_path, monkeypatch, org_repo: str):
    entry = make_entry(org_repo=org_repo, repository_id=1)
    monkeypatch.setattr(registry_cohort, "load_products", lambda *a, **k: (entry,))
    result = build_dashboard(output_root=tmp_path / "proof")
    return result.rows[0]


def test_old_facts_ready_never_combines_with_a_newer_candidate(tmp_path, monkeypatch):
    _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    org_repo = "acme/old-facts-new-candidate"

    write_receipt(
        output_root,
        _CANARIES,
        make_receipt(
            org_repo=org_repo,
            stage="FACTS_READY",
            source_revision=_OLD_REV,
            facts_hash=_FACTS_HASH,
            generated_at=_OLD_TS,
        ),
    )
    write_receipt(
        output_root,
        _FLEET,
        make_receipt(
            org_repo=org_repo,
            stage="CANDIDATE_ASSEMBLED",
            source_revision=_NEW_REV,
            candidate_hash=_CANDIDATE_HASH,
            generated_at=_NEW_TS,
        ),
    )
    row = _dashboard_for(tmp_path, monkeypatch, org_repo)
    assert row.state != "ACCEPTED_30_OF_30"
    assert row.source_revision == _NEW_REV  # the stale-revision FACTS_READY never leaks in


def test_new_facts_never_combine_with_a_stale_review(tmp_path, monkeypatch):
    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    org_repo = "acme/new-facts-old-review"
    _perfect_bundle_files(runs_dir, org_repo)  # a real, otherwise-complete evidence bundle

    write_receipt(
        output_root,
        _CANARIES,
        make_receipt(
            org_repo=org_repo,
            stage="FACTS_READY",
            source_revision=_REV,
            facts_hash="9" * 64,
            generated_at=_NEW_TS,
        ),
    )
    write_receipt(
        output_root,
        _FLEET,
        make_receipt(
            org_repo=org_repo,
            stage="VISITOR_REVIEWED",
            source_revision=_REV,
            facts_hash=_FACTS_HASH,  # the *old* facts hash the stale review was actually bound to
            candidate_hash=_CANDIDATE_HASH,
            generated_at=_OLD_TS,
        ),
    )
    row = _dashboard_for(tmp_path, monkeypatch, org_repo)
    assert row.state != "ACCEPTED_30_OF_30"


def test_two_candidates_with_different_hashes_never_both_stand(tmp_path, monkeypatch):
    _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    org_repo = "acme/two-candidates"

    write_receipt(
        output_root,
        _CANARIES,
        make_receipt(
            org_repo=org_repo,
            stage="CANDIDATE_ASSEMBLED",
            source_revision=_REV,
            candidate_hash="1" * 64,
            generated_at=_OLD_TS,
        ),
    )
    write_receipt(
        output_root,
        _FLEET,
        make_receipt(
            org_repo=org_repo,
            stage="DETERMINISTIC_VALIDATED",
            source_revision=_REV,
            candidate_hash="2" * 64,
            generated_at=_NEW_TS,
        ),
    )
    row = _dashboard_for(tmp_path, monkeypatch, org_repo)
    assert row.state != "ACCEPTED_30_OF_30"
    # The newer candidate hash wins; the older, disagreeing one is not silently kept either.
    assert row.candidate_hash == "2" * 64


def test_changed_source_revision_drops_the_old_revisions_receipts_entirely(tmp_path, monkeypatch):
    _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    org_repo = "acme/revision-changed"

    write_receipt(
        output_root,
        _CANARIES,
        make_receipt(
            org_repo=org_repo,
            stage="ACCEPTED",
            source_revision=_OLD_REV,
            candidate_hash=_CANDIDATE_HASH,
            facts_hash=_FACTS_HASH,
            generated_at=_OLD_TS,
        ),
    )
    write_receipt(
        output_root,
        _FLEET,
        make_receipt(
            org_repo=org_repo,
            stage="INTAKE",
            source_revision=_NEW_REV,
            generated_at=_NEW_TS,
        ),
    )
    row = _dashboard_for(tmp_path, monkeypatch, org_repo)
    assert row.state != "ACCEPTED_30_OF_30"
    assert row.source_revision == _NEW_REV


def test_a_broken_predecessor_chain_is_dropped_despite_a_later_timestamp(tmp_path, monkeypatch):
    _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    org_repo = "acme/broken-predecessor"

    write_receipt(
        output_root,
        _CANARIES,
        make_receipt(
            org_repo=org_repo,
            stage="CANDIDATE_ASSEMBLED",
            source_revision=_REV,
            candidate_hash=_CANDIDATE_HASH,
            generated_at=_OLD_TS,
        ),
    )
    write_receipt(
        output_root,
        _FLEET,
        make_receipt(
            org_repo=org_repo,
            stage="DETERMINISTIC_VALIDATED",
            source_revision=_REV,
            candidate_hash=_CANDIDATE_HASH,
            generated_at=_NEW_TS,
            predecessor_receipt_hash="deadbeef" * 8,  # matches nothing ever written
        ),
    )
    row = _dashboard_for(tmp_path, monkeypatch, org_repo)
    assert row.state != "ACCEPTED_30_OF_30"


def test_individually_complete_30_of_30_files_from_an_incompatible_run_never_accept(
    tmp_path, monkeypatch
):
    """The strongest adversarial case: real, otherwise-fully-passing evidence *files* exist on
    disk for an old candidate -- but the coherent receipt chain now points at a newer revision
    with no candidate evidence at all, so those old files are never even read."""

    runs_dir = _runs_dir(tmp_path, monkeypatch)
    output_root = tmp_path / "proof"
    org_repo = "acme/stale-perfect-files"
    _perfect_bundle_files(
        runs_dir, org_repo, source_revision=_OLD_REV, candidate_hash=_CANDIDATE_HASH
    )

    write_receipt(
        output_root,
        _CANARIES,
        make_receipt(
            org_repo=org_repo,
            stage="ACCEPTED",
            source_revision=_OLD_REV,
            candidate_hash=_CANDIDATE_HASH,
            facts_hash=_FACTS_HASH,
            generated_at=_OLD_TS,
        ),
    )
    write_receipt(
        output_root,
        _FLEET,
        make_receipt(
            org_repo=org_repo,
            stage="INTAKE",
            source_revision=_NEW_REV,
            generated_at=_NEW_TS,
        ),
    )
    row = _dashboard_for(tmp_path, monkeypatch, org_repo)
    assert row.state != "ACCEPTED_30_OF_30"
    assert row.source_revision == _NEW_REV
