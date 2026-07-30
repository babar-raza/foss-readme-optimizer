"""Persist content-addressed trusted composition batches for retry idempotency."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent import paths
from readme_agent.evidence.writer import write_redacted_json
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.readme.trusted_composition_batching import TrustedCompositionBatch
from readme_agent.readme.trusted_composition_models import (
    TrustedCompositionEnvelopeV1,
    TrustedReadmeSectionDraftV1,
    TrustedReadmeSectionToolDraftV1,
)

TRUSTED_BATCH_VALIDATION_CONTRACT_VERSION = "trusted-batch-validation-v2-no-introduced-navigation"
TRUSTED_GLOBAL_REPAIR_PROMOTION_VERSION = "trusted-global-repair-promotion-v1"


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class TrustedCompositionBatchCacheV1(BaseModel):
    """One validated authoring batch bound to immutable inputs and output bytes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    cache_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    org_repo: str = Field(min_length=3)
    source_revision: str = Field(min_length=7)
    batch_id: str = Field(pattern=r"^batch-[0-9]{4}$")
    model: str = Field(min_length=1)
    tool_draft: TrustedReadmeSectionToolDraftV1
    bound_draft: TrustedReadmeSectionDraftV1

    @model_validator(mode="after")
    def _output_hash_matches(self) -> TrustedCompositionBatchCacheV1:
        payload = {
            "tool_draft": self.tool_draft.model_dump(mode="json"),
            "bound_draft": self.bound_draft.model_dump(mode="json"),
        }
        if _canonical_hash(payload) != self.output_sha256:
            raise ValueError("trusted composition batch cache output checksum does not match")
        if self.bound_draft.batch_id != self.batch_id:
            raise ValueError("trusted composition batch cache contains another batch")
        return self


def trusted_batch_cache_key(
    graph: TrustedReadmeFactGraphV1,
    batch: TrustedCompositionBatch,
    envelope: TrustedCompositionEnvelopeV1,
    *,
    prompt_sha256: str,
    tool_schema_sha256: str,
    model: str,
) -> str:
    """Hash every input whose change must invalidate a successful batch."""

    return _canonical_hash(
        {
            "schema_version": 1,
            "validation_contract_version": TRUSTED_BATCH_VALIDATION_CONTRACT_VERSION,
            "global_repair_promotion_version": (
                TRUSTED_GLOBAL_REPAIR_PROMOTION_VERSION if batch.configured_standards else None
            ),
            "org_repo": graph.org_repo,
            "source_revision": graph.source_revision,
            "fact_graph_sha256": graph.canonical_hash(),
            "batch": {
                "batch_id": batch.batch_id,
                "source_items": [item.model_dump(mode="json") for item in batch.source_items],
                "configured_standards": [
                    standard.model_dump(mode="json") for standard in batch.configured_standards
                ],
                "global_structures_allowed": batch.global_structures_allowed,
            },
            "envelope": envelope.model_dump(mode="json"),
            "prompt_sha256": prompt_sha256,
            "tool_schema_sha256": tool_schema_sha256,
            "model": model,
        }
    )


def default_trusted_batch_cache_dir(graph: TrustedReadmeFactGraphV1) -> Path:
    """Return the assurance-isolated revision-addressed batch cache root."""

    org, repo = graph.org_repo.split("/", maxsplit=1)
    return (
        paths.readme_poc_repository_dir(org, repo, graph.source_revision)
        / "assurance"
        / "trusted_inherited"
        / "planning"
        / "batch-cache"
    )


def load_trusted_batch_cache(
    cache_dir: Path,
    batch_id: str,
    cache_key: str,
) -> TrustedCompositionBatchCacheV1 | None:
    """Load one exact cache hit; malformed or mismatched artifacts fail closed."""

    path = cache_dir / f"{batch_id}.json"
    if not path.is_file():
        return None
    try:
        cached = TrustedCompositionBatchCacheV1.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError):
        return None
    if cached.cache_key != cache_key or cached.batch_id != batch_id:
        return None
    return cached


def write_trusted_batch_cache(
    cache_dir: Path,
    *,
    cache_key: str,
    org_repo: str,
    source_revision: str,
    model: str,
    tool_draft: TrustedReadmeSectionToolDraftV1,
    bound_draft: TrustedReadmeSectionDraftV1,
) -> TrustedCompositionBatchCacheV1:
    """Atomically persist one already-validated batch through evidence redaction."""

    output_payload = {
        "tool_draft": tool_draft.model_dump(mode="json"),
        "bound_draft": bound_draft.model_dump(mode="json"),
    }
    cache = TrustedCompositionBatchCacheV1(
        cache_key=cache_key,
        output_sha256=_canonical_hash(output_payload),
        org_repo=org_repo,
        source_revision=source_revision,
        batch_id=bound_draft.batch_id,
        model=model,
        tool_draft=tool_draft,
        bound_draft=bound_draft,
    )
    write_redacted_json(cache_dir / f"{bound_draft.batch_id}.json", cache)
    return cache
