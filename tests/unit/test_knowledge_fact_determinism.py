"""Gate R1.2: identical fact collection calls must produce byte-identical
`FactRecordV2` values and a stable `ProductFactsV2.canonical_hash()` --
never wall-clock-dependent. Each test here fails against the pre-repair
code (which used `datetime.now(UTC).isoformat()` in
`aspose_knowledge_selection.py`, `aspose_seo_keyword_facts.py`, and
`composer_factpack.py::aspose_fact_records()`) and passes after the repair.

Gate R1 closure: the tests above only ever called each function twice in a
row, so they never exercised the one remaining wall-clock leak commit
2608f125 left behind -- `aspose_fact_records()` gated the `aspose.
enterprise_link` fact's `verified` flag (and therefore its
`verification_state`/`confidence`/`ProductFactsV2.canonical_hash()`) on
`EnterpriseLinkDetectionV1.target_map_stale`, itself derived from elapsed
wall-clock age against `STALE_WARN_DAYS`. The tests below construct the
exact same enterprise-link input on both sides of that threshold to prove
the fix, and contrast it against a genuine, content-derived change
(`relationship`) that must still change the fact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent.facts.aspose_detectors import detect_enterprise_link
from readme_agent.facts.aspose_knowledge_selection import knowledge_claim_fact_records
from readme_agent.facts.aspose_seo_keyword_facts import relevant_seo_keyword_fact_record
from readme_agent.facts.composer_factpack import (
    STALE_WARN_DAYS,
    aspose_fact_records,
    build_aspose_detection_bundle,
)
from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2

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


def _fact_hash(fact: FactRecordV2) -> str:
    payload = json.dumps(fact.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_enterprise_link_fact_is_identical_on_both_sides_of_stale_warn_days(tmp_path):
    """Gate R1 closure, mandatory test A: the exact same enterprise-link
    detection, differing only in target_map_age_days/target_map_stale
    straddling STALE_WARN_DAYS, must produce a byte-identical FactRecordV2
    (verification_state, complete serialized value, source identity, and
    per-fact hash included). Fails against the pre-closure code, which set
    `verified=not bool(link.target_map_stale)`."""

    bundle = build_aspose_detection_bundle(
        "cells", "java", data_root=_DATA_ROOT, clone_cache=tmp_path
    )
    assert bundle.enterprise_link.url is not None
    assert bundle.enterprise_link.relationship == "platform"

    fresh_link = bundle.enterprise_link.model_copy(
        update={"target_map_age_days": STALE_WARN_DAYS - 4.0, "target_map_stale": False}
    )
    stale_link = bundle.enterprise_link.model_copy(
        update={"target_map_age_days": STALE_WARN_DAYS + 6.0, "target_map_stale": True}
    )

    fresh_facts = aspose_fact_records(
        bundle.model_copy(update={"enterprise_link": fresh_link}), family="cells", platform="java"
    )
    stale_facts = aspose_fact_records(
        bundle.model_copy(update={"enterprise_link": stale_link}), family="cells", platform="java"
    )

    fresh_fact = next(f for f in fresh_facts if f.field == "aspose.enterprise_link")
    stale_fact = next(f for f in stale_facts if f.field == "aspose.enterprise_link")

    assert fresh_fact.verification_state == "verified"
    assert fresh_fact.model_dump(mode="json") == stale_fact.model_dump(mode="json")
    assert _fact_hash(fresh_fact) == _fact_hash(stale_fact)


def test_end_to_end_canonical_hash_is_stable_across_the_stale_warn_days_threshold(tmp_path):
    """Gate R1 closure, mandatory test B: run the complete imported/aspose
    fact collection twice, with the enterprise-link staleness threshold
    below STALE_WARN_DAYS on one call and above it on the other, and assert
    an identical ProductFactsV2.canonical_hash() -- the actual acceptance
    bar, not just a same-call/same-call comparison."""

    def build_hash(age_days: float, stale: bool) -> str:
        bundle = build_aspose_detection_bundle(
            "3d", "python", data_root=_DATA_ROOT, clone_cache=tmp_path
        )
        aged_link = bundle.enterprise_link.model_copy(
            update={"target_map_age_days": age_days, "target_map_stale": stale}
        )
        bundle = bundle.model_copy(update={"enterprise_link": aged_link})

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

    below_threshold = build_hash(STALE_WARN_DAYS - 4.0, False)
    above_threshold = build_hash(STALE_WARN_DAYS + 6.0, True)

    assert below_threshold == above_threshold


def test_enterprise_link_verification_reflects_relationship_not_staleness(tmp_path):
    """Gate R1 closure, mandatory test C: unlike staleness (tests above), a
    genuine change in the detector's own deterministic target-map
    resolution/relationship-validity signal must still change the emitted
    fact and its hash -- proving the repair narrowed the leak rather than
    freezing `verified` to a constant."""

    bundle = build_aspose_detection_bundle(
        "cells", "java", data_root=_DATA_ROOT, clone_cache=tmp_path
    )
    assert bundle.enterprise_link.relationship == "platform"

    mismatched_link = bundle.enterprise_link.model_copy(
        update={"relationship": "unresolved", "public_platform": None}
    )
    mismatched_bundle = bundle.model_copy(update={"enterprise_link": mismatched_link})

    resolved_facts = aspose_fact_records(bundle, family="cells", platform="java")
    mismatched_facts = aspose_fact_records(mismatched_bundle, family="cells", platform="java")

    resolved_fact = next(f for f in resolved_facts if f.field == "aspose.enterprise_link")
    mismatched_fact = next(f for f in mismatched_facts if f.field == "aspose.enterprise_link")

    assert resolved_fact.verification_state == "verified"
    assert mismatched_fact.verification_state == "unverified"
    assert resolved_fact.value != mismatched_fact.value
    assert _fact_hash(resolved_fact) != _fact_hash(mismatched_fact)


def test_composer_factpack_omits_enterprise_link_when_target_map_is_missing(tmp_path):
    """Gate R1 closure, mandatory test D: a missing/unreadable target map
    must never surface as a verified -- or even unverified -- enterprise-
    link fact; the field stays omitted, exactly as before this repair, and
    fail-closed behavior must not regress while fixing the staleness leak."""

    bundle = build_aspose_detection_bundle(
        "cells", "java", data_root=_DATA_ROOT, clone_cache=tmp_path
    )
    missing_map_link = detect_enterprise_link("cells", "java", data_root=tmp_path)
    assert missing_map_link.url is None

    facts = aspose_fact_records(
        bundle.model_copy(update={"enterprise_link": missing_map_link}),
        family="cells",
        platform="java",
    )

    assert not any(f.field == "aspose.enterprise_link" for f in facts)
