"""Serial prepare/seal/promote adapters for README candidate stage boundaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.llm.verification_prompts import separated_reviewer_standard_hash
from readme_agent.readme.assessment import ReadmeAssessmentV1
from readme_agent.repository_snapshot import RepositorySnapshotV1
from readme_agent.state.backend import StateBackend
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.supervisor.local_poc_evidence import (
    write_local_poc_manifest,
    write_local_poc_readme_candidate,
)
from readme_agent.supervisor.portfolio_scheduler.contracts import (
    build_stage_fence,
    build_stage_work_item,
    canonical_sha256,
)
from readme_agent.supervisor.portfolio_scheduler.lane import (
    prepare_stage_attempt,
    seal_stage_attempt,
)
from readme_agent.supervisor.portfolio_scheduler.reducer import (
    promote_candidate_stage,
    promote_deterministic_validation_stage,
)

_WORKER_IDENTITY = "serial-supervisor"
_CANDIDATE_INPUT_MANIFEST_FIELDS = frozenset(
    {
        "schema_version",
        "org_repo",
        "source_revision",
        "facts_hash",
        "resolution_source",
        "prompt_hash",
        "local_verification_contract_hash",
        "fact_acceptance_contract_hash",
        "fact_acceptance_component_hashes",
        "prompt_registry_content_hash",
        "prompt_hashes_by_id",
        "prompt_dependency_hashes",
        "llm_accounting_status",
        "llm_call_count",
        "llm_call_ids",
        "llm_calls_by_job",
        "llm_fixture_call_count",
        "llm_cache_reuse_count",
        "llm_prompt_tokens",
        "llm_completion_tokens",
        "llm_total_tokens",
        "llm_ledger_sha256",
    }
)


def _compatibility_bundle(snapshot: RepositorySnapshotV1) -> Path:
    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    return paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)


def _load_manifest(bundle_dir: Path) -> dict:
    path = bundle_dir / "manifest.json"
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _candidate_input_manifest(bundle_dir: Path) -> dict:
    """Exclude reducer/review outputs from the repeatable candidate input."""

    manifest = _load_manifest(bundle_dir)
    return {
        key: value for key, value in manifest.items() if key in _CANDIDATE_INPUT_MANIFEST_FIELDS
    }


def _current_lifecycle(
    backend: StateBackend,
    org_repo: str,
) -> ReadmePocLifecycleStateV2:
    state = backend.load(org_repo)
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if not isinstance(lifecycle, ReadmePocLifecycleStateV2):
        raise ValueError(f"{org_repo!r} has no V2 lifecycle for stage preparation")
    if lifecycle.source_revision is None or lifecycle.facts_hash is None:
        raise ValueError(f"{org_repo!r} lifecycle lacks source/fact stage inputs")
    return lifecycle


def prepare_and_promote_candidate_stage(
    snapshot: RepositorySnapshotV1,
    render_result: dict,
    presentation_plan: dict,
    backend: StateBackend,
) -> tuple[Path, str, str, str]:
    """Run the existing candidate writer privately and reduce its sealed result."""

    lifecycle = _current_lifecycle(backend, snapshot.org_repo)
    if lifecycle.source_revision != snapshot.source_revision:
        raise ValueError("candidate stage snapshot disagrees with durable source revision")
    facts_hash = lifecycle.facts_hash
    assert facts_hash is not None
    candidate_text = str(render_result["final_text"])
    candidate_hash = hashlib.sha256(candidate_text.encode("utf-8")).hexdigest()
    assessment = ReadmeAssessmentV1.model_validate(presentation_plan["readme_assessment"])
    assessment_hash = assessment.canonical_hash()
    presentation_plan_hash = canonical_sha256(presentation_plan.get("presentation_plan") or {})
    reviewer_standard_hash = separated_reviewer_standard_hash()
    dependency_hashes = {
        "assessment": assessment_hash,
        "candidate": candidate_hash,
        "facts": facts_hash,
        "presentation_plan": presentation_plan_hash,
        "reviewer_standard": reviewer_standard_hash,
    }
    fence = build_stage_fence(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        lifecycle_status=lifecycle.status,
        facts_hash=facts_hash,
        fact_acceptance_contract_hash=lifecycle.fact_acceptance_contract_hash,
        prompt_hash=lifecycle.prompt_hash,
        candidate_hash=lifecycle.candidate_hash,
    )
    work = build_stage_work_item(
        target_stage="CANDIDATE_GENERATED",
        fence=fence,
        dependency_hashes=dependency_hashes,
    )
    attempt_root, attempt, artifacts_root = prepare_stage_attempt(
        work,
        worker_identity=_WORKER_IDENTITY,
    )
    compatibility_bundle = _compatibility_bundle(snapshot)
    prior_manifest = _candidate_input_manifest(compatibility_bundle)
    if prior_manifest:
        write_redacted_json(artifacts_root / "manifest.json", prior_manifest)
    (
        _attempt_bundle,
        written_assessment_hash,
        written_plan_hash,
        written_candidate_hash,
    ) = write_local_poc_readme_candidate(
        snapshot,
        render_result,
        presentation_plan,
        bundle_dir_override=artifacts_root,
    )
    if (
        written_assessment_hash != assessment_hash
        or written_plan_hash != presentation_plan_hash
        or written_candidate_hash != candidate_hash
    ):
        raise ValueError("private candidate writer changed its declared stage identities")
    seal_stage_attempt(
        work,
        attempt_root,
        attempt=attempt,
        worker_identity=_WORKER_IDENTITY,
    )
    promote_candidate_stage(
        work,
        attempt_root,
        compatibility_bundle,
        backend,
        assessment_hash=assessment_hash,
        presentation_plan_hash=presentation_plan_hash,
        candidate_hash=candidate_hash,
        reviewer_standard_hash=reviewer_standard_hash,
    )
    return compatibility_bundle, assessment_hash, presentation_plan_hash, candidate_hash


def prepare_and_promote_deterministic_validation_stage(
    snapshot: RepositorySnapshotV1,
    validation_record: dict,
    backend: StateBackend,
) -> Path:
    """Seal the combined deterministic verdict before lifecycle promotion."""

    lifecycle = _current_lifecycle(backend, snapshot.org_repo)
    if lifecycle.status != "CANDIDATE_GENERATED" or lifecycle.candidate_hash is None:
        raise ValueError("deterministic validation requires a promoted candidate")
    facts_hash = lifecycle.facts_hash
    assert facts_hash is not None
    validation_hash = canonical_sha256(validation_record)
    dependency_hashes = {
        "candidate": lifecycle.candidate_hash,
        "deterministic_validation": validation_hash,
        "facts": facts_hash,
    }
    fence = build_stage_fence(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        lifecycle_status=lifecycle.status,
        facts_hash=facts_hash,
        fact_acceptance_contract_hash=lifecycle.fact_acceptance_contract_hash,
        prompt_hash=lifecycle.prompt_hash,
        candidate_hash=lifecycle.candidate_hash,
    )
    work = build_stage_work_item(
        target_stage="DETERMINISTIC_VALIDATED",
        fence=fence,
        dependency_hashes=dependency_hashes,
    )
    attempt_root, attempt, artifacts_root = prepare_stage_attempt(
        work,
        worker_identity=_WORKER_IDENTITY,
    )
    compatibility_bundle = _compatibility_bundle(snapshot)
    manifest = _load_manifest(compatibility_bundle)
    completed = [str(stage) for stage in manifest.get("completed_stages", [])]
    if "DETERMINISTIC_VALIDATED" not in completed:
        completed.append("DETERMINISTIC_VALIDATED")
    write_redacted_json(
        artifacts_root / "review" / "deterministic-validation.json",
        validation_record,
    )
    write_local_poc_manifest(
        artifacts_root,
        {
            **manifest,
            "lifecycle_status": "DETERMINISTIC_VALIDATED",
            "complete": False,
            "completed_stages": completed,
            "deterministic_validation_hash": validation_hash,
        },
    )
    refresh_sha256sums(artifacts_root)
    seal_stage_attempt(
        work,
        attempt_root,
        attempt=attempt,
        worker_identity=_WORKER_IDENTITY,
    )
    promote_deterministic_validation_stage(
        work,
        attempt_root,
        compatibility_bundle,
        backend,
    )
    return compatibility_bundle
