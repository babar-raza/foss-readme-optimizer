"""Compile-verified repository examples become one bounded accepted fact."""

from readme_agent.facts.example_execution import ExampleExecutionResultV1
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.isolated_execution_schema import (
    ContainerCleanupV1,
    ContainerImageIdentityV1,
    IsolatedExecutionPolicyV1,
    IsolatedExecutionResultV1,
)
from readme_agent.facts.verified_repository_example_facts import (
    compiled_repository_examples_fact,
)
from readme_agent.registry.models import MinimalExamplePolicy

IMAGE = "example@sha256:" + "b" * 64


def _example(code: str) -> MinimalExamplePolicy:
    return MinimalExamplePolicy(
        language="dotnet",
        class_name="ReadmeExample",
        code=code,
        evidence_paths=["README.md"],
    )


def _result(*, revision: str, accepted: bool) -> LocalProductVerificationV1:
    policy = IsolatedExecutionPolicyV1(immutable_image=IMAGE)
    isolated = IsolatedExecutionResultV1(
        truth_eligible=True,
        org_repo="acme/widget",
        source_revision=revision,
        argv=["dotnet", "build"],
        environment_names=["HOME"],
        input_sha256="c" * 64,
        input_file_count=1,
        policy_sha256="d" * 64,
        policy=policy,
        image=ContainerImageIdentityV1(
            requested_reference=IMAGE,
            repo_digest=IMAGE,
            image_id="sha256:" + "e" * 64,
            operating_system="linux",
            architecture="amd64",
            engine_version="fixture",
        ),
        container_id="fixture",
        process_inventory=[],
        return_code=0,
        stdout="",
        stderr="",
        timed_out=False,
        oom_killed=False,
        started_at="2026-08-25T00:00:00+00:00",
        finished_at="2026-08-25T00:00:01+00:00",
        cleanup=ContainerCleanupV1(
            execution_container_removed=True,
            seed_container_removed=True,
            workspace_volume_removed=True,
        ),
    )
    diagnostic = ExampleExecutionResultV1(
        argv=isolated.argv,
        return_code=0 if accepted else 1,
        stdout="",
        stderr="",
        timed_out=False,
        isolation_kind="isolated_result_projection",
    )
    return LocalProductVerificationV1(
        org_repo="acme/widget",
        source_revision=revision,
        ecosystem="dotnet",
        outcome="SOURCE_BUILD_VERIFIED" if accepted else "BUILD_FAILED",
        detail="controlled result",
        build=diagnostic,
        isolated_execution=isolated if accepted else None,
        truth_eligible=accepted,
        public_api_sha256="a" * 64 if accepted else None,
    )


def test_collects_only_exact_revision_compile_verified_examples() -> None:
    revision = "a" * 40
    accepted = _example("var scene = new Scene();\n")
    rejected = _example("Scene.Render();\n")

    fact = compiled_repository_examples_fact(
        [accepted, rejected],
        org_repo="acme/widget",
        source_revision=revision,
        observed_at=None,
        verify_example_fn=lambda item: _result(
            revision=revision,
            accepted=item == accepted,
        ),
    )

    assert fact is not None
    assert fact.verification_state == "verified"
    assert fact.value == {
        "inline_examples": [
            {
                "title": "ReadmeExample",
                "language": "dotnet",
                "code": "var scene = new Scene();\n",
                "evidence_paths": ["README.md"],
                "static_api_verified": True,
                "runtime_verified": False,
                "verification_outcome": "SOURCE_BUILD_VERIFIED",
                "public_api_sha256": "a" * 64,
            }
        ]
    }


def test_rejects_a_success_from_another_source_revision() -> None:
    fact = compiled_repository_examples_fact(
        [_example("var scene = new Scene();\n")],
        org_repo="acme/widget",
        source_revision="a" * 40,
        observed_at=None,
        verify_example_fn=lambda _item: _result(revision="b" * 40, accepted=True),
    )

    assert fact is None


def test_deduplicates_examples_and_reuses_a_known_validated_result() -> None:
    revision = "a" * 40
    example = _example("var scene = new Scene();\n")
    result = _result(revision=revision, accepted=True)

    fact = compiled_repository_examples_fact(
        [example, example],
        org_repo="acme/widget",
        source_revision=revision,
        observed_at=None,
        verify_example_fn=lambda _item: (_ for _ in ()).throw(AssertionError("unexpected call")),
        known_verifications={example.code.rstrip() + "\n": result},
    )

    assert fact is not None
    assert len(fact.value["inline_examples"]) == 1


def test_bounds_verification_attempts() -> None:
    calls = 0

    def reject(_item: MinimalExamplePolicy) -> LocalProductVerificationV1:
        nonlocal calls
        calls += 1
        return _result(revision="a" * 40, accepted=False)

    candidates = [_example(f"var scene{i} = new Scene();\n") for i in range(12)]

    fact = compiled_repository_examples_fact(
        candidates,
        org_repo="acme/widget",
        source_revision="a" * 40,
        observed_at=None,
        verify_example_fn=reject,
    )

    assert fact is None
    assert calls == 8
