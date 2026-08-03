"""Checksum and revision boundaries for deterministic truth salvage hints."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums
from readme_agent.facts.deterministic_truth_salvage import load_salvage_candidate

ORG_REPO = "acme/widget"
CURRENT_REVISION = "b" * 40
PRIOR_REVISION = "a" * 40
README_SHA256 = "c" * 64


def test_loads_checksum_valid_historical_candidate_only_for_identical_readme(
    tmp_path: Path,
) -> None:
    current = tmp_path / CURRENT_REVISION
    current.mkdir()
    candidate = _candidate()
    prior = _write_bundle(tmp_path, PRIOR_REVISION, candidate=candidate)

    loaded = load_salvage_candidate(
        current,
        org_repo=ORG_REPO,
        source_revision=CURRENT_REVISION,
        current_readme_sha256=README_SHA256,
    )
    mismatched = load_salvage_candidate(
        current,
        org_repo=ORG_REPO,
        source_revision=CURRENT_REVISION,
        current_readme_sha256="d" * 64,
    )
    (prior / "facts" / "proposed-product-truth.json").write_text("{}\n", encoding="utf-8")
    tampered = load_salvage_candidate(
        current,
        org_repo=ORG_REPO,
        source_revision=CURRENT_REVISION,
        current_readme_sha256=README_SHA256,
    )

    assert loaded == candidate
    assert mismatched is None
    assert tampered is None


def test_rejects_historical_candidate_bound_to_another_repository(tmp_path: Path) -> None:
    current = tmp_path / CURRENT_REVISION
    current.mkdir()
    _write_bundle(tmp_path, PRIOR_REVISION, candidate=_candidate(), org_repo="other/widget")

    assert (
        load_salvage_candidate(
            current,
            org_repo=ORG_REPO,
            source_revision=CURRENT_REVISION,
            current_readme_sha256=README_SHA256,
        )
        is None
    )


def test_missing_repository_bundle_parent_fails_closed(tmp_path: Path) -> None:
    missing_current = tmp_path / "missing-repository" / CURRENT_REVISION

    assert (
        load_salvage_candidate(
            missing_current,
            org_repo=ORG_REPO,
            source_revision=CURRENT_REVISION,
            current_readme_sha256=README_SHA256,
        )
        is None
    )


def _write_bundle(
    root: Path,
    revision: str,
    *,
    candidate: dict,
    org_repo: str = ORG_REPO,
) -> Path:
    bundle = root / revision
    (bundle / "facts").mkdir(parents=True)
    (bundle / "source").mkdir()
    (bundle / "manifest.json").write_text(
        json.dumps({"org_repo": org_repo, "source_revision": revision}) + "\n",
        encoding="utf-8",
    )
    (bundle / "facts" / "proposed-product-truth.json").write_text(
        json.dumps(candidate) + "\n", encoding="utf-8"
    )
    (bundle / "source" / "revision.json").write_text(
        json.dumps(
            {
                "org_repo": org_repo,
                "source_revision": revision,
                "readme_sha256": README_SHA256,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    refresh_sha256sums(bundle)
    return bundle


def _candidate() -> dict:
    evidence = {"value": "Process widgets", "evidence_paths": ["src/Widget.cs"]}
    return {
        "audience": ["Developers"],
        "problems_solved": ["Process widgets"],
        "capabilities": [evidence],
        "formats": [{"value": "Input format: WGT", "evidence_paths": ["src/Widget.cs"]}],
        "limitations": [],
        "minimal_example": {
            "language": "dotnet",
            "class_name": "Program",
            "code": "var widget = new Widget();",
            "evidence_paths": ["src/Widget.cs"],
        },
    }
