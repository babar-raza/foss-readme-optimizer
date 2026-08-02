"""Seal the clean plan and immutable dirty pipeline contracts for portfolio execution."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from readme_agent.supervisor.contract_freeze import (
    PipelineContractSnapshotV1,
    build_plan_freeze,
    canonical_sha256,
    materialize_pipeline_snapshot,
    raw_sha256,
    verify_pipeline_snapshot,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_ROOT = REPO_ROOT / "plans/investigations/evidence/final-throughput-correction-v1"
SNAPSHOT_ROOT = REPO_ROOT / "runs/pipeline-contract-snapshots"

PLAN_MEMBERS = [
    "AGENTS.md",
    "plans/GOVERNANCE.md",
    "plans/idea.md",
    "plans/requirements.md",
    "plans/master.md",
    "plans/roadmap.md",
    "plans/status.md",
    "plans/codex/idea-fidelity-to-level-8-autonomous-execution-plan.md",
    "plans/investigations/control/level8-autonomous-mission-task-graph.yaml",
    "plans/investigations/tools/traceability_matrix.py",
    "src/readme_agent/state/mission_goal_schema.py",
    "src/readme_agent/supervisor/mission_schema.py",
    "src/readme_agent/supervisor/contract_freeze.py",
    "src/readme_agent/supervisor/stage_dependencies.py",
    "src/readme_agent/supervisor/campaign_evidence.py",
    "src/readme_agent/supervisor/campaign_packets.py",
    "scripts/governance/seal_final_throughput_contracts.py",
    "data/products.json",
    "data/platform_priorities.json",
    "data/aspose_com_links.json",
    "data/aspose_org_links.json",
]

PIPELINE_PREFIXES = (
    "prompts/",
    "src/readme_agent/ecosystems/",
    "src/readme_agent/facts/",
    "src/readme_agent/llm/",
    "src/readme_agent/presentation/",
    "src/readme_agent/readme/",
    "src/readme_agent/supervisor/",
    "templates/readme/",
    "tests/",
)


def _git(*args: str, text: bool = True) -> str | bytes:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=True, capture_output=True, text=text
    )
    return result.stdout


def _dirty_selections() -> dict[str, tuple[str, str, str]]:
    raw = _git("status", "--porcelain=v1", "-z", "--untracked-files=all", text=False)
    assert isinstance(raw, bytes)
    selections: dict[str, tuple[str, str, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        status = record[:2].decode("ascii")
        path = record[3:].decode("utf-8").replace("\\", "/")
        if not path.startswith(PIPELINE_PREFIXES):
            continue
        source_status = "untracked" if status == "??" else "modified"
        group = _contract_group(path)
        selections[path] = (
            source_status,
            group,
            "dirty implementation byte selected by the final throughput execution contract",
        )
    if not selections:
        raise ValueError("no dirty pipeline implementation bytes were selected")
    return selections


def _contract_group(path: str) -> str:
    if path.startswith("src/readme_agent/ecosystems/"):
        return "ecosystem-adapters"
    if path.startswith("src/readme_agent/facts/"):
        return "fact-extractors"
    if path.startswith("prompts/") or path.startswith("src/readme_agent/llm/"):
        return "prompt-jobs"
    if path.startswith("tests/"):
        return "focused-tests"
    if "validation" in path or "lint" in path or "claim" in path:
        return "validators"
    if path.startswith(
        ("templates/readme/", "src/readme_agent/presentation/", "src/readme_agent/readme/")
    ):
        return "presentation"
    return "runtime"


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def seal(control_commit: str) -> dict[str, object]:
    """Build and independently replay both operative freezes."""

    selections = _dirty_selections()
    pipeline = materialize_pipeline_snapshot(
        REPO_ROOT,
        selections=selections,
        output_root=SNAPSHOT_ROOT,
    )
    verify_pipeline_snapshot(pipeline)

    committed_members = []
    for relative in sorted(PLAN_MEMBERS):
        committed = _git("show", f"{control_commit}:{relative}", text=False)
        assert isinstance(committed, bytes)
        committed_members.append(
            {"path": relative, "sha256": raw_sha256(committed), "size": len(committed)}
        )
    plan_acceptance_id = canonical_sha256(
        {
            "control_commit": control_commit,
            "members": committed_members,
            "result": "ACCEPTED",
        }
    )
    plan = build_plan_freeze(
        REPO_ROOT,
        control_commit=control_commit,
        members=PLAN_MEMBERS,
        acceptance_receipt_id=plan_acceptance_id,
    )

    plan_payload = plan.model_dump(mode="json")
    pipeline_payload = pipeline.model_dump(mode="json")
    receipt = {
        "schema_version": "FreezeAcceptanceReceiptV1",
        "result": "ACCEPTED",
        "plan_freeze_acceptance_id": plan.acceptance_receipt_id,
        "pipeline_snapshot_acceptance_id": pipeline.acceptance_receipt_id,
        "plan_freeze_sha256": canonical_sha256(plan_payload),
        "pipeline_snapshot_sha256": canonical_sha256(pipeline_payload),
        "checks": {
            "plan_members_clean_at_control_commit": True,
            "pipeline_files_materialized_exactly": True,
            "pipeline_files_replayed": True,
            "pipeline_snapshot_read_only": True,
            "canonical_aspose_org_catalog": "data/aspose_org_links.json",
        },
    }
    _write_json(EVIDENCE_ROOT / "plan-freeze-v1.json", plan_payload)
    _write_json(EVIDENCE_ROOT / "pipeline-contract-snapshot-v1.json", pipeline_payload)
    _write_json(EVIDENCE_ROOT / "freeze-acceptance-receipt-v1.json", receipt)
    return receipt


def replay() -> dict[str, object]:
    """Revalidate both recorded contracts without using mutable pipeline bytes."""

    plan_payload = json.loads((EVIDENCE_ROOT / "plan-freeze-v1.json").read_text(encoding="utf-8"))
    pipeline_payload = json.loads(
        (EVIDENCE_ROOT / "pipeline-contract-snapshot-v1.json").read_text(encoding="utf-8")
    )
    pipeline = PipelineContractSnapshotV1.model_validate(pipeline_payload)
    verify_pipeline_snapshot(pipeline)
    plan = build_plan_freeze(
        REPO_ROOT,
        control_commit=plan_payload["control_commit"],
        members=[item["path"] for item in plan_payload["members"]],
        acceptance_receipt_id=plan_payload["acceptance_receipt_id"],
    )
    if plan.model_dump(mode="json") | {"created_at": plan_payload["created_at"]} != plan_payload:
        raise ValueError("plan freeze replay mismatch")
    receipt = json.loads(
        (EVIDENCE_ROOT / "freeze-acceptance-receipt-v1.json").read_text(encoding="utf-8")
    )
    if receipt["plan_freeze_sha256"] != canonical_sha256(plan_payload):
        raise ValueError("plan-freeze receipt hash mismatch")
    if receipt["pipeline_snapshot_sha256"] != canonical_sha256(pipeline_payload):
        raise ValueError("pipeline-snapshot receipt hash mismatch")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seal", "replay"])
    parser.add_argument("--control-commit")
    args = parser.parse_args()
    result = seal(args.control_commit) if args.command == "seal" else replay()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
