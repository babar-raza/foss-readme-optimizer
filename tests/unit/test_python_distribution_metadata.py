"""Isolated generated metadata is the only setup.py compatibility authority."""

from __future__ import annotations

import hashlib
import json

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
from readme_agent.facts.python_toolchain import PYTHON_311_IMAGE
from readme_agent.facts.root_role_schema import PackageRootRoleV1
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _snapshot(tmp_path) -> RepositorySnapshotV1:
    (tmp_path / "setup.py").write_text(
        "from setuptools import setup\nsetup(name='widget')\n",
        encoding="utf-8",
    )
    return RepositorySnapshotV1(
        org_repo="acme/widget",
        source_revision="a" * 40,
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
    stdout: str = "",
    return_code: int = 0,
    truth_eligible: bool = True,
    org_repo: str | None = None,
    source_revision: str | None = None,
    cleanup_complete: bool = True,
    argv: list[str] | None = None,
    environment_names: list[str] | None = None,
    policy: IsolatedExecutionPolicyV1 | None = None,
    input_sha256: str | None = None,
    input_file_count: int | None = None,
    policy_sha256: str | None = None,
) -> IsolatedExecutionResultV1:
    expected = build_isolated_input_bundle(request)
    execution_policy = policy or request.policy
    cleanup = ContainerCleanupV1(
        execution_container_removed=cleanup_complete,
        seed_container_removed=cleanup_complete,
        workspace_volume_removed=cleanup_complete,
    )
    return IsolatedExecutionResultV1(
        truth_eligible=truth_eligible,
        org_repo=org_repo or request.org_repo,
        source_revision=source_revision or request.source_revision,
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
        return_code=return_code,
        stdout=stdout,
        stderr="",
        timed_out=False,
        oom_killed=False,
        started_at="2026-08-05T00:00:00+00:00",
        finished_at="2026-08-05T00:00:01+00:00",
        cleanup=cleanup,
    )


def test_generated_pkg_info_is_snapshot_image_execution_and_hash_bound(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path)
    observed = {}

    def executor(request):
        observed["request"] = request
        assert request.source_root != snapshot.root_path
        assert (request.source_root / "repository" / "setup.py").read_bytes() == (
            snapshot.root_path / "setup.py"
        ).read_bytes()
        driver = request.source_root / "__readme_agent_metadata_driver.py"
        driver_text = driver.read_text(encoding="utf-8")
        assert "stdout=subprocess.PIPE" in driver_text
        assert "BytesParser(policy=policy.default)" in driver_text
        return _execution(request, stdout=_payload())

    monkeypatch.setattr(
        "readme_agent.facts.python_distribution_metadata.verify_repository_snapshot",
        lambda _snapshot: None,
    )

    proof = verify_python_distribution_metadata(snapshot, _root(), executor=executor)

    request = observed["request"]
    assert proof.truth_eligible is True
    assert proof.metadata is not None
    assert proof.metadata.requires_python == ">=3.7"
    assert proof.metadata.python_classifier_versions == [
        "3.7",
        "3.8",
        "3.9",
        "3.10",
        "3.11",
        "3.12",
    ]
    assert "3.13" not in proof.metadata.python_classifier_versions
    assert proof.execution.policy.immutable_image == PYTHON_311_IMAGE
    assert proof.execution.policy.network_mode == "none"
    assert proof.execution.policy.user != "0:0"
    assert proof.manifest_sha256 == hashlib.sha256((tmp_path / "setup.py").read_bytes()).hexdigest()
    assert request.argv == [
        "python",
        "/workspace/__readme_agent_metadata_driver.py",
        "repository",
    ]


@pytest.mark.parametrize(
    ("return_code", "stdout"),
    [
        (20, '{"schema_version":1,"status":"error","reason":"egg_info_failed"}'),
        (21, '{"schema_version":1,"status":"error","reason":"pkg_info_missing"}'),
        (22, '{"schema_version":1,"status":"error","reason":"multiple_pkg_info_files"}'),
    ],
    ids=["nonzero-egg-info", "missing-pkg-info", "multiple-pkg-info"],
)
def test_failed_metadata_generation_is_not_truth_eligible(
    tmp_path, monkeypatch, return_code, stdout
):
    snapshot = _snapshot(tmp_path)
    monkeypatch.setattr(
        "readme_agent.facts.python_distribution_metadata.verify_repository_snapshot",
        lambda _snapshot: None,
    )

    proof = verify_python_distribution_metadata(
        snapshot,
        _root(),
        executor=lambda request: _execution(
            request,
            stdout=stdout,
            return_code=return_code,
        ),
    )

    assert proof.truth_eligible is False
    assert proof.metadata is None
    assert proof.failure_reason == "isolated_execution_not_exact_success"


def test_repository_stdout_cannot_spoof_driver_owned_json(tmp_path, monkeypatch):
    snapshot = _snapshot(tmp_path)
    monkeypatch.setattr(
        "readme_agent.facts.python_distribution_metadata.verify_repository_snapshot",
        lambda _snapshot: None,
    )

    proof = verify_python_distribution_metadata(
        snapshot,
        _root(),
        executor=lambda request: _execution(
            request,
            stdout="repository-spoof\n" + _payload(),
        ),
    )

    assert proof.truth_eligible is False
    assert proof.failure_reason == "driver_output_invalid"


@pytest.mark.parametrize(
    "execution_change",
    [
        {"truth_eligible": False, "cleanup_complete": False},
        {"source_revision": "9" * 40},
        {"org_repo": "attacker/widget"},
    ],
    ids=["no-isolation-proof", "source-revision-mismatch", "repository-mismatch"],
)
def test_unisolated_or_mismatched_execution_is_not_truth_eligible(
    tmp_path, monkeypatch, execution_change
):
    snapshot = _snapshot(tmp_path)
    monkeypatch.setattr(
        "readme_agent.facts.python_distribution_metadata.verify_repository_snapshot",
        lambda _snapshot: None,
    )

    proof = verify_python_distribution_metadata(
        snapshot,
        _root(),
        executor=lambda request: _execution(
            request,
            stdout=_payload(),
            **execution_change,
        ),
    )

    assert proof.truth_eligible is False
    assert proof.metadata is None
    assert proof.failure_reason == (
        "isolated_execution_not_exact_success"
        if execution_change.get("truth_eligible") is False
        else "isolated_execution_request_binding_mismatch"
    )
