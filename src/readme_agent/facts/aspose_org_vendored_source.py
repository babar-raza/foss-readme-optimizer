"""Validate and expose the locally vendored deterministic knowledge extractor."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class VendoredAsposeOrgSourceV1(BaseModel):
    """Immutable identity of the qualified local extractor source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    root: Path
    pipeline: Path
    source_commit: str
    aggregate_sha256: str
    files: dict[str, str]


def load_vendored_aspose_org_source() -> VendoredAsposeOrgSourceV1:
    """Fail closed unless every vendored byte matches the committed provenance manifest."""

    repository_root = Path(__file__).resolve().parents[3]
    manifest_path = repository_root / "data/imported/aspose_org_knowledge_generator_manifest.json"
    vendored_root = repository_root / "src/readme_agent/vendored_asposeorg"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0":
        raise ValueError("unsupported Aspose.org knowledge-generator manifest")
    raw_files = payload.get("files")
    if not isinstance(raw_files, dict) or not raw_files:
        raise ValueError("Aspose.org knowledge-generator manifest has no files")
    files: dict[str, str] = {}
    canonical: dict[str, dict[str, object]] = {}
    for source_path, raw in sorted(raw_files.items()):
        if not isinstance(source_path, str) or not isinstance(raw, dict):
            raise ValueError("invalid Aspose.org generator file record")
        relative = raw.get("destination")
        expected = raw.get("sha256")
        expected_blob = raw.get("git_blob")
        expected_bytes = raw.get("bytes")
        if not all(isinstance(value, str) for value in (relative, expected, expected_blob)):
            raise ValueError(f"invalid Aspose.org generator identity for {source_path}")
        path = vendored_root / "scripts/pipeline/extraction" / str(relative)
        content = path.read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        if actual != expected or len(content) != expected_bytes:
            raise ValueError(f"vendored Aspose.org generator byte mismatch: {source_path}")
        files[path.relative_to(vendored_root).as_posix()] = actual
        canonical[source_path] = {
            "blob": expected_blob,
            "sha256": expected,
            "bytes": expected_bytes,
        }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    aggregate = hashlib.sha256(encoded).hexdigest()
    if aggregate != payload.get("aggregate_sha256"):
        raise ValueError("vendored Aspose.org generator aggregate mismatch")
    commit = payload.get("source_commit")
    if not isinstance(commit, str) or len(commit) != 40:
        raise ValueError("invalid Aspose.org generator source commit")
    return VendoredAsposeOrgSourceV1(
        root=vendored_root,
        pipeline=vendored_root / "scripts/pipeline",
        source_commit=commit,
        aggregate_sha256=aggregate,
        files=files,
    )
