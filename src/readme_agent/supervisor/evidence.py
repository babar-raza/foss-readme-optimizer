"""Write and structurally validate repository-supervision evidence."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from readme_agent.capabilities import registry as capability_registry
from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.evidence.manifest_v3 import RunManifestV3
from readme_agent.evidence.writer import refresh_sha256sums, write_run_manifest_v3
from readme_agent.llm import prompt_registry
from readme_agent.state.lifecycle import LifecycleRecorder, current_lifecycle_recorder
from readme_agent.state.schema import DomainStateV1, SurfaceFreshnessContractV1
from readme_agent.supervisor.models import DecisionSummary
from readme_agent.supervisor.task import TaskGraph

EXPECTED_EVIDENCE_FILES = (
    "specialist_results.json",
    "task_graph.json",
    "decisions.json",
    "manifest.json",
    "sha256sums.txt",
)


def requirement_ids_exercised(
    specialist_results: dict[str, DomainStateV1],
) -> dict[str, bool]:
    result = specialist_results.get(INDEPENDENT_VERIFICATION)
    requirement_map = result.details.get("requirement_map", {}) if result is not None else {}
    return {
        requirement_id: info["exercised_without_error"]
        for requirement_id, info in requirement_map.items()
    }


def write_supervise_evidence(
    evidence_dir: Path,
    run_id: str,
    org_repo: str,
    status: str,
    graph: TaskGraph,
    decisions: list[DecisionSummary],
    specialist_results: dict[str, DomainStateV1] | None = None,
    *,
    control_plane_fingerprint: str | None = None,
    upstream_revision: str | None = None,
    domain_coverage_complete: bool | None = None,
    surface_freshness: dict[str, SurfaceFreshnessContractV1] | None = None,
) -> None:
    """Atomically write the complete evidence bundle for one terminal run."""

    evidence_dir.mkdir(parents=True, exist_ok=True)

    def _write(name: str, data: Any) -> None:
        tmp = evidence_dir / f"{name}.tmp"
        tmp.write_text(
            json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8", newline="\n"
        )
        os.replace(tmp, evidence_dir / name)

    _write(
        "specialist_results.json",
        {
            domain: {
                "accepted_status": result.accepted_status,
                "skipped_this_run": result.skipped_this_run,
                "details": result.details,
            }
            for domain, result in (specialist_results or {}).items()
        },
    )
    _write("task_graph.json", graph.snapshot())
    _write(
        "decisions.json",
        [{"turn": d.turn, "kind": d.kind, "detail": d.detail} for d in decisions],
    )
    lifecycle_recorder = current_lifecycle_recorder()
    verifier_result = (specialist_results or {}).get(INDEPENDENT_VERIFICATION)
    requirement_results = requirement_ids_exercised(specialist_results or {})
    facts = {
        "specialist_fact_hashes": {
            domain: result.accepted_facts_hash
            for domain, result in (specialist_results or {}).items()
            if result.accepted_facts_hash is not None
        }
    }
    effects = [
        {
            "task_id": task.task_id,
            "capability_id": task.capability_id,
            "state": task.state,
            "result": task.result,
        }
        for task in graph.tasks.values()
        if task.capability_id
        and (manifest := capability_registry.get(task.capability_id)) is not None
        and manifest.side_effect_class in {"local_write", "remote_write"}
    ]
    write_run_manifest_v3(
        evidence_dir,
        RunManifestV3(
            run_id=run_id,
            org_repo=org_repo,
            status=status,
            timestamp=datetime.now(UTC).isoformat(),
            prompt_registry_content_hash=prompt_registry.content_hash(),
            control_plane_fingerprint=control_plane_fingerprint,
            upstream_revision=upstream_revision,
            domain_coverage_complete=domain_coverage_complete,
            surface_freshness=surface_freshness or {},
            requirement_ids_exercised=requirement_results,
            trigger=lifecycle_recorder.envelope if lifecycle_recorder else None,
            trigger_status="processing" if lifecycle_recorder else None,
            checkpoints=lifecycle_recorder.checkpoints() if lifecycle_recorder else [],
            facts=facts,
            presentation_plan=graph.snapshot(),
            authorization={
                "record_id": None,
                "status": "not_evaluated" if not effects else "enforced_by_effect_ledger",
            },
            verifier=(
                {
                    "accepted_status": verifier_result.accepted_status,
                    "details": verifier_result.details,
                }
                if verifier_result is not None
                else {"status": "not_run"}
            ),
            effects=effects,
            requirement_results=requirement_results,
        ),
    )
    refresh_sha256sums(evidence_dir)


def finalize_run_manifest_v3(
    evidence_dir: Path,
    lifecycle_recorder: LifecycleRecorder,
    trigger_status: str,
) -> None:
    manifest_path = evidence_dir / "manifest.json"
    manifest = RunManifestV3.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    write_run_manifest_v3(
        evidence_dir,
        manifest.model_copy(
            update={
                "trigger_status": trigger_status,
                "checkpoints": lifecycle_recorder.checkpoints(),
            }
        ),
    )
    refresh_sha256sums(evidence_dir)


def assert_evidence_complete(evidence_dir: Path) -> None:
    """Fail when a terminal evidence bundle is missing or malformed."""

    for name in EXPECTED_EVIDENCE_FILES:
        path = evidence_dir / name
        if not path.exists():
            raise RuntimeError(
                f"incomplete evidence bundle: {name!r} was not written to {evidence_dir}"
            )
        if name == "sha256sums.txt":
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"incomplete evidence bundle: {name!r} in {evidence_dir} is not valid JSON"
            ) from exc
    expected: dict[str, str] = {}
    for line in (evidence_dir / "sha256sums.txt").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        expected[name] = digest
    actual_files = {
        path.name
        for path in evidence_dir.iterdir()
        if path.is_file() and path.name != "sha256sums.txt"
    }
    if set(expected) != actual_files:
        raise RuntimeError(
            f"incomplete evidence bundle: checksum inventory mismatch in {evidence_dir}"
        )
    from readme_agent.evidence.writer import sha256_file

    for name, digest in expected.items():
        actual, _size = sha256_file(evidence_dir / name)
        if actual != digest:
            raise RuntimeError(
                f"incomplete evidence bundle: checksum mismatch for {name!r} in {evidence_dir}"
            )
