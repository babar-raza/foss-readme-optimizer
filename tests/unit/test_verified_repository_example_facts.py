"""Compile-verified repository examples become one bounded accepted fact."""

import hashlib

from readme_agent.facts.compiled_consumer_schema import CompiledConsumerProofV1
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


def _exact_failed_result(*, revision: str, code: str) -> LocalProductVerificationV1:
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
        return_code=1,
        stdout="/workspace/.readme-agent/ReadmeAgentExample.cs(1,1): error CS0117\n",
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
        return_code=1,
        stdout=isolated.stdout,
        stderr="",
        timed_out=False,
        isolation_kind="isolated_result_projection",
    )
    proof = CompiledConsumerProofV1(
        org_repo="acme/widget",
        source_revision=revision,
        ecosystem="dotnet",
        source_paths=["src/Scene.cs"],
        selected_symbols=["Scene"],
        source_sha256="f" * 64,
        example_sha256=hashlib.sha256(code.encode()).hexdigest(),
        isolated_execution=isolated,
        accepted=False,
    )
    return LocalProductVerificationV1(
        org_repo="acme/widget",
        source_revision=revision,
        ecosystem="dotnet",
        outcome="BUILD_FAILED",
        detail="exact consumer compilation failed",
        build=diagnostic,
        example_compile=diagnostic,
        isolated_execution=isolated,
        truth_eligible=False,
        compiled_consumer=proof,
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
        ],
        "withheld_inline_examples": [],
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


def test_does_not_retain_a_rejection_from_another_source_revision() -> None:
    revision = "a" * 40
    accepted = _example("var scene = new Scene();\n")
    rejected = _example("Scene.Render();\n")

    fact = compiled_repository_examples_fact(
        [accepted, rejected],
        org_repo="acme/widget",
        source_revision=revision,
        observed_at=None,
        verify_example_fn=lambda item: _result(
            revision=revision if item == accepted else "b" * 40,
            accepted=item == accepted,
        ),
    )

    assert fact is not None
    assert fact.value["withheld_inline_examples"] == []


def test_retains_only_an_exact_isolated_compiler_failure() -> None:
    revision = "a" * 40
    accepted = _example("var scene = new Scene();\n")
    rejected = _example("Scene.Render();\n")

    fact = compiled_repository_examples_fact(
        [accepted, rejected],
        org_repo="acme/widget",
        source_revision=revision,
        observed_at=None,
        verify_example_fn=lambda item: (
            _result(revision=revision, accepted=True)
            if item == accepted
            else _exact_failed_result(revision=revision, code=item.code)
        ),
    )

    assert fact is not None
    withheld = fact.value["withheld_inline_examples"]
    assert len(withheld) == 1
    assert (
        withheld[0]["compiled_consumer_example_sha256"]
        == hashlib.sha256(rejected.code.encode()).hexdigest()
    )
    assert (
        withheld[0]["compiler_diagnostic_sha256"]
        == hashlib.sha256(
            b"/workspace/.readme-agent/ReadmeAgentExample.cs(1,1): error CS0117\n\n"
        ).hexdigest()
    )
