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

    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    record = {
        "presentation_plan": {
            "claim_accountability": {"claims": [{"claim_id": "source:claim:1:aa"}]},
            "source_claim_resolutions": [{"claim_id": "source:claim:1:aa"}],
            "candidate_sha256": "c" * 64,
        },
        "document_validation": {"errors": ["claim accountability has 1 blocking claim(s)"]},
    }

    _persist_blocked_plan_diagnostics("org/repo", record, {"final_text": "# Candidate\n\nbody\n"})

    diagnostics = tmp_path / "runs" / "readme-poc" / "org__repo" / "diagnostics"
    payload = json.loads(
        (diagnostics / "blocked-presentation-plan.json").read_text(encoding="utf-8")
    )
    assert payload["claim_accountability"]["claims"][0]["claim_id"] == "source:claim:1:aa"
    assert payload["document_validation"]["errors"]
    assert (
        (diagnostics / "blocked-candidate.md").read_text(encoding="utf-8").startswith("# Candidate")
    )


def test_blocked_plan_diagnostics_failure_is_non_fatal(monkeypatch, capsys):
    import readme_agent.paths as paths

    monkeypatch.setattr(
        paths,
        "readme_poc_root",
        lambda: (_ for _ in ()).throw(OSError("disk unavailable")),
    )

    _persist_blocked_plan_diagnostics("org/repo", {}, None)  # must not raise

    assert "non-fatal" in capsys.readouterr().err
