"""Evaluate public-example proof against the governed task acceptance boundary."""

from __future__ import annotations

from typing import Any

from readme_agent.facts.example_quality import generated_example_quality_failures
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1

_SECRET_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "AUTH", "KEY")
_COMPILED_ECOSYSTEMS = {"cpp", "dotnet", "go", "java"}


def _verification(item: dict[str, Any]) -> LocalProductVerificationV1:
    return LocalProductVerificationV1.model_validate(item["verification"])


def evaluate_public_example_checks(
    *,
    control: dict[str, Any],
    start_status: str,
    current_head: str,
    current_status: str,
    results: dict[str, Any],
    curated_controls: dict[str, Any],
    remote_revisions: dict[str, str | None],
    hostile_controls: dict[str, Any],
    focused_exit_code: int,
    official_exit_code: int | None,
) -> dict[str, bool]:
    """Return a complete acceptance map for L8-TRUTH-05-PUBLIC-EXAMPLES."""

    verified = {ecosystem: _verification(item) for ecosystem, item in results.items()}
    isolated = {ecosystem: result.isolated_execution for ecosystem, result in verified.items()}
    curated = {name: _verification(item) for name, item in curated_controls.items()}
    return {
        "control_tree_clean": control["tree_clean_at_start"],
        "seven_ecosystems_present": set(verified)
        == {"cpp", "dotnet", "go", "java", "python", "rust", "typescript"},
        "representatives_clean": all(item["repository_clean"] for item in results.values()),
        "remote_default_revisions_match": all(
            remote_revisions[ecosystem] == result.source_revision
            for ecosystem, result in verified.items()
        ),
        "all_examples_truth_eligible": all(
            result.truth_eligible and result.outcome == "SOURCE_BUILD_VERIFIED"
            for result in verified.values()
        ),
        "all_examples_comment_free": all(
            not generated_example_quality_failures(ecosystem, item["example"]["code"])
            for ecosystem, item in results.items()
        ),
        "public_symbols_proven": all(
            result.verified_public_symbols for result in verified.values()
        ),
        "compiled_consumers_bound": all(
            verified[ecosystem].compiled_consumer is not None
            and verified[ecosystem].compiled_consumer.accepted
            for ecosystem in _COMPILED_ECOSYSTEMS
        ),
        "package_surfaces_bound": all(
            (
                verified["python"].python_package is not None,
                verified["rust"].rust_package is not None,
                verified["typescript"].typescript_package is not None,
            )
        ),
        "immutable_images_named": all(
            execution is not None
            and "@sha256:" in execution.policy.immutable_image
            and execution.image.repo_digest == execution.policy.immutable_image
            for execution in isolated.values()
        ),
        "dependency_inputs_pinned": all(
            bool(result.acquisition_dependency_pins) for result in verified.values()
        ),
        "secret_free_inputs": all(
            execution is not None
            and not any(
                marker in name.upper()
                for name in execution.environment_names
                for marker in _SECRET_MARKERS
            )
            for execution in isolated.values()
        ),
        "network_denied": all(
            execution is not None and execution.policy.network_mode == "none"
            for execution in isolated.values()
        ),
        "cleanup_complete": all(
            execution is not None and execution.cleanup.complete for execution in isolated.values()
        ),
        "stale_curated_examples_fail_closed": all(
            not result.truth_eligible and result.outcome == "BUILD_FAILED"
            for result in curated.values()
        ),
        "hostile_executor_controls_pass": hostile_controls["accepted"],
        "focused_regressions_pass": focused_exit_code == 0,
        "official_checks_pass": official_exit_code == 0,
        "tree_stable": current_head == control["head"] and current_status == start_status,
    }
