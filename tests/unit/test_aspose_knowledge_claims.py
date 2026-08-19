"""Knowledge-application layer, loading tier -- tested against the REAL
imported corpus (data/imported/knowledge/), not synthetic fixtures, mirroring
`test_aspose_detectors.py`'s convention."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.aspose_knowledge_claims import (
    assess_bundle_freshness,
    claims_by_kind,
    knowledge_bundle_dir,
    load_bundle_provenance,
    load_knowledge_claims,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_ROOT = _REPO_ROOT / "data" / "imported"


def test_load_knowledge_claims_real_corpus_returns_typed_claims():
    claims = load_knowledge_claims("3d", "python", data_root=_DATA_ROOT)

    assert len(claims) > 1000  # the real 3d/python bundle carries 3,452 claims
    assert all(claim.family == "3d" for claim in claims)
    assert all(claim.platform == "python" for claim in claims)
    assert all(claim.global_claim_id == f"3d/python/{claim.claim_id}" for claim in claims)


def test_load_knowledge_claims_covers_every_documented_kind_somewhere_in_the_corpus():
    """Every one of the 12 documented kinds is real, present data somewhere
    in the corpus -- proven against the whole tree, not asserted from one
    product (feature/license/dependency are sparse and not present in every
    bundle)."""

    all_kinds: set[str] = set()
    for family_dir in sorted(p for p in (_DATA_ROOT / "knowledge").iterdir() if p.is_dir()):
        for platform_dir in sorted(p for p in family_dir.iterdir() if p.is_dir()):
            claims = load_knowledge_claims(family_dir.name, platform_dir.name, data_root=_DATA_ROOT)
            all_kinds.update(claim.kind for claim in claims)

    expected = {
        "feature",
        "format_support",
        "format",
        "install",
        "license",
        "api",
        "api_class",
        "api_method",
        "api_field",
        "dependency",
        "limitation",
        "troubleshoot",
    }
    assert expected <= all_kinds


def test_load_knowledge_claims_absent_product_degrades_gracefully():
    claims = load_knowledge_claims(
        "nonexistent-family", "nonexistent-platform", data_root=_DATA_ROOT
    )

    assert claims == ()


def test_load_knowledge_claims_absent_data_root_degrades_gracefully(tmp_path):
    claims = load_knowledge_claims("3d", "python", data_root=tmp_path)

    assert claims == ()


def test_claims_by_kind_filters_correctly_on_real_data():
    claims = load_knowledge_claims("3d", "python", data_root=_DATA_ROOT)

    limitations = claims_by_kind(claims, "limitation")

    assert len(limitations) > 0
    assert all(claim.kind == "limitation" for claim in limitations)


def test_load_bundle_provenance_real_model_yaml():
    provenance = load_bundle_provenance("3d", "python", data_root=_DATA_ROOT)

    assert provenance is not None
    assert provenance.family == "3d"
    assert provenance.platform == "python"
    assert provenance.repo_sha is not None
    assert len(provenance.repo_sha) == 40  # a real git commit SHA
    assert provenance.repo_url is not None and "aspose-3d-foss" in provenance.repo_url


def test_load_bundle_provenance_absent_product_returns_none():
    provenance = load_bundle_provenance(
        "nonexistent-family", "nonexistent-platform", data_root=_DATA_ROOT
    )

    assert provenance is None


def test_knowledge_bundle_dir_shape():
    path = knowledge_bundle_dir("cells", "java", data_root=_DATA_ROOT)

    assert path == _DATA_ROOT / "knowledge" / "cells" / "java" / "merged"


def test_assess_bundle_freshness_current_when_repo_sha_matches():
    provenance = load_bundle_provenance("3d", "python", data_root=_DATA_ROOT)
    assert provenance is not None

    freshness = assess_bundle_freshness(provenance, current_repo_sha=provenance.repo_sha)

    assert freshness == "current"


def test_assess_bundle_freshness_stale_when_repo_sha_differs():
    provenance = load_bundle_provenance("3d", "python", data_root=_DATA_ROOT)
    assert provenance is not None

    freshness = assess_bundle_freshness(provenance, current_repo_sha="0" * 40)

    assert freshness == "stale_revision"


def test_assess_bundle_freshness_unknown_when_provenance_missing():
    assert assess_bundle_freshness(None, current_repo_sha="abc123") == "unknown_revision"


def test_assess_bundle_freshness_unknown_when_current_sha_missing():
    provenance = load_bundle_provenance("3d", "python", data_root=_DATA_ROOT)
    assert provenance is not None

    assert assess_bundle_freshness(provenance, current_repo_sha=None) == "unknown_revision"
