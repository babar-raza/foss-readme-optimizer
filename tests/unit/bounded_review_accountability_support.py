"""Tests for the standalone bounded-review packetizer, validator, aggregator, and repair router.

Builds minimal-but-valid ``ReadmeDocumentPlanV1`` / ``ReadmeClaimAccountabilityMapV1`` /
``ProductFactsV2`` instances with a private helper below (no new support module -- outside the
granted writable test scope) against the synthetic ~162KB candidate at
``tests/fixtures/bounded_review_packets/candidate.md``. Claim/provenance spans are located by
searching for exact literal marker sentences in the loaded fixture text at test time, never by
hardcoded byte offsets, so the fixture can be edited without hand-recomputing spans as long as the
markers are preserved.
"""

from __future__ import annotations

from dataclasses import dataclass

from bounded_review_fact_support import (
    _PLACEHOLDER_HASH,
    CANDIDATE_TEXT,
    _build_document_plan,
    _build_product_facts,
    _sha256,
)

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_accountability_models import (
    ReadmeClaimAccountabilityMapV1,
    ReadmeClaimAccountabilityV1,
)
from readme_agent.readme.document_plan import (
    CandidateContentProvenanceV1,
)


@dataclass(frozen=True)
class _ClaimSpec:
    claim_id: str
    marker: str
    fact_id: str | None
    marker_end: str | None = None


def _claim_span(candidate_text: str, spec: _ClaimSpec) -> tuple[int, int]:
    start = candidate_text.index(spec.marker)
    if spec.marker_end is not None:
        end = candidate_text.index(spec.marker_end, start) + len(spec.marker_end)
    else:
        end = start + len(spec.marker)
    return start, end


def _build_claim_accountability(
    candidate_text: str,
    facts: ProductFactsV2,
    specs: list[_ClaimSpec],
) -> ReadmeClaimAccountabilityMapV1:
    claims = []
    for spec in specs:
        start, end = _claim_span(candidate_text, spec)
        byte_start = len(candidate_text[:start].encode("utf-8"))
        byte_end = len(candidate_text[:end].encode("utf-8"))
        content = candidate_text[start:end]
        claims.append(
            ReadmeClaimAccountabilityV1(
                claim_id=spec.claim_id,
                stage="candidate",
                origin="generated",
                source_byte_start=byte_start,
                source_byte_end=byte_end,
                content_sha256=_sha256(content),
                current_disposition="add",
                accepted_fact_ids=[spec.fact_id] if spec.fact_id else [],
                expected_disposition="accepted_fact" if spec.fact_id else "deferred_verification",
                survives_in_candidate=True,
                currently_accountable=True,
                rationale=f"synthetic fixture claim for {spec.claim_id}",
            )
        )
    return ReadmeClaimAccountabilityMapV1(
        org_repo="acme/widget-toolkit",
        facts_hash=facts.canonical_hash(),
        source_sha256=_PLACEHOLDER_HASH,
        candidate_sha256=_sha256(candidate_text),
        claims=claims,
    )


def _default_claim_specs() -> list[_ClaimSpec]:
    return [
        _ClaimSpec(
            "claim-overview-identity",
            "Widget Toolkit is a batteries-included component library for building "
            "desktop-style dashboards in the browser.",
            "product.identity:primary",
        ),
        _ClaimSpec(
            "claim-overview-problem",
            "It solves the recurring problem of assembling consistent, accessible dashboard "
            "widgets from scratch for every internal tool.",
            "product.problems_solved:primary",
        ),
        _ClaimSpec(
            "claim-capabilities",
            "- Drag-and-drop grid layout with responsive breakpoints.",
            "product.capabilities:primary",
            marker_end="- Accessible form controls audited against WCAG 2.1 AA.",
        ),
        _ClaimSpec(
            "claim-installation",
            "pip install widget-toolkit",
            "installation.coordinates:primary",
        ),
        _ClaimSpec(
            "claim-quickstart",
            'dashboard = Dashboard(theme="dark")\ndashboard.add_widget("clock")\n'
            "dashboard.render()",
            "example.minimal:primary",
        ),
        _ClaimSpec(
            "claim-api-release",
            "Every method below is verified against the public API surface for the 2.3 "
            "release line.",
            "release.state:primary",
        ),
        _ClaimSpec(
            "claim-limitations",
            "The virtualization layer does not yet support nested row grouping, and "
            "server-driven pagination is still experimental.",
            "product.limitations:primary",
        ),
        _ClaimSpec(
            "claim-support",
            "Bug reports and feature requests are tracked through the project issue "
            "tracker, and the maintainers respond within two business days.",
            "support.routes:primary",
        ),
        _ClaimSpec(
            "claim-license-terms",
            "Widget Toolkit is distributed under the MIT license, which permits commercial "
            "use, modification, and redistribution with attribution.",
            "product.license:primary",
        ),
        _ClaimSpec(
            "claim-license-relationship",
            "A hosted, fully managed edition with enterprise support is available "
            "separately; this repository contains only the open-source core.",
            "relationship.commercial_foss:primary",
        ),
    ]


def _default_provenance(candidate_text: str) -> list[CandidateContentProvenanceV1]:
    entries = []
    for provenance_id, marker, fact_id, rationale in (
        (
            "provenance-installation",
            "pip install widget-toolkit",
            "installation.coordinates:primary",
            "installation command matches the verified installation coordinates fact",
        ),
        (
            "provenance-license",
            "Widget Toolkit is distributed under the MIT license, which permits commercial "
            "use, modification, and redistribution with attribution.",
            "product.license:primary",
            "license prose matches the verified product license fact",
        ),
    ):
        start = candidate_text.index(marker)
        end = start + len(marker)
        byte_start = len(candidate_text[:start].encode("utf-8"))
        byte_end = len(candidate_text[:end].encode("utf-8"))
        entries.append(
            CandidateContentProvenanceV1(
                provenance_id=provenance_id,
                candidate_byte_start=byte_start,
                candidate_byte_end=byte_end,
                fact_ids=[fact_id],
                rationale=rationale,
            )
        )
    return entries


DEFAULT_DO_NOT_CLAIM = [
    {
        "fact_id": "unused.competitor_claim:primary",
        "field": "unused.competitor_claim",
        "reason": "unresolved_conflict",
    },
    {
        "fact_id": "unused.roadmap_claim:primary",
        "field": "unused.roadmap_claim",
        "reason": "conflicting_evidence",
    },
]

DEFAULT_FACTS = _build_product_facts()
DEFAULT_DOCUMENT_PLAN = _build_document_plan(CANDIDATE_TEXT, DEFAULT_FACTS)
DEFAULT_CLAIM_ACCOUNTABILITY = _build_claim_accountability(
    CANDIDATE_TEXT, DEFAULT_FACTS, _default_claim_specs()
)
DEFAULT_PROVENANCE = _default_provenance(CANDIDATE_TEXT)
