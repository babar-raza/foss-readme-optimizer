# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md
# artifact_role: L8-TRUTH-01A persisted-terminal replay and durable-reopening evidence producer
"""Replay historical terminal fact graphs under the current acceptance contract."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from readme_agent import paths
from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.facts.acceptance_contract import (
    FactAcceptanceContractV1,
    classify_product_truth,
    current_fact_acceptance_contract,
)
from readme_agent.facts.local_verification import local_verification_contract_hash
from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.state.git_backend import default_state_backend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.readme_poc_lifecycle import record_product_facts_outcome
from readme_agent.supervisor.local_poc_evidence import write_local_poc_product_facts

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = (
    REPO_ROOT
    / "plans"
    / "investigations"
    / "evidence"
    / "level8-truth-versioned-fact-acceptance-2026-07-26"
)
HISTORICAL_FACTS_DIR = EVIDENCE_DIR / "historical-terminal-facts"
BARCODE_REPO = "aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python"

CASES = (
    {
        "label": "aspose-3d-java-valid-terminal",
        "org_repo": "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        "source_revision": "8de5f467e93138b3605acdc46ca40e93f0364ee8",
        "historical_status": "NO_OP_PROVEN",
        "expected_outcome": "FACTS_READY",
        "expected_facts_hash": "a2030120a0d0a9ca575c75572da210189ab2b375eaa08f23d0e02497ebf425d2",
        "source_path": (
            "runs/readme-poc/aspose-3d-foss__Aspose.3D-FOSS-for-Java/"
            "8de5f467e93138b3605acdc46ca40e93f0364ee8/facts/product-facts.json"
        ),
    },
    {
        "label": "aspose-3d-python-false-terminal",
        "org_repo": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "source_revision": "ab1a2267a0ba6302311d0c7c4ad01494974c7d76",
        "historical_status": "NO_OP_PROVEN",
        "expected_outcome": "BLOCKED_MISSING_EVIDENCE",
        "expected_facts_hash": "c69342cc863ad1e899dbef39132636db5c90cc88b5c1528bef2b6251bf1313e4",
        "source_path": (
            "runs/readme-proposal-bundles/aspose-3d-foss__Aspose.3D-FOSS-for-Python/"
            "20260726-062651-eb7f/product-facts-v2.json"
        ),
    },
    {
        "label": "aspose-3d-typescript-false-terminal",
        "org_repo": "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
        "source_revision": "227894a1120c22b9b6522564e23dc1d14c8fc39a",
        "historical_status": "NO_OP_PROVEN",
        "expected_outcome": "BLOCKED_MISSING_EVIDENCE",
        "expected_facts_hash": "65977ae5d5c3ebb0c9066ea6d70f57824749b595f8cfc164d02bb26f7bd3a4b6",
        "source_path": (
            "runs/readme-proposal-bundles/aspose-3d-foss__Aspose.3D-FOSS-for-TypeScript/"
            "20260726-075548-2c71/product-facts-v2.json"
        ),
    },
    {
        "label": "aspose-barcode-python-false-terminal",
        "org_repo": BARCODE_REPO,
        "source_revision": "53f2c3350b8171f2c8275e7b1a178f218695ac45",
        "historical_status": "NO_OP_PROVEN",
        "expected_outcome": "BLOCKED_MISSING_EVIDENCE",
        "expected_facts_hash": "81c63498ac84ae8b9ad826350f0415065084fda393835596cd2fef528f98739e",
        "source_path": (
            "runs/readme-proposal-bundles/"
            "aspose-barcode-foss__Aspose.BarCode-FOSS-for-Python/"
            "20260726-062716-14e9/product-facts-v2.json"
        ),
    },
)


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        capture_output=True,
    )
    return completed.stdout.strip()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _historical_facts(case: dict[str, str]) -> tuple[ProductFactsV2, Path]:
    promoted_path = HISTORICAL_FACTS_DIR / f"{case['label']}.json"
    source_path = promoted_path if promoted_path.is_file() else REPO_ROOT / case["source_path"]
    facts = ProductFactsV2.model_validate_json(source_path.read_text(encoding="utf-8"))
    if facts.org_repo != case["org_repo"]:
        raise RuntimeError(f"{source_path} belongs to {facts.org_repo}, not {case['org_repo']}")
    if facts.canonical_hash() != case["expected_facts_hash"]:
        raise RuntimeError(f"historical fact hash changed for {case['org_repo']}")
    write_redacted_json(promoted_path, facts)
    return facts, promoted_path


def _blocking_fields(
    facts: ProductFactsV2,
    contract: FactAcceptanceContractV1,
) -> list[dict[str, str]]:
    blocked: list[dict[str, str]] = []
    for field in contract.required_fields:
        try:
            fact = facts.selected_fact(field)
        except KeyError:
            blocked.append({"field": field, "reason": "no selected fact"})
            continue
        if fact.verification_state not in contract.accepted_verification_states:
            blocked.append(
                {
                    "field": field,
                    "fact_id": fact.fact_id,
                    "reason": f"verification_state={fact.verification_state}",
                }
            )
        elif fact.has_unresolved_conflict:
            blocked.append(
                {
                    "field": field,
                    "fact_id": fact.fact_id,
                    "reason": "unresolved conflict",
                }
            )
    for field in contract.visitor_render_fields:
        view = visitor_fact_render_view(facts, field)
        if (view is None or not view.phrases) and not any(
            item["field"] == field for item in blocked
        ):
            blocked.append(
                {
                    "field": field,
                    "fact_id": facts.selected_fact(field).fact_id,
                    "reason": "no eligible visitor render view",
                }
            )
    return blocked


def _lifecycle(backend: Any, org_repo: str) -> tuple[Any, ReadmePocLifecycleStateV2]:
    state = backend.load(org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        raise RuntimeError(f"{org_repo} has no V2 README lifecycle")
    return state, lifecycle


def _reconcile_interrupted_barcode_manifest(
    backend: Any,
    contract: FactAcceptanceContractV1,
) -> None:
    """Repair only metadata left inconsistent by the interrupted unsafe replay."""

    state, lifecycle = _lifecycle(backend, BARCODE_REPO)
    del state
    revision = lifecycle.source_revision
    if revision is None:
        raise RuntimeError("BarCode lifecycle has no source revision")
    org, repo = BARCODE_REPO.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, revision)
    facts_path = bundle_dir / "facts" / "product-facts.json"
    facts = ProductFactsV2.model_validate_json(facts_path.read_text(encoding="utf-8"))
    if facts.canonical_hash() != lifecycle.facts_hash:
        raise RuntimeError("BarCode runtime fact graph and durable state disagree")
    outcome = classify_product_truth(facts, contract)
    if outcome != "BLOCKED_MISSING_EVIDENCE":
        raise RuntimeError(f"BarCode reconciliation unexpectedly classified {outcome}")
    snapshot = RepositorySnapshotV1.model_validate_json(
        (bundle_dir / "source" / "revision.json").read_text(encoding="utf-8")
    )
    findings_path = bundle_dir / "facts" / "findings.json"
    proposal_path = bundle_dir / "facts" / "proposed-product-truth.json"
    prompt_hash = lifecycle.prompt_hash
    write_local_poc_product_facts(
        snapshot,
        facts,
        findings=_load_json(findings_path) if findings_path.is_file() else [],
        proposed_product_truth=_load_json(proposal_path) if proposal_path.is_file() else None,
        resolution_source="agent_draft" if prompt_hash else "repository_and_policy",
        lifecycle_status=outcome,
        prompt_hash=prompt_hash,
        local_verification_contract_hash=local_verification_contract_hash(),
        fact_acceptance_contract_hash=contract.canonical_hash(),
        fact_acceptance_component_hashes=contract.component_hashes,
    )
    record_product_facts_outcome(
        backend,
        BARCODE_REPO,
        source_revision=revision,
        facts_hash=facts.canonical_hash(),
        outcome=outcome,
        evidence_refs=[
            str(facts_path),
            str(bundle_dir / "facts" / "provenance.json"),
            str(bundle_dir / "facts" / "conflicts.json"),
        ],
        prompt_hash=prompt_hash,
        fact_acceptance_contract_hash=contract.canonical_hash(),
        fact_acceptance_component_hashes=contract.component_hashes,
    )


def _manifest(org_repo: str, revision: str) -> tuple[dict[str, Any], Path]:
    org, repo = org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, revision)
    manifest_path = bundle_dir / "manifest.json"
    return _load_json(manifest_path), manifest_path


def _verify_sha256sums() -> None:
    expected: dict[str, str] = {}
    checksum_path = EVIDENCE_DIR / "sha256sums.txt"
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", maxsplit=1)
        expected[relative] = digest
    observed: dict[str, str] = {}
    for path in sorted(EVIDENCE_DIR.rglob("*")):
        if not path.is_file() or path == checksum_path:
            continue
        raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        observed[path.relative_to(EVIDENCE_DIR).as_posix()] = hashlib.sha256(raw).hexdigest()
    if observed != expected:
        raise RuntimeError("evidence checksum verification failed")


def main() -> int:
    if _git("branch", "--show-current") != "main":
        raise RuntimeError("fact-contract replay must run from control-repository main")
    if _git("status", "--porcelain"):
        raise RuntimeError("fact-contract replay requires a clean committed tree")

    contract = current_fact_acceptance_contract()
    backend = default_state_backend()
    _reconcile_interrupted_barcode_manifest(backend, contract)

    results: list[dict[str, Any]] = []
    for case in CASES:
        facts, promoted_path = _historical_facts(case)
        outcome = classify_product_truth(facts, contract)
        if outcome != case["expected_outcome"]:
            raise RuntimeError(
                f"{case['org_repo']} classified {outcome}, expected {case['expected_outcome']}"
            )
        state, lifecycle = _lifecycle(backend, case["org_repo"])
        manifest, manifest_path = _manifest(case["org_repo"], case["source_revision"])
        expected_durable_status = (
            "NO_OP_PROVEN" if outcome == "FACTS_READY" else "BLOCKED_MISSING_EVIDENCE"
        )
        if lifecycle.status != expected_durable_status:
            raise RuntimeError(
                f"{case['org_repo']} durable status is {lifecycle.status}, "
                f"expected {expected_durable_status}"
            )
        if lifecycle.fact_acceptance_contract_hash != contract.canonical_hash():
            raise RuntimeError(f"{case['org_repo']} lifecycle lacks the current contract")
        if manifest.get("fact_acceptance_contract_hash") != contract.canonical_hash():
            raise RuntimeError(f"{case['org_repo']} manifest lacks the current contract")
        results.append(
            {
                "org_repo": case["org_repo"],
                "source_revision": case["source_revision"],
                "historical_terminal_status": case["historical_status"],
                "historical_facts_path": promoted_path.relative_to(REPO_ROOT).as_posix(),
                "historical_facts_hash": facts.canonical_hash(),
                "current_contract_outcome": outcome,
                "blocking_fields": _blocking_fields(facts, contract),
                "durable_state_version": state.state_version,
                "durable_status_after_replay": lifecycle.status,
                "durable_facts_hash_after_replay": lifecycle.facts_hash,
                "durable_contract_hash": lifecycle.fact_acceptance_contract_hash,
                "latest_acceptance_binding": (
                    lifecycle.fact_acceptance_history[-1].model_dump(mode="json")
                    if lifecycle.fact_acceptance_history
                    else None
                ),
                "manifest_path": manifest_path.relative_to(REPO_ROOT).as_posix(),
                "manifest_status_after_replay": manifest.get("lifecycle_status"),
                "manifest_complete_after_replay": manifest.get("complete"),
                "manifest_contract_hash": manifest.get("fact_acceptance_contract_hash"),
            }
        )

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    write_redacted_json(EVIDENCE_DIR / "fact-acceptance-contract.json", contract)
    write_redacted_json(EVIDENCE_DIR / "replay-results.json", results)
    write_redacted_json(
        EVIDENCE_DIR / "execution.json",
        {
            "schema_version": 1,
            "task_id": "L8-TRUTH-01A-FACT-CONTRACT",
            "requirement_id": "L8-018",
            "generated_at": datetime.now(UTC).isoformat(),
            "control_head": _git("rev-parse", "HEAD"),
            "control_branch": "main",
            "command": [
                ".venv/Scripts/python",
                "plans/investigations/tools/collect_fact_acceptance_contract_replay_evidence.py",
            ],
            "execution_boundary": (
                "Persisted ProductFactsV2 classification and durable metadata reconciliation only"
            ),
            "prohibited_operations_observed": [],
            "product_remote_writes": 0,
            "llm_calls": 0,
            "repository_builds": 0,
            "package_installs": 0,
            "example_executions": 0,
            "historical_terminal_claim_source": (
                "logs/2026-07-26.md#requirements-gate-a-trust-contract"
            ),
        },
    )
    refresh_sha256sums(EVIDENCE_DIR)
    _verify_sha256sums()
    print(
        json.dumps(
            {
                "contract_hash": contract.canonical_hash(),
                "results": [
                    {
                        "org_repo": item["org_repo"],
                        "historical_outcome": item["current_contract_outcome"],
                        "durable_status": item["durable_status_after_replay"],
                    }
                    for item in results
                ],
                "evidence_dir": str(EVIDENCE_DIR),
                "checksum_verified": True,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
