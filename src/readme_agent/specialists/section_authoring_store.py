"""Persist and validate one revision-addressed section-authoring document."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent import paths
from readme_agent.evidence.writer import write_redacted_json
from readme_agent.specialists.section_authoring_contracts import (
    SECTION_AUTHORING_CONTRACT_VERSION,
    SectionAuthoringDocumentRecordV1,
    SectionAuthoringDocumentV1,
)


def section_authoring_document_path(org_repo: str, source_revision: str) -> Path:
    org, repo = org_repo.split("/", maxsplit=1)
    return (
        paths.readme_poc_repository_dir(org, repo, source_revision)
        / "assurance"
        / "section_authoring"
        / "document.json"
    )


def write_section_authoring_document(document: SectionAuthoringDocumentV1) -> Path:
    path = section_authoring_document_path(document.org_repo, document.source_revision)
    record = SectionAuthoringDocumentRecordV1(
        document_sha256=document.canonical_hash(),
        document=document,
    )
    write_redacted_json(path, record)
    return path


def load_section_authoring_document(
    org_repo: str,
    source_revision: str,
    *,
    facts_hash: str | None = None,
    source_sha256: str | None = None,
) -> SectionAuthoringDocumentV1 | None:
    path = section_authoring_document_path(org_repo, source_revision)
    if not path.is_file():
        return None
    try:
        record = SectionAuthoringDocumentRecordV1.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError):
        return None
    document = record.document
    if document.org_repo != org_repo or document.source_revision != source_revision:
        return None
    if facts_hash is not None and document.facts_hash != facts_hash:
        return None
    if source_sha256 is not None and document.source_sha256 != source_sha256:
        return None
    if document.authoring_contract_version != SECTION_AUTHORING_CONTRACT_VERSION:
        return None
    return document


def canonical_specs_hash(specs: object) -> str:
    payload = json.dumps(specs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


__all__ = [
    "canonical_specs_hash",
    "load_section_authoring_document",
    "section_authoring_document_path",
    "write_section_authoring_document",
]
