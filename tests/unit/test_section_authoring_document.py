"""The real candidate-generation entry point: chains planner -> packet -> execute/cache for a
whole document's section specs."""

import pytest
from section_authoring_test_support import build_fact, build_product_facts_v2

from readme_agent.facts.protected_content import fingerprint_protected_content
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.schema import LLMResponseMeta
from readme_agent.specialists.section_authoring_document import (
    SectionAuthoringDocumentError,
    SectionAuthoringSpecV1,
    author_readme_sections,
)

PROTECTED = fingerprint_protected_content("# Example\n\nA focused library.\n")

CAP_1 = "product.capabilities:fixture"
CAP_2 = "product.capabilities:secondary"
INSTALL_1 = "installation.coordinates:fixture"
UNKNOWN_FACT_ID = "does.not.exist:fixture"

PRODUCT_FACTS = build_product_facts_v2(
    field_values={
        "product.capabilities": "Import and export OBJ files.",
        "installation.coordinates": "pip install aspose-3d-foss",
    },
    extra_facts=[build_fact(CAP_2, "product.capabilities", "Import and export GLTF files.")],
)


class ScriptedClient:
    """Returns one canned acceptance-passing response per distinct target_section_id it sees,
    keyed off the fact_ids offered -- close enough to a real client for this seam test."""

    def __init__(self):
        self.calls: list[list[str]] = []

    def analyze_section_cluster(self, messages, accepted_fact_ids):
        self.calls.append(list(accepted_fact_ids))
        heading = (
            "Import and Export 3D Content"
            if any(fact_id.startswith("product.capabilities") for fact_id in accepted_fact_ids)
            else "Install the Package"
        )
        return AnalysisResult(
            parsed={
                "units": [
                    {
                        "heading": heading,
                        "text": "A focused, specific description of this cluster's facts.",
                        "fact_ids": list(accepted_fact_ids),
                    }
                ],
                "omitted": [],
            },
            meta=LLMResponseMeta(request_id="req", model="qwen3-next"),
        )


class FailingSecondSectionClient:
    def __init__(self):
        self.calls = 0

    def analyze_section_cluster(self, messages, accepted_fact_ids):
        self.calls += 1
        if self.calls == 1:
            return AnalysisResult(
                parsed={
                    "units": [
                        {
                            "heading": "Import and Export 3D Content",
                            "text": "Imports and exports OBJ and GLTF files.",
                            "fact_ids": list(accepted_fact_ids),
                        }
                    ],
                    "omitted": [],
                },
                meta=LLMResponseMeta(),
            )
        # every subsequent attempt (including the bounded semantic retry) fails
        return AnalysisResult(
            parsed={
                "units": [{"heading": "x", "text": "x", "fact_ids": [UNKNOWN_FACT_ID]}],
                "omitted": [],
            },
            meta=LLMResponseMeta(),
        )


def _specs():
    return [
        SectionAuthoringSpecV1(
            section_id="capability-overview",
            task_family="capability_entry_cluster",
            section_objective="Introduce the primary capabilities.",
            accepted_fact_ids=(CAP_1, CAP_2),
        ),
        SectionAuthoringSpecV1(
            section_id="installation",
            task_family="installation_framing",
            section_objective="Frame how to install the package.",
            accepted_fact_ids=(INSTALL_1,),
        ),
    ]


def test_authors_every_section_in_the_document():
    client = ScriptedClient()

    outcomes = author_readme_sections(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        source_revision="a" * 40,
        product_facts=PRODUCT_FACTS,
        protected_content=PROTECTED,
        section_specs=_specs(),
        client=client,
    )

    assert [outcome.target_section_id for outcome in outcomes] == [
        "capability-overview",
        "installation",
    ]
    assert len(client.calls) == 2


def test_a_five_fact_section_is_authored_as_two_clusters():
    extra = [
        build_fact(f"product.capabilities:extra-{i}", "product.capabilities", f"Capability {i}.")
        for i in range(1, 5)
    ]
    facts = build_product_facts_v2(
        field_values={"product.capabilities": "Capability 0."}, extra_facts=extra
    )
    fact_ids = (
        "product.capabilities:fixture",
        *[f"product.capabilities:extra-{i}" for i in range(1, 5)],
    )
    spec = SectionAuthoringSpecV1(
        section_id="capabilities",
        task_family="capability_entry_cluster",
        section_objective="Introduce every capability.",
        accepted_fact_ids=fact_ids,
    )
    client = ScriptedClient()

    outcomes = author_readme_sections(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        source_revision="a" * 40,
        product_facts=facts,
        protected_content=PROTECTED,
        section_specs=[spec],
        client=client,
    )

    assert [outcome.target_section_id for outcome in outcomes] == [
        "capabilities-1",
        "capabilities-2",
    ]
    assert len(client.calls) == 2
    assert all(len(call) <= 4 for call in client.calls)
    # every one of the 5 facts is disposed across the two clusters -- none silently dropped
    disposed = {
        fact_id
        for outcome in outcomes
        for unit in outcome.result.units
        for fact_id in unit.fact_ids
    } | {item.fact_id for outcome in outcomes for item in outcome.result.omitted}
    assert disposed == set(fact_ids)


def test_a_failed_section_stops_the_document_but_preserves_earlier_outcomes():
    client = FailingSecondSectionClient()
    specs = [
        SectionAuthoringSpecV1(
            section_id="capability-overview",
            task_family="capability_entry_cluster",
            section_objective="Introduce the primary capabilities.",
            accepted_fact_ids=(CAP_1, CAP_2),
        ),
        SectionAuthoringSpecV1(
            section_id="installation",
            task_family="installation_framing",
            section_objective="Frame how to install the package.",
            accepted_fact_ids=(INSTALL_1,),
        ),
    ]

    with pytest.raises(SectionAuthoringDocumentError) as excinfo:
        author_readme_sections(
            org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
            source_revision="a" * 40,
            product_facts=PRODUCT_FACTS,
            protected_content=PROTECTED,
            section_specs=specs,
            client=client,
        )

    assert "installation" in str(excinfo.value)
    assert [outcome.target_section_id for outcome in excinfo.value.outcomes] == [
        "capability-overview"
    ]


def test_unchanged_document_reuses_every_section_with_zero_calls(tmp_path):
    client = ScriptedClient()
    kwargs = dict(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        source_revision="a" * 40,
        product_facts=PRODUCT_FACTS,
        protected_content=PROTECTED,
        section_specs=_specs(),
        cache_dir=tmp_path,
    )

    first = author_readme_sections(client=client, **kwargs)
    assert len(client.calls) == 2

    exhausting_client = ScriptedClient()
    second = author_readme_sections(client=exhausting_client, **kwargs)

    assert exhausting_client.calls == []
    assert [outcome.reused_from_cache for outcome in second] == [True, True]
    assert [outcome.result for outcome in second] == [outcome.result for outcome in first]
