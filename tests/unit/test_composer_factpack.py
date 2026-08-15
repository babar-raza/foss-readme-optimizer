"""T4 -- ComposerFactpack (merged factpack) + EvidenceGroundedRenderViewV2 +
U7 per-source staleness/coverage surfaces. Tested against the REAL imported
corpus (data/imported/) wherever real data exists, synthetic fixtures for
edge cases."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from readme_agent.facts.composer_factpack import (
    STALE_WARN_DAYS,
    ComposerFactpack,
    assess_source_staleness,
    build_aspose_detection_bundle,
    build_composer_factpack,
)
from readme_agent.facts.render_views import (
    EvidenceGroundedRenderViewV2,
    evidence_grounded_render_view,
)
from readme_agent.facts.schema_v2 import (
    REQUIRED_PRODUCT_FIELDS,
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _REPO_ROOT / "data" / "imported"
_SOURCE_REVISION = "a" * 40


def _ready_product_facts(field_values: dict[str, object] | None = None) -> ProductFactsV2:
    field_values = field_values or {}
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://org/repo",
        source_revision=_SOURCE_REVISION,
    )
    facts = [
        FactRecordV2(
            fact_id=descriptive_fact_id(field, "fixture"),
            field=field,
            value=field_values.get(field, {"field": field}),
            source=source,
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field in REQUIRED_PRODUCT_FIELDS
    ]
    return ProductFactsV2(
        org_repo="org/repo",
        facts=facts,
        selected_fact_ids={
            field: descriptive_fact_id(field, "fixture") for field in REQUIRED_PRODUCT_FIELDS
        },
    )


# --- ComposerFactpack -------------------------------------------------------


def test_build_aspose_detection_bundle_real_data_cells_java():
    bundle = build_aspose_detection_bundle(
        "cells", "java", data_root=_DATA_ROOT, clone_cache=_DATA_ROOT
    )

    assert bundle.archetype.archetype == "transform"
    assert bundle.seo_keywords.entry_found is True
    assert bundle.install_info.source == "package_registry.json"
    assert bundle.homepage_link.verified is False


def test_build_composer_factpack_wraps_the_caller_supplied_product_facts_unchanged():
    product_facts = _ready_product_facts()

    factpack = build_composer_factpack(
        "cells",
        "java",
        data_root=_DATA_ROOT,
        clone_cache=_DATA_ROOT,
        product_facts=product_facts,
    )

    assert factpack.product_facts is product_facts
    assert factpack.family == "cells"
    assert factpack.platform == "java"


def test_composer_factpack_is_frozen_and_rejects_unknown_fields():
    factpack = build_composer_factpack(
        "cells",
        "java",
        data_root=_DATA_ROOT,
        clone_cache=_DATA_ROOT,
        product_facts=_ready_product_facts(),
    )

    with pytest.raises(ValidationError):
        ComposerFactpack(
            family="cells",
            platform="java",
            product_facts=_ready_product_facts(),
            aspose_detections=factpack.aspose_detections,
            unexpected_field="x",
        )
    with pytest.raises(ValidationError):
        factpack.family = "3d"  # type: ignore[misc]


# --- U7: per-source staleness/coverage findings -----------------------------


def test_assess_source_staleness_real_data_cells_java_shapes():
    bundle = build_aspose_detection_bundle(
        "cells", "java", data_root=_DATA_ROOT, clone_cache=_DATA_ROOT
    )

    findings = assess_source_staleness(
        bundle, family="cells", platform="java", data_root=_DATA_ROOT
    )

    by_id = {finding.source_id: finding for finding in findings}
    assert len(findings) == 7
    # keywords entry exists for cells/java -> full coverage, real source present.
    assert by_id["keywords/cells.json"].coverage == "full"
    assert by_id["keywords/cells.json"].present is True
    assert by_id["keywords/cells.json"].age_days is not None
    # content/products.aspose.org/ was never imported (TD-01 scope) -> always absent.
    assert by_id["content/products.aspose.org/"].present is False
    assert by_id["content/products.aspose.org/"].coverage == "absent"
    assert by_id["content/products.aspose.org/"].note is not None
    # package registry has a real entry for cells/java.
    assert by_id["data/package_registry.json"].coverage == "full"


def test_assess_source_staleness_absent_family_all_sources_degrade():
    bundle = build_aspose_detection_bundle(
        "nonexistent-family-xyz", "java", data_root=_DATA_ROOT, clone_cache=_DATA_ROOT
    )

    findings = assess_source_staleness(
        bundle, family="nonexistent-family-xyz", platform="java", data_root=_DATA_ROOT
    )

    by_id = {finding.source_id: finding for finding in findings}
    # keywords/nonexistent-family-xyz.json genuinely does not exist on disk.
    assert by_id["keywords/nonexistent-family-xyz.json"].present is False
    assert by_id["keywords/nonexistent-family-xyz.json"].coverage == "absent"
    # knowledge/.../merged/ directory does not exist for this family either.
    knowledge_id = "knowledge/nonexistent-family-xyz/java/merged/claims.json"
    assert by_id[knowledge_id].present is False
    assert by_id[knowledge_id].coverage == "absent"
    # data/package_registry.json, diagram_archetypes.json, and
    # diagram_capability_dependencies.json are present portfolio-wide files
    # with no entry for this family -> "partial", not "absent".
    assert by_id["data/package_registry.json"].coverage == "partial"
    assert by_id["data/diagram_archetypes.json"].coverage == "partial"
    assert by_id["data/diagram_capability_dependencies.json"].coverage == "partial"


def test_assess_source_staleness_missing_data_root_everything_absent(tmp_path):
    bundle = build_aspose_detection_bundle(
        "cells", "java", data_root=tmp_path, clone_cache=tmp_path
    )

    findings = assess_source_staleness(bundle, family="cells", platform="java", data_root=tmp_path)

    assert all(finding.present is False for finding in findings)
    assert all(finding.age_days is None for finding in findings)
    assert all(finding.stale is None for finding in findings)
    # coverage is "absent" for every source except the target map, whose
    # coverage comes from the enterprise-link detector's own
    # target_map_unavailable fallback classification, not a raw file check.
    assert {finding.coverage for finding in findings} == {"absent"}


def test_assess_source_staleness_flags_a_genuinely_old_source_file(tmp_path):
    keywords_dir = tmp_path / "keywords"
    keywords_dir.mkdir()
    keywords_path = keywords_dir / "cells.json"
    keywords_path.write_text("[]", encoding="utf-8")
    old_time = time.time() - (STALE_WARN_DAYS + 5) * 86400
    os.utime(keywords_path, (old_time, old_time))

    bundle = build_aspose_detection_bundle(
        "cells", "java", data_root=tmp_path, clone_cache=tmp_path
    )
    findings = assess_source_staleness(bundle, family="cells", platform="java", data_root=tmp_path)

    keywords_finding = next(f for f in findings if f.source_id == "keywords/cells.json")
    assert keywords_finding.present is True
    assert keywords_finding.age_days is not None
    assert keywords_finding.age_days > STALE_WARN_DAYS
    assert keywords_finding.stale is True


# --- EvidenceGroundedRenderViewV2 -------------------------------------------


def test_evidence_grounded_render_view_delegates_to_v1_and_preserves_its_citations():
    product_facts = _ready_product_facts(
        {"product.capabilities": ["Reads and writes files quickly"]}
    )
    factpack = build_composer_factpack(
        "cells",
        "java",
        data_root=_DATA_ROOT,
        clone_cache=_DATA_ROOT,
        product_facts=product_facts,
    )

    view = evidence_grounded_render_view(factpack, "product.capabilities")

    assert view is not None
    assert view.phrases == ["Reads and writes files quickly"]
    assert view.product_fact_citations == [descriptive_fact_id("product.capabilities", "fixture")]
    assert view.aspose_evidence_citations == []


def test_evidence_grounded_render_view_returns_none_when_v1_returns_none():
    """product.capabilities is a _VISITOR_REQUIRED_FIELDS entry -- V1 returns
    None when it has no renderable phrases, and the V2 delegation path must
    preserve that, not silently invent a grounded-but-empty view."""

    product_facts = _ready_product_facts({"product.capabilities": ["{not a real phrase}"]})
    factpack = build_composer_factpack(
        "cells",
        "java",
        data_root=_DATA_ROOT,
        clone_cache=_DATA_ROOT,
        product_facts=product_facts,
    )

    assert evidence_grounded_render_view(factpack, "product.capabilities") is None


def test_evidence_grounded_render_view_aspose_seo_keywords_real_data():
    factpack = build_composer_factpack(
        "cells",
        "java",
        data_root=_DATA_ROOT,
        clone_cache=_DATA_ROOT,
        product_facts=_ready_product_facts(),
    )

    view = evidence_grounded_render_view(factpack, "aspose.seo_keywords")

    assert view is not None
    assert len(view.phrases) > 0
    assert view.product_fact_citations == []
    assert len(view.aspose_evidence_citations) == 1
    assert view.aspose_evidence_citations[0].detector == "detect_seo_keywords"
    assert view.aspose_evidence_citations[0].source_id == "keywords/cells.json"


def test_evidence_grounded_render_view_aspose_dependency_claims_real_data():
    factpack = build_composer_factpack(
        "cells",
        "rust",
        data_root=_DATA_ROOT,
        clone_cache=_DATA_ROOT,
        product_facts=_ready_product_facts(),
    )

    view = evidence_grounded_render_view(factpack, "aspose.dependency_claims")

    assert view is not None
    assert len(view.phrases) == 7  # real data: cells/rust has 7 dependency claims
    assert all(isinstance(phrase, str) and phrase for phrase in view.phrases)
    assert view.aspose_evidence_citations[0].detector == "detect_dependency_claims"


def test_evidence_grounded_render_view_aspose_only_field_absent_returns_none():
    """cells/java has no dependency claims (data footprint verified in
    test_aspose_detectors.py) -- the aspose-only renderer must return None,
    never a grounded-but-empty view."""

    factpack = build_composer_factpack(
        "cells",
        "java",
        data_root=_DATA_ROOT,
        clone_cache=_DATA_ROOT,
        product_facts=_ready_product_facts(),
    )

    assert evidence_grounded_render_view(factpack, "aspose.dependency_claims") is None


def test_evidence_grounded_render_view_unknown_field_returns_none():
    factpack = build_composer_factpack(
        "cells",
        "java",
        data_root=_DATA_ROOT,
        clone_cache=_DATA_ROOT,
        product_facts=_ready_product_facts(),
    )

    assert evidence_grounded_render_view(factpack, "not_a_real_field") is None


def test_evidence_grounded_render_view_v2_rejects_phrases_with_no_citation():
    """RC1's actual control: a view carrying rendered phrases but zero
    grounding citations of either kind must fail construction, not silently
    pass through ungrounded prose."""

    with pytest.raises(ValidationError):
        EvidenceGroundedRenderViewV2(field="x", phrases=["some phrase"])


def test_evidence_grounded_render_view_v2_allows_empty_phrases_with_no_citation():
    view = EvidenceGroundedRenderViewV2(field="x", phrases=[])
    assert view.product_fact_citations == []
    assert view.aspose_evidence_citations == []
