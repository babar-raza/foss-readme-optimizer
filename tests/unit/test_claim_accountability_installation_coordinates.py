"""Constrain source-build accountability to exact deterministic distribution claims."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.golden_set.review_fixtures import REVIEW_ARCHETYPES, build_review_facts
from readme_agent.readme.assessment_claims import (
    ReadmeMaterialClaimAssessmentV1,
    assess_material_claims,
)
from readme_agent.readme.claim_accountability_coordinates import structured_fact_coordinates
from readme_agent.readme.document_templates import installation_text

_REVISION = "a" * 40
_ORG_REPO = "aspose-3d-foss/Aspose.3D-FOSS-for-Python"
_DISTRIBUTION = "aspose-3d-foss"
_SOURCE_BUILD_CLAIM = f"Use source installation for the `{_DISTRIBUTION}` distribution."


def _source_build_facts() -> ProductFactsV2:
    facts = ProductFactsV2.model_validate(build_review_facts(REVIEW_ARCHETYPES[2]))
    identity = facts.selected_fact("product.identity")
    coordinates = facts.selected_fact("installation.coordinates")
    acquisition = facts.selected_fact("installation.verified_acquisition")
    source = identity.source.model_copy(update={"source_revision": _REVISION})
    coordinate = {"name": _DISTRIBUTION}
    replacements = {
        identity.fact_id: identity.model_copy(
            update={
                "value": {
                    "family": "3d",
                    "platform": "python",
                    "ecosystem": "python",
                    "repository": _ORG_REPO,
                    "manifest_names": [_DISTRIBUTION],
                },
                "source": source,
            }
        ),
        coordinates.fact_id: coordinates.model_copy(
            update={
                "value": [
                    {
                        "path": ".",
                        "ecosystem": "python",
                        "manifest_path": "setup.py",
                        "name": _DISTRIBUTION,
                        "version": "26.1.0",
                    }
                ],
                "source": source,
            }
        ),
        acquisition.fact_id: acquisition.model_copy(
            update={
                "value": {
                    "schema_version": 1,
                    "org_repo": _ORG_REPO,
                    "source_revision": _REVISION,
                    "ecosystem": "python",
                    "method": "source_build",
                    "outcome": "SOURCE_BUILD_VERIFIED",
                    "detail": "Pinned source package installed and exercised.",
                    "coordinate": coordinate,
                    "registry_receipt": {
                        "schema_version": 1,
                        "resolver_ecosystem": "python",
                        "registry_label": "PyPI",
                        "coordinate": coordinate,
                        "request_url": f"https://pypi.org/pypi/{_DISTRIBUTION}/json",
                        "status_code": 404,
                        "response_sha256": "b" * 64,
                        "retrieved_at": "2026-08-05T00:00:00Z",
                        "found": False,
                        "detail": f"PyPI: {_DISTRIBUTION} NOT FOUND (404)",
                    },
                    "source_build_receipt": {
                        "schema_version": 1,
                        "org_repo": _ORG_REPO,
                        "source_revision": _REVISION,
                        "argv": ["python", "-I", ".readme-agent-consumer-driver.py"],
                        "input_sha256": "c" * 64,
                        "policy_sha256": "d" * 64,
                        "immutable_image": "python@sha256:" + "e" * 64,
                        "network_mode": "none",
                        "dependency_pins": [
                            "python_package_source_sha256=" + "f" * 64,
                            f"source_revision={_REVISION}",
                        ],
                        "cleanup_complete": True,
                        "return_code": 0,
                        "truth_eligible": True,
                    },
                    "truth_eligible": True,
                },
                "source": source,
            }
        ),
    }
    return facts.model_copy(
        update={
            "org_repo": _ORG_REPO,
            "facts": [replacements.get(fact.fact_id, fact) for fact in facts.facts],
        }
    )


def _claim_containing(document: str, phrase: str) -> ReadmeMaterialClaimAssessmentV1:
    encoded = document.encode("utf-8")
    return next(
        claim
        for claim in assess_material_claims(document)
        if phrase in encoded[claim.source_byte_start : claim.source_byte_end].decode("utf-8")
    )


def _coordinate_fields(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    facts: ProductFactsV2,
) -> set[str]:
    return {item.field for item in structured_fact_coordinates(document, claim, facts)}


def test_exact_deterministic_source_build_claim_binds_acquisition_and_distribution() -> None:
    facts = _source_build_facts()
    rendered = installation_text(facts, facts.org_repo, _REVISION)

    assert rendered is not None
    claim = _claim_containing(rendered, _SOURCE_BUILD_CLAIM)
    coordinates = structured_fact_coordinates(rendered, claim, facts)

    assert {item.field for item in coordinates} == {
        "installation.coordinates",
        "installation.verified_acquisition",
    }
    distribution = next(item for item in coordinates if item.field == "installation.coordinates")
    assert distribution.fact_id == facts.selected_fact_ids["installation.coordinates"]
    assert distribution.path.startswith("/python-distributions/")
    assert distribution.path.endswith("/name")


def test_arbitrary_distribution_name_mention_is_not_a_structured_coordinate() -> None:
    facts = _source_build_facts()
    document = f"The `{_DISTRIBUTION}` package exposes the public Python API.\n"
    claim = _claim_containing(document, _DISTRIBUTION)

    assert "installation.coordinates" not in _coordinate_fields(document, claim, facts)


def test_partial_or_spoofed_generated_claim_is_not_a_structured_coordinate() -> None:
    facts = _source_build_facts()
    rendered = installation_text(facts, facts.org_repo, _REVISION)

    assert rendered is not None
    exact = _claim_containing(rendered, _SOURCE_BUILD_CLAIM)
    exact_text = rendered.encode("utf-8")[exact.source_byte_start : exact.source_byte_end].decode()
    for document in (
        f"The `{_DISTRIBUTION}` distribution is available.\n",
        exact_text.replace("source installation", "PyPI installation") + "\n",
    ):
        claim = _claim_containing(document, _DISTRIBUTION)
        assert "installation.coordinates" not in _coordinate_fields(document, claim, facts)


def test_stale_acquisition_revision_cannot_bind_current_distribution_claim() -> None:
    facts = _source_build_facts()
    rendered = installation_text(facts, facts.org_repo, _REVISION)
    acquisition = facts.selected_fact("installation.verified_acquisition")
    stale = acquisition.model_copy(
        update={"source": acquisition.source.model_copy(update={"source_revision": "b" * 40})}
    )
    stale_facts = facts.model_copy(
        update={"facts": [stale if fact.fact_id == stale.fact_id else fact for fact in facts.facts]}
    )

    assert rendered is not None
    claim = _claim_containing(rendered, _DISTRIBUTION)
    assert "installation.coordinates" not in _coordinate_fields(rendered, claim, stale_facts)


def test_other_or_ambiguous_coordinate_cannot_bind_selected_distribution_claim() -> None:
    facts = _source_build_facts()
    rendered = installation_text(facts, facts.org_repo, _REVISION)
    coordinates = facts.selected_fact("installation.coordinates")
    row = coordinates.value[0]

    assert rendered is not None
    claim = _claim_containing(rendered, _DISTRIBUTION)
    for value in (
        [{**row, "name": "other-distribution"}],
        [row, {**row, "path": "bindings/python"}],
    ):
        replacement = coordinates.model_copy(update={"value": value})
        changed = facts.model_copy(
            update={
                "facts": [
                    replacement if fact.fact_id == replacement.fact_id else fact
                    for fact in facts.facts
                ]
            }
        )
        assert "installation.coordinates" not in _coordinate_fields(rendered, claim, changed)
