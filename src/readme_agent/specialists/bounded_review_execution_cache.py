"""Load and persist bounded review packets without broad cache invalidation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from readme_agent.specialists.bounded_review_cache import (
    BoundedReviewCacheContextV1,
    cache_key_for_packet,
    load_bounded_review_packet_cache,
    write_bounded_review_packet_cache,
)
from readme_agent.specialists.bounded_review_packets import (
    BoundedFactualPacketV1,
    BoundedPacketResultV1,
    BoundedReviewPlanV1,
    BoundedVisitorPacketV1,
)

Packet = BoundedFactualPacketV1 | BoundedVisitorPacketV1
PacketExecution = tuple[BoundedPacketResultV1, tuple[dict, ...]]


@dataclass(frozen=True)
class BoundedReviewPacketCache:
    """Provide runtime-bound packet reuse while retaining unaffected cache entries."""

    org_repo: str
    plan: BoundedReviewPlanV1
    cache_dir: Path | None
    context: BoundedReviewCacheContextV1 | None
    blind_prompt_id: str
    factual_prompt_id: str
    record_cache_reuse: Callable[..., None]

    def __post_init__(self) -> None:
        if (self.cache_dir is None) != (self.context is None):
            raise ValueError("bounded review cache directory and context must be supplied together")

    def load(
        self,
        packet: Packet,
        *,
        runtime_contract_hash: str | None = None,
        validate_result: Callable[[BoundedPacketResultV1], bool] | None = None,
    ) -> PacketExecution | None:
        """Load one matching packet and revalidate it when the caller supplies a gate."""

        if self.cache_dir is None or self.context is None:
            return None
        cache_key = cache_key_for_packet(
            packet,
            self.context,
            runtime_contract_hash=runtime_contract_hash,
        )
        cached = load_bounded_review_packet_cache(
            self.cache_dir,
            cache_key=cache_key,
            org_repo=self.org_repo,
            context=self.context,
            packet=packet,
            plan=self.plan,
        )
        if cached is None:
            return None
        if validate_result is not None and not validate_result(cached.result):
            return None
        model, _schema_hash, _sampling = self.context.identity_for(packet)
        prompt_id = self.blind_prompt_id if packet.facet == "visitor" else self.factual_prompt_id
        self.record_cache_reuse(
            job=prompt_id,
            prompt_id=prompt_id,
            prompt_sha256=packet.prompt_contract_hash,
            model=model,
            disposition="cache_reuse",
            request={"cache_key": cache_key, "packet_id": packet.packet_id},
        )
        history = (
            *cached.grounding_history,
            {
                "role": "blind_quality" if packet.facet == "visitor" else "factual_plan",
                "attempt": 0,
                "context_mode": "bounded_packet_cache_reuse",
                "valid": True,
                "errors": [],
                "packet_id": packet.packet_id,
                "cache_key": cache_key,
            },
        )
        return cached.result, history

    def persist(
        self,
        packet: Packet,
        result: BoundedPacketResultV1,
        history: tuple[dict, ...],
        *,
        runtime_contract_hash: str | None = None,
    ) -> None:
        """Persist one packet under its exact runtime contract identity."""

        if self.cache_dir is None or self.context is None:
            return
        write_bounded_review_packet_cache(
            self.cache_dir,
            cache_key=cache_key_for_packet(
                packet,
                self.context,
                runtime_contract_hash=runtime_contract_hash,
            ),
            org_repo=self.org_repo,
            context=self.context,
            packet=packet,
            result=result,
            grounding_history=history,
        )


__all__ = ["BoundedReviewPacketCache", "PacketExecution"]
