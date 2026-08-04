"""Checksum and revision boundaries for deterministic truth salvage hints."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from readme_agent.evidence.writer import refresh_sha256sums
from readme_agent.facts.deterministic_truth_salvage import (
    _dependent_product_source_block_category,
    _finding,
    _repository_enriched_technical_facts,
    _verified_example_fact,
    load_salvage_candidate,
)
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, ProductFactsV2
from readme_agent.facts.verified_repository_examples import RepositoryExampleSelectionV2
from readme_agent.registry.models import ProductTruthPolicy

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


def test_normalized_display_literal_is_the_exact_code_sent_to_local_verification(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate = _candidate()
    candidate["minimal_example"]["code"] = (
        'from aspose_pdf import Document\nprint("Hello from Aspose.PDF FOSS!")'
    )
    identity = FactRecordV2(
        fact_id="product.identity:verified",
        field="product.identity",
        value={"product_name": "Aspose.PDF", "platform": "python"},
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="pyproject.toml",
            source_revision=CURRENT_REVISION,
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    facts = ProductFactsV2.model_construct(
        schema_version=2,
        content_assurance="repository_verified",
        org_repo=ORG_REPO,
        facts=[identity],
        selected_fact_ids={"product.identity": identity.fact_id},
        package_root_roles=None,
    )
    captured = {}

    def verify(_snapshot, example):
        captured["code"] = example.code
        return SimpleNamespace(
            detail="controlled non-truth-eligible result",
            truth_eligible=False,
            outcome="BUILD_FAILED",
            fact_projection=lambda: {},
        )

    monkeypatch.setattr(
        "readme_agent.facts.deterministic_truth_salvage.evidence_failures",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "readme_agent.facts.deterministic_truth_salvage.generated_example_quality_failures",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "readme_agent.facts.deterministic_truth_salvage.local_fact_verification_allowed",
        lambda: True,
    )
    monkeypatch.setattr(
        "readme_agent.facts.deterministic_truth_salvage.verify_local_product_example",
        verify,
    )

    fact, _verification = _verified_example_fact(
        SimpleNamespace(
            root_path=tmp_path,
            source_revision=CURRENT_REVISION,
        ),
        ProductTruthPolicy.model_validate(candidate),
        facts,
        "2026-08-03T00:00:00+00:00",
    )

    expected = 'from aspose_pdf import Document\nprint("Hello from Aspose.PDF FOSS for Python!")'
    assert captured["code"] == expected
    assert fact.value["code"] == expected


def test_terminal_repository_source_failure_replaces_malformed_draft_without_approval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate = _candidate()
    candidate["minimal_example"] = {
        "language": "python",
        "class_name": "Draft",
        "code": "for broken in",
        "evidence_paths": ["README.md"],
    }
    repository_example = ProductTruthPolicy.model_validate(
        {
            **candidate,
            "minimal_example": {
                "language": "python",
                "class_name": "RepositoryExample",
                "code": "from aspose_tex import Engine\nprint(Engine)",
                "evidence_paths": ["README.md"],
            },
        }
    ).minimal_example
    terminal = LocalProductVerificationV1.model_construct(
        schema_version=1,
        org_repo=ORG_REPO,
        source_revision=CURRENT_REVISION,
        detail="product import failed: IndentationError in src/aspose_tex/_input/catcode.py",
        truth_eligible=False,
        outcome="BUILD_FAILED",
        ecosystem="python",
        build=SimpleNamespace(return_code=21, stdout="", stderr=""),
        example_compile=None,
        isolated_execution=SimpleNamespace(return_code=21, truth_eligible=False),
    )
    identity = FactRecordV2(
        fact_id="product.identity:verified",
        field="product.identity",
        value={"product_name": "Aspose.TeX", "platform": "python"},
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="pyproject.toml",
            source_revision=CURRENT_REVISION,
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme"],
    )
    facts = ProductFactsV2.model_construct(
        schema_version=2,
        content_assurance="repository_verified",
        org_repo=ORG_REPO,
        facts=[identity],
        selected_fact_ids={"product.identity": identity.fact_id},
        package_root_roles=None,
    )
    monkeypatch.setattr(
        "readme_agent.facts.deterministic_truth_salvage.evidence_failures",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "readme_agent.facts.deterministic_truth_salvage.generated_example_quality_failures",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        "readme_agent.facts.deterministic_truth_salvage.local_fact_verification_allowed",
        lambda: True,
    )
    monkeypatch.setattr(
        "readme_agent.facts.deterministic_truth_salvage.verify_local_product_example",
        lambda *_args: SimpleNamespace(
            detail="malformed draft",
            truth_eligible=False,
            outcome="BUILD_FAILED",
            ecosystem="python",
            isolated_execution=SimpleNamespace(return_code=22),
            fact_projection=lambda: {},
        ),
    )
    monkeypatch.setattr(
        "readme_agent.facts.deterministic_truth_salvage.select_verified_repository_example",
        lambda *_args, **_kwargs: RepositoryExampleSelectionV2(
            outcome="TERMINAL_PRODUCT_FAILURE",
            example=repository_example,
            verification=terminal,
            candidate_count=2,
            attempted_count=1,
            selected_rank=1,
        ),
    )

    fact, verification = _verified_example_fact(
        SimpleNamespace(root_path=tmp_path, source_revision=CURRENT_REVISION),
        ProductTruthPolicy.model_validate(candidate),
        facts,
        "2026-08-03T00:00:00+00:00",
    )
    finding = _finding(fact)

    assert verification is terminal
    assert fact.verification_state == "blocked"
    assert fact.value["code"] == repository_example.code
    assert fact.value["verification_detail"] == terminal.detail
    assert fact.value["blocked_category"] == "infra_external"
    assert fact.value["repairable_by_example_change"] is False
    assert finding["blocked_category"] == "infra_external"
    assert "product-owned source/import defect" in finding["required_action"]
    acquisition = fact.model_copy(
        update={
            "fact_id": "installation.verified_acquisition:blocked-source-build",
            "field": "installation.verified_acquisition",
            "value": {
                "source_revision": CURRENT_REVISION,
                "method": "source_build",
                "outcome": "BUILD_FAILED",
                "truth_eligible": False,
            },
        }
    )
    inherited = _dependent_product_source_block_category(acquisition, fact, CURRENT_REVISION)
    acquisition_finding = _finding(acquisition, blocked_category_override=inherited)
    assert acquisition_finding["blocked_category"] == "infra_external"
    assert "product-owned source/import defect" in acquisition_finding["required_action"]
    unrelated = acquisition.model_copy(
        update={"value": {**acquisition.value, "outcome": "BLOCKED_NETWORK"}}
    )
    unrelated_inherited = _dependent_product_source_block_category(
        unrelated, fact, CURRENT_REVISION
    )
    unrelated_finding = _finding(unrelated, blocked_category_override=unrelated_inherited)
    assert unrelated_inherited is None
    assert unrelated_finding["blocked_category"] == "agent_fixable"
    assert "supply a current-revision repository" in unrelated_finding["required_action"]


def test_repository_extensions_enrich_only_selected_verified_technical_facts() -> None:
    source = FactSourceV2(
        source_type="mechanical_repository",
        location="repository://source.py,tests/test_source.py",
        source_revision=CURRENT_REVISION,
    )
    detail = FactRecordV2(
        fact_id="repository.capability_details:python-public-source-surfaces",
        field="repository.capability_details",
        value={
            "input_formats": ["PDF"],
            "output_formats": ["PDF", "PNG", "TIFF"],
            "capability_groups": [
                {"label": "Render PDF pages to PNG or TIFF images"},
                {"label": "Extract text, images, and attachments"},
            ],
        },
        source=source,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.capabilities"],
    )
    boundaries = FactRecordV2(
        fact_id="repository.verified_boundaries:authoritative-source-and-tests",
        field="repository.verified_boundaries",
        value={"boundaries": ["OCR is not implemented.", "Rendering is best effort."]},
        source=source,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=["readme.limitations"],
    )
    base = ProductFactsV2.model_construct(
        schema_version=2,
        content_assurance="repository_verified",
        org_repo=ORG_REPO,
        facts=[detail, boundaries],
        selected_fact_ids={
            detail.field: detail.fact_id,
            boundaries.field: boundaries.fact_id,
        },
        package_root_roles=None,
    )
    technical = {
        field: FactRecordV2(
            fact_id=f"{field}:policy",
            field=field,
            value=value,
            source=source,
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["readme"],
        )
        for field, value in {
            "product.capabilities": ["Document lifecycle management"],
            "product.formats": ["Input format: PDF", "Output format: PDF"],
            "product.limitations": ["OCR is not implemented."],
        }.items()
    }

    enriched = _repository_enriched_technical_facts(base, technical)

    assert enriched["product.capabilities"].value == [
        "Render PDF pages to PNG or TIFF images",
        "Extract text, images, and attachments",
        "Document lifecycle management",
    ]
    assert enriched["product.formats"].value == [
        "Input format: PDF",
        "Output format: PDF",
        "Output format: PNG",
        "Output format: TIFF",
    ]
    assert enriched["product.limitations"].value == [
        "OCR is not implemented.",
        "Rendering is best effort.",
    ]
    assert all(fact.source.source_type == "mechanical_repository" for fact in enriched.values())


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
