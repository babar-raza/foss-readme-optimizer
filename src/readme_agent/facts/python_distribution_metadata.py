"""Generate Python distribution metadata in the hardened isolated executor."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections.abc import Callable
from pathlib import Path

from readme_agent.facts.compiled_consumer import copy_snapshot
from readme_agent.facts.isolated_execution import execute_isolated
from readme_agent.facts.isolated_execution_inputs import (
    IsolatedInputBundle,
    build_isolated_input_bundle,
)
from readme_agent.facts.isolated_execution_schema import (
    IsolatedExecutionPolicyV1,
    IsolatedExecutionRequestV1,
    IsolatedExecutionResultV1,
)
from readme_agent.facts.python_distribution_metadata_schema import (
    PythonDistributionMetadataPayloadV1,
    PythonDistributionMetadataProofV1,
)
from readme_agent.facts.python_toolchain import PYTHON_311_IMAGE
from readme_agent.facts.root_role_schema import (
    PackageRootRoleV1,
    filesystem_repository_path,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

IsolatedExecutor = Callable[[IsolatedExecutionRequestV1], IsolatedExecutionResultV1]

_DRIVER = r"""from email import policy
from email.parser import BytesParser
import hashlib
import json
from pathlib import Path
import subprocess
import sys

PREFIX = "Programming Language :: Python :: "

def finish(payload, code):
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    raise SystemExit(code)

package_root = Path(sys.argv[1]).resolve()
metadata_root = Path("/workspace/__metadata__")
metadata_root.mkdir(parents=True, exist_ok=False)
child = subprocess.run(
    [sys.executable, "setup.py", "egg_info", "--egg-base", str(metadata_root)],
    cwd=package_root,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    check=False,
)
if child.returncode != 0:
    finish({"schema_version": 1, "status": "error", "reason": "egg_info_failed"}, 20)
pkg_infos = sorted(metadata_root.rglob("PKG-INFO"))
if not pkg_infos:
    finish(
        {
            "schema_version": 1,
            "status": "error",
            "reason": "pkg_info_missing",
        },
        21,
    )
if len(pkg_infos) > 1:
    finish(
        {
            "schema_version": 1,
            "status": "error",
            "reason": "multiple_pkg_info_files",
            "pkg_info_count": len(pkg_infos),
        },
        22,
    )
pkg_info = pkg_infos[0]
payload = pkg_info.read_bytes()
message = BytesParser(policy=policy.default).parsebytes(payload)
versions = set()
for classifier in message.get_all("Classifier", []):
    if not classifier.startswith(PREFIX):
        continue
    version = classifier.removeprefix(PREFIX)
    parts = version.split(".")
    if len(parts) == 2 and all(part.isdigit() for part in parts):
        versions.add((int(parts[0]), int(parts[1])))
finish(
    {
        "schema_version": 1,
        "status": "ok",
        "pkg_info_path": pkg_info.relative_to(metadata_root).as_posix(),
        "pkg_info_sha256": hashlib.sha256(payload).hexdigest(),
        "requires_python": message.get("Requires-Python"),
        "python_classifier_versions": [
            f"{major}.{minor}" for major, minor in sorted(versions)
        ],
    },
    0,
)
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _proof(
    snapshot: RepositorySnapshotV1,
    selected_root: PackageRootRoleV1,
    request: IsolatedExecutionRequestV1,
    expected_inputs: IsolatedInputBundle,
    execution: IsolatedExecutionResultV1,
    manifest_sha256: str,
) -> PythonDistributionMetadataProofV1:
    metadata: PythonDistributionMetadataPayloadV1 | None = None
    failure_reason: str | None = None
    exact_request_binding = (
        execution.org_repo == request.org_repo
        and execution.source_revision == request.source_revision
        and execution.argv == request.argv
        and execution.environment_names == sorted(request.environment)
        and execution.policy == request.policy
        and execution.image.requested_reference == request.policy.immutable_image
        and execution.image.repo_digest == request.policy.immutable_image
        and execution.input_sha256 == expected_inputs.input_sha256
        and execution.input_file_count == expected_inputs.input_file_count
        and execution.policy_sha256 == expected_inputs.policy_sha256
    )
    exact_execution = (
        exact_request_binding
        and execution.truth_eligible
        and execution.return_code == 0
        and not execution.timed_out
        and not execution.oom_killed
        and execution.cleanup.complete
        and execution.org_repo == snapshot.org_repo
        and execution.source_revision == snapshot.source_revision
    )
    if not exact_request_binding:
        failure_reason = "isolated_execution_request_binding_mismatch"
    elif not exact_execution:
        failure_reason = "isolated_execution_not_exact_success"
    else:
        try:
            metadata = PythonDistributionMetadataPayloadV1.model_validate(
                json.loads(execution.stdout)
            )
        except (json.JSONDecodeError, ValueError):
            failure_reason = "driver_output_invalid"
    truth_eligible = exact_execution and metadata is not None
    if truth_eligible and metadata is not None:
        if metadata.requires_python is None and not metadata.python_classifier_versions:
            truth_eligible = False
            failure_reason = "generated_metadata_has_no_compatibility"
    return PythonDistributionMetadataProofV1(
        org_repo=snapshot.org_repo,
        source_revision=snapshot.source_revision,
        snapshot_inventory_sha256=snapshot.inventory_sha256,
        package_root_path=selected_root.path,
        manifest_path=selected_root.manifest_path,
        manifest_sha256=manifest_sha256,
        driver_sha256=hashlib.sha256(_DRIVER.encode("utf-8")).hexdigest(),
        execution=execution,
        metadata=metadata,
        truth_eligible=truth_eligible,
        failure_reason=failure_reason,
    )


def verify_python_distribution_metadata(
    snapshot: RepositorySnapshotV1,
    selected_root: PackageRootRoleV1,
    *,
    executor: IsolatedExecutor = execute_isolated,
    immutable_image: str = PYTHON_311_IMAGE,
) -> PythonDistributionMetadataProofV1:
    """Generate one setup.py PKG-INFO proof without executing on the operator host."""

    verify_repository_snapshot(snapshot)
    if selected_root.ecosystem != "python" or Path(selected_root.manifest_path).name != "setup.py":
        raise ValueError("isolated distribution metadata requires a selected Python setup.py root")
    with tempfile.TemporaryDirectory(prefix="readme-agent-python-metadata-") as temp:
        workspace = Path(temp)
        repository = workspace / "repository"
        copy_snapshot(snapshot, repository)
        exported_manifest = repository / filesystem_repository_path(selected_root.manifest_path)
        if not exported_manifest.is_file():
            raise ValueError("exported selected setup.py manifest is unavailable")
        manifest_sha256 = _sha256(exported_manifest)
        driver = workspace / "__readme_agent_metadata_driver.py"
        driver.write_text(_DRIVER, encoding="utf-8", newline="\n")
        package_root = Path("repository") / filesystem_repository_path(selected_root.path)
        request = IsolatedExecutionRequestV1(
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            source_root=workspace,
            argv=[
                "python",
                "/workspace/__readme_agent_metadata_driver.py",
                package_root.as_posix(),
            ],
            environment={"HOME": "/tmp", "TMPDIR": "/tmp"},
            policy=IsolatedExecutionPolicyV1(
                immutable_image=immutable_image,
                timeout_seconds=300,
            ),
        )
        expected_inputs = build_isolated_input_bundle(request)
        execution = executor(request)
    verify_repository_snapshot(snapshot)
    return _proof(
        snapshot,
        selected_root,
        request,
        expected_inputs,
        execution,
        manifest_sha256,
    )
