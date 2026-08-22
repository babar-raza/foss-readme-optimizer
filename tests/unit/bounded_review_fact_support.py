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

import hashlib
import pathlib

from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.readme.document_plan import (
    PresentationSpanAdoptionV1,
    ReadmeDocumentPlanV1,
)

FIXTURE_DIR = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "bounded_review_packets"
CANDIDATE_PATH = FIXTURE_DIR / "candidate.md"

FACTUAL_PROMPT_SHA256 = hashlib.sha256(b"bounded-review-factual-prompt-v1").hexdigest()
VISITOR_PROMPT_SHA256 = hashlib.sha256(b"bounded-review-visitor-prompt-v1").hexdigest()

# Fits the ~26KB "Bundled Default Configuration" fence comfortably, so the default/"clean" fixture
# plan never surfaces an oversized_unit record by accident -- test_oversized_unit_* below uses a
# deliberately smaller budget to exercise that path on purpose.
DEFAULT_BUDGET_CHARS = 30_000


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_candidate() -> str:
    return CANDIDATE_PATH.read_text(encoding="utf-8")


CANDIDATE_TEXT = _read_candidate()


# --------------------------------------------------------------------------------------------
# Minimal-but-valid producer model builders
# --------------------------------------------------------------------------------------------

_FACT_VALUES: dict[str, object] = {
    "product.identity": "Widget Toolkit is a component library for building dashboards.",
    "product.audience": "Internal-tools teams building operational dashboards.",
    "product.problems_solved": "Assembling consistent dashboard widgets from scratch.",
    "product.capabilities": [
        "Drag-and-drop grid layout",
        "Theming",
        "Virtualized tables",
        "Accessible forms",
    ],
    "product.formats": ["JSON", "YAML"],
    "product.platforms": ["Web"],
    "installation.coordinates": "pip install widget-toolkit",
    "installation.verified_acquisition": {"registry": "pypi", "package": "widget-toolkit"},
    "example.minimal": {"language": "python", "code": "from widget_toolkit import Dashboard"},
    "documentation.links": ["https://example.invalid/docs"],
    "release.state": "2.3",
    "product.limitations": "No nested row grouping; pagination is experimental.",
    "product.compatibility": "Python 3.9+",
    "product.license": "MIT",
    "support.routes": "GitHub issue tracker",
    "relationship.commercial_foss": "A hosted managed edition is available separately.",
}


def _build_fact(field_name: str, value: object) -> FactRecordV2:
    return FactRecordV2(
        fact_id=f"{field_name}:primary",
        field=field_name,
        value=value,
        source=FactSourceV2(
            source_type="approved_documentation",
            location="fixture://source",
            source_revision="1",
        ),
        verification_state="verified",
        authoritative_owner="fixture-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )


def _build_product_facts(overrides: dict[str, object] | None = None) -> ProductFactsV2:
    values = dict(_FACT_VALUES)
    if overrides:
        values.update(overrides)
    facts = [_build_fact(field, value) for field, value in values.items()]
    selected_fact_ids = {field: f"{field}:primary" for field in values}
    return ProductFactsV2(
        org_repo="acme/widget-toolkit",
        facts=facts,
        selected_fact_ids=selected_fact_ids,
    )


_PLACEHOLDER_HASH = _sha256("synthetic-source")


def _build_document_plan(candidate_text: str, facts: ProductFactsV2) -> ReadmeDocumentPlanV1:
    return ReadmeDocumentPlanV1(
        org_repo="acme/widget-toolkit",
        immutable_base_revision="0" * 40,
        facts_hash=facts.canonical_hash(),
        template_sha256=_PLACEHOLDER_HASH,
        source_sha256=_PLACEHOLDER_HASH,
        adoption=PresentationSpanAdoptionV1(
            already_adopted=True,
            source_document_sha256=_PLACEHOLDER_HASH,
            source_inner_sha256=_PLACEHOLDER_HASH,
            source_inner_bytes=0,
            preservation_check="byte_identical",
        ),
        operations=[],
        candidate_sha256=_sha256(candidate_text),
    )
