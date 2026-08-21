"""Persist and validate source-bound repository knowledge generation receipts."""

from __future__ import annotations

import hashlib
from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import refresh_sha256sums, write_redacted_json
from readme_agent.facts.repository_knowledge_generator import (
    RepositoryKnowledgeGenerationV1,
    current_repository_knowledge_generator_sha256,
)
from readme_agent.repository_snapshot import RepositorySnapshotV1


def write_repository_knowledge_generation(
    snapshot: RepositorySnapshotV1,
    generation: RepositoryKnowledgeGenerationV1,
) -> Path:
    """Write one generation receipt beside the revision-addressed fact graph."""

    if generation.org_repo != snapshot.org_repo:
        raise ValueError("knowledge generation belongs to another repository")
    if generation.source_revision != snapshot.source_revision:
        raise ValueError("knowledge generation belongs to another source revision")
    org, repo = snapshot.org_repo.split("/", maxsplit=1)
    bundle_dir = paths.readme_poc_repository_dir(org, repo, snapshot.source_revision)
    receipt_path = bundle_dir / "facts" / "knowledge-generation.json"
    write_redacted_json(receipt_path, generation)
    refresh_sha256sums(bundle_dir)
    return receipt_path


def load_current_repository_knowledge_generation(
    bundle_dir: Path,
    *,
    org_repo: str,
    source_revision: str,
) -> RepositoryKnowledgeGenerationV1 | None:
    """Fail cache reuse when generation identity or artifact bytes are stale."""

    receipt_path = bundle_dir / "facts" / "knowledge-generation.json"
    if not receipt_path.is_file():
        return None
    try:
        generation = RepositoryKnowledgeGenerationV1.model_validate_json(
            receipt_path.read_text(encoding="utf-8")
        )
        if generation.status not in {"generated", "reused"}:
            return None
        if generation.org_repo != org_repo or generation.source_revision != source_revision:
            return None
        if generation.generator_sha256 != current_repository_knowledge_generator_sha256():
            return None
        if generation.output_root is None:
            return None
        output_root = Path(generation.output_root)
        if not output_root.is_dir():
            return None
        actual = {
            path.relative_to(output_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(output_root.rglob("*"))
            if path.is_file()
        }
        if actual != generation.artifacts:
            return None
    except (OSError, ValueError):
        return None
    return generation
