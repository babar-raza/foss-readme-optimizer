"""Gate R1.2: identical fact collection calls must produce byte-identical
`FactRecordV2` values and a stable `ProductFactsV2.canonical_hash()` --
never wall-clock-dependent. Each test here fails against the pre-repair
code (which used `datetime.now(UTC).isoformat()` in
`aspose_knowledge_selection.py`, `aspose_seo_keyword_facts.py`, and
`composer_factpack.py::aspose_fact_records()`) and passes after the repair.
"""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.aspose_knowledge_selection import knowledge_claim_fact_records
from readme_agent.facts.aspose_seo_keyword_facts import relevant_seo_keyword_fact_record
from readme_agent.facts.composer_factpack import aspose_fact_records, build_aspose_detection_bundle
from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.schema_v2 import FactSourceV2

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _REPO_ROOT / "data" / "imported"
_3D_PYTHON_REPO_SHA = "ee05c1ba9153ef5916b7a108406c794f2e464d01"


def test_knowledge_claim_fact_records_are_byte_identical_across_calls(tmp_path):
    kwargs = dict(
        family="3d",
        platform="python",
        data_root=_DATA_ROOT,
        clone_cache=tmp_path,
        source_revision=_3D_PYTHON_REPO_SHA,
    )
    first = [f.model_dump(mode="json") for f in knowledge_claim_fact_records(**kwargs)]
    second = [f.model_dump(mode="json") for f in knowledge_claim_fact_records(**kwargs)]

    assert first
    assert first == second


def test_relevant_seo_keyword_fact_record_is_byte_identical_across_calls():
    first = relevant_seo_keyword_fact_record("cells", "go", data_root=_DATA_ROOT)
    second = relevant_seo_keyword_fact_record("cells", "go", data_root=_DATA_ROOT)

    assert first is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_composer_factpack_facts_are_byte_identical_across_calls(tmp_path):
    def build():
        bundle = build_aspose_detection_bundle(
            "3d", "python", data_root=_DATA_ROOT, clone_cache=tmp_path
        )
        facts = aspose_fact_records(bundle, family="3d", platform="python")
        return [f.model_dump(mode="json") for f in facts]

    first = build()
    second = build()

    assert first
    assert first == second


def test_composer_factpack_enterprise_link_value_excludes_volatile_age_fields(tmp_path):
    """The deeper defect this session's own verification caught:
    target_map_age_days is a live "seconds since file mtime" float embedded
    directly in the fact VALUE (not just source metadata), so excluding it
    only from source_revision was not sufficient -- it must never appear in
    the hashed value payload either."""

    bundle = build_aspose_detection_bundle(
        "3d", "python", data_root=_DATA_ROOT, clone_cache=tmp_path
    )
    facts = aspose_fact_records(bundle, family="3d", platform="python")
    enterprise_link_fact = next((f for f in facts if f.field == "aspose.enterprise_link"), None)

    assert enterprise_link_fact is not None
    assert "target_map_age_days" not in enterprise_link_fact.value
    assert "target_map_stale" not in enterprise_link_fact.value


def test_end_to_end_product_facts_canonical_hash_is_stable_across_collections(tmp_path):
    """The complete acceptance bar: combining every aspose.* fact source
    this repo produces, ProductFactsV2.canonical_hash() must be identical
    across independent collection calls against unchanged inputs."""

    def build_hash() -> str:
        bundle = build_aspose_detection_bundle(
            "3d", "python", data_root=_DATA_ROOT, clone_cache=tmp_path
        )
        candidates = aspose_fact_records(bundle, family="3d", platform="python")
        candidates.extend(
            knowledge_claim_fact_records(
                "3d",
                "python",
                data_root=_DATA_ROOT,
                clone_cache=tmp_path,
                source_revision=_3D_PYTHON_REPO_SHA,
            )
        )
        seo_fact = relevant_seo_keyword_fact_record("3d", "python", data_root=_DATA_ROOT)
        if seo_fact is not None:
            candidates.append(seo_fact)
        resolved = resolve_product_facts(
            "aspose-3d-foss/x",
            candidates,
            missing_source=FactSourceV2(
                source_type="mechanical_repository", location="r", retrieved_at="2026-01-01"
            ),
            missing_field_surfaces={},
        )
        return resolved.canonical_hash()

    first = build_hash()
    second = build_hash()
    third = build_hash()

    assert first == second == third
