"""Blocked presentation plans leave an offline-debuggable diagnostic snapshot.

2026-08-18 mission recovery: a `presentation_plan:blocked` member left no
recoverable per-claim analysis anywhere (durable state keeps only the failure
message string), so diagnosing any claim-accountability block required
re-running the whole pipeline live just to look at an analysis it had already
computed once.
"""

from __future__ import annotations

import json

from readme_agent.specialists.readme_presentation import _persist_blocked_plan_diagnostics


def test_blocked_plan_diagnostics_write_claims_and_candidate(monkeypatch, tmp_path):
    import readme_agent.paths as paths
    import readme_agent.repository_snapshot as repository_snapshot

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        repository_snapshot, "current_repository_snapshot", lambda org_repo: object()
    )
    # `claim_accountability`/`source_claim_resolutions`/`composition_ledger`/
    # `candidate_sha256` live on `readme_document_plan` (ReadmeDocumentPlanV1) in the
    # real capability output (build_presentation_plan.py), not on the flat
    # `presentation_plan` key (RepositoryPresentationPlanV1 has no such fields).
    record = {
        "presentation_plan": {"candidate_sha256": "wrong-nest-c" * 5},
        "readme_document_plan": {
            "claim_accountability": {"claims": [{"claim_id": "source:claim:1:aa"}]},
            "source_claim_resolutions": [{"claim_id": "source:claim:1:aa"}],
            "candidate_sha256": "c" * 64,
            "composition_ledger": {
                "segments": [{"segment_id": "composition.segment.0032", "authority": "unbound"}]
            },
        },
        "document_validation": {"errors": ["claim accountability has 1 blocking claim(s)"]},
    }

    _persist_blocked_plan_diagnostics("org/repo", record, {"final_text": "# Candidate\n\nbody\n"})

    diagnostics = tmp_path / "runs" / "readme-poc" / "org__repo" / "diagnostics"
    payload = json.loads(
        (diagnostics / "blocked-presentation-plan.json").read_text(encoding="utf-8")
    )
    assert payload["claim_accountability"]["claims"][0]["claim_id"] == "source:claim:1:aa"
    assert payload["source_claim_resolutions"][0]["claim_id"] == "source:claim:1:aa"
    assert payload["candidate_sha256"] == "c" * 64
    assert payload["composition_ledger"]["segments"][0]["segment_id"] == (
        "composition.segment.0032"
    )
    assert payload["document_validation"]["errors"]
    assert (
        (diagnostics / "blocked-candidate.md").read_text(encoding="utf-8").startswith("# Candidate")
    )


def test_no_bound_snapshot_writes_nothing(monkeypatch, tmp_path):
    """The blocked branch runs in unit tests against fixture repos with no
    snapshot scope; diagnostics must never pollute the real runs/ tree from
    a test (found live: a fixture repo's diagnostics landed in runs/)."""

    import readme_agent.paths as paths
    import readme_agent.repository_snapshot as repository_snapshot

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(repository_snapshot, "current_repository_snapshot", lambda org_repo: None)

    _persist_blocked_plan_diagnostics("org/repo", {"presentation_plan": {}}, None)

    assert not (tmp_path / "runs").exists()


def test_blocked_plan_diagnostics_failure_is_non_fatal(monkeypatch, capsys):
    import readme_agent.paths as paths
    import readme_agent.repository_snapshot as repository_snapshot

    monkeypatch.setattr(
        repository_snapshot, "current_repository_snapshot", lambda org_repo: object()
    )
    monkeypatch.setattr(
        paths,
        "readme_poc_root",
        lambda: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    _persist_blocked_plan_diagnostics("org/repo", {}, None)  # must not raise

    assert "non-fatal" in capsys.readouterr().err


def test_blocked_factuality_diagnostics_write_the_full_payload(monkeypatch, tmp_path):
    import readme_agent.paths as paths
    import readme_agent.repository_snapshot as repository_snapshot
    from readme_agent.specialists.readme_presentation import (
        _persist_blocked_factuality_diagnostics,
    )

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(
        repository_snapshot, "current_repository_snapshot", lambda org_repo: object()
    )

    class _FakeFactuality:
        def model_dump(self, mode="json"):
            return {"valid": False, "claim_conflicts": [], "protected_content_losses": ["x"]}

    _persist_blocked_factuality_diagnostics(
        "org/repo", _FakeFactuality(), {"final_text": "# Candidate\n\nbody\n"}
    )

    diagnostics = tmp_path / "runs" / "readme-poc" / "org__repo" / "diagnostics"
    payload = json.loads((diagnostics / "blocked-factuality.json").read_text(encoding="utf-8"))
    assert payload["factuality"]["protected_content_losses"] == ["x"]
    assert (
        (diagnostics / "blocked-candidate.md").read_text(encoding="utf-8").startswith("# Candidate")
    )


def test_blocked_factuality_diagnostics_no_snapshot_writes_nothing(monkeypatch, tmp_path):
    import readme_agent.paths as paths
    import readme_agent.repository_snapshot as repository_snapshot
    from readme_agent.specialists.readme_presentation import (
        _persist_blocked_factuality_diagnostics,
    )

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    monkeypatch.setattr(repository_snapshot, "current_repository_snapshot", lambda org_repo: None)

    _persist_blocked_factuality_diagnostics("org/repo", {"valid": False}, None)

    assert not (tmp_path / "runs").exists()


def test_blocked_factuality_diagnostics_failure_is_non_fatal(monkeypatch, capsys):
    import readme_agent.repository_snapshot as repository_snapshot
    from readme_agent.specialists.readme_presentation import (
        _persist_blocked_factuality_diagnostics,
    )

    monkeypatch.setattr(
        repository_snapshot, "current_repository_snapshot", lambda org_repo: object()
    )
    monkeypatch.setattr(
        "readme_agent.paths.readme_poc_root",
        lambda: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    _persist_blocked_factuality_diagnostics("org/repo", {"valid": False}, None)  # must not raise

    assert "non-fatal" in capsys.readouterr().err
