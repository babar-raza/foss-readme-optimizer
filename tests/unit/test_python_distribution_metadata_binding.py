"""Generated Python metadata must match the exact isolated execution request."""

from __future__ import annotations

import hashlib
import json
import subprocess

import pytest

from readme_agent.facts.isolated_execution_inputs import build_isolated_input_bundle
from readme_agent.facts.isolated_execution_schema import (
    ContainerCleanupV1,
    ContainerImageIdentityV1,
    IsolatedExecutionPolicyV1,
    IsolatedExecutionResultV1,
)
from readme_agent.facts.python_distribution_metadata import (
    verify_python_distribution_metadata,
)
from readme_agent.facts.root_role_schema import PackageRootRoleV1
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _snapshot(tmp_path, *, revision: str = "a" * 40) -> RepositorySnapshotV1:
    return RepositorySnapshotV1(
        org_repo="acme/widget",
        source_revision=revision,
        snapshot_root=str(tmp_path.resolve()),
        inventory_sha256="b" * 64,
        package_roots=(),
        captured_at="2026-08-05T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.test/acme/widget.git",
            git_tree_sha256="b" * 64,
        ),
    )


def _root() -> PackageRootRoleV1:
    return PackageRootRoleV1(
        path=".",
        ecosystem="python",
        manifest_path="setup.py",
        role="product",
        confidence=1.0,
        rationale=["selected root"],
    )


def _payload() -> str:
    return json.dumps(
        {
            "schema_version": 1,
            "status": "ok",
            "pkg_info_path": "widget.egg-info/PKG-INFO",
            "pkg_info_sha256": "c" * 64,
            "requires_python": ">=3.7",
            "python_classifier_versions": ["3.7", "3.8", "3.9", "3.10", "3.11", "3.12"],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _execution(
    request,
    *,
    policy: IsolatedExecutionPolicyV1 | None = None,
    argv: list[str] | None = None,
    environment_names: list[str] | None = None,
    input_sha256: str | None = None,
    input_file_count: int | None = None,
    policy_sha256: str | None = None,
) -> IsolatedExecutionResultV1:
    expected = build_isolated_input_bundle(request)
    execution_policy = policy or request.policy
    return IsolatedExecutionResultV1(
        truth_eligible=True,
        org_repo=request.org_repo,
        source_revision=request.source_revision,
        argv=argv or request.argv,
        environment_names=(
            environment_names if environment_names is not None else sorted(request.environment)
        ),
        input_sha256=input_sha256 or expected.input_sha256,
        input_file_count=(
            input_file_count if input_file_count is not None else expected.input_file_count
        ),
        policy_sha256=policy_sha256 or expected.policy_sha256,
        policy=execution_policy,
        image=ContainerImageIdentityV1(
            requested_reference=execution_policy.immutable_image,
            repo_digest=execution_policy.immutable_image,
            image_id="sha256:" + "f" * 64,
            operating_system="linux",
            architecture="amd64",
            engine_version="28.4.0",
        ),
        container_id="container-id",
        process_inventory=["python __readme_agent_metadata_driver.py"],
        return_code=0,
        stdout=_payload(),
        stderr="",
        timed_out=False,
        oom_killed=False,
        started_at="2026-08-05T00:00:00+00:00",
        finished_at="2026-08-05T00:00:01+00:00",
        cleanup=ContainerCleanupV1(
            execution_container_removed=True,
            seed_container_removed=True,
            workspace_volume_removed=True,
        ),
    )


@pytest.mark.parametrize(
    "forgery",
    ["argv", "environment", "policy", "image", "input_hash", "input_count", "policy_hash"],
)
def test_executor_self_report_cannot_replace_expected_request_binding(
    tmp_path, monkeypatch, forgery
):
    (tmp_path / "setup.py").write_text("from setuptools import setup\n", encoding="utf-8")
    snapshot = _snapshot(tmp_path)
    monkeypatch.setattr(
        "readme_agent.facts.python_distribution_metadata.verify_repository_snapshot",
        lambda _snapshot: None,
    )

    def executor(request):
        changes = {}
        if forgery == "argv":
            changes["argv"] = ["python", "/workspace/attacker.py"]
        elif forgery == "environment":
            changes["environment_names"] = ["HOME"]
        elif forgery == "policy":
            changes["policy"] = request.policy.model_copy(update={"cpu_limit": 2.0})
        elif forgery == "image":
            changes["policy"] = request.policy.model_copy(
                update={"immutable_image": "attacker/python@sha256:" + "9" * 64}
            )
        elif forgery == "input_hash":
            changes["input_sha256"] = "9" * 64
        elif forgery == "input_count":
            changes["input_file_count"] = 999
        elif forgery == "policy_hash":
            changes["policy_sha256"] = "9" * 64
        return _execution(request, **changes)

    proof = verify_python_distribution_metadata(snapshot, _root(), executor=executor)

    assert proof.truth_eligible is False
    assert proof.metadata is None
    assert proof.failure_reason == "isolated_execution_request_binding_mismatch"


def test_manifest_hash_and_execution_use_exported_head_not_dirty_checkout(tmp_path, monkeypatch):
    head_setup = b"from setuptools import setup\nsetup(name='widget', python_requires='>=3.7')\n"
    dirty_setup = b"from setuptools import setup\nsetup(name='widget', python_requires='>=9.9')\n"
    (tmp_path / "setup.py").write_bytes(head_setup)
    for argv in (
        ["git", "init"],
        ["git", "config", "user.email", "test@example.invalid"],
        ["git", "config", "user.name", "Test"],
        ["git", "add", "setup.py"],
        ["git", "commit", "-m", "fixture"],
    ):
        subprocess.run(argv, cwd=tmp_path, check=True, capture_output=True)
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    (tmp_path / "setup.py").write_bytes(dirty_setup)
    snapshot = _snapshot(tmp_path, revision=revision)
    monkeypatch.setattr(
        "readme_agent.facts.python_distribution_metadata.verify_repository_snapshot",
        lambda _snapshot: None,
    )

    def executor(request):
        exported = request.source_root / "repository" / "setup.py"
        assert exported.read_bytes() == head_setup
        assert exported.read_bytes() != dirty_setup
        return _execution(request)

    proof = verify_python_distribution_metadata(snapshot, _root(), executor=executor)

    assert proof.truth_eligible is True
    assert proof.metadata is not None
    assert proof.metadata.requires_python == ">=3.7"
    assert proof.manifest_sha256 == hashlib.sha256(head_setup).hexdigest()
    assert proof.manifest_sha256 != hashlib.sha256(dirty_setup).hexdigest()
