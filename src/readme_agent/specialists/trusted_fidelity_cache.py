"""Persist validated trusted fidelity sub-batches for retry idempotency."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent import paths
from readme_agent.evidence.writer import write_redacted_json
from readme_agent.facts.trusted_readme_schema import TrustedReadmeFactGraphV1
from readme_agent.specialists.trusted_transform_review_models import (
    TrustedFidelityReviewResultV1,
)

FIDELITY_BATCH_CONTRACT_VERSION = "trusted-fidelity-batch-v10-canonical-role-scope"


class TrustedFidelityBatchCacheV1(BaseModel):
    """One grounded sub-batch bound to every input that affects its verdict."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    cache_key: str = Field(pattern=r"^[0-9a-f]{64}$")
    output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    org_repo: str = Field(min_length=3)
    source_revision: str = Field(min_length=7)
    review_batch_id: str = Field(pattern=r"^batch-[0-9]{4}\.part-[0-9]{4}$")
    result: TrustedFidelityReviewResultV1
    retry_history: tuple[dict, ...]

    @model_validator(mode="after")
    def _output_hash_matches(self) -> TrustedFidelityBatchCacheV1:
        if _canonical_hash(_output_payload(self.result, self.retry_history)) != self.output_sha256:
            raise ValueError("trusted fidelity cache output checksum does not match")
        return self


def trusted_fidelity_cache_key(
    graph: TrustedReadmeFactGraphV1,
    *,
    plan_hash: str,
    candidate_sha256: str,
    review_batch_id: str,
    fact_ids: tuple[str, ...],
    fact_context: dict,
    plan_context: dict,
    prompt_sha256: str,
    model: str,
) -> str:
    """Hash source, candidate, bounded context, contract, prompt, and route."""

    return _canonical_hash(
        {
            "contract_version": FIDELITY_BATCH_CONTRACT_VERSION,
            "org_repo": graph.org_repo,
            "source_revision": graph.source_revision,
            "fact_graph_sha256": graph.canonical_hash(),
            "plan_hash": plan_hash,
            "candidate_sha256": candidate_sha256,
            "review_batch_id": review_batch_id,
            "fact_ids": fact_ids,
            "fact_context": fact_context,
            "plan_context": plan_context,
            "prompt_sha256": prompt_sha256,
            "model": model,
        }
    )


def default_trusted_fidelity_cache_dir(graph: TrustedReadmeFactGraphV1) -> Path:
    """Return the revision- and assurance-bound fidelity checkpoint root."""

    org, repo = graph.org_repo.split("/", maxsplit=1)
    return (
        paths.readme_poc_repository_dir(org, repo, graph.source_revision)
        / "assurance"
        / "trusted_inherited"
        / "review"
        / "fidelity-batch-cache"
    )


def load_trusted_fidelity_cache(
    cache_dir: Path,
    review_batch_id: str,
    cache_key: str,
) -> TrustedFidelityBatchCacheV1 | None:
    """Load only an exact, structurally valid checkpoint."""

    path = cache_dir / f"{review_batch_id}.json"
    if not path.is_file():
        return None
    try:
        cached = TrustedFidelityBatchCacheV1.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    if cached.cache_key != cache_key or cached.review_batch_id != review_batch_id:
        return None
    return cached


def write_trusted_fidelity_cache(
    cache_dir: Path,
    *,
    cache_key: str,
    graph: TrustedReadmeFactGraphV1,
    review_batch_id: str,
    result: TrustedFidelityReviewResultV1,
    retry_history: tuple[dict, ...],
) -> TrustedFidelityBatchCacheV1:
    """Persist an already-grounded result through the evidence redactor."""

    cache = TrustedFidelityBatchCacheV1(
        cache_key=cache_key,
        output_sha256=_canonical_hash(_output_payload(result, retry_history)),
        org_repo=graph.org_repo,
        source_revision=graph.source_revision,
        review_batch_id=review_batch_id,
        result=result,
        retry_history=retry_history,
    )
    write_redacted_json(cache_dir / f"{review_batch_id}.json", cache)
    return cache


def _output_payload(
    result: TrustedFidelityReviewResultV1,
    retry_history: tuple[dict, ...],
) -> dict:
    return {
        "result": result.model_dump(mode="json"),
        "retry_history": retry_history,
    }


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
