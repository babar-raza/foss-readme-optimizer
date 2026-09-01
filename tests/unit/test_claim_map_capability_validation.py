"""Deterministic defense-in-depth: claim-map validation rejects capability
wording that is backed only by an unimplemented member's presence in the
`api.public_surface` catalog."""

from __future__ import annotations

import hashlib

from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2
from readme_agent.readme.claim_map import ReadmeClaimBindingV1, ReadmeClaimMapV1
from readme_agent.readme.claim_map_capability_validation import (
    api_capability_claims_without_implementation_evidence,
)

_ORG_REPO = "acme/widget"


def _api_public_surface_facts(members: list[dict]):
    fact = FactRecordV2(
        fact_id="api.public_surface:python-exports",
        field="api.public_surface",
        value={
            "modules": [{"module": "acme.widget", "exports": ["NurbsSurface"]}],
            "classes": [
                {
                    "name": "NurbsSurface",
                    "description": "",
                    "kind": "class",
                    "members": members,
                }
            ],
        },
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://acme/widget",
            source_revision="a" * 40,
        ),
        verification_state="verified",
        authoritative_owner="repository",
        confidence=1.0,
        affected_surfaces=["readme.api_reference"],
    )
    return resolve_product_facts(
        _ORG_REPO,
        [fact],
        missing_source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://acme/widget",
            source_revision="a" * 40,
        ),
        missing_field_surfaces={},
    )


def _claim(fact_id: str, text: str, *, byte_start: int) -> ReadmeClaimBindingV1:
    text_bytes = text.encode("utf-8")
    return ReadmeClaimBindingV1(
        claim_id=f"claim:{fact_id}:{byte_start}",
        operation_id="readme.test.op",
        fact_id=fact_id,
        field="api.public_surface",
        verification_state="verified",
        fact_value_sha256=hashlib.sha256(b"value").hexdigest(),
        introduced_text_sha256=hashlib.sha256(text_bytes).hexdigest(),
        coordinate_space="candidate_utf8",
        byte_start=byte_start,
        byte_end=byte_start + len(text_bytes),
        claim_text_sha256=hashlib.sha256(text_bytes).hexdigest(),
        rationale="test claim",
    )


def _claim_map(claims: list[ReadmeClaimBindingV1]) -> ReadmeClaimMapV1:
    return ReadmeClaimMapV1(
        org_repo=_ORG_REPO,
        facts_hash="f" * 64,
        candidate_sha256="c" * 64,
        claims=claims,
    )


def test_capability_wording_for_a_stub_member_is_a_violation():
    facts = _api_public_surface_facts([{"name": "to_mesh", "kind": "method", "implemented": False}])
    # A realistic API-reference-table row: the raw member name and its
    # capability description bound together on one rendered line.
    candidate_text = "`to_mesh()` - Supports converting content to mesh through `NurbsSurface`."
    claim = _claim("api.public_surface:python-exports", candidate_text, byte_start=0)

    violations = api_capability_claims_without_implementation_evidence(
        _claim_map([claim]), facts, candidate_text
    )

    assert violations
    assert "to_mesh" in violations[0]


def test_capability_wording_for_an_implemented_member_is_not_a_violation():
    facts = _api_public_surface_facts([{"name": "to_mesh", "kind": "method", "implemented": True}])
    candidate_text = "Supports converting content to mesh through `NurbsSurface`."
    claim = _claim("api.public_surface:python-exports", candidate_text, byte_start=0)

    violations = api_capability_claims_without_implementation_evidence(
        _claim_map([claim]), facts, candidate_text
    )

    assert violations == []


def test_neutral_stub_description_is_not_a_violation():
    facts = _api_public_surface_facts([{"name": "to_mesh", "kind": "method", "implemented": False}])
    candidate_text = "Declares the `to_mesh` operation on `NurbsSurface` (not yet implemented)."
    claim = _claim("api.public_surface:python-exports", candidate_text, byte_start=0)

    violations = api_capability_claims_without_implementation_evidence(
        _claim_map([claim]), facts, candidate_text
    )

    assert violations == []


def test_unknown_implementation_status_is_never_flagged():
    """A member with no resolved `implemented` field (absent, not False)
    must never be treated as negative evidence -- absence is never itself a
    signal."""

    facts = _api_public_surface_facts([{"name": "to_mesh", "kind": "method"}])
    candidate_text = "Supports converting content to mesh through `NurbsSurface`."
    claim = _claim("api.public_surface:python-exports", candidate_text, byte_start=0)

    violations = api_capability_claims_without_implementation_evidence(
        _claim_map([claim]), facts, candidate_text
    )

    assert violations == []


def test_non_capability_wording_for_a_stub_member_is_not_flagged():
    facts = _api_public_surface_facts([{"name": "to_mesh", "kind": "method", "implemented": False}])
    candidate_text = "See `to_mesh` in the API reference table below."
    claim = _claim("api.public_surface:python-exports", candidate_text, byte_start=0)

    violations = api_capability_claims_without_implementation_evidence(
        _claim_map([claim]), facts, candidate_text
    )

    assert violations == []


def test_namespace_or_prose_token_does_not_impersonate_a_stub_method_reference():
    facts = _api_public_surface_facts([{"name": "render", "kind": "method", "implemented": False}])
    candidate_text = (
        "The `aspose.threed.render` namespace documents rendering types. "
        "`Renderer` renders scene content."
    )
    claim = _claim("api.public_surface:python-exports", candidate_text, byte_start=0)

    violations = api_capability_claims_without_implementation_evidence(
        _claim_map([claim]), facts, candidate_text
    )

    assert violations == []


def test_stub_member_named_after_a_capability_verb_does_not_self_trigger():
    """PWD-043: `aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python`'s real API Method Index
    row reads "| `Renderer` | `Renderer.render(symbol, layout, options) -> RenderedArtifact`
    | Declares the `render` operation on `Renderer` (not yet implemented). |" -- an honest,
    correctly-neutral disclosure. Unlike `test_neutral_stub_description_is_not_a_violation`'s
    "to_mesh" fixture, "render" is *itself* one of `_CAPABILITY_VERB_RE`'s own words, so the
    row's own backtick-quoted method signature (`Renderer.render(...)`) was self-triggering
    the capability-verb scan even though the row's actual prose is a plain disclosure."""

    facts = _api_public_surface_facts([{"name": "render", "kind": "method", "implemented": False}])
    candidate_text = (
        "| `Renderer` | `Renderer.render(symbol, layout, options) -> RenderedArtifact` | "
        "Declares the `render` operation on `Renderer` (not yet implemented). |"
    )
    claim = _claim("api.public_surface:python-exports", candidate_text, byte_start=0)

    violations = api_capability_claims_without_implementation_evidence(
        _claim_map([claim]), facts, candidate_text
    )

    assert violations == []


def test_real_capability_verb_named_stub_is_still_caught_outside_code_spans():
    """Negative control: a genuine capability claim about the same verb-named stub member,
    with the capability wording in real prose rather than only inside the member's own code
    reference, must still be caught -- the fix only excludes backtick-quoted code spans from
    the wording scan, it does not weaken the check."""

    facts = _api_public_surface_facts([{"name": "render", "kind": "method", "implemented": False}])
    candidate_text = "Renders barcodes to PDF through `PdfRenderer.render(symbol, layout, options)`"
    claim = _claim("api.public_surface:python-exports", candidate_text, byte_start=0)

    violations = api_capability_claims_without_implementation_evidence(
        _claim_map([claim]), facts, candidate_text
    )

    assert violations
    assert "render" in violations[0]


def test_preserved_source_span_claims_are_out_of_scope():
    """Only newly rendered (`candidate_utf8`) bindings are checked --
    preserved source text is a separate accountability concern."""

    facts = _api_public_surface_facts([{"name": "to_mesh", "kind": "method", "implemented": False}])
    candidate_text = "Supports converting content to mesh through `NurbsSurface`."
    claim = _claim("api.public_surface:python-exports", candidate_text, byte_start=0).model_copy(
        update={"coordinate_space": "presentation_inner_source_utf8"}
    )

    violations = api_capability_claims_without_implementation_evidence(
        _claim_map([claim]), facts, candidate_text
    )

    assert violations == []
