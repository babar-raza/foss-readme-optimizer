"""Validate the current seven-ecosystem FACTS_READY portfolio slice."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from readme_agent.facts.acceptance_contract import (
    classify_product_truth,
    current_fact_acceptance_contract,
)
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.registry.priority import load_platform_priority

REPRESENTATIVES = {
    "python": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
    "net": "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
    "java": "aspose-cells-foss/Aspose.Cells-FOSS-for-Java",
    "cpp": "aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp",
    "typescript": "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
    "rust": "aspose-cells-foss/Aspose.Cells-FOSS-for-Rust",
    "go": "aspose-pdf-foss/Aspose-PDF-FOSS-for-Go",
}
PUBLIC_EXAMPLE_NAMES = {"net": "dotnet"}
EXPECTED_STAGES = ["SNAPSHOTTED", "PROFILED", "FACTS_READY"]


def sha256_bytes(value: bytes) -> str:
    """Return a stable SHA-256 digest."""

    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    """Return a file SHA-256 digest."""

    return sha256_bytes(path.read_bytes())


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _bundle_root(repo_root: Path, org_repo: str) -> Path:
    container = repo_root / "runs/readme-poc" / org_repo.replace("/", "__")
    candidates = [
        path.parent
        for path in container.glob("*/manifest.json")
        if _read_json(path).get("lifecycle_status") == "FACTS_READY"
    ]
    if len(candidates) != 1:
        raise RuntimeError(
            f"{org_repo} must have exactly one FACTS_READY revision bundle; found {len(candidates)}"
        )
    return candidates[0]


def _fact(facts: ProductFactsV2, field: str):
    return facts.selected_fact(field)


def _native_tool_record(
    repo_root: Path,
    ecosystem: str,
    source_revision: str,
) -> dict[str, Any]:
    evidence_name = PUBLIC_EXAMPLE_NAMES.get(ecosystem, ecosystem)
    path = (
        repo_root
        / "plans/investigations/evidence/level8-public-examples"
        / f"{evidence_name}-verification.json"
    )
    record = _read_json(path)
    verification = record["verification"]
    execution = verification["isolated_execution"]
    stdout = str(execution.get("stdout", ""))
    stderr = str(execution.get("stderr", ""))
    return {
        "evidence_path": path.relative_to(repo_root).as_posix(),
        "evidence_sha256": sha256_file(path),
        "source_revision": verification.get("source_revision"),
        "source_revision_matches": verification.get("source_revision") == source_revision,
        "outcome": verification.get("outcome"),
        "truth_eligible": verification.get("truth_eligible"),
        "command": execution.get("argv"),
        "immutable_image": execution.get("policy", {}).get("immutable_image"),
        "network_mode": execution.get("policy", {}).get("network_mode"),
        "input_sha256": execution.get("input_sha256"),
        "stdout_sha256": sha256_bytes(stdout.encode("utf-8")),
        "stderr_sha256": sha256_bytes(stderr.encode("utf-8")),
        "dependency_pins": verification.get("acquisition_dependency_pins", []),
        "cleanup_complete": all(execution.get("cleanup", {}).values()),
    }


def verify_representative(repo_root: Path, ecosystem: str, org_repo: str) -> dict[str, Any]:
    """Validate one persisted fact bundle against the current acceptance contract."""

    root = _bundle_root(repo_root, org_repo)
    manifest_path = root / "manifest.json"
    facts_path = root / "facts/product-facts.json"
    manifest = _read_json(manifest_path)
    facts = ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
    source_revision = str(manifest.get("source_revision", ""))
    contract = current_fact_acceptance_contract()
    acquisition = _fact(facts, "installation.verified_acquisition")
    example = _fact(facts, "example.minimal")
    acquisition_value = acquisition.value if isinstance(acquisition.value, dict) else {}
    example_value = example.value if isinstance(example.value, dict) else {}
    native_tool = _native_tool_record(repo_root, ecosystem, source_revision)
    checks = {
        "repository_identity_matches": facts.org_repo == org_repo,
        "source_revision_addressed": root.name == source_revision,
        "manifest_facts_hash_matches": manifest.get("facts_hash") == facts.canonical_hash(),
        "current_acceptance_contract": (
            manifest.get("fact_acceptance_contract_hash") == contract.canonical_hash()
        ),
        "current_classification_facts_ready": classify_product_truth(facts, contract)
        == "FACTS_READY",
        "stage_boundary_exact": (
            manifest.get("lifecycle_status") == "FACTS_READY"
            and manifest.get("completed_stages") == EXPECTED_STAGES
        ),
        "acquisition_verified": (
            acquisition.verification_state == "verified"
            and acquisition_value.get("truth_eligible") is True
            and acquisition_value.get("source_revision") == source_revision
        ),
        "example_verified": (
            example.verification_state == "verified"
            and example_value.get("verification_outcome") == "SOURCE_BUILD_VERIFIED"
        ),
        "native_tool_truth_eligible": (
            native_tool["source_revision_matches"]
            and native_tool["outcome"] == "SOURCE_BUILD_VERIFIED"
            and native_tool["truth_eligible"] is True
            and bool(native_tool["command"])
            and bool(native_tool["immutable_image"])
            and bool(native_tool["input_sha256"])
            and bool(native_tool["dependency_pins"])
            and native_tool["cleanup_complete"]
        ),
        "network_denied": native_tool["network_mode"] == "none",
    }
    return {
        "ecosystem": ecosystem,
        "org_repo": org_repo,
        "source_revision": source_revision,
        "bundle_root": root.relative_to(repo_root).as_posix(),
        "bundle_manifest_sha256": sha256_file(manifest_path),
        "product_facts_sha256": sha256_file(facts_path),
        "facts_hash": facts.canonical_hash(),
        "fact_acceptance_contract_hash": contract.canonical_hash(),
        "selected_fact_ids": facts.selected_fact_ids,
        "acquisition": {
            "fact_id": acquisition.fact_id,
            "method": acquisition_value.get("method"),
            "outcome": acquisition_value.get("outcome"),
        },
        "example": {
            "fact_id": example.fact_id,
            "language": example_value.get("language"),
            "verification_outcome": example_value.get("verification_outcome"),
        },
        "native_tool": native_tool,
        "checks": checks,
    }


def verify_campaign(repo_root: Path) -> dict[str, Any]:
    """Validate configured order, portfolio summary, and all seven fact bundles."""

    configured_order = list(load_platform_priority().execution_order)
    results = [
        verify_representative(repo_root, ecosystem, REPRESENTATIVES[ecosystem])
        for ecosystem in configured_order
    ]
    summary_path = repo_root / "runs/readme-poc/portfolio-summary.json"
    summary = _read_json(summary_path)
    summary_order = [item["org_repo"] for item in summary.get("results", [])]
    expected_repositories = [REPRESENTATIVES[item] for item in configured_order]
    checks = {
        "configured_order_exact": configured_order == list(REPRESENTATIVES),
        "portfolio_denominator_seven": summary.get("registry_count") == 7,
        "portfolio_order_exact": summary_order == expected_repositories,
        "execution_slice_complete": summary.get("execution_slice_complete") is True,
        "all_facts_ready": all(
            item.get("status") == "FACTS_READY" for item in summary.get("results", [])
        ),
        "unchanged_pass_zero_provider_calls": summary.get("llm_provider_call_count") == 0,
        "unchanged_pass_seven_cache_reuses": summary.get("llm_cache_reuse_count") == 7,
        "all_representatives_valid": all(all(item["checks"].values()) for item in results),
    }
    return {
        "schema_version": 1,
        "configured_order": configured_order,
        "expected_repositories": expected_repositories,
        "portfolio_summary_path": summary_path.relative_to(repo_root).as_posix(),
        "portfolio_summary_sha256": sha256_file(summary_path),
        "portfolio_generated_at": summary.get("generated_at"),
        "llm_provider_call_count": summary.get("llm_provider_call_count"),
        "llm_cache_reuse_count": summary.get("llm_cache_reuse_count"),
        "representatives": results,
        "checks": checks,
    }
