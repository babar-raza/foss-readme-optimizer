"""Run the qualified deterministic repository-knowledge scout from local vendored source."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.aspose_org_vendored_source import load_vendored_aspose_org_source
from readme_agent.facts.example_execution import secret_free_environment
from readme_agent.facts.repository_knowledge_adapter import (
    ADAPTER_SCHEMA_VERSION,
    adapt_scout_output,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1, verify_repository_snapshot

_PLATFORM_ALIASES = {"dotnet": "net", ".net": "net", "csharp": "net", "ts": "typescript"}
_SUPPORTED_PLATFORMS = frozenset(
    {"python", "net", "java", "cpp", "typescript", "javascript", "go", "rust"}
)
_RUNNER = r"""
import json, sys, types, yaml
from pathlib import Path
pipeline, family, platform, repository, output = sys.argv[1:]
package = types.ModuleType("extraction")
package.__package__ = "extraction"
package.__path__ = [str(Path(pipeline) / "extraction")]
sys.modules["extraction"] = package
from extraction.scout import Scout
from extraction.validate_scout_output import validate_scout_output
Scout(family, platform, Path(repository), Path(output)).run()
model = yaml.safe_load((Path(output) / "model.yaml").read_text(encoding="utf-8"))
validation = validate_scout_output(model, Path(repository), platform)
(Path(output) / "scout-validation.json").write_text(
    json.dumps(validation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
if validation["verdict"] == "EXTRACTION_FAILURE":
    print(validation["message"], file=sys.stderr)
    raise SystemExit(3)
"""


class RepositoryKnowledgeGenerationV1(BaseModel):
    """Identity and result of one source-revision-bound deterministic scout."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["generated", "reused", "unavailable"]
    org_repo: str
    source_revision: str
    family: str
    platform: str
    output_root: str | None = None
    generator_source_commit: str | None = None
    generator_sha256: str | None = None
    upstream_generator_sha256: str | None = None
    adapter_schema_version: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    detail: str


def _commit_timestamp(root: Path, revision: str) -> str:
    result = subprocess.run(
        ["git", "show", "-s", "--format=%cI", revision],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
        env=secret_free_environment(),
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise ValueError("cannot obtain the immutable source commit timestamp")
    return result.stdout.strip()


def current_repository_knowledge_generator_sha256() -> str:
    """Hash upstream extractor bytes together with the local compatibility adapter."""

    source = load_vendored_aspose_org_source()
    adapter_path = Path(__file__).with_name("repository_knowledge_adapter.py")
    payload = {
        "upstream_generator_sha256": source.aggregate_sha256,
        "adapter_schema_version": ADAPTER_SCHEMA_VERSION,
        "adapter_sha256": hashlib.sha256(adapter_path.read_bytes()).hexdigest(),
        "wrapper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def repository_knowledge_data_root(snapshot: RepositorySnapshotV1) -> Path:
    """Return the revision- and generator-addressed root consumed by knowledge loaders."""

    from readme_agent import paths

    repository_alias = hashlib.sha256(snapshot.org_repo.encode()).hexdigest()[:16]
    return (
        paths.runs_dir()
        / "knowledge"
        / "r"
        / repository_alias
        / "s"
        / snapshot.source_revision[:20]
        / "g"
        / current_repository_knowledge_generator_sha256()[:20]
    )


def _artifact_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def generate_repository_knowledge(
    snapshot: RepositorySnapshotV1,
    *,
    family: str,
    platform: str,
    output_root: Path,
) -> RepositoryKnowledgeGenerationV1:
    """Generate deterministic raw evidence without granting it factual authority."""

    verify_repository_snapshot(snapshot)
    normalized_platform = _PLATFORM_ALIASES.get(platform.casefold(), platform.casefold())
    if normalized_platform not in _SUPPORTED_PLATFORMS:
        return RepositoryKnowledgeGenerationV1(
            status="unavailable",
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            family=family,
            platform=normalized_platform,
            detail=f"unsupported deterministic scout platform: {normalized_platform}",
        )
    try:
        source = load_vendored_aspose_org_source()
        generator_sha256 = current_repository_knowledge_generator_sha256()
        extracted_at = _commit_timestamp(snapshot.root_path, snapshot.source_revision)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return RepositoryKnowledgeGenerationV1(
            status="unavailable",
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            family=family,
            platform=normalized_platform,
            detail=f"qualified generator unavailable: {exc}",
        )
    destination = output_root.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="knowledge-", dir=destination.parent))
    try:
        environment = secret_free_environment()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                "-c",
                _RUNNER,
                str(source.pipeline),
                family.casefold(),
                normalized_platform,
                str(snapshot.root_path),
                str(staging),
            ],
            cwd=source.root,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
            env=environment,
        )
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "deterministic scout failed"
            return RepositoryKnowledgeGenerationV1(
                status="unavailable",
                org_repo=snapshot.org_repo,
                source_revision=snapshot.source_revision,
                family=family,
                platform=normalized_platform,
                generator_source_commit=source.source_commit,
                generator_sha256=generator_sha256,
                upstream_generator_sha256=source.aggregate_sha256,
                adapter_schema_version=ADAPTER_SCHEMA_VERSION,
                detail=detail[:2000],
            )
        adapt_scout_output(
            staging,
            extracted_at=extracted_at,
            generator_sha256=generator_sha256,
        )
        hashes = _artifact_hashes(staging)
        if not hashes:
            raise ValueError("deterministic scout produced no artifacts")
        status: Literal["generated", "reused"] = "generated"
        if destination.exists():
            if _artifact_hashes(destination) != hashes:
                raise ValueError(
                    "existing revision-addressed knowledge differs from regenerated bytes"
                )
            status = "reused"
        else:
            staging.replace(destination)
        verify_repository_snapshot(snapshot)
        return RepositoryKnowledgeGenerationV1(
            status=status,
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            family=family,
            platform=normalized_platform,
            output_root=str(destination),
            generator_source_commit=source.source_commit,
            generator_sha256=generator_sha256,
            upstream_generator_sha256=source.aggregate_sha256,
            adapter_schema_version=ADAPTER_SCHEMA_VERSION,
            artifacts=hashes,
            detail=f"{status} {len(hashes)} source-derived artifacts",
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return RepositoryKnowledgeGenerationV1(
            status="unavailable",
            org_repo=snapshot.org_repo,
            source_revision=snapshot.source_revision,
            family=family,
            platform=normalized_platform,
            generator_source_commit=source.source_commit,
            generator_sha256=generator_sha256,
            upstream_generator_sha256=source.aggregate_sha256,
            adapter_schema_version=ADAPTER_SCHEMA_VERSION,
            detail=str(exc),
        )
    finally:
        if staging.exists():
            shutil.rmtree(staging)
