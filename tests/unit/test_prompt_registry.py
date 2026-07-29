"""Offline tests for the categorical prompt registry (GOV-024, Wave 8.5) --
mirrors test_capabilities.py::TestRegistry's own build-time-gate testing
style: call `_build()` directly against a fixture directory rather than
relying on the real, eagerly-cached module-level registry."""

from pathlib import Path

import pytest

from readme_agent.errors import ConfigError
from readme_agent.llm import prompt_registry
from readme_agent.llm.prompt_schema import PromptManifest

_VALID_YAML = """prompt_id: {prompt_id}
category: {category}
version: "1"
model_route: {model_route}
owner: readme-agent
runtime_consumer: readme_agent.llm.planning_prompts
output_contract: TestOutputV1
invalidation_scope: test
dependent_artifacts:
  - test-output
system: |
  A system prompt.
user_template: |
  Hello $name.
"""


def _write(tmp_path: Path, category: str, filename: str, content: str) -> Path:
    directory = tmp_path / category
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(content, encoding="utf-8")
    return path


class TestBuild:
    def test_loads_a_valid_prompt(self, tmp_path):
        _write(
            tmp_path,
            "generation",
            "job_a.yaml",
            _VALID_YAML.format(prompt_id="job_a", category="generation", model_route="some_job"),
        )
        manifests, raw_content = prompt_registry._build(tmp_path)
        assert set(manifests) == {"job_a"}
        assert isinstance(manifests["job_a"], PromptManifest)
        assert "job_a" in raw_content

    def test_duplicate_prompt_id_raises(self, tmp_path):
        _write(
            tmp_path,
            "generation",
            "job_a.yaml",
            _VALID_YAML.format(prompt_id="job_a", category="generation", model_route="some_job"),
        )
        _write(
            tmp_path,
            "planning",
            "job_a.yaml",
            _VALID_YAML.format(prompt_id="job_a", category="planning", model_route="another_job"),
        )
        with pytest.raises(ConfigError, match="duplicate prompt_id"):
            prompt_registry._build(tmp_path)

    def test_category_directory_mismatch_raises(self, tmp_path):
        _write(
            tmp_path,
            "generation",
            "job_a.yaml",
            _VALID_YAML.format(prompt_id="job_a", category="planning", model_route="some_job"),
        )
        with pytest.raises(ConfigError, match="does not match"):
            prompt_registry._build(tmp_path)

    def test_prompt_id_must_match_filename(self, tmp_path):
        _write(
            tmp_path,
            "generation",
            "wrong-name.yaml",
            _VALID_YAML.format(prompt_id="job_a", category="generation", model_route="some_job"),
        )
        with pytest.raises(ConfigError, match="must match filename"):
            prompt_registry._build(tmp_path)

    def test_malformed_yaml_raises_config_error(self, tmp_path):
        _write(tmp_path, "generation", "a.yaml", "not: valid: yaml: [")
        with pytest.raises(ConfigError, match="not valid YAML"):
            prompt_registry._build(tmp_path)

    def test_schema_invalid_manifest_raises_config_error(self, tmp_path):
        _write(tmp_path, "generation", "a.yaml", "category: generation\n")  # missing prompt_id etc.
        with pytest.raises(ConfigError, match="malformed"):
            prompt_registry._build(tmp_path)

    def test_empty_directory_builds_cleanly(self, tmp_path):
        manifests, raw_content = prompt_registry._build(tmp_path)
        assert manifests == {}
        assert raw_content == {}

    def test_duplicate_model_route_raises(self, tmp_path):
        _write(
            tmp_path,
            "generation",
            "job_a.yaml",
            _VALID_YAML.format(prompt_id="job_a", category="generation", model_route="same_job"),
        )
        _write(
            tmp_path,
            "planning",
            "job_b.yaml",
            _VALID_YAML.format(prompt_id="job_b", category="planning", model_route="same_job"),
        )
        with pytest.raises(ConfigError, match="duplicate prompt model_route"):
            prompt_registry._build(tmp_path)

    def test_deprecated_prompt_is_not_active(self, tmp_path):
        _write(
            tmp_path,
            "generation",
            "job_a.yaml",
            _VALID_YAML.format(prompt_id="job_a", category="generation", model_route="some_job")
            + "deprecated: true\nreplacement_prompt_id: job_b\n",
        )
        with pytest.raises(ConfigError, match="deprecated prompt"):
            prompt_registry._build(tmp_path)


class TestContentHash:
    def test_deterministic_and_order_independent(self, tmp_path):
        _write(
            tmp_path,
            "generation",
            "job_a.yaml",
            _VALID_YAML.format(prompt_id="job_a", category="generation", model_route="job_a"),
        )
        _write(
            tmp_path,
            "planning",
            "job_b.yaml",
            _VALID_YAML.format(prompt_id="job_b", category="planning", model_route="job_b"),
        )
        manifests_1, raw_1 = prompt_registry._build(tmp_path)

        def _hash(raw_content: dict[str, str]) -> str:
            from readme_agent.readme.facts import sha256_text

            combined = "\x00".join(raw_content[key] for key in sorted(raw_content))
            return sha256_text(combined)

        assert _hash(raw_1) == _hash(dict(reversed(list(raw_1.items()))))

    def test_changes_when_any_registered_file_changes(self, tmp_path):
        path = _write(
            tmp_path,
            "generation",
            "job_a.yaml",
            _VALID_YAML.format(prompt_id="job_a", category="generation", model_route="some_job"),
        )
        _, raw_before = prompt_registry._build(tmp_path)
        path.write_text(
            _VALID_YAML.format(prompt_id="job_a", category="generation", model_route="some_job")
            + "notes: edited\n",
            encoding="utf-8",
        )
        _, raw_after = prompt_registry._build(tmp_path)
        assert raw_before != raw_after


class TestRealRegistry:
    """The real, eagerly-built module-level registry (from this repo's own
    prompts/ tree, populated once at import time)."""

    def test_all_real_prompts_are_registered(self):
        assert set(prompt_registry.all_manifests()) == {
            "blind_readme_quality_review",
            "draft_product_truth",
            "factual_readme_plan_review",
            "independent_readme_review",
            "plan_readme_composition",
            "trusted_readme_section_transform",
            "presentation_standard_compliance",
            "prose_quality_check",
            "relationship_explained",
            "repair_capability_selection",
            "specialist_selection_turn",
            "supervisor_turn",
            "visual_asset_accuracy",
        }

    def test_unknown_prompt_id_returns_none(self):
        assert prompt_registry.get("does_not_exist") is None

    def test_content_hash_is_stable_across_calls(self):
        assert prompt_registry.content_hash() == prompt_registry.content_hash()

    def test_supervisor_turn_has_a_turn_context_template(self):
        manifest = prompt_registry.get("supervisor_turn")
        assert manifest is not None
        assert manifest.turn_context_template is not None

    def test_relationship_explained_has_a_user_template(self):
        manifest = prompt_registry.get("relationship_explained")
        assert manifest is not None
        assert manifest.user_template is not None

    def test_default_build_is_independent_of_current_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        manifests, _ = prompt_registry._build()
        assert "supervisor_turn" in manifests
        assert "relationship_explained" in manifests

    def test_every_model_route_resolves_to_one_prompt(self):
        for prompt_id, manifest in prompt_registry.all_manifests().items():
            assert prompt_registry.prompt_id_for_route(manifest.model_route) == prompt_id

    def test_job_prompt_mismatch_fails_closed(self):
        with pytest.raises(ConfigError, match="requires prompt_id"):
            prompt_registry.validate_job_prompt("supervisor_planning", "relationship_explained")
