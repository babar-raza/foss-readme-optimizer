"""Evaluate acceptance and hostile-executor controls for acquisition evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from acquisition_truth_evidence_sources import verify_evidence_inventory

from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionResultV1

EXPECTED_REGISTRY_CASES = {
    "java_published",
    "dotnet_published",
    "cpp_nuget_published",
    "go_proxy_published",
}
EXPECTED_SOURCE_CASES = {
    "python_source_build",
    "typescript_source_build",
    "rust_source_build",
}


def verify_hostile_executor_controls(root: Path) -> dict[str, Any]:
    """Re-derive the hostile-build boundary from checksum-valid executor evidence."""

    inventory = verify_evidence_inventory(root)
    success = IsolatedExecutionResultV1.model_validate_json(
        (root / "isolated-success.json").read_text(encoding="utf-8")
    )
    timeout = IsolatedExecutionResultV1.model_validate_json(
        (root / "isolated-timeout.json").read_text(encoding="utf-8")
    )
    host = json.loads((root / "host-negative-control.json").read_text(encoding="utf-8"))
    cleanup = json.loads((root / "cleanup-inventory.json").read_text(encoding="utf-8"))
    control_script = (root / "control.sh").read_text(encoding="utf-8")
    checks = {
        "checksum_inventory_valid": inventory["accepted"],
        "operator_filesystem_hidden": (
            "test ! -e /operator-host-sentinel" in control_script and success.return_code == 0
        ),
        "credentials_not_inherited": (
            'test -z "${GH_TOKEN+x}"' in control_script
            and not success.environment_names
            and success.return_code == 0
        ),
        "workspace_escape_blocked": (
            success.policy.read_only_rootfs
            and success.policy.cap_drop_all
            and success.policy.no_new_privileges
            and success.policy.user != "0:0"
        ),
        "descendants_removed_after_cancellation": (
            timeout.timed_out
            and timeout.cleanup.execution_container_removed
            and timeout.cleanup.seed_container_removed
            and timeout.cleanup.workspace_volume_removed
            and cleanup == {"containers": [], "volumes": []}
        ),
        "undeclared_network_blocked": (
            success.policy.network_mode == "none"
            and timeout.policy.network_mode == "none"
            and "interfaces=lo" in success.stdout
        ),
        "resource_bounds_observed": (
            success.policy.cpu_limit > 0
            and success.policy.memory_mebibytes > 0
            and success.policy.pids_limit > 0
            and "pids=" in success.stdout
            and "memory=" in success.stdout
            and "cpu=" in success.stdout
        ),
        "host_result_truth_ineligible": host.get("truth_eligible") is False,
    }
    return {
        "evidence_path": root.as_posix(),
        "inventory": inventory,
        "checks": checks,
        "accepted": all(checks.values()),
    }


def evaluate_acquisition_checks(
    *,
    control: dict[str, Any],
    start_status: str,
    current_head: str,
    current_status: str,
    clean_representatives: dict[str, bool],
    revisions: dict[str, str],
    remote_revisions: dict[str, str | None],
    inventories: dict[str, dict[str, Any]],
    source_verifications: tuple[LocalProductVerificationV1, ...],
    acquisition_controls: dict[str, Any],
    hostile_controls: dict[str, Any],
    focused_exit_code: int,
    official_exit_code: int | None,
) -> dict[str, bool]:
    """Return the complete taskcard acceptance map for one stable run."""

    decisions = acquisition_controls["decisions"]
    negatives = acquisition_controls["negative_controls"]
    return {
        "control_tree_clean": control["tree_clean_at_start"],
        "representatives_clean": all(clean_representatives.values()),
        "remote_default_revisions_match": all(
            remote_revisions[org_repo] == revision for org_repo, revision in revisions.items()
        ),
        "source_proof_inventories_valid": all(item["accepted"] for item in inventories.values()),
        "source_revisions_match": all(
            verification.source_revision == revisions[verification.org_repo]
            for verification in source_verifications
        ),
        "published_coordinates_have_receipts": all(
            decisions[name]["outcome"] == "REGISTRY_VERIFIED"
            and decisions[name]["registry_receipt"]["status_code"] == 200
            for name in EXPECTED_REGISTRY_CASES
        ),
        "unpublished_sources_have_both_receipts": all(
            decisions[name]["outcome"] == "SOURCE_BUILD_VERIFIED"
            and decisions[name]["registry_receipt"]["status_code"] == 404
            and decisions[name]["source_build_receipt"]["network_mode"] == "none"
            and len(decisions[name]["source_build_receipt"]["dependency_pins"]) >= 5
            for name in EXPECTED_SOURCE_CASES
        ),
        "synthetic_false_maven_rejected": (
            decisions["synthetic_false_maven"]["truth_eligible"] is False
            and decisions["synthetic_false_maven"]["registry_receipt"]["status_code"] == 404
        ),
        "readme_prose_cannot_verify_source": (
            negatives["readme_prose_only"]["truth_eligible"] is False
        ),
        "host_only_build_cannot_verify_source": (
            negatives["host_only_source_build"]["truth_eligible"] is False
        ),
        "network_uncertainty_blocks": (
            negatives["network_uncertainty"]["outcome"] == "BLOCKED_NETWORK"
            and negatives["network_uncertainty"]["truth_eligible"] is False
        ),
        "hostile_build_controls_pass": hostile_controls["accepted"],
        "focused_tests_pass": focused_exit_code == 0,
        "official_checks_pass": official_exit_code in {None, 0},
        "tree_stable": current_head == control["head"] and current_status == start_status,
    }
