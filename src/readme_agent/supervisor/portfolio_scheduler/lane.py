"""Write and independently validate private stage attempts before promotion."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import write_redacted_json, write_redacted_text
from readme_agent.supervisor.portfolio_scheduler.contracts import (
    LaneResultV1,
    PortfolioStageWorkItemV1,
    StageArtifactV1,
    StageSealV1,
    canonical_sha256,
)


def _raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_inventory(artifacts_root: Path) -> list[StageArtifactV1]:
    return [
        StageArtifactV1(
            path=path.relative_to(artifacts_root).as_posix(),
            sha256=_raw_sha256(path),
            size=path.stat().st_size,
        )
        for path in sorted(artifacts_root.rglob("*"))
        if path.is_file()
    ]


def next_attempt_root(work: PortfolioStageWorkItemV1) -> tuple[Path, int]:
    """Allocate a private retry root without deleting an interrupted attempt."""

    org, repo = work.fence.org_repo.split("/", maxsplit=1)
    work_root = paths.readme_poc_campaign_work_dir(
        work.campaign_id,
        org,
        repo,
        work.fence.source_revision,
        work.work_id,
    )
    for request_path in work_root.glob("*/request.json"):
        request = json.loads(request_path.read_text(encoding="utf-8"))
        recorded = PortfolioStageWorkItemV1.model_validate(request.get("work"))
        if (
            recorded.campaign_id != work.campaign_id
            or recorded.work_id != work.work_id
            or recorded.fence.org_repo != work.fence.org_repo
            or recorded.fence.source_revision != work.fence.source_revision
        ):
            raise ValueError("compact stage path alias collision")
    attempt = 1
    while (work_root / str(attempt)).exists():
        attempt += 1
    return work_root / str(attempt), attempt


def prepare_stage_attempt(
    work: PortfolioStageWorkItemV1,
    *,
    worker_identity: str,
) -> tuple[Path, int, Path]:
    """Persist the immutable request and return the lane-owned artifact root."""

    attempt_root, attempt = next_attempt_root(work)
    artifacts_root = attempt_root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=False)
    write_redacted_json(
        attempt_root / "request.json",
        {
            "schema_version": 1,
            "work": work.model_dump(mode="json"),
            "attempt": attempt,
            "worker_identity": worker_identity,
        },
    )
    return attempt_root, attempt, artifacts_root


def seal_stage_attempt(
    work: PortfolioStageWorkItemV1,
    attempt_root: Path,
    *,
    attempt: int,
    worker_identity: str,
) -> LaneResultV1:
    """Write result/inventory and SEALED last after artifact validation."""

    artifacts_root = attempt_root / "artifacts"
    if (attempt_root / "SEALED").exists():
        raise ValueError("stage attempt is already sealed")
    artifacts = _artifact_inventory(artifacts_root)
    if not artifacts:
        raise ValueError("cannot seal a stage attempt with no artifacts")
    output_hash = canonical_sha256([item.model_dump(mode="json") for item in artifacts])
    result = LaneResultV1(
        campaign_id=work.campaign_id,
        work_id=work.work_id,
        target_stage=work.target_stage,
        attempt=attempt,
        worker_identity=worker_identity,
        fence_token=work.fence.fence_token,
        artifacts=artifacts,
        output_hash=output_hash,
    )
    write_redacted_json(attempt_root / "result.json", result)
    inventory_lines = [
        f"{_raw_sha256(attempt_root / 'request.json')}  request.json",
        *[f"{artifact.sha256}  artifacts/{artifact.path}" for artifact in artifacts],
        f"{_raw_sha256(attempt_root / 'result.json')}  result.json",
    ]
    write_redacted_text(attempt_root / "sha256sums.txt", "\n".join(inventory_lines) + "\n")
    seal = StageSealV1(
        campaign_id=work.campaign_id,
        work_id=work.work_id,
        target_stage=work.target_stage,
        attempt=attempt,
        request_sha256=_raw_sha256(attempt_root / "request.json"),
        result_sha256=_raw_sha256(attempt_root / "result.json"),
        inventory_sha256=_raw_sha256(attempt_root / "sha256sums.txt"),
    )
    write_redacted_json(attempt_root / "SEALED", seal)
    return result


def validate_sealed_stage_attempt(
    work: PortfolioStageWorkItemV1,
    attempt_root: Path,
) -> tuple[LaneResultV1, StageSealV1]:
    """Reconstruct a lane result from bytes without trusting the worker object."""

    request_path = attempt_root / "request.json"
    result_path = attempt_root / "result.json"
    inventory_path = attempt_root / "sha256sums.txt"
    seal_path = attempt_root / "SEALED"
    if not all(path.is_file() for path in (request_path, result_path, inventory_path, seal_path)):
        raise ValueError("stage attempt is not sealed")
    seal = StageSealV1.model_validate_json(seal_path.read_text(encoding="utf-8"))
    result = LaneResultV1.model_validate_json(result_path.read_text(encoding="utf-8"))
    if (
        seal.campaign_id != work.campaign_id
        or seal.work_id != work.work_id
        or seal.target_stage != work.target_stage
        or result.campaign_id != work.campaign_id
        or result.work_id != work.work_id
        or result.target_stage != work.target_stage
        or result.fence_token != work.fence.fence_token
    ):
        raise ValueError("sealed stage identity does not match its work request")
    if (
        _raw_sha256(request_path) != seal.request_sha256
        or _raw_sha256(result_path) != seal.result_sha256
        or _raw_sha256(inventory_path) != seal.inventory_sha256
    ):
        raise ValueError("sealed stage control-file checksum mismatch")
    expected_lines = inventory_path.read_text(encoding="utf-8").splitlines()
    expected: dict[str, str] = {}
    for line in expected_lines:
        digest, relative = line.split("  ", maxsplit=1)
        if relative in expected:
            raise ValueError("duplicate path in stage inventory")
        expected[relative] = digest
    actual_paths = {
        "request.json": request_path,
        "result.json": result_path,
        **{
            f"artifacts/{item.path}": attempt_root / "artifacts" / item.path
            for item in result.artifacts
        },
    }
    if set(expected) != set(actual_paths) or any(
        not path.is_file() or _raw_sha256(path) != expected[relative]
        for relative, path in actual_paths.items()
    ):
        raise ValueError("sealed stage artifact inventory mismatch")
    if result.output_hash != canonical_sha256(
        [item.model_dump(mode="json") for item in result.artifacts]
    ):
        raise ValueError("sealed stage output hash mismatch")
    return result, seal


def atomic_copy_file(source: Path, target: Path) -> None:
    """Replace one compatibility-view file without exposing partial bytes."""

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_bytes(source.read_bytes())
    os.replace(temporary, target)
