"""Section-cluster authoring schema, messages, and recorded-response compatibility."""

import json
from pathlib import Path

import pytest
from section_authoring_test_support import build_fact, build_product_facts_v2

from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.llm.section_authoring_prompts import (
    MAX_UNITS,
    TASK_FAMILIES,
    build_section_cluster_authoring_messages,
    build_section_cluster_authoring_tool_schema,
)
from readme_agent.specialists.section_authoring_contracts import (
    SectionClusterAuthoringResultV1,
)
from readme_agent.specialists.section_authoring_packet import build_section_authoring_packet
from readme_agent.specialists.section_authoring_prompt_projection import (
    authoring_fact_prompt_payload,
)
from readme_agent.specialists.section_cluster_authoring import (
    SectionAuthoringAcceptanceError,
    _validate_acceptance,
)

_PROBE_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "section_authoring"
    / "qwen3-next-overview-capabilities-3d-python.json"
)


def test_five_task_families_are_registered():
    assert set(TASK_FAMILIES) == {
        "opening_summary",
        "capability_entry_cluster",
        "installation_framing",
        "verified_example_framing",
        "scope_and_limitations",
    }


def test_schema_binds_fact_ids_enum_to_accepted_facts_only():
    schema = build_section_cluster_authoring_tool_schema(["F.1", "F.2"])
    params = schema["function"]["parameters"]

    assert schema["function"]["name"] == "submit_section_cluster"
    assert params["additionalProperties"] is False
    unit_schema = params["properties"]["units"]["items"]
    assert unit_schema["properties"]["fact_ids"]["items"]["enum"] == ["F.1", "F.2"]
    assert params["properties"]["units"]["maxItems"] == MAX_UNITS
    omitted_schema = params["properties"]["omitted"]["items"]
    assert omitted_schema["properties"]["fact_id"]["enum"] == ["F.1", "F.2"]


def test_schema_never_makes_a_do_not_claim_fact_citable():
    """The do_not_claim facts a caller knows about are never passed to the schema builder at
    all -- only accepted_fact_ids are. This test documents that contract at the call boundary."""

    accepted = ["F.CAP.01", "F.CAP.02"]
    do_not_claim = ["F.LIM.01"]

    schema = build_section_cluster_authoring_tool_schema(accepted)

    unit_fact_ids_schema = schema["function"]["parameters"]["properties"]["units"]["items"][
        "properties"
    ]["fact_ids"]["items"]
    enum_values = unit_fact_ids_schema["enum"]
    assert set(enum_values) == set(accepted)
    assert not set(enum_values) & set(do_not_claim)


def test_messages_are_system_then_user_and_never_leak_the_full_fact_corpus():
    messages = build_section_cluster_authoring_messages(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        public_product_name="Aspose.3D FOSS for Python",
        target_section_id="capability-overview",
        task_family="capability_entry_cluster",
        section_objective="Introduce the primary capabilities.",
        accepted_facts_json=json.dumps([{"fact_id": "F.CAP.01", "text": "Imports OBJ files."}]),
        do_not_claim_json=json.dumps([{"fact_id": "F.LIM.01", "text": "No COLLADA export."}]),
        seo_vocabulary_json=json.dumps(["3D file conversion"]),
        current_source_text="",
    )

    assert [message["role"] for message in messages] == ["system", "user"]
    user_content = messages[1]["content"]
    assert "F.CAP.01" in user_content
    assert "F.LIM.01" in user_content
    assert "capability-overview" in user_content
    assert "Aspose.3D FOSS for Python" in user_content
    # a full claim corpus / ProductFacts dump would carry many more fact IDs than this bounded
    # packet does -- this test only proves the exact packet content round-trips, not its size.


def test_repair_hint_slot_carries_correction_text_alongside_the_full_packet():
    messages = build_section_cluster_authoring_messages(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        public_product_name="Aspose.3D FOSS for Python",
        target_section_id="capability-overview",
        task_family="capability_entry_cluster",
        section_objective="Introduce the primary capabilities.",
        accepted_facts_json=json.dumps([{"fact_id": "F.CAP.01", "text": "Imports OBJ files."}]),
        do_not_claim_json=json.dumps([{"fact_id": "F.LIM.01", "text": "No COLLADA export."}]),
        seo_vocabulary_json=json.dumps(["3D file conversion"]),
        current_source_text="",
        repair_hint="Attempt 1 failed: unsupported fact_id ['F.DOES-NOT-EXIST'].",
    )

    user_content = messages[1]["content"]
    # a retry turn must never lose the original packet content the model needs to fix its
    # answer -- the repair hint is additive, not a replacement for the facts/objective/source
    assert "F.CAP.01" in user_content
    assert "F.LIM.01" in user_content
    assert "capability-overview" in user_content
    assert "unsupported fact_id" in user_content


def test_model_facing_fact_projection_keeps_semantics_but_hides_deterministic_literals():
    facts = build_product_facts_v2(
        field_values={
            "installation.verified_acquisition": {
                "method": "source_build",
                "outcome": "SOURCE_BUILD_VERIFIED",
                "coordinate": {"name": "aspose-3d-foss"},
                "source_revision": "a" * 40,
                "truth_eligible": True,
            }
        }
    )
    fact = facts.selected_fact("installation.verified_acquisition")
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="installation",
        task_family="installation_framing",
        section_objective="Frame source acquisition.",
        product_facts=facts,
        accepted_fact_ids=[fact.fact_id],
        protected_content=fingerprint_protected_content("# Example\n"),
    )

    projected = authoring_fact_prompt_payload(packet.accepted_facts[0])
    serialized = json.dumps(projected, sort_keys=True)

    assert '"acquisition_method": "source_build"' in serialized
    assert "registry_install_supported" not in serialized
    assert "aspose-3d-foss" not in serialized
    assert "a" * 40 not in serialized
    assert "protected_literals" not in serialized
    assert "location" not in serialized


def test_directional_format_fact_suppresses_ambiguous_capability_format_projection():
    facts = build_product_facts_v2(
        field_values={
            "product.capabilities": [
                "3D primitives including Box and Sphere",
                "File format import and export for OBJ, GLTF, STL, and 3MF",
                "Animation system with keyframe support",
            ]
        }
    )
    fact = facts.selected_fact("product.capabilities")
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="summary",
        task_family="opening_summary",
        section_objective="Introduce the product.",
        product_facts=facts,
        accepted_fact_ids=[fact.fact_id],
        protected_content=fingerprint_protected_content("# Example\n"),
    )

    projected = authoring_fact_prompt_payload(
        packet.accepted_facts[0],
        suppress_directionless_formats=True,
    )

    assert projected["value"] == [
        "3D primitives including Box and Sphere",
        "Animation system with keyframe support",
    ]

    directional_facts = build_product_facts_v2(
        field_values={"product.formats": ["Input format: OBJ", "Output format: GLTF"]}
    )
    directional = directional_facts.selected_fact("product.formats")
    hidden = authoring_fact_prompt_payload(
        build_section_authoring_packet(
            org_repo=facts.org_repo,
            source_revision="a" * 40,
            target_section_id="scope",
            task_family="scope_and_limitations",
            section_objective="State limitations.",
            product_facts=directional_facts,
            accepted_fact_ids=[directional.fact_id],
            protected_content=fingerprint_protected_content("# Example\n"),
        ).accepted_facts[0],
        suppress_directionless_formats=True,
    )
    assert hidden["value"] == {"reserved_for_deterministic_rendering": True}


def test_real_recorded_probe_response_requires_v2_heading_recovery_after_schema_parse():
    """The probe's own `section_cluster_schema` used a `sections` field with no disposition
    tracking; production's `submit_section_cluster` renames it to `units` and adds `omitted`.
    Adapting the recorded response's shape (never its content) proves a real model response at
    this bounded scale still parses. The tightened v2 public contract intentionally rejects its
    generic noun headings so the bounded recovery turn can replace them with action-led visitor
    search phrases."""

    payload = json.loads(_PROBE_FIXTURE.read_text(encoding="utf-8"))
    call_result = payload["call_result"]
    recorded_sections = call_result["parsed_arguments"]["sections"]
    # The probe's own bespoke fact-ID scheme (e.g. "F.3D.CAP.01") predates production's
    # descriptive_fact_id() lowercase convention and doesn't match FactRecordV2's fact_id
    # regex -- lowercased 1:1 below so this real recorded response can be replayed through a
    # real ProductFactsV2 fixture; only the ID casing changes, never the cited content.
    lower = str.lower
    # The probe authorized all 8 facts for one evaluation-scale call; production's packet is
    # capped at 4 accepted facts, so this test narrows to the 3 facts the recording actually
    # cited (evaluation.fact_ids_used) -- a within-cap slice of the same real response, not a
    # rewritten one. The 5 never-cited facts still round-trip as do_not_claim context.
    accepted_fact_ids = [lower(fact_id) for fact_id in payload["evaluation"]["fact_ids_used"]]
    all_authorized_ids = [lower(fact_id) for fact_id in call_result["authorized_fact_ids"]]
    do_not_claim_fact_ids = [
        fact_id for fact_id in all_authorized_ids if fact_id not in accepted_fact_ids
    ]
    assert 1 <= len(accepted_fact_ids) <= 4
    assert do_not_claim_fact_ids  # proves this fixture actually exercises do_not_claim context

    adapted = {
        "units": [
            {
                "heading": s["heading"],
                "text": s["text"],
                "fact_ids": [lower(fact_id) for fact_id in s["fact_ids"]],
            }
            for s in recorded_sections
            if {lower(fact_id) for fact_id in s["fact_ids"]} <= set(accepted_fact_ids)
        ],
        "omitted": [],
    }

    result = SectionClusterAuthoringResultV1.model_validate(adapted)

    product_facts = build_product_facts_v2(
        extra_facts=[
            build_fact(fact_id, "product.capabilities", f"Capability {fact_id}.")
            for fact_id in all_authorized_ids
        ]
    )
    packet = build_section_authoring_packet(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        source_revision="a" * 40,
        target_section_id="overview-capabilities",
        task_family="capability_entry_cluster",
        section_objective="Introduce the primary capabilities.",
        product_facts=product_facts,
        accepted_fact_ids=accepted_fact_ids,
        do_not_claim_fact_ids=do_not_claim_fact_ids,
        protected_content=fingerprint_protected_content("# Example\n"),
    )

    with pytest.raises(
        SectionAuthoringAcceptanceError,
        match=(
            "action-led|unsupported quality, completeness, guarantee|"
            "recognized file formats are absent"
        ),
    ):
        _validate_acceptance(packet, result)
