"""Deterministic projection of ProductFactsV2 into a bounded authoring packet.

Proves the packet reuses `agentic_composition_inputs.py`'s canonical compact projection
(`composition_fact_payloads`/`do_not_claim_payloads`) rather than flattening structured facts
through `fact_strings()[0]` -- every ecosystem's acquisition coordinates, API visibility/
reachability/implementation state, and corroboration/conflict evidence must survive intact.
"""

import pytest
from section_authoring_test_support import (
    build_conflict,
    build_evidence_assessment,
    build_fact,
    build_product_facts_v2,
)

from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.specialists.section_authoring_packet import build_section_authoring_packet

PROTECTED = fingerprint_protected_content("# Example\n\nA focused library.\n")

# Real shapes for three of the seven ecosystems' acquisition coordinates (Python/pip,
# Java/Maven, Go modules) -- proves the packet preserves each platform's own structured
# coordinate shape rather than reducing every platform to one flattened string.
_ACQUISITION_COORDINATES = {
    "python": [{"ecosystem": "python", "manifest_path": "setup.py", "name": "aspose-3d-foss"}],
    "java": [
        {
            "ecosystem": "java",
            "manifest_path": "pom.xml",
            "group_id": "com.aspose",
            "artifact_id": "aspose-3d-foss",
        }
    ],
    "go": [
        {
            "ecosystem": "go",
            "manifest_path": "go.mod",
            "module": "github.com/aspose-pdf-foss/pdf-go",
        }
    ],
}

_API_SURFACE_ALL_UNKNOWN = {
    "modules": [{"module": "aspose3d"}],
    "classes": [
        {"name": "Scene", "state": {"visibility": "public", "reachable": True}},
    ],
}

_API_SURFACE_IMPLEMENTED = {
    "modules": [{"module": "aspose3d"}],
    "classes": [
        {
            "name": "Scene",
            "state": {"visibility": "public", "reachable": True, "implemented": True},
            "methods": ["load"],
        },
    ],
}


def _packet(**overrides):
    product_facts = overrides.pop("product_facts", build_product_facts_v2())
    kwargs = {
        "org_repo": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "source_revision": "a" * 40,
        "target_section_id": "capability-overview",
        "task_family": "capability_entry_cluster",
        "section_objective": "Introduce the primary import/export capabilities.",
        "product_facts": product_facts,
        "accepted_fact_ids": ["product.capabilities:fixture"],
        "do_not_claim_fact_ids": [],
        "protected_content": PROTECTED,
    }
    kwargs.update(overrides)
    return build_section_authoring_packet(**kwargs)


def test_builds_a_packet_with_accepted_facts():
    packet = _packet()

    assert packet.allowed_fact_ids == ["product.capabilities:fixture"]
    fact = packet.accepted_facts[0]
    assert fact.polarity == "positive_implementation"
    assert packet.protected_literal_hash == PROTECTED.maintainer_region_hash


def test_do_not_claim_fact_uses_explicit_constraint_polarity():
    facts = build_product_facts_v2(
        field_values={"product.limitations": "COLLADA export is not implemented."}
    )
    packet = _packet(product_facts=facts, do_not_claim_fact_ids=["product.limitations:fixture"])

    do_not_claim = {fact.fact_id: fact for fact in packet.do_not_claim}
    assert do_not_claim["product.limitations:fixture"].polarity == "explicit_constraint"


@pytest.mark.parametrize("ecosystem", ["python", "java", "go"])
def test_acquisition_coordinates_survive_structured_not_flattened(ecosystem):
    coordinates = _ACQUISITION_COORDINATES[ecosystem]
    facts = build_product_facts_v2(field_values={"installation.coordinates": coordinates})
    packet = _packet(
        product_facts=facts,
        task_family="installation_framing",
        accepted_fact_ids=["installation.coordinates:fixture"],
    )

    fact = packet.accepted_facts[0]
    assert fact.value == coordinates  # the real structured list/dict, not a flattened string
    assert isinstance(fact.value, list)


def test_a_genuinely_absent_coordinate_stays_absent_never_invented():
    facts = build_product_facts_v2(field_values={"installation.coordinates": None})
    packet = _packet(
        product_facts=facts,
        task_family="installation_framing",
        accepted_fact_ids=["installation.coordinates:fixture"],
    )

    assert packet.accepted_facts[0].value is None


def _api_surface_facts(value, org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python"):
    return build_product_facts_v2(
        org_repo=org_repo,
        extra_facts=[build_fact("api.public_surface:fixture", "api.public_surface", value)],
    )


def test_api_surface_implementation_states_survive_serialization():
    facts = _api_surface_facts(_API_SURFACE_ALL_UNKNOWN)
    packet = _packet(
        product_facts=facts,
        task_family="scope_and_limitations",  # non-capability-claiming family: no gate applies
        accepted_fact_ids=["api.public_surface:fixture"],
    )

    classes = packet.accepted_facts[0].value["representative_classes"]
    assert classes[0]["name"] == "Scene"
    assert classes[0].get("implementation_states") is None  # no member ever proved implemented


def test_unknown_implementation_state_cannot_authorize_capability_entry_cluster():
    facts = _api_surface_facts(_API_SURFACE_ALL_UNKNOWN)

    with pytest.raises(ValueError, match="no proven-implemented API surface"):
        _packet(
            product_facts=facts,
            task_family="capability_entry_cluster",
            accepted_fact_ids=["api.public_surface:fixture"],
        )


def test_stubbed_or_not_reachable_states_also_cannot_authorize_capability_wording():
    stubbed = {
        "modules": [{"module": "aspose3d"}],
        "classes": [
            {
                "name": "Scene",
                "state": {"visibility": "public", "reachable": False},
                "methods": ["load"],
                "members": [{"implemented": False}],
            },
        ],
    }
    facts = _api_surface_facts(stubbed)

    with pytest.raises(ValueError, match="no proven-implemented API surface"):
        _packet(
            product_facts=facts,
            task_family="capability_entry_cluster",
            accepted_fact_ids=["api.public_surface:fixture"],
        )


def test_verified_implemented_api_item_can_authorize_capability_entry_cluster():
    facts = _api_surface_facts(_API_SURFACE_IMPLEMENTED)

    packet = _packet(
        product_facts=facts,
        task_family="capability_entry_cluster",
        accepted_fact_ids=["api.public_surface:fixture"],
    )

    classes = packet.accepted_facts[0].value["representative_classes"]
    assert classes[0]["implementation_states"] == ["implemented"]


def test_unknown_implementation_state_still_authorizes_a_non_capability_family():
    """implemented=unknown may still authorize neutral, non-capability-claiming wording --
    the gate is specific to capability_entry_cluster, not a blanket rejection."""

    facts = _api_surface_facts(_API_SURFACE_ALL_UNKNOWN)

    packet = _packet(
        product_facts=facts,
        task_family="opening_summary",
        accepted_fact_ids=["api.public_surface:fixture"],
    )

    assert packet.accepted_facts[0].field == "api.public_surface"


def test_unverified_fact_rejected_as_accepted():
    extra = build_fact(
        "product.capabilities:extra",
        "product.capabilities",
        "Might support FBX.",
        verification_state="unverified",
    )
    facts = build_product_facts_v2(extra_facts=[extra])

    with pytest.raises(ValueError, match="not verified/policy_approved"):
        _packet(product_facts=facts, accepted_fact_ids=["product.capabilities:extra"])


def test_unresolved_conflict_fact_rejected_as_accepted():
    extra = build_fact(
        "product.capabilities:conflicted",
        "product.capabilities",
        "Supports real-time rendering.",
        verification_state="conflicting",
        conflicts=[build_conflict(conflicting_fact_id="product.capabilities:fixture")],
    )
    facts = build_product_facts_v2(extra_facts=[extra])

    with pytest.raises(ValueError, match="not verified/policy_approved"):
        _packet(product_facts=facts, accepted_fact_ids=["product.capabilities:conflicted"])


def test_conflicting_fact_automatically_becomes_do_not_claim_context():
    extra = build_fact(
        "product.capabilities:conflicted",
        "product.capabilities",
        "Supports real-time rendering.",
        verification_state="conflicting",
        conflicts=[build_conflict(conflicting_fact_id="product.capabilities:fixture")],
    )
    facts = build_product_facts_v2(extra_facts=[extra])

    packet = _packet(product_facts=facts)

    do_not_claim_ids = {fact.fact_id for fact in packet.do_not_claim}
    assert "product.capabilities:conflicted" in do_not_claim_ids


def test_corroboration_anchors_and_conflict_counts_survive_into_the_packet():
    extra = build_fact(
        "product.capabilities:corroborated",
        "product.capabilities",
        "Imports OBJ files.",
        verification_state="verified",
        evidence_assessments=[
            build_evidence_assessment(
                "product.capabilities:corroborated", field="product.capabilities"
            )
        ],
    )
    facts = build_product_facts_v2(extra_facts=[extra])

    packet = _packet(product_facts=facts, accepted_fact_ids=["product.capabilities:corroborated"])

    corroboration = packet.accepted_facts[0].corroboration
    assert corroboration.evidence_assessment_count == 1
    assert len(corroboration.accepted_evidence_anchors) == 1
    assert corroboration.accepted_evidence_anchors[0].source_path == "src/example.py"
    assert corroboration.has_unresolved_conflict is False


def test_unknown_fact_id_rejected():
    with pytest.raises(ValueError, match="unknown fact_id"):
        _packet(accepted_fact_ids=["product.capabilities:fixture", "does.not.exist:anywhere"])


def test_five_accepted_facts_rejected_by_packet_validator():
    extra_facts = [
        build_fact(f"product.capabilities:extra-{i}", "product.capabilities", f"Capability {i}.")
        for i in range(4)
    ]
    facts = build_product_facts_v2(extra_facts=extra_facts)
    ids = ["product.capabilities:fixture", *[f"product.capabilities:extra-{i}" for i in range(4)]]

    with pytest.raises(ValueError, match="1-4 accepted facts"):
        _packet(product_facts=facts, accepted_fact_ids=ids, do_not_claim_fact_ids=[])


def test_fact_appearing_in_both_accepted_and_do_not_claim_rejected():
    with pytest.raises(ValueError, match="both accepted_facts and do_not_claim"):
        _packet(
            accepted_fact_ids=["product.capabilities:fixture"],
            do_not_claim_fact_ids=["product.capabilities:fixture"],
        )


def test_current_source_text_is_preserved_verbatim_when_supplied():
    packet = _packet(current_source_text="Existing overview paragraph.")

    assert packet.current_source_text == "Existing overview paragraph."


def test_canonical_hash_is_stable_and_changes_with_content():
    packet_a = _packet()
    packet_b = _packet()
    packet_c = _packet(section_objective="A different objective.")

    assert packet_a.canonical_hash() == packet_b.canonical_hash()
    assert packet_a.canonical_hash() != packet_c.canonical_hash()


@pytest.mark.parametrize(
    "changed",
    ["visibility", "reachable", "implementation_state", "coordinates"],
)
def test_changing_structured_truth_state_changes_the_packet_hash(changed):
    base_surface = {
        "modules": [{"module": "aspose3d"}],
        "classes": [
            {
                "name": "Scene",
                "state": {"visibility": "public", "reachable": True},
                "methods": ["load"],
                "members": [{"implemented": False}],
            }
        ],
    }
    base_class = base_surface["classes"][0]
    variants = {
        "visibility": {
            **base_surface,
            "classes": [{**base_class, "state": {"visibility": "internal", "reachable": True}}],
        },
        "reachable": {
            **base_surface,
            "classes": [{**base_class, "state": {"visibility": "public", "reachable": False}}],
        },
        "implementation_state": {
            **base_surface,
            "classes": [{**base_class, "members": [{"implemented": True}]}],
        },
        "coordinates": {**base_surface, "modules": [{"module": "aspose3d_v2"}]},
    }
    facts_base = _api_surface_facts(base_surface)
    facts_changed = _api_surface_facts(variants[changed])

    packet_base = _packet(
        product_facts=facts_base,
        task_family="scope_and_limitations",
        accepted_fact_ids=["api.public_surface:fixture"],
    )
    packet_changed = _packet(
        product_facts=facts_changed,
        task_family="scope_and_limitations",
        accepted_fact_ids=["api.public_surface:fixture"],
    )

    assert packet_base.canonical_hash() != packet_changed.canonical_hash()
