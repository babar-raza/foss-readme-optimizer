"""Git LFS build inputs are acquired in a hardened container and verified."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from readme_agent.facts.dotnet_lfs_acquisition import acquire_repository_lfs_dependencies

_IMAGE = "mcr.microsoft.com/dotnet/sdk@sha256:" + "a" * 64


class LfsRunner:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.commands: list[list[str]] = []

    def run(
        self,
        argv: list[str],
        *,
        timeout_seconds: float,
        input_bytes: bytes | None = None,
    ) -> subprocess.CompletedProcess[str]:
        self.commands.append(argv)
        if argv[0] == "run":
            mounted = argv[argv.index("--volume") + 1]
            workspace = Path(mounted.removesuffix(":/workspace"))
            (workspace / "lfs" / "0").write_bytes(self.payload)
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:2] == ["rm", "--force"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        if argv[:2] == ["container", "inspect"]:
            return subprocess.CompletedProcess(argv, 1, "", "No such container")
        if argv[:2] == ["ps", "-aq"]:
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(f"unexpected command: {argv}")


def test_repository_lfs_dependency_is_hardened_hydrated_and_identity_bound(tmp_path):
    repository = tmp_path / "repository"
    dependency = repository / "packages" / "Legacy.dll"
    dependency.parent.mkdir(parents=True)
    payload = b"immutable fixture assembly"
    sha256 = hashlib.sha256(payload).hexdigest()
    dependency.write_text(
        f"version https://git-lfs.github.com/spec/v1\noid sha256:{sha256}\nsize {len(payload)}\n",
        encoding="ascii",
    )
    runner = LfsRunner(payload)

    artifacts = acquire_repository_lfs_dependencies(
        repository,
        org_repo="example/Aspose.Widget-FOSS-for-.NET",
        source_revision="b" * 40,
        runner=runner,
        immutable_image=_IMAGE,
        retry_sleep=lambda _seconds: None,
    )

    assert dependency.read_bytes() == payload
    assert [artifact.relative_path for artifact in artifacts] == ["packages/Legacy.dll"]
    assert artifacts[0].sha256 == sha256
    docker_argv = next(argv for argv in runner.commands if argv[0] == "run")
    joined = "\0".join(docker_argv)
    for expected in (
        ["--network", "bridge"],
        ["--read-only"],
        ["--cap-drop", "ALL"],
        ["--security-opt", "no-new-privileges:true"],
        ["--user", "65534:65534"],
    ):
        assert "\0".join(expected) in joined
    assert "media.githubusercontent.com/media/example/Aspose.Widget-FOSS-for-.NET/" in joined
