"""Private-attempt sealing and reducer-only stage promotion contracts."""

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from readme_agent import paths
from readme_agent.evidence.writer import write_redacted_json, write_redacted_text
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.schema import RunStateV2
from readme_agent.supervisor.portfolio_scheduler.contracts import (
    build_stage_fence,
    build_stage_work_item,
)
from readme_agent.supervisor.portfolio_scheduler.lane import (
    atomic_copy_file,
    prepare_stage_attempt,
    seal_stage_attempt,
    validate_sealed_stage_attempt,
)
from readme_agent.supervisor.portfolio_scheduler.reducer import (
    promote_candidate_stage,
    promote_deterministic_validation_stage,
)
from tests.unit.test_state_backend import FakeStateBackend

ORG_REPO = "acme/widget"
SOURCE_REVISION = "a" * 40
FACTS_HASH = "b" * 64
CONTRACT_HASH = "c" * 64
PROMPT_HASH = "d" * 64
ASSESSMENT_HASH = "e" * 64
PLAN_HASH = "f" * 64
CANDIDATE_HASH = "1" * 64
REVIEWER_HASH = "2" * 64


def test_atomic_copy_file_supports_same_process_concurrent_writers(tmp_path):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    target = tmp_path / "planning" / "presentation-component-manifest.json"
    first.write_text('{"writer": "first"}\n', encoding="utf-8")
    second.write_text('{"writer": "second"}\n', encoding="utf-8")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(atomic_copy_file, source, target) for source in (first, second)]
        for future in futures:
            future.result()

    assert target.read_text(encoding="utf-8") in {
        '{"writer": "first"}\n',
        '{"writer": "second"}\n',
    }
    assert list(target.parent.glob("*.tmp")) == []


def _backend(status: str = "FACTS_READY", *, candidate_hash: str | None = None):
    backend = FakeStateBackend()
    backend.save(
        ORG_REPO,
        RunStateV2(
            org_repo=ORG_REPO,
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(
                status=status,
                source_revision=SOURCE_REVISION,
                facts_hash=FACTS_HASH,
                fact_acceptance_contract_hash=CONTRACT_HASH,
                prompt_hash=PROMPT_HASH,
                candidate_hash=candidate_hash,
            ),
        ),
        None,
    )
    return backend


def _candidate_work(candidate_hash: str = CANDIDATE_HASH):
    fence = build_stage_fence(
        org_repo=ORG_REPO,
        source_revision=SOURCE_REVISION,
        lifecycle_status="FACTS_READY",
        facts_hash=FACTS_HASH,
        fact_acceptance_contract_hash=CONTRACT_HASH,
        prompt_hash=PROMPT_HASH,
        candidate_hash=None,
    )
    return build_stage_work_item(
        target_stage="CANDIDATE_GENERATED",
        fence=fence,
        dependency_hashes={
            "assessment": ASSESSMENT_HASH,
            "candidate": candidate_hash,
            "facts": FACTS_HASH,
            "presentation_plan": PLAN_HASH,
            "reviewer_standard": REVIEWER_HASH,
        },
    )


def test_stage_work_identity_is_idempotent_and_fence_complete():
    dependencies = {
        "assessment": ASSESSMENT_HASH,
        "candidate": CANDIDATE_HASH,
        "facts": FACTS_HASH,
        "presentation_plan": PLAN_HASH,
        "reviewer_standard": REVIEWER_HASH,
    }

    def work(**fence_changes):
        fence_inputs = {
            "org_repo": ORG_REPO,
            "source_revision": SOURCE_REVISION,
            "lifecycle_status": "FACTS_READY",
            "facts_hash": FACTS_HASH,
            "fact_acceptance_contract_hash": CONTRACT_HASH,
            "prompt_hash": PROMPT_HASH,
            "candidate_hash": None,
        }
        fence_inputs.update(fence_changes)
        return build_stage_work_item(
            target_stage="CANDIDATE_GENERATED",
            fence=build_stage_fence(**fence_inputs),
            dependency_hashes=dependencies,
        )

    original = work()
    identical = work()
    changed_contract = work(fact_acceptance_contract_hash="9" * 64)
    changed_prompt = work(prompt_hash="8" * 64)
    changed_status = work(lifecycle_status="README_ASSESSED")
    changed_facts = work(facts_hash="7" * 64)
    changed_candidate = work(candidate_hash="6" * 64)
    changed_generation = work(generation=2)

    assert identical.campaign_id == original.campaign_id
    assert identical.work_id == original.work_id
    for changed in (
        changed_contract,
        changed_prompt,
        changed_status,
        changed_facts,
        changed_candidate,
        changed_generation,
    ):
        assert changed.fence.fence_token != original.fence.fence_token
        assert changed.campaign_id != original.campaign_id
        assert changed.work_id != original.work_id


def _sealed_candidate_attempt(
    tmp_path,
    monkeypatch,
    *,
    candidate_hash: str = CANDIDATE_HASH,
):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    work = _candidate_work(candidate_hash)
    attempt_root, attempt, artifacts = prepare_stage_attempt(
        work,
        worker_identity="test-worker",
    )
    write_redacted_json(
        artifacts / "manifest.json",
        {
            "org_repo": ORG_REPO,
            "source_revision": SOURCE_REVISION,
            "lifecycle_status": "CANDIDATE_GENERATED",
            "facts_hash": FACTS_HASH,
            "candidate_hash": candidate_hash,
            "completed_stages": ["FACTS_READY", "CANDIDATE_GENERATED"],
        },
    )
    write_redacted_text(
        artifacts / "candidate" / "README.md",
        f"# Candidate {candidate_hash[:8]}\n",
    )
    return work, attempt_root, attempt


def test_unsealed_or_corrupt_attempt_cannot_publish(tmp_path, monkeypatch):
    work, attempt_root, attempt = _sealed_candidate_attempt(tmp_path, monkeypatch)

    with pytest.raises(ValueError, match="not sealed"):
        validate_sealed_stage_attempt(work, attempt_root)

    seal_stage_attempt(
        work,
        attempt_root,
        attempt=attempt,
        worker_identity="test-worker",
    )
    (attempt_root / "artifacts" / "candidate" / "README.md").write_text(
        "# Tampered\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="inventory mismatch"):
        validate_sealed_stage_attempt(work, attempt_root)


def test_candidate_reducer_promotes_once_and_materializes_receipt_view(
    tmp_path,
    monkeypatch,
):
    work, attempt_root, attempt = _sealed_candidate_attempt(tmp_path, monkeypatch)
    seal_stage_attempt(
        work,
        attempt_root,
        attempt=attempt,
        worker_identity="test-worker",
    )
    backend = _backend()
    compatibility = tmp_path / "compatibility"

    first = promote_candidate_stage(
        work,
        attempt_root,
        compatibility,
        backend,
        assessment_hash=ASSESSMENT_HASH,
        presentation_plan_hash=PLAN_HASH,
        candidate_hash=CANDIDATE_HASH,
        reviewer_standard_hash=REVIEWER_HASH,
    )
    history_after_first = len(backend.load(ORG_REPO).readme_poc_lifecycle.history)
    second = promote_candidate_stage(
        work,
        attempt_root,
        compatibility,
        backend,
        assessment_hash=ASSESSMENT_HASH,
        presentation_plan_hash=PLAN_HASH,
        candidate_hash=CANDIDATE_HASH,
        reviewer_standard_hash=REVIEWER_HASH,
    )

    lifecycle = backend.load(ORG_REPO).readme_poc_lifecycle
    assert lifecycle.status == "CANDIDATE_GENERATED"
    assert lifecycle.candidate_hash == CANDIDATE_HASH
    assert len(lifecycle.history) == history_after_first
    assert first == second
    assert (compatibility / "candidate" / "README.md").is_file()
    receipt_path = compatibility / "receipts" / "CANDIDATE_GENERATED.json"
    assert receipt_path.is_file()
    manifest = json.loads((compatibility / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["acceptance_authority"] == "sealed_stage_receipts"
    assert manifest["stage_receipts"]["CANDIDATE_GENERATED"]["work_id"] == work.work_id


def test_candidate_reducer_rejects_changed_stage_owned_artifact_for_same_work(
    tmp_path,
    monkeypatch,
):
    work, first_root, first_attempt = _sealed_candidate_attempt(tmp_path, monkeypatch)
    seal_stage_attempt(
        work,
        first_root,
        attempt=first_attempt,
        worker_identity="test-worker",
    )
    backend = _backend()
    compatibility = tmp_path / "compatibility"
    first = promote_candidate_stage(
        work,
        first_root,
        compatibility,
        backend,
        assessment_hash=ASSESSMENT_HASH,
        presentation_plan_hash=PLAN_HASH,
        candidate_hash=CANDIDATE_HASH,
        reviewer_standard_hash=REVIEWER_HASH,
    )

    retry_root, retry_attempt, retry_artifacts = prepare_stage_attempt(
        work,
        worker_identity="retry-worker",
    )
    write_redacted_json(
        retry_artifacts / "manifest.json",
        {
            "org_repo": ORG_REPO,
            "source_revision": SOURCE_REVISION,
            "lifecycle_status": "CANDIDATE_GENERATED",
            "facts_hash": FACTS_HASH,
            "candidate_hash": CANDIDATE_HASH,
            "completed_stages": ["FACTS_READY", "CANDIDATE_GENERATED"],
        },
    )
    write_redacted_text(
        retry_artifacts / "candidate" / "README.md",
        f"# Candidate {CANDIDATE_HASH[:8]}\n",
    )
    write_redacted_text(retry_artifacts / "retry-observation.txt", "new call id\n")
    seal_stage_attempt(
        work,
        retry_root,
        attempt=retry_attempt,
        worker_identity="retry-worker",
    )

    with pytest.raises(ValueError, match="different result already owns"):
        promote_candidate_stage(
            work,
            retry_root,
            compatibility,
            backend,
            assessment_hash=ASSESSMENT_HASH,
            presentation_plan_hash=PLAN_HASH,
            candidate_hash=CANDIDATE_HASH,
            reviewer_standard_hash=REVIEWER_HASH,
        )

    assert not (compatibility / "retry-observation.txt").exists()
    assert (compatibility / "candidate" / "README.md").read_text(
        encoding="utf-8"
    ) == f"# Candidate {CANDIDATE_HASH[:8]}\n"
    receipt = json.loads(
        (compatibility / "receipts" / "CANDIDATE_GENERATED.json").read_text(encoding="utf-8")
    )
    assert receipt["output_hash"] == first.output_hash


def test_new_candidate_receipt_replaces_stale_completed_manifest(
    tmp_path,
    monkeypatch,
):
    first_work, first_attempt_root, first_attempt = _sealed_candidate_attempt(
        tmp_path,
        monkeypatch,
    )
    seal_stage_attempt(
        first_work,
        first_attempt_root,
        attempt=first_attempt,
        worker_identity="test-worker",
    )
    backend = _backend()
    compatibility = tmp_path / "compatibility"
    promote_candidate_stage(
        first_work,
        first_attempt_root,
        compatibility,
        backend,
        assessment_hash=ASSESSMENT_HASH,
        presentation_plan_hash=PLAN_HASH,
        candidate_hash=CANDIDATE_HASH,
        reviewer_standard_hash=REVIEWER_HASH,
    )

    next_candidate_hash = "3" * 64
    backend = _backend()
    next_work, next_attempt_root, next_attempt = _sealed_candidate_attempt(
        tmp_path,
        monkeypatch,
        candidate_hash=next_candidate_hash,
    )
    seal_stage_attempt(
        next_work,
        next_attempt_root,
        attempt=next_attempt,
        worker_identity="test-worker",
    )
    promote_candidate_stage(
        next_work,
        next_attempt_root,
        compatibility,
        backend,
        assessment_hash=ASSESSMENT_HASH,
        presentation_plan_hash=PLAN_HASH,
        candidate_hash=next_candidate_hash,
        reviewer_standard_hash=REVIEWER_HASH,
    )

    manifest = json.loads((compatibility / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["candidate_hash"] == next_candidate_hash
    assert manifest["stage_receipts"]["CANDIDATE_GENERATED"]["work_id"] == next_work.work_id
    assert (compatibility / "candidate" / "README.md").read_text(
        encoding="utf-8"
    ) == f"# Candidate {next_candidate_hash[:8]}\n"


def test_sealed_result_waits_for_reducer_and_stale_fence_fails_closed(
    tmp_path,
    monkeypatch,
):
    work, attempt_root, attempt = _sealed_candidate_attempt(tmp_path, monkeypatch)
    seal_stage_attempt(
        work,
        attempt_root,
        attempt=attempt,
        worker_identity="test-worker",
    )
    backend = _backend(status="FACTS_COLLECTING")
    compatibility = tmp_path / "compatibility"

    assert not compatibility.exists()
    with pytest.raises(ValueError, match="fence is stale"):
        promote_candidate_stage(
            work,
            attempt_root,
            compatibility,
            backend,
            assessment_hash=ASSESSMENT_HASH,
            presentation_plan_hash=PLAN_HASH,
            candidate_hash=CANDIDATE_HASH,
            reviewer_standard_hash=REVIEWER_HASH,
        )
    assert not (compatibility / "receipts" / "CANDIDATE_GENERATED.json").exists()


def test_deterministic_receipt_advances_without_review_and_retries_as_noop(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(paths, "runs_dir", lambda: tmp_path / "runs")
    backend = _backend(status="CANDIDATE_GENERATED", candidate_hash=CANDIDATE_HASH)
    fence = build_stage_fence(
        org_repo=ORG_REPO,
        source_revision=SOURCE_REVISION,
        lifecycle_status="CANDIDATE_GENERATED",
        facts_hash=FACTS_HASH,
        fact_acceptance_contract_hash=CONTRACT_HASH,
        prompt_hash=PROMPT_HASH,
        candidate_hash=CANDIDATE_HASH,
    )
    work = build_stage_work_item(
        target_stage="DETERMINISTIC_VALIDATED",
        fence=fence,
        dependency_hashes={
            "candidate": CANDIDATE_HASH,
            "deterministic_validation": "3" * 64,
            "facts": FACTS_HASH,
        },
    )
    attempt_root, attempt, artifacts = prepare_stage_attempt(
        work,
        worker_identity="test-worker",
    )
    write_redacted_json(
        artifacts / "manifest.json",
        {
            "org_repo": ORG_REPO,
            "source_revision": SOURCE_REVISION,
            "lifecycle_status": "DETERMINISTIC_VALIDATED",
            "facts_hash": FACTS_HASH,
            "candidate_hash": CANDIDATE_HASH,
            "completed_stages": ["FACTS_READY", "CANDIDATE_GENERATED", "DETERMINISTIC_VALIDATED"],
        },
    )
    write_redacted_json(
        artifacts / "review" / "deterministic-validation.json",
        {"valid": True},
    )
    seal_stage_attempt(
        work,
        attempt_root,
        attempt=attempt,
        worker_identity="test-worker",
    )
    compatibility = tmp_path / "compatibility"

    first = promote_deterministic_validation_stage(
        work,
        attempt_root,
        compatibility,
        backend,
    )
    history_count = len(backend.load(ORG_REPO).readme_poc_lifecycle.history)
    second = promote_deterministic_validation_stage(
        work,
        attempt_root,
        compatibility,
        backend,
    )

    assert first == second
    assert backend.load(ORG_REPO).readme_poc_lifecycle.status == "DETERMINISTIC_VALIDATED"
    assert len(backend.load(ORG_REPO).readme_poc_lifecycle.history) == history_count
    assert (compatibility / "review" / "deterministic-validation.json").is_file()
