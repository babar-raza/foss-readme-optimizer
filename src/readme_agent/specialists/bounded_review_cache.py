"""Persist validated bounded-review packet results for exact-input reuse."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from readme_agent.evidence.writer import write_redacted_json
from readme_agent.specialists.bounded_review_contracts import (
    _SHA256_PATTERN,
    BoundedPacketV1,
    BoundedReviewPlanV1,
    PacketFacet,
)
from readme_agent.specialists.bounded_review_hashing import _canonical_hash
from readme_agent.specialists.bounded_review_repairs import (
    is_reusable_cache_entry,
    packet_cache_key,
)
from readme_agent.specialists.bounded_review_results import (
    BoundedPacketResultV1,
    validate_packet_result,
)


class BoundedReviewCacheContextV1(BaseModel):
    """Exact identities that can affect one packet-review result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    source_revision: str = Field(pattern=r"^[0-9a-f]+$")
    blind_model: str = Field(min_length=1)
    factual_model: str = Field(min_length=1)
    blind_schema_sha256: str = Field(pattern=_SHA256_PATTERN)
    factual_schema_sha256: str = Field(pattern=_SHA256_PATTERN)
    facts_hash: str = Field(pattern=_SHA256_PATTERN)
    provenance_hash: str = Field(pattern=_SHA256_PATTERN)
    blind_sampling_parameters: dict = Field(default_factory=dict)
    factual_sampling_parameters: dict = Field(default_factory=dict)

    def identity_for(self, packet: BoundedPacketV1) -> tuple[str, str, dict]:
        """Return model, response schema hash, and sampling parameters for a facet."""

        if packet.facet == "visitor":
            return self.blind_model, self.blind_schema_sha256, self.blind_sampling_parameters
        return self.factual_model, self.factual_schema_sha256, self.factual_sampling_parameters


class BoundedReviewPacketCacheV1(BaseModel):
    """One validated packet result bound to its complete cache identity."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    cache_key: str = Field(pattern=_SHA256_PATTERN)
    result_sha256: str = Field(pattern=_SHA256_PATTERN)
    org_repo: str = Field(min_length=3)
    source_revision: str = Field(pattern=r"^[0-9a-f]+$")
    packet_id: str = Field(min_length=1)
    packet_sha256: str = Field(pattern=_SHA256_PATTERN)
    facet: PacketFacet
    result: BoundedPacketResultV1
    grounding_history: tuple[dict, ...] = ()

    @model_validator(mode="after")
    def _binding_is_coherent(self) -> BoundedReviewPacketCacheV1:
        if self.result.packet_id != self.packet_id:
            raise ValueError("bounded-review cache packet ID does not match result")
        if self.result.packet_sha256 != self.packet_sha256:
            raise ValueError("bounded-review cache packet hash does not match result")
        if self.result.facet != self.facet:
            raise ValueError("bounded-review cache facet does not match result")
        if _canonical_hash(self.result.model_dump(mode="json")) != self.result_sha256:
            raise ValueError("bounded-review cache result checksum does not match")
        return self


def cache_key_for_packet(
    packet: BoundedPacketV1,
    context: BoundedReviewCacheContextV1,
    *,
    runtime_contract_hash: str | None = None,
) -> str:
    """Build one exact cache key from the packet and facet-specific client contract."""

    model, schema_sha256, sampling_parameters = context.identity_for(packet)
    return packet_cache_key(
        packet,
        model=model,
        schema_sha256=schema_sha256,
        facts_hash=context.facts_hash,
        provenance_hash=context.provenance_hash,
        sampling_parameters=sampling_parameters,
        runtime_contract_hash=runtime_contract_hash,
    )


def load_bounded_review_packet_cache(
    cache_dir: Path,
    *,
    cache_key: str,
    org_repo: str,
    context: BoundedReviewCacheContextV1,
    packet: BoundedPacketV1,
    plan: BoundedReviewPlanV1,
) -> BoundedReviewPacketCacheV1 | None:
    """Load only an exact, structurally valid, reusable packet result."""

    path = cache_dir / f"{cache_key}.json"
    if not path.is_file():
        return None
    try:
        cached = BoundedReviewPacketCacheV1.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return None
    if (
        cached.cache_key != cache_key
        or cached.org_repo != org_repo
        or cached.source_revision != context.source_revision
        or cached.packet_id != packet.packet_id
        or cached.packet_sha256 != packet.packet_sha256
        or not is_reusable_cache_entry(cached.result)
        or not validate_packet_result(plan, cached.result).valid
    ):
        return None
    return cached


def write_bounded_review_packet_cache(
    cache_dir: Path,
    *,
    cache_key: str,
    org_repo: str,
    context: BoundedReviewCacheContextV1,
    packet: BoundedPacketV1,
    result: BoundedPacketResultV1,
    grounding_history: tuple[dict, ...],
) -> BoundedReviewPacketCacheV1:
    """Atomically persist one already-validated, non-system-failure result."""

    if not is_reusable_cache_entry(result):
        raise ValueError("SYSTEM_FAILURE bounded-review results cannot be cached")
    cached = BoundedReviewPacketCacheV1(
        cache_key=cache_key,
        result_sha256=_canonical_hash(result.model_dump(mode="json")),
        org_repo=org_repo,
        source_revision=context.source_revision,
        packet_id=packet.packet_id,
        packet_sha256=packet.packet_sha256,
        facet=packet.facet,
        result=result,
        grounding_history=grounding_history,
    )
    write_redacted_json(cache_dir / f"{cache_key}.json", cached)
    return cached


__all__ = [
    "BoundedReviewCacheContextV1",
    "BoundedReviewPacketCacheV1",
    "cache_key_for_packet",
    "load_bounded_review_packet_cache",
    "write_bounded_review_packet_cache",
]
