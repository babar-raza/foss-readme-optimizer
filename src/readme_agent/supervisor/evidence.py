"""Write and structurally validate repository-supervision evidence."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from readme_agent.capabilities.domains import INDEPENDENT_VERIFICATION
from readme_agent.evidence.manifest_v2 import RunManifestV2
from readme_agent.evidence.writer import write_run_manifest_v2
from readme_agent.llm import prompt_registry
from readme_agent.state.schema import DomainStateV1, SurfaceFreshnessContractV1
from readme_agent.supervisor.models import DecisionSummary
from readme_agent.supervisor.task import TaskGraph

EXPECTED_EVIDENCE_FILES = (
    "specialist_results.json",
    "task_graph.json",
    "decisions.json",
    "manifest.json",
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
    write_run_manifest_v2(
        evidence_dir,
        RunManifestV2(
            run_id=run_id,
            org_repo=org_repo,
            status=status,
            timestamp=datetime.now(UTC).isoformat(),
            prompt_registry_content_hash=prompt_registry.content_hash(),
            control_plane_fingerprint=control_plane_fingerprint,
            upstream_revision=upstream_revision,
            domain_coverage_complete=domain_coverage_complete,
            surface_freshness=surface_freshness or {},
            requirement_ids_exercised=requirement_ids_exercised(specialist_results or {}),
        ),
    )


def assert_evidence_complete(evidence_dir: Path) -> None:
    """Fail when a terminal evidence bundle is missing or malformed."""

    for name in EXPECTED_EVIDENCE_FILES:
        path = evidence_dir / name
        if not path.exists():
            raise RuntimeError(
                f"incomplete evidence bundle: {name!r} was not written to {evidence_dir}"
            )
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"incomplete evidence bundle: {name!r} in {evidence_dir} is not valid JSON"
            ) from exc
