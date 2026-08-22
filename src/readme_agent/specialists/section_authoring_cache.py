"""Persist accepted section-cluster authoring outcomes for zero-call reuse.

Mirrors `trusted_fidelity_cache.py`'s exact shape: one JSON file per section under a
revision-scoped directory, a cache key hashing every input that could change the output, and a
strict `load` that returns `None` on any mismatch (fail-open to recompute, never fail-closed on
a stale hit). A successful, unchanged section reuses with zero Qwen calls; a failed section
retries only that section -- callers key their per-section cache lookup on `target_section_id`
alone, never on the whole README.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent import paths
from readme_agent.evidence.writer import write_redacted_json
from readme_agent.specialists.section_authoring_contracts import (
    SECTION_AUTHORING_CONTRACT_VERSION,
    SectionAuthoringOutcomeV1,
)


# Bump whenever the authoring contract, tool schema shape, or acceptance validators change --
# invalidates every cached entry at once, the same convention as
# trusted_fidelity_cache.py::FIDELITY_BATCH_CONTRACT_VERSION.
class SectionAuthoringCacheV1(BaseModel):
    """One section's accepted outcome bound to every input that affects its content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    cache_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    org_repo: str = Field(min_length=3)
    source_revision: str = Field(min_length=1)
    target_section_id: str = Field(min_length=1)
    outcome: SectionAuthoringOutcomeV1

    @model_validator(mode="after")
    def _output_hash_matches(self) -> SectionAuthoringCacheV1:
        if _canonical_hash(self.outcome.model_dump(mode="json")) != self.output_sha256:
            raise ValueError("section authoring cache output checksum does not match")
        if self.outcome.target_section_id != self.target_section_id:
            raise ValueError("section authoring cache section identity does not match outcome")
        return self


def section_authoring_cache_key(
    *,
    org_repo: str,
    source_revision: str,
    packet_hash: str,
    target_section_id: str,
    prompt_sha256: str,
    schema_sha256: str,
    model: str,
    sampling_parameters: dict,
    protected_literal_hash: str,
    authoring_contract_version: str | None = None,
) -> str:
    """Bind source revision, accepted-fact packet hash, target section, prompt/schema hash,
    requested model, sampling parameters, protected-literal hash, and the authoring
    implementation/version hash into one cache identity."""

    return _canonical_hash(
        {
            "authoring_contract_version": (
                authoring_contract_version or SECTION_AUTHORING_CONTRACT_VERSION
            ),
            "org_repo": org_repo,
            "source_revision": source_revision,
            "packet_hash": packet_hash,
            "target_section_id": target_section_id,
            "prompt_sha256": prompt_sha256,
            "schema_sha256": schema_sha256,
            "model": model,
            "sampling_parameters": sampling_parameters,
            "protected_literal_hash": protected_literal_hash,
        }
    )


def default_section_authoring_cache_dir(org: str, repo: str, source_revision: str) -> Path:
    """Return the revision-scoped section-authoring cache root."""

    return (
        paths.readme_poc_repository_dir(org, repo, source_revision)
        / "assurance"
        / "section_authoring"
        / "cache"
    )


def load_section_authoring_cache(
    cache_dir: Path,
    target_section_id: str,
    cache_key: str,
) -> SectionAuthoringCacheV1 | None:
    """Load only an exact, structurally valid checkpoint for this exact section and key."""

    path = cache_dir / f"{target_section_id}.json"
    if not path.is_file():
        return None
    try:
        cached = SectionAuthoringCacheV1.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    if cached.cache_key != cache_key or cached.target_section_id != target_section_id:
        return None
    return cached


def write_section_authoring_cache(
    cache_dir: Path,
    *,
    cache_key: str,
    org_repo: str,
    source_revision: str,
    outcome: SectionAuthoringOutcomeV1,
) -> SectionAuthoringCacheV1:
    """Persist an already-accepted outcome through the evidence redactor."""

    cache = SectionAuthoringCacheV1(
        cache_key=cache_key,
        output_sha256=_canonical_hash(outcome.model_dump(mode="json")),
        org_repo=org_repo,
        source_revision=source_revision,
        target_section_id=outcome.target_section_id,
        outcome=outcome,
    )
    write_redacted_json(cache_dir / f"{outcome.target_section_id}.json", cache)
    return cache


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
