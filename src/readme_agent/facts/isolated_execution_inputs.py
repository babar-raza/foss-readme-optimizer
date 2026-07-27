"""Build checksum-addressed input provenance and tar streams for isolated execution."""

from __future__ import annotations

import hashlib
import io
import json
import os
import tarfile
from dataclasses import dataclass
from pathlib import Path

from readme_agent.errors import ReadmeAgentError
from readme_agent.facts.isolated_execution_schema import IsolatedExecutionRequestV1


class IsolatedExecutionInputError(ReadmeAgentError):
    """The immutable input tree cannot be represented safely."""

    exit_code = 3


@dataclass(frozen=True)
class IsolatedInputBundle:
    """Deterministic inventory plus the transport archive consumed by Docker."""

    input_sha256: str
    input_file_count: int
    policy_sha256: str
    source_archive: bytes


def _inventory(root: Path) -> tuple[str, int]:
    if not root.is_dir():
        raise IsolatedExecutionInputError(f"isolated source root is not a directory: {root}")
    digest = hashlib.sha256()
    count = 0
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        if path.is_symlink():
            kind = b"symlink"
            payload = os.readlink(path).encode("utf-8")
        elif path.is_dir():
            kind = b"directory"
            payload = b""
        elif path.is_file():
            kind = b"file"
            payload = path.read_bytes()
        else:
            raise IsolatedExecutionInputError(f"unsupported input filesystem entry: {relative}")
        digest.update(kind)
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
        count += 1
    return digest.hexdigest(), count


def build_isolated_input_bundle(request: IsolatedExecutionRequestV1) -> IsolatedInputBundle:
    """Hash the source/policy and create the path-free `docker cp -` payload."""

    input_sha256, input_file_count = _inventory(request.source_root)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", dereference=False) as archive:
        for path in sorted(
            request.source_root.rglob("*"),
            key=lambda item: item.relative_to(request.source_root).as_posix(),
        ):
            archive.add(
                path,
                arcname=path.relative_to(request.source_root).as_posix(),
                recursive=False,
            )
    policy_payload = json.dumps(
        request.policy.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return IsolatedInputBundle(
        input_sha256=input_sha256,
        input_file_count=input_file_count,
        policy_sha256=hashlib.sha256(policy_payload.encode("utf-8")).hexdigest(),
        source_archive=buffer.getvalue(),
    )
