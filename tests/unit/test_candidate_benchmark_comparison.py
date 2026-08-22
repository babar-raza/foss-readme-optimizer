"""Candidate benchmark comparison remains local, bounded, and non-authoritative."""

import json

import pytest

from readme_agent.presentation.candidate_benchmark_comparison import (
    build_candidate_benchmark_comparison,
    load_benchmark_quality_profile,
)


def _profile(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(
        json.dumps(
            {
                "profile_type": "BenchmarkQualityProfileV1",
                "state": "BENCHMARK_PROFILE_FROZEN",
                "runtime_dependency_on_aspose_org": False,
                "snapshot_sha256": "a" * 64,
                "dimensions": [
                    {
                        "dimension_id": "product_specificity",
                        "disposition": "accepted",
                        "obligation": "Use repository-specific facts.",
                    },
                    {
                        "dimension_id": "benchmark_claim_authority",
                        "disposition": "quarantined",
                        "obligation": "Never treat benchmark claims as facts.",
                    },
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_committed_profile_is_the_exact_qualified_pf01_copy():
    profile, digest = load_benchmark_quality_profile()

    assert digest == "8881d3d4859a66173178b9b641693d0fbd81c690ea9786e04c2633ad8b776d35"
    assert len(profile["dimensions"]) == 17
    assert profile["snapshot_sha256"] == (
        "0f4571f698b3fb9d49003bb8e16b44776e64dc6e1a5571c94c53e5cc59ae058d"
    )


def test_comparison_binds_local_evidence_without_granting_acceptance(tmp_path):
    bundle = tmp_path / "bundle"
    for relative in ("candidate/claim-map.json", "assessment/evidence-map.json"):
        path = bundle / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")

    comparison = build_candidate_benchmark_comparison(
        repository="acme/widget",
        source_revision="1" * 40,
        candidate_sha256="2" * 64,
        bundle_dir=bundle,
        profile_path=_profile(tmp_path),
    )

    assert comparison.acceptance_status == "PENDING_DETERMINISTIC_AND_INDEPENDENT_REVIEW"
    assert comparison.benchmark_prose_used is False
    assert comparison.runtime_dependency_on_aspose_org is False
    assert comparison.dimensions[0].status == "EVIDENCE_BOUND_PENDING_ACCEPTANCE"
    assert comparison.dimensions[1].status == "QUARANTINED_NOT_FACT_AUTHORITY"


def test_comparison_fails_closed_when_candidate_evidence_is_missing(tmp_path):
    with pytest.raises(ValueError, match="lacks candidate evidence"):
        build_candidate_benchmark_comparison(
            repository="acme/widget",
            source_revision="1" * 40,
            candidate_sha256="2" * 64,
            bundle_dir=tmp_path / "missing",
            profile_path=_profile(tmp_path),
        )


def test_inherited_content_benchmark_rejects_error_shaped_reconciliation(tmp_path):
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_type": "BenchmarkQualityProfileV1",
                "state": "BENCHMARK_PROFILE_FROZEN",
                "runtime_dependency_on_aspose_org": False,
                "snapshot_sha256": "a" * 64,
                "dimensions": [
                    {
                        "dimension_id": "inherited_content_accountability",
                        "disposition": "accepted",
                        "obligation": "Account for every inherited source byte.",
                    }
                ],
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    bundle = tmp_path / "bundle"
    for relative in (
        "assessment/evidence-map.json",
        "candidate/readme-reconciliation.json",
    ):
        path = bundle / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"schema_version":1,"error":"overlap"}\n', encoding="utf-8")

    with pytest.raises(ValueError):
        build_candidate_benchmark_comparison(
            repository="acme/widget",
            source_revision="1" * 40,
            candidate_sha256="2" * 64,
            bundle_dir=bundle,
            profile_path=profile_path,
        )
