"""Bounded authoring: acceptance gates, up to two semantic repairs, and zero-call cache."""

import json
from pathlib import Path

import pytest
from section_authoring_test_support import build_fact, build_product_facts_v2

from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.llm import verifier_client
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.call_ledger import (
    bind_llm_repository_revision,
    current_llm_call_context,
    load_llm_call_records,
    reset_llm_call_accounting,
    start_llm_call_accounting,
)
from readme_agent.llm.schema import LLMResponseMeta, Usage
from readme_agent.llm.section_author_client import LiveSectionClusterAuthorClient
from readme_agent.specialists.section_authoring_packet import build_section_authoring_packet
from readme_agent.specialists.section_cluster_authoring import (
    SectionAuthoringAcceptanceError,
    execute_section_cluster_authoring,
)

PROTECTED = fingerprint_protected_content("# Example\n\nA focused library.\n")

CAP_1 = "product.capabilities:fixture"
CAP_2 = "product.capabilities:secondary"
LIM_1 = "product.limitations:fixture"
UNKNOWN_FACT_ID = "does.not.exist:fixture"


def _product_facts(org_repo: str = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"):
    return build_product_facts_v2(
        org_repo=org_repo,
        field_values={
            "product.capabilities": "Import and export OBJ files.",
            "product.limitations": "COLLADA export is not implemented.",
        },
        extra_facts=[
            build_fact(CAP_2, "product.capabilities", "Import and export GLTF files."),
        ],
    )


def _packet(*, org_repo: str = "aspose-3d-foss/Aspose.3D-FOSS-for-Python", product_facts=None):
    return build_section_authoring_packet(
        org_repo=org_repo,
        source_revision="a" * 40,
        target_section_id="capability-overview",
        task_family="capability_entry_cluster",
        section_objective="Introduce the primary import/export capabilities.",
        product_facts=product_facts or _product_facts(org_repo=org_repo),
        accepted_fact_ids=[CAP_1, CAP_2],
        do_not_claim_fact_ids=[LIM_1],
        protected_content=PROTECTED,
    )


def _installation_packet():
    facts = build_product_facts_v2(
        field_values={
            "installation.verified_acquisition": {
                "method": "source_build",
                "outcome": "SOURCE_BUILD_VERIFIED",
                "coordinate": {"name": "aspose-3d-foss"},
                "truth_eligible": True,
            },
            "installation.coordinates": [
                {
                    "ecosystem": "python",
                    "manifest_path": "setup.py",
                    "name": "aspose-3d-foss",
                    "version": "26.1.0",
                }
            ],
            "product.compatibility": [{"runtime_label": "Python", "minimum_runtime": ">=3.7"}],
        }
    )
    fact_ids = [
        facts.selected_fact_ids[field]
        for field in (
            "installation.verified_acquisition",
            "installation.coordinates",
            "product.compatibility",
        )
    ]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="installation",
        task_family="installation_framing",
        section_objective="Frame source acquisition without spelling deterministic literals.",
        product_facts=facts,
        accepted_fact_ids=fact_ids,
        protected_content=PROTECTED,
    )
    return packet, fact_ids


class FakeSectionAuthorClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[dict] = []

    def analyze_section_cluster(self, messages, accepted_fact_ids):
        index = len(self.calls)
        self.calls.append({"messages": messages, "accepted_fact_ids": list(accepted_fact_ids)})
        parsed = self._responses[index]
        return AnalysisResult(
            parsed=parsed,
            meta=LLMResponseMeta(
                request_id=f"req-{index}",
                model="qwen3-next",
                usage=Usage(prompt_tokens=100, completion_tokens=50),
                latency_ms=1234.0,
            ),
        )


def _valid_response() -> dict:
    return {
        "units": [
            {
                "heading": "Import and Export 3D Content",
                "text": "Exchange OBJ and GLTF assets through a focused Python API.",
                "fact_ids": [CAP_1, CAP_2],
            }
        ],
        "omitted": [],
    }


def test_accepts_a_valid_response_on_the_first_attempt():
    packet = _packet()
    client = FakeSectionAuthorClient([_valid_response()])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert len(client.calls) == 1
    assert outcome.reused_from_cache is False
    assert outcome.receipt.semantic_retry_used is False
    assert outcome.receipt.logical_call_count == 1
    assert client.calls[0]["accepted_fact_ids"] == ["F1", "F2"]
    assert {fact_id for unit in outcome.result.units for fact_id in unit.fact_ids} == {
        CAP_1,
        CAP_2,
    }
    assert outcome.receipt.token_usage[0].prompt_tokens == 100
    assert outcome.receipt.latency_ms[0] == 1234.0


def test_define_is_a_concrete_action_led_capability_heading():
    packet = _packet()
    response = _valid_response()
    response["units"][0]["heading"] = "Define Animations With Keyframes"
    client = FakeSectionAuthorClient([response])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.result.units[0].heading == "Define Animations With Keyframes"


@pytest.mark.parametrize(
    "heading",
    [
        "Construct Mesh Geometry Primitives",
        "Model Geometry and Materials",
        "Perform Vector Math Operations",
        "Assign Materials to 3D Objects",
    ],
)
def test_concrete_developer_actions_are_action_led_capability_headings(heading):
    packet = _packet()
    response = _valid_response()
    response["units"][0]["heading"] = heading
    client = FakeSectionAuthorClient([response])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.result.units[0].heading == heading
    assert outcome.receipt.semantic_retry_used is False


def test_animate_is_a_concrete_action_led_capability_heading():
    packet = _packet()
    response = _valid_response()
    response["units"][0]["heading"] = "Animate Scenes With Keyframes"
    client = FakeSectionAuthorClient([response])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is False


def test_unsupported_fact_id_triggers_one_semantic_retry_then_succeeds():
    packet = _packet()
    client = FakeSectionAuthorClient(
        [
            {
                "units": [
                    {
                        "heading": "Overview",
                        "text": "Overreaching claim.",
                        "fact_ids": [CAP_1],
                    }
                ],
                "omitted": [{"fact_id": UNKNOWN_FACT_ID, "reason": "not relevant"}],
            },
            _valid_response(),
        ]
    )

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert len(client.calls) == 2
    assert outcome.receipt.semantic_retry_used is True
    assert outcome.receipt.logical_call_count == 2
    # the retry turn adds a repair hint on top of the full original packet content -- never
    # in place of it, or the model would be asked to fix facts it can no longer see
    retry_messages = client.calls[1]["messages"]
    assert retry_messages[0]["role"] == "system"
    assert retry_messages[1]["role"] == "user"
    retry_content = retry_messages[1]["content"]
    assert "acceptance" in retry_content.casefold()
    assert '"fact_id":"F1"' in retry_content
    assert '"fact_id":"F2"' in retry_content
    assert '"fact_id":"N1"' in retry_content  # do_not_claim context also survives the retry
    assert CAP_1 not in retry_content
    assert CAP_2 not in retry_content
    assert LIM_1 not in retry_content


class _TruncatingThenValidClient:
    """RDM-033: a forced tool call cut off mid-JSON (finish_reason == 'length') must
    retry through this module's own same-cluster correction loop, asking the model to
    be more concise -- not crash the whole cluster on the first truncation."""

    def __init__(self, *, truncate_calls: int, final_response: dict):
        self._truncate_calls = truncate_calls
        self._final_response = final_response
        self.calls: list[dict] = []

    def analyze_section_cluster(self, messages, accepted_fact_ids):
        index = len(self.calls)
        self.calls.append({"messages": messages, "accepted_fact_ids": list(accepted_fact_ids)})
        if index < self._truncate_calls:
            raise verifier_client.LLMTruncatedResponseError(
                "forced tool call response was truncated: Expecting ',' delimiter",
                finish_reason="length",
                completion_tokens=2048,
            )
        return AnalysisResult(
            parsed=self._final_response,
            meta=LLMResponseMeta(
                request_id=f"req-{index}",
                model="qwen3-next",
                usage=Usage(prompt_tokens=100, completion_tokens=50),
                latency_ms=1234.0,
            ),
        )


def test_truncated_response_triggers_a_concise_retry_then_succeeds():
    packet = _packet()
    client = _TruncatingThenValidClient(truncate_calls=1, final_response=_valid_response())

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert len(client.calls) == 2
    assert outcome.receipt.semantic_retry_used is True
    assert outcome.receipt.logical_call_count == 2
    retry_content = client.calls[1]["messages"][1]["content"]
    assert "cut off" in retry_content.casefold()
    assert "concisely" in retry_content.casefold()
    # the retry still carries the full original packet content, not a lossy summary
    assert '"fact_id":"F1"' in retry_content
    assert '"fact_id":"F2"' in retry_content


def test_truncated_response_exhausts_retries_and_fails_closed():
    packet = _packet()
    client = _TruncatingThenValidClient(truncate_calls=3, final_response=_valid_response())

    with pytest.raises(SectionAuthoringAcceptanceError, match="failed acceptance"):
        execute_section_cluster_authoring(packet=packet, client=client)

    assert len(client.calls) == 3


def test_internal_verification_narration_triggers_targeted_recovery():
    packet = _packet()
    internal = _valid_response()
    internal["units"][0]["text"] = (
        "This package was checked at the exact source revision in an isolated "
        "verification environment."
    )
    client = FakeSectionAuthorClient([internal, _valid_response()])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert len(client.calls) == 2
    assert outcome.receipt.semantic_retry_used is True
    assert "internal verification narration" in client.calls[1]["messages"][1]["content"]


def test_capability_body_that_repeats_heading_triggers_targeted_recovery():
    packet = _packet()
    repeated = _valid_response()
    repeated["units"][0]["heading"] = "Create 3D Primitives"
    repeated["units"][0]["text"] = "Create 3D primitives."
    client = FakeSectionAuthorClient([repeated, _valid_response()])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    assert "repeat their headings" in client.calls[1]["messages"][1]["content"]


def test_capability_body_may_repeat_heading_terms_when_it_adds_visitor_detail():
    packet = _packet()
    detailed = _valid_response()
    detailed["units"][0]["heading"] = "Import and Export 3D Content"
    detailed["units"][0]["text"] = (
        "Import and export 3D content by exchanging OBJ and GLTF assets through a focused "
        "Python API."
    )
    client = FakeSectionAuthorClient([detailed])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is False
    assert len(client.calls) == 1


def test_unsupported_quality_and_dependency_positioning_triggers_targeted_recovery():
    packet = _packet()
    inflated = _valid_response()
    inflated["units"][0]["text"] = "Use a reliable and rapid API without external dependencies."
    client = FakeSectionAuthorClient([inflated, _valid_response()])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    repair = client.calls[1]["messages"][1]["content"]
    assert "unsupported quality, completeness, guarantee" in repair
    assert "End each sentence immediately after the behavior" in repair


@pytest.mark.parametrize("wording", ["smallest possible", "simplest possible"])
def test_closed_list_superlative_is_removed_without_repeating_provider_call(wording):
    packet = _packet()
    response = _valid_response()
    response["units"][0]["text"] = (
        f"Exchange OBJ and GLTF assets through the {wording} focused Python API."
    )
    client = FakeSectionAuthorClient([response])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert len(client.calls) == 1
    assert wording not in outcome.result.units[0].text.casefold()
    assert outcome.receipt.semantic_retry_used is False


@pytest.mark.parametrize(
    "wording",
    [
        "This is the fully implemented workflow.",
        "Build from source to ensure compatibility.",
        "Create scenes without external assets.",
        "This is the only supported acquisition path.",
        "Use this runtime, requiring only a compatible environment.",
    ],
)
def test_unsupported_guarantees_and_absolutes_trigger_recovery(wording):
    packet = _packet()
    inflated = _valid_response()
    inflated["units"][0]["text"] = wording
    client = FakeSectionAuthorClient([inflated, _valid_response()])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True


def test_positive_format_inventory_cannot_become_a_closed_world_denial():
    facts = build_product_facts_v2(field_values={"product.formats": ["OBJ", "GLTF", "STL", "3MF"]})
    fact_id = facts.selected_fact_ids["product.formats"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="scope_and_limitations",
        task_family="scope_and_limitations",
        section_objective="State supported formats.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "Use Supported Formats",
                "text": "The library does not support other formats beyond OBJ and GLTF.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Use Supported Formats",
                "text": "The library supports OBJ, GLTF, STL, and 3MF formats.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    assert "closed-world denials" in client.calls[1]["messages"][1]["content"]


def test_example_framing_cannot_invent_operations_absent_from_exact_code():
    facts = build_product_facts_v2(
        field_values={
            "example.minimal": {
                "language": "python",
                "class_name": "Scene",
                "code": "from aspose.threed import Scene\n\nscene = Scene()\n",
            }
        }
    )
    fact_id = facts.selected_fact_ids["example.minimal"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="quick_start",
        task_family="verified_example_framing",
        section_objective="Explain the introductory example.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "Create a 3D Scene",
                "text": "The example adds a shape and saves the scene to a file.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Create a 3D Scene",
                "text": "The example instantiates one public API object.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    repair = client.calls[1]["messages"][1]["content"]
    assert "does not execute the claimed" in repair


def test_product_identity_spelling_must_match_public_name_exactly():
    facts = build_product_facts_v2(
        field_values={
            "product.identity": {
                "product_name": "Aspose.3D",
                "family": "3d",
                "platform": "python",
                "ecosystem": "python",
            }
        }
    )
    fact_id = facts.selected_fact_ids["product.identity"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="summary",
        task_family="opening_summary",
        section_objective="Introduce the product.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "Python Library",
                "text": "Aspose.3D-FOSS for Python processes 3D content.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Python Library",
                "text": "Aspose.3D FOSS for Python is a Python library.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    assert "preserve exact public name" in client.calls[1]["messages"][1]["content"]
    assert "Replace the product spelling" in client.calls[1]["messages"][1]["content"]


@pytest.mark.parametrize(
    "invalid_text",
    [
        "Aspose 3D FOSS for Python processes 3D content.",
        "The Aspose product processes 3D content.",
        "Aspose.3D FOSS for python processes 3D content.",
    ],
)
def test_every_aspose_mention_requires_the_exact_public_product_name(invalid_text):
    facts = build_product_facts_v2(
        field_values={
            "product.identity": {
                "product_name": "Aspose.3D",
                "family": "3d",
                "platform": "python",
                "ecosystem": "python",
            }
        }
    )
    fact_id = facts.selected_fact_ids["product.identity"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="summary",
        task_family="opening_summary",
        section_objective="Introduce the product.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "Python Library",
                "text": invalid_text,
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Python Library",
                "text": "Aspose.3D FOSS for Python is a Python library.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    assert "preserve exact public name" in client.calls[1]["messages"][1]["content"]


@pytest.mark.parametrize(
    "invalid_text",
    [
        "Aspose.3D FOSS for Python uses corrupted punctuation\ufffd here.",
        "Aspose.3D FOSS for Python supports meshes\u00e2\u20ac\u201dincluding primitives.",
        "Aspose.3D FOSS for Python has an \u00c3encoded word.",
    ],
)
def test_public_authoring_rejects_replacement_characters_and_mojibake(invalid_text):
    facts = build_product_facts_v2()
    fact_id = facts.selected_fact_ids["product.identity"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="summary",
        task_family="opening_summary",
        section_objective="Introduce the product.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "Python Library",
                "text": invalid_text,
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Python Library",
                "text": "Aspose.3D FOSS for Python is a Python library.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    repair = client.calls[1]["messages"][1]["content"]
    assert "UTF-8 mojibake" in repair
    assert "ordinary UTF-8 punctuation" in repair


def test_recognized_format_absent_from_cited_facts_triggers_same_cluster_recovery():
    facts = build_product_facts_v2(field_values={"product.formats": ["OBJ", "GLTF", "STL", "3MF"]})
    fact_id = facts.selected_fact_ids["product.formats"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="summary",
        task_family="opening_summary",
        section_objective="Summarize supported formats.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "Work With 3D Content",
                "text": "Work with OBJ and PDF content.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Work With 3D Content",
                "text": "Work with OBJ and GLTF content.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    repair = client.calls[1]["messages"][1]["content"]
    assert "recognized file formats are absent from cited accepted facts" in repair


def test_identity_only_summary_cannot_authorize_capability_operations():
    facts = build_product_facts_v2()
    fact_id = facts.selected_fact_ids["product.identity"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="summary",
        task_family="opening_summary",
        section_objective="Introduce the product.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "Python Library",
                "text": ("Aspose.3D FOSS for Python imports, exports, and manipulates 3D scenes."),
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Python Library",
                "text": "Aspose.3D FOSS for Python is a Python library.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    repair = client.calls[1]["messages"][1]["content"]
    assert "cited accepted facts do not authorize operations" in repair


def test_relationship_fact_cannot_authorize_unrelated_scope_operations():
    facts = build_product_facts_v2(
        field_values={
            "relationship.commercial_foss": [
                "open_source_scope",
                "commercial_upgrade_path",
            ]
        }
    )
    fact_id = facts.selected_fact_ids["relationship.commercial_foss"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="scope_and_limitations",
        task_family="scope_and_limitations",
        section_objective="State the open-source and commercial relationship.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "Create and Edit 3D Scenes",
                "text": ("Load and save scenes before choosing the commercial upgrade path."),
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Choose the Appropriate Edition",
                "text": (
                    "The FOSS project has an open-source scope and a separate commercial "
                    "upgrade path."
                ),
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    repair = client.calls[1]["messages"][1]["content"]
    assert "cited accepted facts do not authorize operations" in repair


def test_directional_format_fact_blocks_unsupported_output_claim():
    facts = build_product_facts_v2(
        field_values={
            "product.capabilities": ["File format import and export for OBJ, GLTF, STL, and 3MF"],
            "product.formats": [
                "Input format: OBJ",
                "Input format: GLTF",
                "Output format: GLTF",
                "Input format: STL",
                "Output format: STL",
                "Input format: 3MF",
                "Output format: 3MF",
            ],
        }
    )
    capability_id = facts.selected_fact_ids["product.capabilities"]
    formats_id = facts.selected_fact_ids["product.formats"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="summary",
        task_family="opening_summary",
        section_objective="Summarize format support.",
        product_facts=facts,
        accepted_fact_ids=[capability_id, formats_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "3D File Formats",
                "text": "Read and write OBJ, GLTF, STL, and 3MF files.",
                "fact_ids": [capability_id, formats_id],
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "3D File Formats",
                "text": ("Import OBJ, GLTF, STL, and 3MF files. Export GLTF, STL, and 3MF files."),
                "fact_ids": [capability_id, formats_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    repair = client.calls[1]["messages"][1]["content"]
    assert "OBJ does not have cited direction support for ['output']" in repair
    assert "separate input and output statements" in repair


def test_reserved_directional_unit_is_removed_without_reauthoring_valid_siblings():
    facts = build_product_facts_v2(
        field_values={
            "product.limitations": [
                "Inspect mesh geometry; mesh boolean operations are not implemented."
            ],
            "product.formats": ["Input format: OBJ", "Output format: GLTF"],
            "relationship.commercial_foss": [
                "open_source_scope",
                "commercial_upgrade_path",
            ],
        }
    )
    limitations_id = facts.selected_fact_ids["product.limitations"]
    formats_id = facts.selected_fact_ids["product.formats"]
    relationship_id = facts.selected_fact_ids["relationship.commercial_foss"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="scope_and_limitations",
        task_family="scope_and_limitations",
        section_objective="State practical limitations.",
        product_facts=facts,
        accepted_fact_ids=[limitations_id, relationship_id],
        do_not_claim_fact_ids=[formats_id],
        protected_content=PROTECTED,
    )
    response = {
        "units": [
            {
                "heading": "Inspect Mesh Geometry",
                "text": "Mesh boolean operations are not implemented.",
                "fact_ids": [limitations_id],
            },
            {
                "heading": "Export Scenes",
                "text": "Export scenes to DAE files.",
                "fact_ids": [relationship_id],
            },
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([response])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is False
    assert [unit.heading for unit in outcome.result.units] == ["Inspect Mesh Geometry"]
    assert len(outcome.receipt.deterministically_rejected_unit_sha256) == 1
    assert outcome.receipt.deterministically_omitted_fact_ids == (relationship_id,)
    assert outcome.result.omitted[0].fact_id == relationship_id


def test_all_reserved_directional_units_are_omitted_without_provider_retry():
    facts = build_product_facts_v2(
        field_values={
            "product.formats": ["Input format: OBJ", "Output format: GLTF"],
            "relationship.commercial_foss": [
                "open_source_scope",
                "commercial_upgrade_path",
            ],
        }
    )
    formats_id = facts.selected_fact_ids["product.formats"]
    relationship_id = facts.selected_fact_ids["relationship.commercial_foss"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="scope_and_limitations",
        task_family="scope_and_limitations",
        section_objective="State the open-source and commercial relationship.",
        product_facts=facts,
        accepted_fact_ids=[relationship_id],
        do_not_claim_fact_ids=[formats_id],
        protected_content=PROTECTED,
    )
    response = {
        "units": [
            {
                "heading": "Export Scenes",
                "text": "Export scenes to DAE files.",
                "fact_ids": [relationship_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([response])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is False
    assert outcome.result.units == ()
    assert outcome.receipt.deterministically_omitted_fact_ids == (relationship_id,)
    assert outcome.result.omitted[0].fact_id == relationship_id
    assert len(client.calls) == 1


def test_directional_format_prose_gets_deterministic_directional_fact_provenance():
    facts = build_product_facts_v2(
        field_values={
            "product.capabilities": ["File format import for OBJ and GLTF"],
            "product.formats": ["Input format: OBJ", "Input format: GLTF"],
        }
    )
    capability_id = facts.selected_fact_ids["product.capabilities"]
    formats_id = facts.selected_fact_ids["product.formats"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="summary",
        task_family="opening_summary",
        section_objective="Summarize format support.",
        product_facts=facts,
        accepted_fact_ids=[capability_id, formats_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "3D File Formats",
                "text": "Import OBJ and GLTF files.",
                "fact_ids": [capability_id],
            }
        ],
        "omitted": [{"fact_id": formats_id, "reason": "not cited"}],
    }
    client = FakeSectionAuthorClient([invalid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is False
    assert outcome.result.units[0].fact_ids == (capability_id, formats_id)
    assert outcome.result.omitted == ()


@pytest.mark.parametrize(
    "invalid_text",
    [
        "The example opens a 3D file and converts its scene.",
        "The example deletes nodes and renders an image.",
    ],
)
def test_example_action_must_be_demonstrated_by_cited_code(invalid_text):
    facts = build_product_facts_v2(
        field_values={
            "example.minimal": {
                "language": "python",
                "code": "scene = Scene()",
                "class_name": "Scene",
            }
        }
    )
    fact_id = facts.selected_fact_ids["example.minimal"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="quick_start",
        task_family="verified_example_framing",
        section_objective="Explain the introductory example.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "Start With the API",
                "text": invalid_text,
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Start With the API",
                "text": "The example instantiates one public API object.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    repair = client.calls[1]["messages"][1]["content"]
    assert "does not execute the claimed" in repair


def test_example_editorial_predicate_is_not_mistaken_for_an_executed_operation():
    facts = build_product_facts_v2(
        field_values={
            "example.minimal": {
                "language": "python",
                "code": "scene = Scene()",
                "class_name": "Scene",
            }
        }
    )
    fact_id = facts.selected_fact_ids["example.minimal"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="quick_start",
        task_family="verified_example_framing",
        section_objective="Explain the introductory example.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    response = {
        "units": [
            {
                "heading": "Instantiate a Scene Object",
                "text": (
                    "The example instantiates one public API object and provides a concise "
                    "starting point."
                ),
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([response])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is False


def test_independent_sibling_capabilities_cannot_be_fused_into_one_unit():
    facts = build_product_facts_v2(
        field_values={
            "product.capabilities": [
                "3D primitives including Box and Sphere",
                "File format import and export for OBJ, GLTF, STL, and 3MF",
                "Animation system with keyframe support",
            ]
        }
    )
    fact_id = facts.selected_fact_ids["product.capabilities"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="key_capabilities",
        task_family="capability_entry_cluster",
        section_objective="Describe distinct capabilities.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    conflated = {
        "units": [
            {
                "heading": "Define and Export Animations",
                "text": "Build keyframe animations and export them to GLTF, STL, and 3MF.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    separated = {
        "units": [
            {
                "heading": "Create 3D Primitives",
                "text": "Construct Box and Sphere geometry for scenes.",
                "fact_ids": ["F1"],
            },
            {
                "heading": "Import and Export 3D Files",
                "text": "Exchange OBJ, GLTF, STL, and 3MF assets.",
                "fact_ids": ["F2"],
            },
            {
                "heading": "Define Keyframe Animations",
                "text": "Control scene changes over time with keyframes.",
                "fact_ids": ["F3"],
            },
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([conflated, separated])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    assert client.calls[1]["accepted_fact_ids"] == ["F1", "F2", "F3"]
    assert all(unit.fact_ids == (fact_id,) for unit in outcome.result.units)
    assert "combines 2 independent sibling items" in client.calls[1]["messages"][1]["content"]
    assert (
        "Each unit must describe exactly one sibling item"
        in client.calls[1]["messages"][1]["content"]
    )


def test_itemized_capability_recovery_accepts_explicit_editorial_omission():
    facts = build_product_facts_v2(
        field_values={"product.capabilities": ["Create meshes", "Animate scenes", "Add lights"]}
    )
    fact_id = facts.selected_fact_ids["product.capabilities"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="key_capabilities",
        task_family="capability_entry_cluster",
        section_objective="Describe selected capabilities.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    conflated = {
        "units": [
            {
                "heading": "Create and Animate Scenes",
                "text": "Build meshes and animate them over time.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    curated = {
        "units": [
            {
                "heading": "Create Mesh Geometry",
                "text": "Build mesh objects for a scene graph.",
                "fact_ids": ["F1"],
            },
            {
                "heading": "Animate Scene Content",
                "text": "Control scene changes over time.",
                "fact_ids": ["F2"],
            },
        ],
        "omitted": [{"fact_id": "F3", "reason": "Lower-priority supporting capability."}],
    }

    outcome = execute_section_cluster_authoring(
        packet=packet,
        client=FakeSectionAuthorClient([conflated, curated]),
    )

    assert len(outcome.result.units) == 2
    assert outcome.result.omitted == ()
    assert all(unit.fact_ids == (fact_id,) for unit in outcome.result.units)


def test_opening_summary_may_synthesize_multiple_verified_capabilities():
    facts = build_product_facts_v2(
        field_values={
            "product.capabilities": [
                "Create 3D primitives",
                "Import and export 3D formats",
                "Define keyframe animations",
            ]
        }
    )
    fact_id = facts.selected_fact_ids["product.capabilities"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="summary",
        task_family="opening_summary",
        section_objective="Summarize the product.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    synthesized = {
        "units": [
            {
                "heading": "Work With 3D Content",
                "text": "Create primitives, exchange 3D formats, and define keyframe animations.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([synthesized])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is False


def test_live_internal_assurance_wording_triggers_targeted_recovery():
    packet, fact_ids = _installation_packet()
    invalid = {
        "units": [
            {
                "heading": "Install From Source",
                "text": (
                    "The package was verified by source build in an isolated Python "
                    "environment, and its public imports and example execution were confirmed."
                ),
                "fact_ids": fact_ids,
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Install From Source",
                "text": (
                    "Build and install the library from source for its supported Python runtime."
                ),
                "fact_ids": fact_ids,
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    assert len(client.calls) == 2
    assert "internal verification narration" in client.calls[1]["messages"][1]["content"]


def test_internal_deterministic_ownership_narration_triggers_targeted_recovery():
    facts = build_product_facts_v2(
        field_values={"product.limitations": ["Scene rendering is not implemented."]}
    )
    fact_id = facts.selected_fact_ids["product.limitations"]
    packet = build_section_authoring_packet(
        org_repo=facts.org_repo,
        source_revision="a" * 40,
        target_section_id="scope_and_limitations",
        task_family="scope_and_limitations",
        section_objective="State practical limitations.",
        product_facts=facts,
        accepted_fact_ids=[fact_id],
        protected_content=PROTECTED,
    )
    invalid = {
        "units": [
            {
                "heading": "Render Scenes",
                "text": (
                    "Scene rendering is not implemented and is reserved for deterministic "
                    "internal use."
                ),
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Render Scenes",
                "text": "Scene rendering is not implemented.",
                "fact_ids": [fact_id],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    assert "Remove the verification method" in client.calls[1]["messages"][1]["content"]


def test_source_build_cannot_authorize_pypi_publication_and_recovers_only_cluster():
    packet, fact_ids = _installation_packet()
    invalid = {
        "units": [
            {
                "heading": "Install the Package",
                "text": "Install the aspose-3d-foss package from PyPI.",
                "fact_ids": fact_ids,
            }
        ],
        "omitted": [],
    }
    valid = {
        "units": [
            {
                "heading": "Install From Source",
                "text": "Build and install the library from source for Python projects.",
                "fact_ids": fact_ids,
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, valid])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is True
    assert len(client.calls) == 2
    repair = client.calls[1]["messages"][1]["content"]
    assert "source-build acquisition cannot authorize" in repair
    assert "belongs to deterministic rendering" in repair


@pytest.mark.parametrize(
    "text",
    [
        "The aspose-3d-foss package is published under this distribution name.",
        "Use version 26.1.0 from setup.py.",
        "The package is not published to public Python package registries.",
    ],
)
def test_installation_literals_and_unproved_publication_fail_closed_after_retry(text):
    packet, fact_ids = _installation_packet()
    invalid = {
        "units": [{"heading": "Install", "text": text, "fact_ids": fact_ids}],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([invalid, invalid, invalid])

    with pytest.raises(SectionAuthoringAcceptanceError, match="structured fact coordinates"):
        execute_section_cluster_authoring(packet=packet, client=client)

    assert len(client.calls) == 3


def test_do_not_claim_fact_id_cannot_authorize_positive_prose():
    packet = _packet()
    forbidden = {
        "units": [
            {
                "heading": "Overview",
                "text": "Also supports COLLADA export.",
                "fact_ids": [CAP_1, LIM_1],
            }
        ],
        "omitted": [{"fact_id": CAP_2, "reason": "not covered in this cluster"}],
    }
    client = FakeSectionAuthorClient([forbidden, forbidden, forbidden])

    with pytest.raises(SectionAuthoringAcceptanceError, match="do_not_claim"):
        execute_section_cluster_authoring(packet=packet, client=client)

    assert len(client.calls) == 3  # one normal attempt + two exhausted semantic retries


def test_undisposed_accepted_fact_is_rejected():
    packet = _packet()
    incomplete = {
        "units": [{"heading": "Overview", "text": "Imports OBJ files.", "fact_ids": [CAP_1]}],
        "omitted": [],  # CAP_2 neither cited nor omitted
    }
    client = FakeSectionAuthorClient([incomplete, incomplete, incomplete])

    with pytest.raises(SectionAuthoringAcceptanceError, match="neither used nor omitted"):
        execute_section_cluster_authoring(packet=packet, client=client)

    assert "Do not leave any missing alias undisposed" in client.calls[1]["messages"][1]["content"]


def test_fact_both_cited_and_omitted_keeps_validated_use_without_retry():
    packet = _packet()
    contradictory = {
        "units": [
            {
                "heading": "Import and Export 3D Content",
                "text": "Exchange OBJ and GLTF assets through a focused Python API.",
                "fact_ids": [CAP_1, CAP_2],
            }
        ],
        "omitted": [{"fact_id": CAP_2, "reason": "also omitted, contradictorily"}],
    }
    client = FakeSectionAuthorClient([contradictory])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert len(client.calls) == 1
    assert outcome.result.units[0].fact_ids == (CAP_1, CAP_2)
    assert outcome.result.omitted == ()


def test_uncited_omission_is_preserved_during_fact_disposition_reconciliation():
    packet = _packet()
    result = {
        "units": [
            {
                "heading": "Import OBJ Content",
                "text": "Open OBJ assets through the Python API.",
                "fact_ids": [CAP_1],
            }
        ],
        "omitted": [{"fact_id": CAP_2, "reason": "not relevant to this section"}],
    }
    client = FakeSectionAuthorClient([result])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert len(client.calls) == 1
    assert outcome.result.omitted[0].fact_id == CAP_2


def test_authored_code_fence_is_rejected_because_deterministic_code_owns_examples():
    packet = _packet()
    with_code = {
        "units": [
            {
                "heading": "Overview",
                "text": "Install it:\n```bash\npip install aspose-3d\n```",
                "fact_ids": [CAP_1, CAP_2],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([with_code, with_code, with_code])

    with pytest.raises(SectionAuthoringAcceptanceError, match="code block or command"):
        execute_section_cluster_authoring(packet=packet, client=client)


def test_authored_command_line_is_rejected():
    packet = _packet()
    with_command = {
        "units": [
            {
                "heading": "Installation",
                "text": "pip install aspose-3d-foss to get started.",
                "fact_ids": [CAP_1, CAP_2],
            }
        ],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([with_command, with_command, with_command])

    with pytest.raises(SectionAuthoringAcceptanceError, match="code block or command"):
        execute_section_cluster_authoring(packet=packet, client=client)


def test_exhausting_semantic_recovery_raises_after_exactly_three_calls():
    packet = _packet()
    always_bad = {
        "units": [{"heading": "Overview", "text": "x", "fact_ids": [CAP_1]}],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([always_bad, always_bad, always_bad])

    with pytest.raises(SectionAuthoringAcceptanceError, match="failed acceptance"):
        execute_section_cluster_authoring(packet=packet, client=client)

    assert len(client.calls) == 3


def test_accepted_section_cache_hit_makes_zero_provider_calls(tmp_path):
    packet = _packet()
    client = FakeSectionAuthorClient([_valid_response()])

    first = execute_section_cluster_authoring(packet=packet, client=client, cache_dir=tmp_path)
    assert len(client.calls) == 1
    assert first.reused_from_cache is False

    exhausting_client = FakeSectionAuthorClient([])  # any call would IndexError
    second = execute_section_cluster_authoring(
        packet=packet, client=exhausting_client, cache_dir=tmp_path
    )

    assert exhausting_client.calls == []
    assert second.reused_from_cache is True
    assert second.result == first.result


def test_accepted_section_cache_hit_is_recorded_in_central_ledger(tmp_path, monkeypatch):
    monkeypatch.setenv("README_AGENT_RUNS_DIR", str(tmp_path / "runs"))
    packet = _packet()
    execute_section_cluster_authoring(
        packet=packet,
        client=FakeSectionAuthorClient([_valid_response()]),
        cache_dir=tmp_path / "cache",
    )
    start_llm_call_accounting(packet.org_repo, "cache-reuse-test")
    bind_llm_repository_revision(packet.source_revision, stage="README_PROCESSING")
    try:
        execute_section_cluster_authoring(
            packet=packet,
            client=FakeSectionAuthorClient([]),
            cache_dir=tmp_path / "cache",
        )
        context = current_llm_call_context()
        assert context is not None
        records = load_llm_call_records(Path(context.ledger_path))
    finally:
        reset_llm_call_accounting()

    assert len(records) == 1
    assert records[0].job == "section_cluster_authoring"
    assert records[0].disposition == "cache_reuse"
    assert records[0].outcome == "cache_reuse"


def test_a_failed_section_retries_only_that_section_never_writes_a_cache_entry(tmp_path):
    packet = _packet()
    always_bad = {
        "units": [{"heading": "Overview", "text": "x", "fact_ids": [CAP_1]}],
        "omitted": [],
    }
    client = FakeSectionAuthorClient([always_bad, always_bad, always_bad])

    with pytest.raises(SectionAuthoringAcceptanceError):
        execute_section_cluster_authoring(packet=packet, client=client, cache_dir=tmp_path)

    assert not (tmp_path / f"{packet.target_section_id}.json").exists()

    # a fresh attempt against the same section, uncached, is what "retry only that section" means
    retry_client = FakeSectionAuthorClient([_valid_response()])
    outcome = execute_section_cluster_authoring(
        packet=packet, client=retry_client, cache_dir=tmp_path
    )
    assert outcome.reused_from_cache is False
    assert len(retry_client.calls) == 1


def test_a_failed_cluster_never_erases_a_prior_successful_outcome_for_the_same_section(tmp_path):
    """Once a section has an accepted cache entry, a later re-run that happens to fail must not
    delete or overwrite that entry -- caching only ever writes on success (see
    `execute_section_cluster_authoring`, which calls `write_section_authoring_cache` only after
    `result is not None`), so the cache file physically cannot be touched by a failing attempt."""

    packet = _packet()
    client = FakeSectionAuthorClient([_valid_response()])
    first = execute_section_cluster_authoring(packet=packet, client=client, cache_dir=tmp_path)
    cache_paths = list(tmp_path.glob("*.json"))
    assert len(cache_paths) == 1
    cache_path = cache_paths[0]
    original_bytes = cache_path.read_bytes()

    # A second packet for a *different* section must never touch this section's cache file --
    # simulates "one section fails later in a document" without perturbing this fixture's own
    # accepted packet/cache key.
    always_bad = {
        "units": [{"heading": "Overview", "text": "x", "fact_ids": [UNKNOWN_FACT_ID]}],
        "omitted": [],
    }
    other_packet = build_section_authoring_packet(
        org_repo=packet.org_repo,
        source_revision=packet.source_revision,
        target_section_id="installation",
        task_family="installation_framing",
        section_objective="Frame installation.",
        product_facts=_product_facts(),
        accepted_fact_ids=[CAP_1],
        protected_content=PROTECTED,
    )
    failing_client = FakeSectionAuthorClient([always_bad, always_bad, always_bad])
    with pytest.raises(SectionAuthoringAcceptanceError):
        execute_section_cluster_authoring(
            packet=other_packet, client=failing_client, cache_dir=tmp_path
        )

    assert cache_path.read_bytes() == original_bytes
    assert first.result.units[0].fact_ids == (CAP_1, CAP_2)


@pytest.mark.parametrize(
    "org_repo",
    [
        "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "aspose-3d-foss/Aspose.3D-FOSS-for-Java",
        "aspose-3d-foss/Aspose.3D-FOSS-for-.NET",
        "aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript",
    ],
)
def test_identical_authoring_contract_across_platforms_no_branch(org_repo):
    """Same schema, same prompt, same acceptance code path for every ecosystem -- only packet
    content (org_repo/facts) varies, matching the probe's cross-platform finding."""

    packet = _packet(org_repo=org_repo)
    client = FakeSectionAuthorClient([_valid_response()])

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert outcome.receipt.semantic_retry_used is False
    assert len(client.calls) == 1


def _tool_call_response(status_code, *, arguments=None, finish_reason="tool_calls"):
    if arguments is None:
        return {"status_code": status_code, "text": "Cannot connect to host text-model.vllm-qwen"}
    return {
        "status_code": 200,
        "json": {
            "id": "chatcmpl-worst-case",
            "choices": [
                {
                    "finish_reason": finish_reason,
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call1",
                                "function": {
                                    "name": "submit_section_cluster",
                                    "arguments": json.dumps(arguments),
                                },
                            }
                        ]
                    },
                }
            ],
        },
    }


class _FakeHttpResponse:
    def __init__(self, spec):
        self.status_code = spec["status_code"]
        self._json = spec.get("json")
        self.text = spec.get("text", "")

    def json(self):
        return self._json


def test_worst_case_composed_bound_is_exactly_six_physical_calls_for_one_cluster(monkeypatch):
    """Proves the documented worst case end to end through the REAL client (not a fixture
    double): logical attempt 1 needs its own transport retry (500 then success-but-invalid),
    logical attempts 2 and 3 also need transport retries, with the third finally accepted -- 3
    logical attempts x 2 physical transport attempts each = 6 physical HTTP calls total, never
    more, and the cluster still succeeds by the end of its bounded budget."""

    packet = _packet()
    invalid_schema_args = {
        "units": [{"heading": "x", "text": "x", "fact_ids": [UNKNOWN_FACT_ID]}],
        "omitted": [],
    }
    valid_args = _valid_response()
    responses = [
        _tool_call_response(500),  # logical attempt 1, physical attempt 1: transient failure
        _tool_call_response(200, arguments=invalid_schema_args),  # physical attempt 2: invalid
        _tool_call_response(500),  # logical attempt 2, physical attempt 1: transient failure
        _tool_call_response(200, arguments=invalid_schema_args),  # physical attempt 2: invalid
        _tool_call_response(500),  # logical attempt 3, physical attempt 1: transient failure
        _tool_call_response(200, arguments=valid_args),  # physical attempt 2: valid, accepted
    ]
    physical_calls = {"n": 0}

    def fake_post(url, json, headers, timeout):
        response = _FakeHttpResponse(responses[physical_calls["n"]])
        physical_calls["n"] += 1
        return response

    monkeypatch.setattr(verifier_client.requests, "post", fake_post)
    monkeypatch.setattr(verifier_client.time, "sleep", lambda _: None)
    client = LiveSectionClusterAuthorClient("https://example/v1", "key", "qwen3-next")

    outcome = execute_section_cluster_authoring(packet=packet, client=client)

    assert physical_calls["n"] == 6  # the documented worst-case ceiling, exactly reached
    assert outcome.receipt.logical_call_count == 3
    assert outcome.receipt.semantic_retry_used is True
