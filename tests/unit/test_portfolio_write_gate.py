"""TW-01 -- remote writes require BOTH a portfolio-wide receipt AND a per-repo grant."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import yaml

from readme_agent.authorization.portfolio_write_gate import (
    PortfolioApprovalReceiptV1,
    RemoteWriteBlockedError,
    assert_remote_write_authorized,
    load_portfolio_approval_receipt,
    rejection_log_path,
)

ORG_REPO = "aspose-cells-foss/Aspose.Cells-FOSS-for-Java"


def _write_receipt(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "portfolio_inventory_revision": "sha256:" + "a" * 64,
                "approved_at": datetime.now(UTC).isoformat(),
                "approval_note": "fixture approval",
            }
        ),
        encoding="utf-8",
    )


def _write_authorization_record(authorization_dir: Path, org_repo: str) -> None:
    org, _, repo = org_repo.partition("/")
    authorization_dir.mkdir(parents=True, exist_ok=True)
    (authorization_dir / f"{org}__{repo}.yml").write_text(
        yaml.safe_dump(
            {
                "repository": org_repo,
                "effect_classes": ["PR_CREATE_OR_UPDATE"],
                "branch_pattern": "readme-agent/*",
                "approving_identity": "fixture-owner",
                "rollback": "close the PR and delete the branch",
                "expiration": None,
            }
        ),
        encoding="utf-8",
    )


def test_blocked_when_no_portfolio_receipt_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_REJECTION_LOG_PATH", str(tmp_path / "rejected.jsonl"))
    missing_receipt = tmp_path / "no-such-receipt.json"

    with pytest.raises(RemoteWriteBlockedError, match="no portfolio-wide approval receipt"):
        assert_remote_write_authorized(ORG_REPO, "PR_CREATE_OR_UPDATE", receipt_dir=missing_receipt)

    rejected = json.loads(rejection_log_path().read_text(encoding="utf-8").strip())
    assert rejected["org_repo"] == ORG_REPO
    assert "portfolio" in rejected["reason"]


def test_blocked_when_receipt_exists_but_repo_has_no_grant(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_REJECTION_LOG_PATH", str(tmp_path / "rejected.jsonl"))
    monkeypatch.setenv("README_AGENT_AUTHORIZATION_DIR", str(tmp_path / "config" / "authorization"))
    receipt = tmp_path / "receipt.json"
    _write_receipt(receipt)
    # No AuthorizationRecordV1 written -- the empty-registry, fail-closed default.

    with pytest.raises(RemoteWriteBlockedError, match="no AuthorizationRecordV1 grant"):
        assert_remote_write_authorized(ORG_REPO, "PR_CREATE_OR_UPDATE", receipt_dir=receipt)


def test_allowed_only_when_both_gates_are_satisfied(tmp_path, monkeypatch):
    authorization_dir = tmp_path / "config" / "authorization"
    monkeypatch.setenv("README_AGENT_AUTHORIZATION_DIR", str(authorization_dir))
    receipt = tmp_path / "receipt.json"
    _write_receipt(receipt)
    _write_authorization_record(authorization_dir, ORG_REPO)

    assert_remote_write_authorized(ORG_REPO, "PR_CREATE_OR_UPDATE", receipt_dir=receipt)  # no raise


def test_one_approved_product_does_not_open_the_gate_for_an_unrelated_one(tmp_path, monkeypatch):
    """The exact scenario this plan's amendment names: one repo's grant existing
    must never substitute for another repo's own grant, even with a portfolio
    receipt present."""

    authorization_dir = tmp_path / "config" / "authorization"
    monkeypatch.setenv("README_AGENT_AUTHORIZATION_DIR", str(authorization_dir))
    receipt = tmp_path / "receipt.json"
    _write_receipt(receipt)
    _write_authorization_record(authorization_dir, ORG_REPO)

    other_repo = "aspose-pdf-foss/Aspose.PDF-FOSS-for-Python"
    with pytest.raises(RemoteWriteBlockedError):
        assert_remote_write_authorized(other_repo, "PR_CREATE_OR_UPDATE", receipt_dir=receipt)


def test_malformed_receipt_is_treated_as_absent_not_approved(tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text("{not valid json", encoding="utf-8")

    assert load_portfolio_approval_receipt(path=receipt) is None


def test_receipt_missing_required_field_is_treated_as_absent(tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")

    assert load_portfolio_approval_receipt(path=receipt) is None


def test_expired_authorization_record_still_blocks_even_with_a_receipt(tmp_path, monkeypatch):
    authorization_dir = tmp_path / "config" / "authorization"
    monkeypatch.setenv("README_AGENT_AUTHORIZATION_DIR", str(authorization_dir))
    receipt = tmp_path / "receipt.json"
    _write_receipt(receipt)
    authorization_dir.mkdir(parents=True, exist_ok=True)
    org, _, repo = ORG_REPO.partition("/")
    (authorization_dir / f"{org}__{repo}.yml").write_text(
        yaml.safe_dump(
            {
                "repository": ORG_REPO,
                "effect_classes": ["PR_CREATE_OR_UPDATE"],
                "branch_pattern": "readme-agent/*",
                "approving_identity": "fixture-owner",
                "rollback": "close the PR and delete the branch",
                "expiration": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RemoteWriteBlockedError):
        assert_remote_write_authorized(ORG_REPO, "PR_CREATE_OR_UPDATE", receipt_dir=receipt)


def test_receipt_model_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError):
        PortfolioApprovalReceiptV1.model_validate(
            {
                "schema_version": 1,
                "portfolio_inventory_revision": "sha256:" + "a" * 64,
                "approved_at": "2026-08-15T00:00:00+00:00",
                "approval_note": "fixture",
                "unexpected_field": "should be rejected",
            }
        )
