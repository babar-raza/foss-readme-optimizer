"""PF04 external-fact receipts must be current and dependency-bound."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from readme_agent.supervisor.proven_transaction_runner import pf04_case_evidence
from readme_agent.supervisor.proven_transaction_runner.pf04_case_evidence import (
    ExternalFactReplayCaseV1,
)


def _case() -> ExternalFactReplayCaseV1:
    return ExternalFactReplayCaseV1(
        org_repo="acme/widget",
        source_revision="a" * 40,
        expected_surfaces=("example.minimal",),
    )


def test_current_fact_receipt_rejects_any_stale_contract_axis(monkeypatch):
    contract = SimpleNamespace(
        canonical_hash=lambda: "b" * 64,
        component_hashes={"facts": "c" * 64},
    )
    monkeypatch.setattr(
        pf04_case_evidence,
        "require_listed",
        lambda _repo: SimpleNamespace(ecosystem="python", family="widget"),
    )
    monkeypatch.setattr(
        pf04_case_evidence,
        "current_fact_acceptance_contract",
        lambda _ecosystem, _family: contract,
    )
    monkeypatch.setattr(
        pf04_case_evidence,
        "local_verification_contract_hash",
        lambda _ecosystem: "d" * 64,
    )
    manifest = {
        "org_repo": "acme/widget",
        "source_revision": "a" * 40,
        "fact_acceptance_contract_hash": "b" * 64,
        "fact_acceptance_component_hashes": {"facts": "c" * 64},
        "local_verification_contract_hash": "d" * 64,
        "lifecycle_status": "BLOCKED_MISSING_EVIDENCE",
    }

    pf04_case_evidence.require_current_fact_receipt(_case(), manifest)
    for field in (
        "fact_acceptance_contract_hash",
        "fact_acceptance_component_hashes",
        "local_verification_contract_hash",
    ):
        stale = dict(manifest)
        stale[field] = "stale"
        with pytest.raises(ValueError, match=field):
            pf04_case_evidence.require_current_fact_receipt(_case(), stale)


def test_missing_persisted_resolution_fails_closed(tmp_path: Path):
    findings = tmp_path / "findings.json"
    findings.write_text(json.dumps([{"finding_id": "missing-resolution"}]), encoding="utf-8")

    with pytest.raises(ValueError, match="persisted external decisions drifted"):
        pf04_case_evidence._load_persisted_decisions(_case(), findings)
