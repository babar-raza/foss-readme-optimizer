"""Rust dependency acquisition and locked external-consumer contracts."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from readme_agent.ecosystems.rust_api_schema import RustConsumerExampleV1
from readme_agent.ecosystems.rust_package_layout import inspect_rust_package_layout
from readme_agent.ecosystems.rust_public_api import inspect_rust_public_api
from readme_agent.facts import rust_consumer, rust_dependency_acquisition
from readme_agent.facts.isolated_execution import IsolatedExecutionError
from readme_agent.facts.isolated_execution_schema import (
    ContainerCleanupV1,
    ContainerImageIdentityV1,
    IsolatedExecutionResultV1,
)
from readme_agent.facts.rust_consumer import prove_rust_consumer
from readme_agent.facts.rust_dependency_acquisition import (
    RUST_188_IMAGE,
    acquire_rust_dependencies,
    materialize_rust_dependencies,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def _source(root: Path) -> None:
    _write(
        root / "Cargo.toml",
        """
[package]
name = "widget-core"
version = "1.0.0"
edition = "2021"
publish = false

[dependencies]
serde = "1"
""".strip(),
    )
    _write(
        root / "src/lib.rs",
        """
pub struct Root {
    pub visible: i32,
    pub(crate) hidden: i32,
}

impl Root {
    pub fn new() -> Self { Self { visible: 1, hidden: 2 } }
}
""".strip(),
    )


def _snapshot(root: Path) -> RepositorySnapshotV1:
    return RepositorySnapshotV1(
        org_repo="fixture/widget-core",
        source_revision="a" * 40,
        snapshot_root=str(root.resolve()),
        inventory_sha256="0" * 64,
        captured_at="2026-07-27T00:00:00+00:00",
        provenance=SnapshotProvenanceV1(
            clone_url="https://example.invalid/fixture/widget-core.git",
            git_tree_sha256="0" * 64,
        ),
    )


def _completed(
    argv: list[str],
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, returncode, stdout, stderr)


class AcquisitionRunner:
    """Fake Docker boundary that materializes the Cargo outputs it reports."""

    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def run(self, argv, *, timeout_seconds, input_bytes=None):
        self.commands.append(argv)
        if argv[:2] == ["image", "inspect"]:
            return _completed(
                argv,
                stdout=json.dumps(
                    [
                        {
                            "RepoDigests": [RUST_188_IMAGE],
                            "Id": "sha256:" + "b" * 64,
                            "Os": "linux",
                            "Architecture": "amd64",
                        }
                    ]
                ),
            )
        if argv[:2] == ["version", "--format"]:
            return _completed(argv, stdout="28.4.0\n")
        if argv[0] == "run":
            mounted = argv[argv.index("--volume") + 1]
            workspace = Path(mounted.removesuffix(":/workspace"))
            consumer = workspace / "consumer"
            cargo_args = argv[argv.index(RUST_188_IMAGE) + 1 :]
            if cargo_args == ["generate-lockfile"]:
                (consumer / "Cargo.lock").write_text(
                    'version = 4\n\n[[package]]\nname = "serde"\nversion = "1.0.0"\n',
                    encoding="utf-8",
                )
                return _completed(argv)
            if cargo_args == ["vendor", "--locked", "vendor"]:
                _write(consumer / "vendor/serde/src/lib.rs", "pub trait Serialize {}\n")
                return _completed(
                    argv,
                    stdout=(
                        "[source.crates-io]\nreplace-with = "
                        '"vendored-sources"\n\n[source.vendored-sources]\n'
                        'directory = "vendor"\n'
                    ),
                )
        if argv[:2] == ["rm", "--force"]:
            return _completed(argv)
        if argv[:2] == ["container", "inspect"]:
            return _completed(argv, returncode=1, stderr="not found")
        if argv[:2] == ["ps", "-aq"]:
            return _completed(argv)
        raise AssertionError(f"unexpected Docker command: {argv}")


class FailingAcquisitionRunner(AcquisitionRunner):
    def run(self, argv, *, timeout_seconds, input_bytes=None):
        if argv[0] == "run":
            self.commands.append(argv)
            return _completed(argv, returncode=101, stderr="registry unavailable")
        return super().run(
            argv,
            timeout_seconds=timeout_seconds,
            input_bytes=input_bytes,
        )


class TransientAcquisitionRunner(AcquisitionRunner):
    def __init__(self) -> None:
        super().__init__()
        self.failures_remaining = 1

    def run(self, argv, *, timeout_seconds, input_bytes=None):
        if argv[0] == "run" and self.failures_remaining:
            self.commands.append(argv)
            self.failures_remaining -= 1
            return _completed(argv, returncode=125, stderr="Docker transport interrupted")
        return super().run(
            argv,
            timeout_seconds=timeout_seconds,
            input_bytes=input_bytes,
        )


def _isolated_result(request, *, return_code: int = 0) -> IsolatedExecutionResultV1:
    return IsolatedExecutionResultV1(
        truth_eligible=True,
        org_repo=request.org_repo,
        source_revision=request.source_revision,
        argv=request.argv,
        environment_names=sorted(request.environment),
        input_sha256="1" * 64,
        input_file_count=8,
        policy_sha256="2" * 64,
        policy=request.policy,
        image=ContainerImageIdentityV1(
            requested_reference=RUST_188_IMAGE,
            repo_digest=RUST_188_IMAGE,
            image_id="sha256:" + "b" * 64,
            operating_system="linux",
            architecture="amd64",
            engine_version="28.4.0",
        ),
        container_id="container-id",
        process_inventory=[],
        return_code=return_code,
        stdout="",
        stderr="" if return_code == 0 else "error[E0624]: associated function is private",
        timed_out=False,
        oom_killed=False,
        started_at="2026-07-27T00:00:00+00:00",
        finished_at="2026-07-27T00:00:01+00:00",
        cleanup=ContainerCleanupV1(
            execution_container_removed=True,
            seed_container_removed=True,
            workspace_volume_removed=True,
        ),
    )


def test_acquisition_is_networked_but_bounded_and_cache_validated(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    package = inspect_rust_package_layout(source)
    cache = tmp_path / "cache"
    runner = AcquisitionRunner()
    monkeypatch.setattr(rust_dependency_acquisition, "verify_repository_snapshot", lambda _: None)

    bundle = acquire_rust_dependencies(
        snapshot,
        package,
        cache_root=cache,
        runner=runner,
    )
    materialized = tmp_path / "materialized"
    materialized.mkdir()
    materialize_rust_dependencies(bundle, materialized)

    assert bundle.acquisition.network_mode == "bridge"
    assert bundle.acquisition.environment_names == [
        "CARGO_HOME",
        "CARGO_TERM_COLOR",
        "HOME",
    ]
    assert bundle.acquisition.commands == [
        ["generate-lockfile"],
        ["vendor", "--locked", "vendor"],
    ]
    assert bundle.acquisition.lock_package_count == 1
    assert (materialized / "Cargo.lock").is_file()
    assert (materialized / "vendor/serde/src/lib.rs").is_file()
    assert (materialized / ".cargo/config.toml").is_file()
    docker_runs = [argv for argv in runner.commands if argv[0] == "run"]
    assert len(docker_runs) == 2
    for argv in docker_runs:
        joined = "\0".join(argv)
        for expected in (
            ["--network", "bridge"],
            ["--read-only"],
            ["--cap-drop", "ALL"],
            ["--security-opt", "no-new-privileges:true"],
            ["--user", "65534:65534"],
        ):
            assert "\0".join(expected) in joined
        assert not any("TOKEN" in item or "SECRET" in item for item in argv)

    second_runner = AcquisitionRunner()
    second = acquire_rust_dependencies(
        snapshot,
        package,
        cache_root=cache,
        runner=second_runner,
    )
    assert second.acquisition == bundle.acquisition
    assert second_runner.commands == []


def test_external_consumer_uses_locked_offline_public_surface(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    package = inspect_rust_package_layout(source)
    surface = inspect_rust_public_api(
        source,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    runner = AcquisitionRunner()
    monkeypatch.setattr(rust_dependency_acquisition, "verify_repository_snapshot", lambda _: None)
    monkeypatch.setattr(rust_consumer, "verify_repository_snapshot", lambda _: None)
    bundle = acquire_rust_dependencies(
        snapshot,
        package,
        cache_root=tmp_path / "cache",
        runner=runner,
    )
    requests = []
    materialized = {}

    def execute(request):
        requests.append(request)
        materialized["lock"] = (request.source_root / "consumer/Cargo.lock").is_file()
        materialized["vendor"] = (request.source_root / "vendor").is_dir()
        materialized["config"] = (request.source_root / ".cargo/config.toml").is_file()
        return _isolated_result(request)

    example = RustConsumerExampleV1(
        code=(
            "use widget_core::Root;\n"
            "fn main() {\n"
            "    let value = Root::new();\n"
            '    println!("{}", value.visible);\n'
            "}\n"
        ),
        required_symbols=[
            "widget_core::Root",
            "widget_core::Root.new",
            "widget_core::Root.visible",
        ],
    )
    proof = prove_rust_consumer(
        snapshot,
        package,
        surface,
        example,
        acquirer=lambda _snapshot, _package: bundle,
        executor=execute,
    )

    assert proof.accepted is True
    assert set(proof.verified_symbols) == set(example.required_symbols)
    assert len(requests) == 1
    request = requests[0]
    assert request.policy.network_mode == "none"
    assert request.argv == [
        "cargo",
        "check",
        "--locked",
        "--offline",
        "--manifest-path",
        "consumer/Cargo.toml",
    ]
    assert materialized == {"lock": True, "vendor": True, "config": True}


def test_acquisition_failure_cleans_container_and_publishes_no_bundle(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    package = inspect_rust_package_layout(source)
    cache = tmp_path / "cache"
    runner = FailingAcquisitionRunner()
    monkeypatch.setattr(rust_dependency_acquisition, "verify_repository_snapshot", lambda _: None)

    with pytest.raises(IsolatedExecutionError, match="networked Cargo acquisition failed"):
        acquire_rust_dependencies(
            snapshot,
            package,
            cache_root=cache,
            runner=runner,
        )

    assert any(argv[:2] == ["rm", "--force"] for argv in runner.commands)
    assert any(argv[:2] == ["container", "inspect"] for argv in runner.commands)
    assert list(cache.glob("*/acquisition.json")) == []


def test_transient_acquisition_control_failure_retries_idempotently(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    package = inspect_rust_package_layout(source)
    runner = TransientAcquisitionRunner()
    monkeypatch.setattr(rust_dependency_acquisition, "verify_repository_snapshot", lambda _: None)

    bundle = acquire_rust_dependencies(
        snapshot,
        package,
        cache_root=tmp_path / "cache",
        runner=runner,
    )

    assert bundle.acquisition.lock_package_count == 1
    assert len([argv for argv in runner.commands if argv[0] == "run"]) == 3


def test_checksum_corruption_blocks_cache_reuse(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    package = inspect_rust_package_layout(source)
    cache = tmp_path / "cache"
    monkeypatch.setattr(rust_dependency_acquisition, "verify_repository_snapshot", lambda _: None)
    bundle = acquire_rust_dependencies(
        snapshot,
        package,
        cache_root=cache,
        runner=AcquisitionRunner(),
    )
    (bundle.root / "vendor/serde/src/lib.rs").write_text("tampered\n", encoding="utf-8")

    with pytest.raises(ValueError, match="checksum validation"):
        acquire_rust_dependencies(
            snapshot,
            package,
            cache_root=cache,
            runner=AcquisitionRunner(),
        )


def test_compile_failure_remains_diagnostic_and_unverified(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    package = inspect_rust_package_layout(source)
    surface = inspect_rust_public_api(
        source,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    monkeypatch.setattr(rust_dependency_acquisition, "verify_repository_snapshot", lambda _: None)
    monkeypatch.setattr(rust_consumer, "verify_repository_snapshot", lambda _: None)
    bundle = acquire_rust_dependencies(
        snapshot,
        package,
        cache_root=tmp_path / "cache",
        runner=AcquisitionRunner(),
    )
    example = RustConsumerExampleV1(
        code="use widget_core::Root;\nfn main() { let _ = Root::new(); }\n",
        required_symbols=["widget_core::Root", "widget_core::Root.new"],
    )

    proof = prove_rust_consumer(
        snapshot,
        package,
        surface,
        example,
        acquirer=lambda _snapshot, _package: bundle,
        executor=lambda request: _isolated_result(request, return_code=101),
    )

    assert proof.accepted is False
    assert proof.verified_symbols == []
    assert proof.missing_symbols == example.required_symbols
    assert any("private" in diagnostic for diagnostic in proof.diagnostics)


def test_restricted_symbol_is_rejected_before_acquisition_or_execution(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    package = inspect_rust_package_layout(source)
    surface = inspect_rust_public_api(
        source,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    monkeypatch.setattr(rust_consumer, "verify_repository_snapshot", lambda _: None)
    calls = []
    example = RustConsumerExampleV1(
        code=(
            "use widget_core::Root;\n"
            'fn main() { let value = Root::new(); println!("{}", value.hidden); }\n'
        ),
        required_symbols=["widget_core::Root", "widget_core::Root.hidden"],
    )

    with pytest.raises(ValueError, match="non-public"):
        prove_rust_consumer(
            snapshot,
            package,
            surface,
            example,
            acquirer=lambda *_: calls.append("acquired"),
            executor=lambda request: calls.append(request),
        )
    assert calls == []


def test_declared_public_member_must_be_used_before_compiler_proof(tmp_path, monkeypatch):
    source = tmp_path / "source"
    _source(source)
    snapshot = _snapshot(source)
    package = inspect_rust_package_layout(source)
    surface = inspect_rust_public_api(
        source,
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
    )
    monkeypatch.setattr(rust_consumer, "verify_repository_snapshot", lambda _: None)
    calls = []
    example = RustConsumerExampleV1(
        code="use widget_core::Root;\nfn main() { let _value: Option<Root> = None; }\n",
        required_symbols=["widget_core::Root", "widget_core::Root.new"],
    )

    with pytest.raises(ValueError, match="import and use"):
        prove_rust_consumer(
            snapshot,
            package,
            surface,
            example,
            acquirer=lambda *_: calls.append("acquired"),
            executor=lambda request: calls.append(request),
        )
    assert calls == []
