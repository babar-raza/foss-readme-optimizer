"""Prove the verified Python canary cohort evidence producer fails closed."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from readme_agent.evidence.writer import refresh_sha256sums
from readme_agent.readme.document_hashing import sha256_hex

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "plans" / "investigations" / "tools" / "build_verified_python_canary_cohort.py"
SPEC = importlib.util.spec_from_file_location("build_verified_python_canary_cohort", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
cohort_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cohort_tool)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _candidate(title: str, *, license_benefits: bool = True) -> str:
    license_text = (
        "The MIT License permits use, modification, distribution, and commercial use."
        if license_benefits
        else "MIT."
    )
    return (
        f"# {title}\n\n![Platform](https://img.shields.io/badge/Platform-Python-blue)\n\n"
        "## Navigation\n\n"
        "- [At a glance](#at-a-glance)\n"
        "- [Key capabilities](#key-capabilities)\n"
        "- [License](#license)\n"
        "- [Scope and limitations](#scope-and-limitations)\n\n"
        "## At a glance\n\n```mermaid\nflowchart LR\n"
        f'  product["{title}"]\n```\n\n'
        "## Key capabilities\n\n- Render documents.\n\n"
        f"## License\n\n{license_text}\n\n"
        "## Scope and limitations\n\n- Bounded feature set.\n"
    )


def _bundle(tmp_path: Path, *, license_benefits: bool = True) -> tuple[str, Path]:
    org_repo = "example/Aspose.Note-FOSS-for-Python"
    bundle = tmp_path / "bundle"
    candidate = _candidate("Aspose.Note FOSS for Python", license_benefits=license_benefits)
    candidate_hash = sha256_hex(candidate)
    (bundle / "candidate").mkdir(parents=True)
    (bundle / "candidate" / "README.md").write_text(candidate, encoding="utf-8")
    _write_json(bundle / "facts" / "product-facts.json", {"schema_version": 2})
    _write_json(
        bundle / "planning" / "readme-document-plan.json",
        {
            "candidate_sha256": candidate_hash,
            "facts_hash": "f" * 64,
            "template_sha256": "t" * 64,
        },
    )
    _write_json(bundle / "review" / "deterministic-validation.json", {"verdict": "accept"})
    _write_json(
        bundle / "review" / "final-verdict.json",
        {"verdict": "AGENT_APPROVED", "agent_approved": True},
    )
    _write_json(bundle / "review" / "independent-agent-review.json", {"verdict": "accept"})
    _write_json(
        bundle / "review" / "no-op-proof.json",
        {
            "verdict": "NO_OP_PROVEN",
            "candidate_hash": candidate_hash,
            "new_provider_call_count": 0,
            "patch_created": False,
            "duplicate_bundle_created": False,
        },
    )
    _write_json(
        bundle / "manifest.json",
        {
            "org_repo": org_repo,
            "source_revision": "a" * 40,
            "content_assurance": "repository_verified",
            "complete": True,
            "lifecycle_status": "NO_OP_PROVEN",
            "candidate_hash": candidate_hash,
            "facts_hash": "f" * 64,
        },
    )
    refresh_sha256sums(bundle)
    return org_repo, bundle


def test_member_accepts_complete_repository_verified_bundle(tmp_path: Path) -> None:
    org_repo, bundle = _bundle(tmp_path)

    member, candidate, failures = cohort_tool.inspect_member(org_repo, bundle)

    assert failures == []
    assert member["checks"]["complete_list_navigation"] is True
    assert member["checks"]["license_benefits_visible"] is True
    assert member["checks"]["mermaid_uses_full_product_name"] is True
    assert candidate.startswith("# Aspose.Note FOSS for Python")


def test_member_rejects_bare_license_declaration(tmp_path: Path) -> None:
    org_repo, bundle = _bundle(tmp_path, license_benefits=False)

    member, _, failures = cohort_tool.inspect_member(org_repo, bundle)

    assert member["checks"]["license_benefits_visible"] is False
    assert f"{org_repo}:license_benefits_visible" in failures
