"""Tests for exact deterministic grounding of structural factual headings."""

from readme_agent.specialists.bounded_review_contracts import BoundedFactualPacketV1
from readme_agent.specialists.bounded_review_mechanical_facts import (
    mechanical_factual_heading_review,
)

_DIGEST = "a" * 64


def _packet(text: str, *, claim_ids: tuple[str, ...] = ()) -> BoundedFactualPacketV1:
    return BoundedFactualPacketV1(
        packet_id="pkt-factual-heading",
        stable_slot_id="factual:api-reference/entities:00",
        order=0,
        candidate_sha256=_DIGEST,
        section_path="api-reference/entities",
        char_start=0,
        char_end=len(text),
        line_start=1,
        line_end=1,
        unit_text=text,
        covered_unit_ids=("unit-heading",),
        claim_ids=claim_ids,
        accepted_fact_ids=("api.public_surface:exports",),
        facts=(),
        provenance_ids=("template.heading",),
        prompt_contract_hash=_DIGEST,
        input_contract_hash=_DIGEST,
        packet_sha256=_DIGEST,
    )


def _facts() -> dict:
    return {
        "selected_fact_ids": {"api.public_surface": "api.public_surface:exports"},
        "facts": [
            {
                "fact_id": "api.public_surface:exports",
                "verification_state": "verified",
                "value": {"namespace": "aspose.threed.entities"},
                "protected_literals": ["aspose.threed.entities"],
                "conflicts": [],
                "source": {"location": "repository://aspose/threed/entities/__init__.py"},
            }
        ],
    }


def test_exact_verified_namespace_heading_is_grounded_without_prose_judgment() -> None:
    result = mechanical_factual_heading_review(
        _packet("### Aspose.3D.Entities Namespace (`aspose.threed.entities`)\n"),
        _facts(),
    )

    assert result is not None
    assert result.verdict == "ACCEPT"
    assert result.findings[0].fact_id == "api.public_surface:exports"
    assert result.findings[0].evidence_excerpt == "aspose.threed.entities"


def test_prose_or_accountable_claims_never_use_the_mechanical_fast_path() -> None:
    assert mechanical_factual_heading_review(_packet("The API is complete.\n"), _facts()) is None
    assert (
        mechanical_factual_heading_review(
            _packet(
                "### Aspose.3D.Entities Namespace (`aspose.threed.entities`)\n",
                claim_ids=("claim-1",),
            ),
            _facts(),
        )
        is None
    )
