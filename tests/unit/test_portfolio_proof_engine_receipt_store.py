"""Atomic, resumable, repository-relative receipt storage."""

from __future__ import annotations

from readme_agent.supervisor.portfolio_proof_engine.receipt_store import (
    all_receipts_for_repo,
    all_repos_in_campaign,
    latest_receipt,
    read_receipt,
    write_receipt,
)
from tests.unit.portfolio_proof_engine_fixtures import make_receipt


def test_write_then_read_round_trips(tmp_path):
    receipt = make_receipt(org_repo="acme/widget", stage="INTAKE")
    write_receipt(tmp_path, "campaign1", receipt)
    loaded = read_receipt(tmp_path, "campaign1", "acme/widget", "INTAKE")
    assert loaded is not None
    assert loaded.canonical_hash() == receipt.canonical_hash()


def test_read_receipt_missing_returns_none(tmp_path):
    assert read_receipt(tmp_path, "campaign1", "acme/widget", "INTAKE") is None


def test_receipt_path_is_repository_relative_never_absolute_outside_root(tmp_path):
    receipt = make_receipt(org_repo="acme/widget", stage="INTAKE")
    path = write_receipt(tmp_path, "campaign1", receipt)
    assert path.is_relative_to(tmp_path)


def test_write_receipt_produces_a_checksum_manifest(tmp_path):
    receipt = make_receipt(org_repo="acme/widget", stage="INTAKE")
    path = write_receipt(tmp_path, "campaign1", receipt)
    assert (path.parent / "sha256sums.txt").is_file()


def test_all_receipts_for_repo_collects_every_stage(tmp_path):
    write_receipt(tmp_path, "c", make_receipt(org_repo="acme/widget", stage="INTAKE"))
    write_receipt(
        tmp_path,
        "c",
        make_receipt(
            org_repo="acme/widget",
            stage="SOURCE_BOUND",
            source_revision="a" * 40,
        ),
    )
    receipts = all_receipts_for_repo(tmp_path, "c", "acme/widget")
    assert set(receipts) == {"INTAKE", "SOURCE_BOUND"}


def test_latest_receipt_follows_stage_order_not_write_order(tmp_path):
    # Write SOURCE_BOUND first, then INTAKE second -- latest must still be SOURCE_BOUND since it
    # is later in STAGE_ORDER, proving "latest" is deterministic by stage progression, not mtime.
    write_receipt(
        tmp_path,
        "c",
        make_receipt(org_repo="acme/widget", stage="SOURCE_BOUND", source_revision="a" * 40),
    )
    write_receipt(tmp_path, "c", make_receipt(org_repo="acme/widget", stage="INTAKE"))
    latest = latest_receipt(tmp_path, "c", "acme/widget")
    assert latest is not None
    assert latest.stage == "SOURCE_BOUND"


def test_latest_receipt_missing_repo_is_none(tmp_path):
    assert latest_receipt(tmp_path, "c", "acme/widget") is None


def test_write_receipt_replaces_same_stage_observation(tmp_path):
    write_receipt(tmp_path, "c", make_receipt(org_repo="acme/widget", stage="INTAKE"))
    write_receipt(
        tmp_path,
        "c",
        make_receipt(
            org_repo="acme/widget", stage="INTAKE", status="FAILED", failure_reason="changed"
        ),
    )
    loaded = read_receipt(tmp_path, "c", "acme/widget", "INTAKE")
    assert loaded is not None
    assert loaded.status == "FAILED"


def test_all_repos_in_campaign_lists_distinct_repositories(tmp_path):
    write_receipt(tmp_path, "c", make_receipt(org_repo="acme/widget", stage="INTAKE"))
    write_receipt(tmp_path, "c", make_receipt(org_repo="acme/gadget", stage="INTAKE"))
    assert set(all_repos_in_campaign(tmp_path, "c")) == {"acme/widget", "acme/gadget"}


def test_all_repos_in_campaign_empty_campaign_is_empty_list(tmp_path):
    assert all_repos_in_campaign(tmp_path, "nonexistent-campaign") == []
