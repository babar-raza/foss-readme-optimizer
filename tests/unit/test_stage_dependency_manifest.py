from pathlib import Path

import pytest

from readme_agent.supervisor import stage_dependencies
from readme_agent.supervisor.presentation_component_versions import classify_component_delta
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
    assert "src/readme_agent/readme/capability_semantics.py" in selected
    assert "src/readme_agent/readme/diagram_role_semantics.py" in selected
    assert "src/readme_agent/readme/diagram_semantic_candidates.py" in selected
    assert "src/readme_agent/readme/header_visual_mermaid.py" in selected
    assert "src/readme_agent/readme/header_visual_layout.py" in selected
    assert "src/readme_agent/readme/opening_summary_fallback.py" in selected
    assert "src/readme_agent/presentation/verified_source_claim_matching.py" in selected
    assert "src/readme_agent/presentation/verified_source_claim_resolution_engine.py" in selected
    assert "src/readme_agent/presentation/verified_source_detail_presentation.py" in selected
    assert "src/readme_agent/readme/source_claim_conversion_binding.py" in selected
    assert "src/readme_agent/readme/source_claim_mcp_binding.py" in selected
    assert "src/readme_agent/readme/source_claim_repository_asset_binding.py" in selected
    assert "src/readme_agent/readme/source_claim_structured_matching.py" in selected
    assert "src/readme_agent/presentation/verified_template_documentation.py" in selected
    assert "src/readme_agent/presentation/verified_template_api_reference.py" in selected
    assert "src/readme_agent/presentation/verified_template_capabilities.py" in selected
    assert "src/readme_agent/presentation/verified_template_capability_seo.py" in selected
    assert "src/readme_agent/presentation/verified_template_example_presentation.py" in selected
    assert "src/readme_agent/presentation/verified_template_provenance.py" in selected
    assert "src/readme_agent/readme/example_assurance_validation.py" in selected
    assert "src/readme_agent/presentation/verified_template_link_budget.py" in selected
    assert "src/readme_agent/links/allocation.py" in selected
    assert "prompts/generation/plan_readme_composition.yaml" in selected
    assert "templates/readme/repository-presentation-v1.json" in selected
    assert "templates/readme/verified-minimal-example.md" in selected
    assert "src/readme_agent/validation/presentation_template.py" in selected
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
    assert "prompts/verification/independent_readme_review.yaml" in selected
    assert all("reviewer_client" not in path for path in selected)


def test_candidate_manifest_tracks_semantic_owners_at_the_earliest_affected_stage() -> None:
    groups = stage_dependencies._CANDIDATE_DEPENDENCY_GROUPS

    assert {
        "src/readme_agent/presentation/verified_template_api_descriptions.py",
        "src/readme_agent/presentation/verified_template_api_members.py",
        "src/readme_agent/presentation/verified_template_api_text.py",
        "src/readme_agent/presentation/verified_template_golden_workflow.py",
        "src/readme_agent/readme/public_limitations.py",
    } <= set(groups["document_compilation"][2])
    assert {
        "src/readme_agent/readme/claim_accountability_coordinates.py",
        "src/readme_agent/readme/source_claim_fact_binding.py",
        "src/readme_agent/readme/source_claim_obligations.py",
    } <= set(groups["source_claim_accountability"][2])
    assert "src/readme_agent/readme/presentation_lint_api_reference.py" in set(
        groups["presentation_validation"][2]
    )


def test_selected_owner_byte_change_alters_candidate_stage_key(tmp_path: Path, monkeypatch) -> None:
    for _scope, _stage, relative_paths in stage_dependencies._CANDIDATE_DEPENDENCY_GROUPS.values():
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


def _component_manifest(*, scope: str, digest: str, stage: str = "PLAN_READY"):
    return build_stage_dependency_manifest(
        repository="org/repo",
        source_revision="1" * 40,
        stage="CANDIDATE",
        ecosystem="python",
        dependencies=[
            SelectedDependencyV1(
                dependency_id="presentation/test",
                files={"component.py": digest},
                semantic_scope=scope,
                earliest_affected_stage=stage,
            )
        ],
    )


def test_cosmetic_component_delta_preserves_validity_as_available_update() -> None:
    delta = classify_component_delta(
        _component_manifest(scope="cosmetic", digest=SHA_A),
        _component_manifest(scope="cosmetic", digest=SHA_B),
    )

    assert delta.outcome == "VALID_UPDATE_AVAILABLE"
    assert delta.fact_validity_preserved is True
    assert delta.presentation_validity_preserved is True
    assert delta.earliest_affected_stage == "PLAN_READY"


def test_factuality_component_delta_fails_closed_at_fact_boundary() -> None:
    delta = classify_component_delta(
        _component_manifest(scope="factuality", digest=SHA_A, stage="FACTS_COLLECTING"),
        _component_manifest(scope="factuality", digest=SHA_B, stage="FACTS_COLLECTING"),
    )

    assert delta.outcome == "INVALIDATED"
    assert delta.fact_validity_preserved is False
    assert delta.earliest_affected_stage == "FACTS_COLLECTING"


def test_scope_downgrade_cannot_turn_prior_safety_owner_into_cosmetic_update() -> None:
    delta = classify_component_delta(
        _component_manifest(scope="safety", digest=SHA_A, stage="CANDIDATE_GENERATED"),
        _component_manifest(scope="cosmetic", digest=SHA_B, stage="PLAN_READY"),
    )

    assert delta.outcome == "INVALIDATED"
    assert set(delta.changed_scopes) == {"cosmetic", "safety"}
    assert delta.earliest_affected_stage == "PLAN_READY"


def test_component_versions_and_manifest_key_are_self_authenticating() -> None:
    manifest = _component_manifest(scope="structural", digest=SHA_A)
    payload = manifest.model_dump(mode="json")
    payload["dependencies"][0]["component_version"] = "9" * 64

    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="component_version"):
        type(manifest).model_validate(payload)
