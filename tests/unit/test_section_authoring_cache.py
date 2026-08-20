"""Section-level content-addressed cache: zero-call reuse, per-section resume on failure."""

import pytest

from readme_agent.specialists.section_authoring_cache import (
    SectionAuthoringCacheV1,
    load_section_authoring_cache,
    section_authoring_cache_key,
    write_section_authoring_cache,
)
from readme_agent.specialists.section_authoring_contracts import (
    SectionAuthoringOutcomeV1,
    SectionAuthoringReceiptV1,
    SectionClusterAuthoringResultV1,
    SectionClusterUnitV1,
)


def _outcome(target_section_id: str = "capability-overview") -> SectionAuthoringOutcomeV1:
    return SectionAuthoringOutcomeV1(
        target_section_id=target_section_id,
        packet_hash="a" * 64,
        result=SectionClusterAuthoringResultV1(
            units=(
                SectionClusterUnitV1(
                    heading="Overview",
                    text="A focused capability description.",
                    fact_ids=("F.CAP.01",),
                ),
            ),
            omitted=(),
        ),
        receipt=SectionAuthoringReceiptV1(
            actor_id="llm-route:section-cluster-authoring",
            prompt_id="section_cluster_authoring",
            prompt_sha256="b" * 64,
            packet_hash="a" * 64,
            raw_output_sha256="c" * 64,
            semantic_retry_used=False,
            logical_call_count=1,
        ),
    )


def _key(**overrides) -> str:
    kwargs = {
        "org_repo": "aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        "source_revision": "a" * 40,
        "packet_hash": "a" * 64,
        "target_section_id": "capability-overview",
        "prompt_sha256": "b" * 64,
        "schema_sha256": "d" * 64,
        "model": "qwen3-next",
        "sampling_parameters": {"temperature": 0.0},
        "protected_literal_hash": "e" * 64,
    }
    kwargs.update(overrides)
    return section_authoring_cache_key(**kwargs)


def test_write_then_load_round_trips(tmp_path):
    key = _key()
    outcome = _outcome()

    write_section_authoring_cache(
        tmp_path,
        cache_key=key,
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        source_revision="a" * 40,
        outcome=outcome,
    )
    loaded = load_section_authoring_cache(tmp_path, "capability-overview", key)

    assert loaded is not None
    assert loaded.outcome.result == outcome.result
    assert loaded.cache_key == key


def test_missing_cache_file_returns_none(tmp_path):
    assert load_section_authoring_cache(tmp_path, "capability-overview", _key()) is None


def test_wrong_cache_key_is_a_miss_not_a_stale_hit(tmp_path):
    write_section_authoring_cache(
        tmp_path,
        cache_key=_key(),
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        source_revision="a" * 40,
        outcome=_outcome(),
    )

    stale = load_section_authoring_cache(
        tmp_path, "capability-overview", _key(packet_hash="f" * 64)
    )

    assert stale is None


def test_corrupt_cache_file_is_a_miss_not_a_crash(tmp_path):
    (tmp_path / "capability-overview.json").write_text("not json", encoding="utf-8")

    assert load_section_authoring_cache(tmp_path, "capability-overview", _key()) is None


def test_a_failed_section_never_touches_another_sections_cache_file(tmp_path):
    write_section_authoring_cache(
        tmp_path,
        cache_key=_key(target_section_id="capability-overview"),
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        source_revision="a" * 40,
        outcome=_outcome("capability-overview"),
    )

    # A different section's cache lookup is independent -- resume retries only that section.
    assert load_section_authoring_cache(tmp_path, "installation", _key()) is None
    own_key = _key(target_section_id="capability-overview")
    assert load_section_authoring_cache(tmp_path, "capability-overview", own_key) is not None


@pytest.mark.parametrize(
    "changed_field",
    [
        "source_revision",
        "packet_hash",
        "target_section_id",
        "prompt_sha256",
        "schema_sha256",
        "model",
        "protected_literal_hash",
    ],
)
def test_every_bound_input_changes_the_cache_key(changed_field):
    base = _key()
    overrides = {
        "source_revision": "b" * 40,
        "packet_hash": "f" * 64,
        "target_section_id": "installation",
        "prompt_sha256": "0" * 64,
        "schema_sha256": "1" * 64,
        "model": "gpt-oss",
        "protected_literal_hash": "9" * 64,
    }
    changed = _key(**{changed_field: overrides[changed_field]})

    assert changed != base


def test_cache_key_binds_sampling_parameters():
    key_a = _key(sampling_parameters={"temperature": 0.0})
    key_b = _key(sampling_parameters={"temperature": 0.7})

    assert key_a != key_b


def test_contract_version_bump_invalidates_cache_key():
    default_key = _key()
    bumped_key = section_authoring_cache_key(
        org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
        source_revision="a" * 40,
        packet_hash="a" * 64,
        target_section_id="capability-overview",
        prompt_sha256="b" * 64,
        schema_sha256="d" * 64,
        model="qwen3-next",
        sampling_parameters={"temperature": 0.0},
        protected_literal_hash="e" * 64,
        authoring_contract_version="section-authoring-v2-someday",
    )

    assert default_key != bumped_key


def test_cache_record_rejects_a_tampered_output_hash():
    with pytest.raises(ValueError, match="checksum does not match"):
        SectionAuthoringCacheV1(
            cache_key="a" * 64,
            output_sha256="0" * 64,
            org_repo="aspose-3d-foss/Aspose.3D-FOSS-for-Python",
            source_revision="a" * 40,
            target_section_id="capability-overview",
            outcome=_outcome(),
        )
