"""Cross-ecosystem course-correction: `compact_prompt_fact_value`'s generic,
schema-driven projection, and the new verification-state/polarity/
protected-literal/do-not-claim fields `composition_fact_payloads` carries."""

from __future__ import annotations

import pytest

from readme_agent.ecosystems.foss_coordinate import canonical_foss_coordinate
from readme_agent.facts.acquisition_schema import AcquisitionDecisionV1
from readme_agent.facts.evidence_polarity import EvidencePolarityAssessmentV1
from readme_agent.facts.readme_facts_readiness import build_repository_facts_readiness
from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2
from readme_agent.readme.agentic_composition_inputs import (
    compact_prompt_fact_value,
    composition_fact_payloads,
    do_not_claim_payloads,
)

_ORG_REPO = "acme/widget"
_SOURCE = FactSourceV2(
    source_type="mechanical_repository",
    location="repository://acme/widget",
    source_revision="a" * 40,
)


def _facts(records: list[FactRecordV2]):
    return resolve_product_facts(
        _ORG_REPO, records, missing_source=_SOURCE, missing_field_surfaces={}
    )


def _fact(field: str, value: object, *, verification_state: str = "verified") -> FactRecordV2:
    return FactRecordV2(
        fact_id=f"{field}:test",
        field=field,
        value=value,
        source=_SOURCE,
        verification_state=verification_state,  # type: ignore[arg-type]
        authoritative_owner="repository",
        confidence=1.0 if verification_state == "verified" else 0.4,
        affected_surfaces=["readme.example"],
    )


# --- Mandatory cross-ecosystem coverage: one fixture per platform, proving
# each platform's own ecosystem metadata survives `compact_prompt_fact_value`
# generically -- no per-platform branch decides which key to keep. Python/
# TypeScript/Rust use their own `*_package` field; Java/.NET/C++/Go all
# share the one `compiled_consumer` proof (compiled_consumer_schema.py).


def test_compact_prompt_fact_value_python_package_survives():
    value = {
        "language": "python",
        "code": "widget.export()",
        "python_package": {"distribution_name": "widget-foss", "canonical_import": "widget"},
    }

    compacted = compact_prompt_fact_value("example.minimal", value)

    assert compacted["python_package"]["distribution_name"] == "widget-foss"


def test_compact_prompt_fact_value_typescript_package_survives():
    value = {
        "language": "typescript",
        "code": "widget.export();",
        "typescript_package": {"entry_points": ["index.ts"], "canonical_import": "widget"},
    }

    compacted = compact_prompt_fact_value("example.minimal", value)

    assert compacted["typescript_package"]["canonical_import"] == "widget"


def test_compact_prompt_fact_value_rust_package_survives():
    value = {
        "language": "rust",
        "code": "widget::export();",
        "rust_package": {"crate_name": "widget-foss"},
        "rust_formats": [{"format": "obj"}],
    }

    compacted = compact_prompt_fact_value("example.minimal", value)

    assert compacted["rust_package"]["crate_name"] == "widget-foss"
    assert compacted["rust_formats"] == [{"format": "obj"}]


def test_compact_prompt_fact_value_java_compiled_consumer_survives():
    value = {
        "language": "java",
        "code": "Widget.export();",
        "compiled_consumer": {
            "ecosystem": "java",
            "source_paths": ["src/Widget.java"],
            "selected_symbols": ["Widget.export"],
            "accepted": True,
        },
    }

    compacted = compact_prompt_fact_value("example.minimal", value)

    assert compacted["compiled_consumer"]["ecosystem"] == "java"
    assert compacted["compiled_consumer"]["selected_symbols"] == ["Widget.export"]


def test_compact_prompt_fact_value_dotnet_compiled_consumer_survives():
    value = {
        "language": "dotnet",
        "code": "Widget.Export();",
        "compiled_consumer": {
            "ecosystem": "dotnet",
            "source_paths": ["Widget.cs"],
            "selected_symbols": ["Widget.Export"],
            "accepted": True,
        },
    }

    compacted = compact_prompt_fact_value("example.minimal", value)

    assert compacted["compiled_consumer"]["ecosystem"] == "dotnet"


def test_compact_prompt_fact_value_cpp_compiled_consumer_survives():
    value = {
        "language": "cpp",
        "code": "widget::export_it();",
        "compiled_consumer": {
            "ecosystem": "cpp",
            "source_paths": ["include/widget.h"],
            "selected_symbols": ["widget::export_it"],
            "accepted": True,
        },
    }

    compacted = compact_prompt_fact_value("example.minimal", value)

    assert compacted["compiled_consumer"]["ecosystem"] == "cpp"


def test_compact_prompt_fact_value_go_compiled_consumer_survives():
    value = {
        "language": "go",
        "code": "widget.Export()",
        "compiled_consumer": {
            "ecosystem": "go",
            "source_paths": ["widget.go"],
            "selected_symbols": ["Export"],
            "accepted": True,
        },
    }

    compacted = compact_prompt_fact_value("example.minimal", value)

    assert compacted["compiled_consumer"]["ecosystem"] == "go"


def test_compact_prompt_fact_value_bounds_a_native_transcript_regardless_of_ecosystem():
    """The same generic length rule applies to every platform's own
    verbose sub-field -- never a per-ecosystem branch to know which field
    names are transcripts."""

    value = {
        "language": "go",
        "code": "widget.Export()",
        "compiled_consumer": {
            "ecosystem": "go",
            "source_paths": ["widget.go"],
            "selected_symbols": ["Export"],
            "accepted": True,
            "isolated_execution": {"stdout": "x" * 50_000},
        },
    }

    compacted = compact_prompt_fact_value("example.minimal", value)

    assert len(compacted["compiled_consumer"]["isolated_execution"]["stdout"]) < 600


# --- Owner review (2026-08-20), check 1: `installation.verified_acquisition`'s
# `coordinate` (the one existing normalized package-coordinate structure --
# `dict[str, str]`, `acquisition_schema.py::AcquisitionDecisionV1`, the same
# shape `ecosystems/foss_coordinate.py` already produces for every
# registered ecosystem: `{"name": ...}` everywhere except Java's `{"group_id",
# "artifact_id"}`) must survive `compact_prompt_fact_value` identically for
# all 7 platforms -- no per-ecosystem branch, since `_ACQUISITION_PROMPT_KEYS`
# already allow-lists `coordinate` generically and nothing further bounds it.


def _acquisition_value(ecosystem: str, coordinate: dict[str, str] | None) -> dict:
    outcome = "NOT_PUBLISHED" if coordinate is None else "SOURCE_TREE_VERIFIED"
    decision = AcquisitionDecisionV1(
        org_repo="acme/widget",
        source_revision="a" * 40,
        ecosystem=ecosystem,
        method="repository_manifest",
        outcome=outcome,
        detail="real per-ecosystem coordinate survival check",
        coordinate=coordinate,
        truth_eligible=False,
    )
    return decision.model_dump(mode="json")


@pytest.mark.parametrize(
    "ecosystem",
    ["java", "python", "net", "cpp", "typescript", "go", "rust"],
)
def test_compact_prompt_fact_value_preserves_the_real_coordinate_per_ecosystem(ecosystem):
    _, coordinate = canonical_foss_coordinate("widget", ecosystem, org="acme", repo="widget-foss")
    value = _acquisition_value(ecosystem, coordinate)

    compacted = compact_prompt_fact_value("installation.verified_acquisition", value)

    assert compacted["coordinate"] == coordinate
    assert compacted["ecosystem"] == ecosystem


def test_compact_prompt_fact_value_preserves_a_genuinely_absent_coordinate_as_none():
    """Correction 1's own explicit boundary: when the fact model genuinely
    has no coordinate for this repository (unpublished, no source-build
    proof either), the projection must carry that absence through as
    `None` -- never fabricate a placeholder value. A repository in this
    state correctly reports BLOCKED_FACTS for `installation_coordinates`
    in `readme_facts_readiness.py` (no accepted fact declares the surface),
    not a silently invented coordinate."""

    value = _acquisition_value("go", None)

    compacted = compact_prompt_fact_value("installation.verified_acquisition", value)

    assert compacted["coordinate"] is None


# --- Owner review (2026-08-20), check 2: an api.public_surface class with
# implemented="unknown" must survive compact projection with that state
# intact, remain available for the public_api_reference section, but never
# be reachable through the key_capabilities_formats section's accepted-fact
# set -- proven structurally via affected_surfaces routing, not by trusting
# the template renderer alone.


def _api_public_surface_fact() -> FactRecordV2:
    return _fact(
        "api.public_surface",
        {
            "modules": [
                {"module": "widget", "exports": ["Known", "Mystery"]},
            ],
            "classes": [
                {
                    "name": "Known",
                    "description": "",
                    "kind": "class_definition",
                    "methods": [{"name": "run", "doc": "", "signature": "run()"}],
                    "properties": [],
                    "state": {
                        "visibility": "public",
                        "reachable": "unknown",
                        "implemented": "implemented",
                    },
                },
                {
                    "name": "Mystery",
                    "description": "",
                    "kind": "class_definition",
                    "methods": [{"name": "run", "doc": "", "signature": "run()"}],
                    "properties": [],
                    "state": {
                        "visibility": "public",
                        "reachable": "unknown",
                        "implemented": "unknown",
                    },
                },
            ],
            "model_sha": None,
        },
    ).model_copy(update={"affected_surfaces": ["readme.api_reference"]})


def test_api_public_surface_unknown_implementation_survives_compact_projection():
    fact = _api_public_surface_fact()

    compacted = compact_prompt_fact_value(fact.field, fact.value)

    classes_by_name = {item["name"]: item for item in compacted["representative_classes"]}
    assert classes_by_name["Known"]["implementation_states"] == ["implemented"]
    assert classes_by_name["Mystery"]["implementation_states"] == ["unknown"]
    assert classes_by_name["Mystery"]["visibility"] == "public"


def test_api_public_surface_fact_is_available_for_api_reference_but_never_key_capabilities():
    fact = _api_public_surface_fact()
    facts = _facts([fact])

    payloads = composition_fact_payloads(facts, {fact.fact_id})
    api_payload = next(p for p in payloads if p["field"] == "api.public_surface")
    unknown_class = next(
        item for item in api_payload["value"]["representative_classes"] if item["name"] == "Mystery"
    )
    assert unknown_class["implementation_states"] == ["unknown"]

    readiness = build_repository_facts_readiness(
        facts,
        family="widget",
        platform="python",
        source_revision=_SOURCE.source_revision,
        knowledge_revision=None,
        freshness="current",
    )
    api_reference_section = readiness.section("public_api_reference")
    capabilities_section = readiness.section("key_capabilities_formats")
    assert fact.fact_id in api_reference_section.accepted_fact_ids
    assert fact.fact_id not in capabilities_section.accepted_fact_ids


# --- composition_fact_payloads: verification_state, polarity, protected
# literals, and do_not_claim.


def test_composition_fact_payloads_carries_verification_state_and_polarity():
    facts = _facts(
        [
            _fact("product.capabilities", ["Exports widgets"]),
            _fact("product.limitations", ["Does not support gadgets"]),
        ]
    )
    accepted_ids = {fact.fact_id for fact in facts.facts}

    payloads = composition_fact_payloads(facts, accepted_ids)

    capabilities = next(p for p in payloads if p["field"] == "product.capabilities")
    limitations = next(p for p in payloads if p["field"] == "product.limitations")
    assert capabilities["verification_state"] == "verified"
    assert capabilities["polarity"] == "positive_implementation"
    assert limitations["polarity"] == "explicit_constraint"


def test_composition_fact_payloads_carries_corroboration_distinct_from_verification_state():
    """Owner review (2026-08-20), correction 5: corroboration is a
    separate concept from verification_state -- two facts can share the
    same verification_state while one carries real, per-anchor evidence
    and the other carries none, and the author must be able to see that
    difference."""

    assessed = _fact("product.capabilities", ["Exports widgets"])
    assessed = assessed.model_copy(
        update={
            "evidence_assessments": [
                EvidencePolarityAssessmentV1(
                    fact_id=assessed.fact_id,
                    claim_text="Exports widgets",
                    expected_polarity="positive_implementation",
                    observed_polarity="positive_implementation",
                    source_path="src/widget.py",
                    source_revision=_SOURCE.source_revision,
                    line_number=12,
                    anchor="def export",
                    exact_excerpt="def export(self):",
                    context_excerpt="def export(self):\n    ...",
                    accepted=True,
                    reason="method body implements real export logic",
                )
            ]
        }
    )
    unassessed = _fact("product.compatibility", "Works on widgets")
    facts = _facts([assessed, unassessed])
    accepted_ids = {fact.fact_id for fact in facts.facts}

    payloads = composition_fact_payloads(facts, accepted_ids)

    assessed_payload = next(p for p in payloads if p["field"] == "product.capabilities")
    unassessed_payload = next(p for p in payloads if p["field"] == "product.compatibility")
    assert assessed_payload["verification_state"] == unassessed_payload["verification_state"]
    assert assessed_payload["corroboration"]["evidence_assessment_count"] == 1
    assert assessed_payload["corroboration"]["accepted_evidence_anchors"] == [
        {"source_path": "src/widget.py", "line_number": 12}
    ]
    assert assessed_payload["corroboration"]["has_unresolved_conflict"] is False
    assert unassessed_payload["corroboration"] == {
        "evidence_assessment_count": 0,
        "accepted_evidence_anchors": [],
        "has_unresolved_conflict": False,
        "resolved_conflict_count": 0,
    }


def test_composition_fact_payloads_protected_literals_reflect_compacted_value():
    """Protected literals are derived from the already-compacted value, so
    a bounded-out native transcript never leaks back in through this field
    (the exact regression the course-correction's fix closed)."""

    facts = _facts(
        [
            _fact(
                "example.minimal",
                {
                    "language": "go",
                    "code": "widget.Export()",
                    "compiled_consumer": {"stdout": "x" * 50_000},
                },
            )
        ]
    )
    accepted_ids = {fact.fact_id for fact in facts.facts}

    payloads = composition_fact_payloads(facts, accepted_ids)
    example = next(p for p in payloads if p["field"] == "example.minimal")

    assert "widget.Export()" in example["protected_literals"]
    assert all(len(literal) < 600 for literal in example["protected_literals"])


def test_do_not_claim_payloads_surfaces_conflicting_facts_only():
    conflicting = _fact(
        "product.compatibility", "conflicting value", verification_state="conflicting"
    )
    verified = _fact("product.capabilities", ["Exports widgets"])
    facts = _facts([conflicting, verified])

    do_not_claim = do_not_claim_payloads(facts)

    assert any(item["fact_id"] == conflicting.fact_id for item in do_not_claim)
    assert all(item["fact_id"] != verified.fact_id for item in do_not_claim)


def test_do_not_claim_payloads_empty_when_nothing_conflicts():
    facts = _facts([_fact("product.capabilities", ["Exports widgets"])])

    assert do_not_claim_payloads(facts) == []
