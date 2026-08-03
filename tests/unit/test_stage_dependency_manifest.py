from pathlib import Path

from readme_agent.supervisor import stage_dependencies
from readme_agent.supervisor.stage_dependencies import (
    SelectedDependencyV1,
    build_stage_dependency_manifest,
    current_candidate_stage_dependency_manifest,
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


def test_current_candidate_manifest_selects_code_prompt_and_template_without_tests() -> None:
    manifest = current_candidate_stage_dependency_manifest(
        repository="org/repo",
        source_revision="1" * 40,
        ecosystem="python",
    )

    selected = {path for dependency in manifest.dependencies for path in dependency.files}
    assert "src/readme_agent/readme/diagram_role_semantics.py" in selected
    assert "prompts/generation/plan_readme_composition.yaml" in selected
    assert "templates/readme/repository-presentation-v1.json" in selected
    required_candidate_owners = {
        "src/readme_agent/capabilities/build_presentation_plan.py",
        "src/readme_agent/capabilities/render_readme_candidate.py",
        "src/readme_agent/presentation/document_planner.py",
        "src/readme_agent/presentation/git_patch.py",
        "src/readme_agent/readme/idea_candidate.py",
        "src/readme_agent/readme/verified_preservation_composition.py",
        "src/readme_agent/supervisor/local_poc_evidence.py",
        "src/readme_agent/supervisor/local_poc_snapshot_evidence.py",
        "src/readme_agent/supervisor/portfolio_scheduler/contracts.py",
        "src/readme_agent/supervisor/portfolio_scheduler/lane.py",
        "src/readme_agent/supervisor/portfolio_scheduler/reducer.py",
        "src/readme_agent/supervisor/portfolio_scheduler/stages.py",
    }
    assert required_candidate_owners <= selected
    assert all(not path.startswith("tests/") for path in selected)
    assert all("readme_review" not in path for path in selected)
    assert all("reviewer_client" not in path for path in selected)


def test_selected_owner_byte_change_alters_candidate_stage_key(tmp_path: Path, monkeypatch) -> None:
    for relative_paths in stage_dependencies._CANDIDATE_DEPENDENCY_GROUPS.values():
        for relative_path in relative_paths:
            path = tmp_path / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"baseline:{relative_path}\n", encoding="utf-8")
    monkeypatch.setattr(stage_dependencies, "_REPOSITORY_ROOT", tmp_path)

    before = current_candidate_stage_dependency_manifest(
        repository="org/repo",
        source_revision="1" * 40,
        ecosystem="python",
    )
    owner = tmp_path / "src/readme_agent/capabilities/build_presentation_plan.py"
    owner.write_text("changed source-bound plan owner\n", encoding="utf-8")
    after = current_candidate_stage_dependency_manifest(
        repository="org/repo",
        source_revision="1" * 40,
        ecosystem="python",
    )

    assert before.stage == after.stage == "CANDIDATE"
    assert before.stage_key != after.stage_key
    changed_groups = {
        current.dependency_id
        for prior, current in zip(before.dependencies, after.dependencies, strict=True)
        if prior != current
    }
    assert changed_groups == {"candidate_orchestration"}
