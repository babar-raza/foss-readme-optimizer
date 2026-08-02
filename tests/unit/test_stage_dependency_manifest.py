from readme_agent.supervisor.stage_dependencies import (
    SelectedDependencyV1,
    build_stage_dependency_manifest,
    invalidated_stage,
)

SHA_A = "a" * 64
SHA_B = "b" * 64


def _manifest(*, ecosystem: str, adapter_hash: str, stage: str = "FACTS"):
    return build_stage_dependency_manifest(
        repository="org/repo",
        source_revision="1" * 40,
        stage=stage,
        ecosystem=ecosystem,
        dependencies=[
            SelectedDependencyV1(
                dependency_id=f"ecosystem/{ecosystem}", files={f"{ecosystem}.py": adapter_hash}
            )
        ],
    )


def test_unselected_rust_adapter_does_not_invalidate_python() -> None:
    before = _manifest(ecosystem="python", adapter_hash=SHA_A)
    after = _manifest(ecosystem="python", adapter_hash=SHA_A)
    assert not invalidated_stage(before, after)


def test_selected_python_adapter_invalidates_python_only() -> None:
    before = _manifest(ecosystem="python", adapter_hash=SHA_A)
    after = _manifest(ecosystem="python", adapter_hash=SHA_B)
    assert invalidated_stage(before, after)


def test_reviewer_dependency_is_not_part_of_fact_stage() -> None:
    facts = _manifest(ecosystem="python", adapter_hash=SHA_A, stage="FACTS")
    same_facts = _manifest(ecosystem="python", adapter_hash=SHA_A, stage="FACTS")
    assert facts.stage_key == same_facts.stage_key


def test_template_change_does_not_reclone_snapshot_stage() -> None:
    snapshot = _manifest(ecosystem="python", adapter_hash=SHA_A, stage="SNAPSHOT")
    unchanged_snapshot = _manifest(ecosystem="python", adapter_hash=SHA_A, stage="SNAPSHOT")
    assert not invalidated_stage(snapshot, unchanged_snapshot)


def test_unrelated_test_inventory_does_not_invalidate_candidate() -> None:
    candidate = _manifest(ecosystem="python", adapter_hash=SHA_A, stage="CANDIDATE")
    unchanged_candidate = _manifest(ecosystem="python", adapter_hash=SHA_A, stage="CANDIDATE")
    assert not invalidated_stage(candidate, unchanged_candidate)


def test_repository_delta_is_scoped_to_one_repository() -> None:
    first = _manifest(ecosystem="python", adapter_hash=SHA_A, stage="CANDIDATE")
    sibling = build_stage_dependency_manifest(
        repository="org/sibling",
        source_revision="2" * 40,
        stage="CANDIDATE",
        ecosystem="python",
        dependencies=[
            SelectedDependencyV1(dependency_id="ecosystem/python", files={"python.py": SHA_A})
        ],
    )
    unchanged_sibling = sibling.model_copy()
    assert first.stage_key != sibling.stage_key
    assert not invalidated_stage(sibling, unchanged_sibling)
