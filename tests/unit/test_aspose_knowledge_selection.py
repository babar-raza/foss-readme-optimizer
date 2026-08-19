"""Knowledge-application layer, selection tier -- bounded relevance
selection, freshness/corroboration gating, and the per-claim disposition
ledger. Tested against the REAL imported corpus, mirroring
`test_aspose_knowledge_claims.py`'s convention."""

from __future__ import annotations

from pathlib import Path

import pytest

from readme_agent.facts.aspose_knowledge_selection import (
    _MAX_SELECTED_PER_KIND,
    _MIN_CONFIDENCE,
    select_knowledge_claims,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _REPO_ROOT / "data" / "imported"

# The real, current repo_sha recorded in data/imported/knowledge/3d/python/merged/model.yaml.
_3D_PYTHON_REPO_SHA = "ee05c1ba9153ef5916b7a108406c794f2e464d01"
# barcode/python: the only bundle among the three test fixtures used here that
# carries real claims of every kind this test file exercises (license,
# dependency, api/api_method) -- 3d/python has none of those three kinds.
_BARCODE_PYTHON_REPO_SHA = "53f2c3350b8171f2c8275e7b1a178f218695ac45"


@pytest.fixture
def clone_without_license(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def clone_with_mit_license(tmp_path: Path) -> Path:
    (tmp_path / "LICENSE").write_text("MIT License\n\nCopyright ...\n", encoding="utf-8")
    return tmp_path


def test_select_knowledge_claims_product_platform_matching_real_data(clone_without_license):
    result = select_knowledge_claims(
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    assert result.family == "3d"
    assert result.platform == "python"
    assert result.freshness == "current"
    assert result.selected_count > 0
    assert all(d.family == "3d" and d.platform == "python" for d in result.dispositions)


def test_select_knowledge_claims_unmatched_product_selects_nothing(clone_without_license):
    result = select_knowledge_claims(
        "nonexistent-family",
        "nonexistent-platform",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=None,
    )

    assert result.selected_count == 0
    assert result.rejected_count == 0
    assert result.fact_records == ()
    assert result.freshness == "unknown_revision"


def test_select_knowledge_claims_rejects_stale_revision_below_confidence_floor(
    clone_without_license,
):
    """A bundle whose recorded repo_sha does not match the current
    repository revision has its claim confidence scaled down; a claim that
    drops below the selection floor is rejected with an explicit reason,
    never silently dropped."""

    result = select_knowledge_claims(
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision="0" * 40,  # deliberately wrong -- proves staleness rejection
    )

    assert result.freshness == "stale_revision"
    stale_rejections = [
        d
        for d in result.dispositions
        if not d.accepted and d.rejection_reason == "below_confidence_threshold"
    ]
    assert stale_rejections  # at least one claim was actually rejected for staleness


def test_select_knowledge_claims_current_repo_evidence_wins_on_license_conflict(
    clone_without_license,
):
    """No LICENSE file present in the current clone -- the imported "Licensed
    under MIT" claim is never corroborated and stays capped at unverified,
    proving current repository evidence (its absence, here) is never
    silently overridden by imported knowledge."""

    result = select_knowledge_claims(
        "barcode",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=_BARCODE_PYTHON_REPO_SHA,
    )

    license_fact = next(
        (f for f in result.fact_records if f.field == "aspose.license_claims"), None
    )
    assert license_fact is not None
    assert license_fact.verification_state == "unverified"


def test_select_knowledge_claims_corroborated_license_reaches_verified(clone_with_mit_license):
    """A real MIT LICENSE file in the current clone corroborates the
    imported "Licensed under MIT" claim -- it reaches `verified`, the one
    real corroboration path this layer implements."""

    result = select_knowledge_claims(
        "barcode",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_with_mit_license,
        source_revision=_BARCODE_PYTHON_REPO_SHA,
    )

    license_fact = next(
        (f for f in result.fact_records if f.field == "aspose.license_claims"), None
    )
    assert license_fact is not None
    assert license_fact.verification_state == "verified"

    license_disposition = next(d for d in result.dispositions if d.kind == "license" and d.accepted)
    assert license_disposition.verification_state == "verified"


def test_select_knowledge_claims_bounded_selection_never_exceeds_cap(clone_without_license):
    """3d/python's real corpus has far more than `_MAX_SELECTED_PER_KIND`
    claims in several kinds (1400 api_method, 987 api, 112 feature, ...) --
    proves the cap is enforced against real over-supply, not merely
    documented."""

    result = select_knowledge_claims(
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    for fact in result.fact_records:
        assert len(fact.value) <= _MAX_SELECTED_PER_KIND

    cap_rejections = [
        d for d in result.dispositions if d.rejection_reason == "exceeds_selection_cap"
    ]
    assert cap_rejections  # the real corpus genuinely exceeds the cap for at least one kind


def test_select_knowledge_claims_selection_is_by_confidence_not_file_order(clone_without_license):
    """Selection ranks by confidence (descending) across the whole target
    FIELD (`format` and `format_support` share one field), never by
    claims.json's own insertion order -- the "not arbitrary first-N
    truncation" requirement. Every claim accepted into a field has
    confidence >= every claim rejected from that same field for exceeding
    the selection cap (grouped by field, not by raw `kind`, since two kinds
    can legitimately differ in typical confidence -- observed for real:
    `format_support` claims are always confidence 1.0, `format` claims
    range 0.75-0.95, so an all-format_support top-N is correct ranking
    behavior, not a bug)."""

    result = select_knowledge_claims(
        "3d",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=_3D_PYTHON_REPO_SHA,
    )

    by_field_accepted: dict[str, list[float]] = {}
    by_field_capped: dict[str, list[float]] = {}
    for d in result.dispositions:
        if d.confidence is None or d.resulting_fact_field is None:
            continue
        if d.accepted:
            by_field_accepted.setdefault(d.resulting_fact_field, []).append(d.confidence)
        elif d.rejection_reason == "exceeds_selection_cap":
            by_field_capped.setdefault(d.resulting_fact_field, []).append(d.confidence)

    assert by_field_capped  # the real corpus genuinely exceeds the cap for at least one field
    for field, capped_confidences in by_field_capped.items():
        accepted_confidences = by_field_accepted[field]
        assert min(accepted_confidences) >= max(capped_confidences)


def test_select_knowledge_claims_dependency_and_api_kinds_are_explicitly_never_selected(
    clone_without_license,
):
    """`dependency` (covered by the existing aspose.dependency_claims field)
    and `api*` (covered by the structural api_surface.json field) are
    rejected with an explicit, real reason -- never silently dropped and
    never duplicated across two divergent fact fields."""

    result = select_knowledge_claims(
        "barcode",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=_BARCODE_PYTHON_REPO_SHA,
    )

    for kind, expected_reason in (
        ("dependency", "kind_covered_by_existing_dependency_claims_field"),
        ("api", "kind_covered_by_api_surface_field"),
        ("api_method", "kind_covered_by_api_surface_field"),
    ):
        matching = [d for d in result.dispositions if d.kind == kind]
        assert matching, f"expected real {kind!r} claims in the 3d/python corpus"
        assert all(not d.accepted and d.rejection_reason == expected_reason for d in matching)

    assert not any(f.field.startswith("aspose.dependency") for f in result.fact_records)
    assert not any(f.field.startswith("aspose.api") for f in result.fact_records)


def test_select_knowledge_claims_every_considered_claim_has_exactly_one_disposition(
    clone_without_license,
):
    """No silent-drop path: every claim in the real corpus for this
    product/platform appears in the disposition ledger exactly once."""

    from readme_agent.facts.aspose_knowledge_claims import load_knowledge_claims

    all_claims = load_knowledge_claims("barcode", "python", data_root=_DATA_ROOT)
    result = select_knowledge_claims(
        "barcode",
        "python",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=None,
    )

    disposed_ids = [d.global_claim_id for d in result.dispositions]
    assert len(disposed_ids) == len(set(disposed_ids))  # each claim disposed exactly once
    assert set(disposed_ids) == {claim.global_claim_id for claim in all_claims}
    assert result.selected_count + result.rejected_count == len(all_claims)


def test_select_knowledge_claims_min_confidence_threshold_is_real_and_positive():
    assert 0.0 < _MIN_CONFIDENCE <= 1.0


def test_select_knowledge_claims_platform_mismatched_keyword_never_leaks_into_another_platform(
    clone_without_license,
):
    """Negative test: selecting knowledge for one family/platform never
    returns claims tagged with a different family or platform -- proves
    the loader/selector is scoped correctly, not merely documented as such."""

    result = select_knowledge_claims(
        "cells",
        "java",
        data_root=_DATA_ROOT,
        clone_cache=clone_without_license,
        source_revision=None,
    )

    for disposition in result.dispositions:
        assert disposition.family == "cells"
        assert disposition.platform == "java"
    for fact in result.fact_records:
        assert fact.source.location == "data/imported:cells/java"
