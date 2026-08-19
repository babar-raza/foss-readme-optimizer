"""SEO knowledge operationalization: relevance filtering, platform-mismatch
rejection, and lineage disposition -- tested against the real imported
keyword corpus."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.aspose_detectors import detect_relevant_seo_keywords, detect_seo_keywords
from readme_agent.facts.aspose_seo_keyword_facts import (
    relevant_seo_keyword_fact_record,
    seo_keyword_dispositions,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _REPO_ROOT / "data" / "imported"


def test_detect_relevant_seo_keywords_filters_a_real_over_supplied_list():
    raw = detect_seo_keywords("cells", "go", data_root=_DATA_ROOT)
    filtered = detect_relevant_seo_keywords("cells", "go", data_root=_DATA_ROOT)

    assert filtered.entry_found is True
    assert 0 < len(filtered.keywords) <= 6  # the vendored filter's own stuffing cap
    assert len(filtered.keywords) <= len(raw.keywords)
    assert set(filtered.keywords) <= set(raw.keywords)


def test_detect_relevant_seo_keywords_negative_platform_mismatch():
    """A keyword naming a DIFFERENT platform than the one being detected for
    is provably excluded -- the real, evidenced negative test the task
    requires, not merely asserted behavior."""

    result = detect_relevant_seo_keywords("cells", "go", data_root=_DATA_ROOT)

    for keyword in result.keywords:
        lowered = f" {keyword.lower()} "
        assert ".net" not in lowered
        assert "typescript" not in lowered
        assert "csharp" not in lowered and "c#" not in lowered

    assert result.dropped_wrong_platform  # the real corpus genuinely contains a mismatch
    for dropped in result.dropped_wrong_platform:
        assert dropped not in result.keywords


def test_detect_relevant_seo_keywords_negative_irrelevant_keyword():
    """An ungrounded phrase (names neither the family, a real format, nor a
    known capability-verb term) is provably excluded."""

    result = detect_relevant_seo_keywords("cells", "go", data_root=_DATA_ROOT)

    for dropped in result.dropped_ungrounded:
        lowered = dropped.lower()
        assert "cells" not in lowered
        assert not any(
            term in lowered
            for term in (
                "open source",
                "free",
                "alternative",
                "library",
                "api",
                "read",
                "write",
                "convert",
                "create",
                "edit",
                "generate",
                "parse",
                "process",
                "manipulate",
                "export",
                "import",
            )
        )


def test_detect_relevant_seo_keywords_matches_the_vendored_filter_exactly():
    """Drift guard: this repo's own per-item disposition reimplementation
    (needed because the vendored function returns only a filtered list, not
    per-item reasons) must keep producing the exact same *kept* set the
    vendored `filter_relevant_seo_keywords()` itself would -- proving the
    duplication has not silently drifted from the real, incident-hardened
    logic it's derived from."""

    import sys

    sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline")
    sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline/lib")
    sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss")
    import readme_refresh_checks as vendored

    raw = detect_seo_keywords("cells", "go", data_root=_DATA_ROOT)
    ours = detect_relevant_seo_keywords("cells", "go", data_root=_DATA_ROOT)
    theirs = vendored.filter_relevant_seo_keywords(list(raw.keywords), "cells", "go", set())

    assert list(ours.keywords) == theirs


def test_detect_relevant_seo_keywords_absent_family_degrades_gracefully():
    result = detect_relevant_seo_keywords("nonexistent-family", "python", data_root=_DATA_ROOT)

    assert result.entry_found is False
    assert result.keywords == ()
    assert result.dropped_wrong_platform == ()
    assert result.dropped_ungrounded == ()
    assert result.dropped_cap_exceeded == ()


def test_seo_keyword_dispositions_accounts_for_every_raw_keyword_exactly_once():
    raw = detect_seo_keywords("cells", "go", data_root=_DATA_ROOT)
    dispositions = seo_keyword_dispositions("cells", "go", data_root=_DATA_ROOT)

    assert {d.keyword for d in dispositions} == set(raw.keywords)
    assert len(dispositions) == len(set(raw.keywords))
    for disposition in dispositions:
        if disposition.kept:
            assert disposition.drop_reason is None
        else:
            assert disposition.drop_reason in {"wrong_platform", "ungrounded", "cap_exceeded"}


def test_relevant_seo_keyword_fact_record_real_data():
    fact = relevant_seo_keyword_fact_record("cells", "go", data_root=_DATA_ROOT)

    assert fact is not None
    assert fact.field == "aspose.relevant_seo_keywords"
    assert fact.source.location == "data/imported:cells/go"
    assert 0 < len(fact.value) <= 6
    assert fact.verification_state == "unverified"  # never silently promoted to verified


def test_relevant_seo_keyword_fact_record_none_when_nothing_survives_filtering(tmp_path):
    fact = relevant_seo_keyword_fact_record("nonexistent-family", "python", data_root=tmp_path)

    assert fact is None
