"""Acquire and verify the pinned TypeScript compiler toolchain as inert archives."""

from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Literal

import requests
from pydantic import BaseModel, ConfigDict

NODE_22_IMAGE = "node@sha256:6c74791e557ce11fc957704f6d4fe134a7bc8d6f5ca4403205b2966bd488f6b3"


class TypeScriptToolchainArtifactV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    name: str
    version: str
    filename: str
    url: str
    sha256: str


class TypeScriptToolchainLockV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    compiler_version: str
    immutable_image: str
    artifacts: list[TypeScriptToolchainArtifactV1]


TOOLCHAIN_LOCK = TypeScriptToolchainLockV1(
    compiler_version="5.8.3",
    immutable_image=NODE_22_IMAGE,
    artifacts=[
        TypeScriptToolchainArtifactV1(
            name="typescript",
            version="5.8.3",
            filename="typescript-5.8.3.tgz",
            url="https://registry.npmjs.org/typescript/-/typescript-5.8.3.tgz",
            sha256="72e75dbeb92c2e6eb9a34cb59d74fab5c2ee6f32a0324a89405f6165d5a08374",
        ),
        TypeScriptToolchainArtifactV1(
            name="@types/node",
            version="22.15.17",
            filename="types-node-22.15.17.tgz",
            url="https://registry.npmjs.org/@types/node/-/node-22.15.17.tgz",
            sha256="d4f15ddec10551421843fb307521d074614f70d00759e185488aec49e0b6e8f0",
        ),
        TypeScriptToolchainArtifactV1(
            name="undici-types",
            version="6.21.0",
            filename="undici-types-6.21.0.tgz",
            url="https://registry.npmjs.org/undici-types/-/undici-types-6.21.0.tgz",
            sha256="cfa1a9a5e18988850e548f4f6b629c58da32dc32bebb116e58ea301e516fd16d",
        ),
    ],
)


def _default_cache_root() -> Path:
    configured = os.getenv("README_AGENT_TYPESCRIPT_TOOLCHAIN_CACHE")
    if configured:
        return Path(configured)
    repository_root = Path(__file__).resolve().parents[3]
    return repository_root / "runs" / "tooling" / "typescript-5.8.3-node-types-22.15.17"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_typescript_toolchain(cache_root: Path | None = None) -> dict[str, Path]:
    """Download only missing inert archives, then require exact recorded hashes."""

    root = cache_root or _default_cache_root()
    root.mkdir(parents=True, exist_ok=True)
    resolved: dict[str, Path] = {}
    for artifact in TOOLCHAIN_LOCK.artifacts:
        path = root / artifact.filename
        if not path.is_file():
            pending_path: Path | None = None
            try:
                with requests.get(artifact.url, timeout=120, stream=True) as response:
                    response.raise_for_status()
                    with tempfile.NamedTemporaryFile(dir=root, delete=False) as pending:
                        pending_path = Path(pending.name)
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                pending.write(chunk)
            except Exception:
                if pending_path is not None:
                    pending_path.unlink(missing_ok=True)
                raise
            assert pending_path is not None
            if _sha256(pending_path) != artifact.sha256:
                pending_path.unlink(missing_ok=True)
                raise ValueError(
                    f"TypeScript toolchain download hash mismatch for {artifact.filename}"
                )
            pending_path.replace(path)
        actual = _sha256(path)
        if actual != artifact.sha256:
            raise ValueError(
                f"TypeScript toolchain hash mismatch for {artifact.filename}: {actual}"
            )
        resolved[artifact.name] = path
    return resolved
