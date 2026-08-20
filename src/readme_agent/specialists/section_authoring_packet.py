"""Project `ProductFactsV2` into one bounded section-authoring packet.

Reuses the SAME canonical compact projection every other authoring/reviewing caller already
uses (`readme/agentic_composition_inputs.py::composition_fact_payloads`/`do_not_claim_payloads`)
-- never a second, independent, or flattening projection. A fact's structured `value` (package
acquisition coordinates, API visibility/reachability/implementation state, minimal-example
metadata, ...) survives here exactly as that shared projection produces it.

Every accepted fact must already be `verified`/`policy_approved` with no unresolved conflict --
this builder is the deterministic gate that keeps unresolved or synthetic-only evidence out of
an authoring call entirely, before any provider request is built. An accepted `api.public_surface`
fact additionally cannot authorize `capability_entry_cluster` wording unless at least one of its
representative classes is proven `implemented` -- `implemented=unknown`/`stubbed` may still
appear as `do_not_claim` context, or be accepted for a non-capability-claiming task family, but
must never reach Key Capabilities wording.
"""

from __future__ import annotations

from collections.abc import Sequence

from readme_agent.facts.protected_content import ProtectedContentSnapshotV1
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.llm.section_authoring_prompts import SectionAuthoringTaskFamily
from readme_agent.readme.agentic_composition_inputs import (
    composition_fact_payloads,
    do_not_claim_payloads,
)
from readme_agent.specialists.section_authoring_contracts import (
    SectionAuthoringFactV1,
    SectionAuthoringPacketV1,
)

_ACCEPTED_VERIFICATION_STATES = {"verified", "policy_approved"}
_CAPABILITY_CLAIMING_FAMILY: SectionAuthoringTaskFamily = "capability_entry_cluster"
_API_SURFACE_FIELD = "api.public_surface"


def _api_surface_authorizes_capability_claim(value: object) -> bool:
    """True only when at least one representative class in a compacted `api.public_surface`
    value is proven `implemented`. An `implementation_states` set of only `unknown`/`stubbed`
    (or no representative classes at all) must never authorize Key Capabilities wording, though
    it may still authorize neutral API-inventory wording for a non-capability-claiming family."""

    if not isinstance(value, dict):
        return True  # not an api.public_surface-shaped value; this gate does not apply
    classes = value.get("representative_classes") or []
    return any(
        "implemented" in (item.get("implementation_states") or [])
        for item in classes
        if isinstance(item, dict)
    )


def _payloads_by_id(facts: ProductFactsV2, fact_ids: set[str]) -> dict[str, dict]:
    return {payload["fact_id"]: payload for payload in composition_fact_payloads(facts, fact_ids)}


def _require_known(facts: ProductFactsV2, fact_id: str) -> None:
    try:
        facts.fact_by_id(fact_id)
    except KeyError as exc:
        raise ValueError(
            f"section authoring packet references unknown fact_id: {fact_id!r}"
        ) from exc


def _validate_accepted_payload(fact_id: str, payload: dict, *, task_family: str) -> None:
    verification_state = payload["verification_state"]
    if verification_state not in _ACCEPTED_VERIFICATION_STATES:
        raise ValueError(
            f"accepted fact {fact_id!r} is not verified/policy_approved "
            f"(verification_state={verification_state!r})"
        )
    if payload["corroboration"]["has_unresolved_conflict"]:
        raise ValueError(f"accepted fact {fact_id!r} carries an unresolved conflict")
    if (
        task_family == _CAPABILITY_CLAIMING_FAMILY
        and payload["field"] == _API_SURFACE_FIELD
        and not _api_surface_authorizes_capability_claim(payload["value"])
    ):
        raise ValueError(
            f"accepted fact {fact_id!r} has no proven-implemented API surface; "
            f"implemented=unknown/stubbed cannot authorize {_CAPABILITY_CLAIMING_FAMILY} wording "
            "-- accept it for a non-capability-claiming family instead, or move it to "
            "do_not_claim"
        )


def build_section_authoring_packet(
    *,
    org_repo: str,
    source_revision: str,
    target_section_id: str,
    task_family: SectionAuthoringTaskFamily,
    section_objective: str,
    product_facts: ProductFactsV2,
    accepted_fact_ids: Sequence[str],
    do_not_claim_fact_ids: Sequence[str] = (),
    protected_content: ProtectedContentSnapshotV1,
    seo_vocabulary: Sequence[str] = (),
    current_source_text: str | None = None,
) -> SectionAuthoringPacketV1:
    """Build the exact, minimal request one authoring call is allowed to see."""

    for fact_id in (*accepted_fact_ids, *do_not_claim_fact_ids):
        _require_known(product_facts, fact_id)

    auto_do_not_claim_ids = {item["fact_id"] for item in do_not_claim_payloads(product_facts)}
    all_do_not_claim_ids = set(do_not_claim_fact_ids) | (
        auto_do_not_claim_ids - set(accepted_fact_ids)
    )

    payloads_by_id = _payloads_by_id(product_facts, set(accepted_fact_ids) | all_do_not_claim_ids)

    accepted = []
    for fact_id in accepted_fact_ids:
        payload = payloads_by_id[fact_id]
        _validate_accepted_payload(fact_id, payload, task_family=task_family)
        accepted.append(SectionAuthoringFactV1.model_validate(payload))

    do_not_claim = [
        SectionAuthoringFactV1.model_validate(payloads_by_id[fact_id])
        for fact_id in sorted(all_do_not_claim_ids)
    ]

    return SectionAuthoringPacketV1(
        org_repo=org_repo,
        source_revision=source_revision,
        target_section_id=target_section_id,
        task_family=task_family,
        section_objective=section_objective,
        accepted_facts=tuple(accepted),
        do_not_claim=tuple(do_not_claim),
        protected_literal_hash=protected_content.maintainer_region_hash,
        seo_vocabulary=tuple(seo_vocabulary),
        current_source_text=current_source_text,
    )
