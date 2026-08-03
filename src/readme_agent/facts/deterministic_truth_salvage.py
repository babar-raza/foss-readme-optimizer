"""Revalidate historical product-truth candidates without provider calls."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.evidence.writer import verify_sha256sums
from readme_agent.facts.acquisition_facts import reconcile_acquisition_fact
from readme_agent.facts.aspose_org_format_adapter import extract_aspose_org_formats
from readme_agent.facts.example_quality import generated_example_quality_failures
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.format_direction import directional_format_fact_from_verified_evidence
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.policy_evidence import (
    evidence_fact_candidate,
    evidence_failures,
    limitation_fact_candidate,
)
from readme_agent.facts.problem_grounding import derive_grounded_problem_fallback
from readme_agent.facts.render_views import ecosystem_display_label
from readme_agent.facts.schema_v2 import (
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.registry.loader import require_listed
from readme_agent.registry.models import ProductTruthPolicy
from readme_agent.repository_snapshot import (
    RepositorySnapshotV1,
    local_fact_verification_allowed,
)


class DeterministicTruthSalvageV1(BaseModel):
    """Current-revision facts revalidated from a non-authoritative candidate."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    facts: ProductFactsV2
    candidate_sha256: str
    reused_fields: list[str]
    findings: list[dict] = Field(default_factory=list)


def load_salvage_candidate(
    bundle_dir: Path,
    *,
    org_repo: str,
    source_revision: str,
    current_readme_sha256: str | None = None,
) -> dict | None:
    """Load an exact candidate or a README-identical historical hint candidate."""

    exact = _load_bound_candidate(
        bundle_dir,
        org_repo=org_repo,
        expected_revision=source_revision,
        expected_readme_sha256=current_readme_sha256,
    )
    if exact is not None or current_readme_sha256 is None:
        return exact
    if len(current_readme_sha256) != 64 or any(
        character not in "0123456789abcdef" for character in current_readme_sha256
    ):
        return None
    repository_bundle_dir = bundle_dir.parent
    if not repository_bundle_dir.is_dir():
        return None
    for historical_dir in sorted(repository_bundle_dir.iterdir(), reverse=True):
        if (
            historical_dir == bundle_dir
            or not historical_dir.is_dir()
            or len(historical_dir.name) != 40
            or any(character not in "0123456789abcdef" for character in historical_dir.name)
        ):
            continue
        candidate = _load_bound_candidate(
            historical_dir,
            org_repo=org_repo,
            expected_revision=historical_dir.name,
            expected_readme_sha256=current_readme_sha256,
        )
        if candidate is not None:
            return candidate
    return None


def _load_bound_candidate(
    bundle_dir: Path,
    *,
    org_repo: str,
    expected_revision: str,
    expected_readme_sha256: str | None,
) -> dict | None:
    """Validate one candidate's repository, revision, README identity, and inventory."""

    manifest_path = bundle_dir / "manifest.json"
    proposal_path = bundle_dir / "facts" / "proposed-product-truth.json"
    revision_path = bundle_dir / "source" / "revision.json"
    if (
        not manifest_path.is_file()
        or not proposal_path.is_file()
        or not revision_path.is_file()
        or not verify_sha256sums(bundle_dir)
    ):
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        candidate = json.loads(proposal_path.read_text(encoding="utf-8"))
        revision = json.loads(revision_path.read_text(encoding="utf-8"))
        ProductTruthPolicy.model_validate(candidate)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None
    if (
        manifest.get("org_repo") != org_repo
        or manifest.get("source_revision") != expected_revision
        or revision.get("org_repo") != org_repo
        or revision.get("source_revision") != expected_revision
        or (
            expected_readme_sha256 is not None
            and revision.get("readme_sha256") != expected_readme_sha256
        )
        or not isinstance(candidate, dict)
    ):
        return None
    return candidate


def _replace_selected(
    facts: ProductFactsV2,
    replacements: dict[str, FactRecordV2],
) -> ProductFactsV2:
    retained = [fact for fact in facts.facts if fact.field not in replacements]
    retained.extend(replacements.values())
    selected = dict(facts.selected_fact_ids)
    selected.update({field: fact.fact_id for field, fact in replacements.items()})
    return ProductFactsV2(
        org_repo=facts.org_repo,
        facts=retained,
        selected_fact_ids=selected,
        package_root_roles=facts.package_root_roles,
    )


def _verified_example_fact(
    snapshot: RepositorySnapshotV1,
    truth: ProductTruthPolicy,
    observed_at: str,
) -> tuple[FactRecordV2, LocalProductVerificationV1 | None]:
    example = truth.minimal_example
    failures = evidence_failures(
        snapshot.root_path,
        example.evidence_paths,
        example.required_symbols,
        allow_partial_symbols=True,
    )
    failures.extend(generated_example_quality_failures(example.language, example.code))
    verification = None
    if not failures and local_fact_verification_allowed():
        verification = verify_local_product_example(snapshot, example)
    if failures:
        detail = "; ".join(failures)
    elif verification is None:
        detail = "local example verification is disabled for this execution profile"
    else:
        detail = verification.detail
    verified = bool(
        verification is not None
        and verification.truth_eligible
        and verification.outcome == "SOURCE_BUILD_VERIFIED"
    )
    value = {
        "language": example.language,
        "class_name": example.class_name,
        "code": example.code,
        "verification_outcome": (
            verification.outcome if verification is not None else "BLOCKED_LOCAL_VERIFICATION"
        ),
        "verification_detail": detail,
        **(
            verification.fact_projection()
            if verification is not None
            else {
                "verified_public_symbols": [],
                "input_fixture_bindings": [],
                "public_api_sha256": None,
                "python_package": None,
                "typescript_package": None,
                "rust_package": None,
                "rust_formats": [],
                "rust_source_dependency": None,
            }
        ),
    }
    fact = FactRecordV2(
        fact_id=descriptive_fact_id(
            "example.minimal",
            "compiled-salvaged-example" if verified else "salvaged-example-blocked",
        ),
        field="example.minimal",
        value=value,
        source=FactSourceV2(
            source_type="mechanical_test",
            location="local-verifier://example.minimal",
            source_revision=snapshot.source_revision,
        ),
        verification_state="verified" if verified else "blocked",
        authoritative_owner="repository-owner",
        confidence=1.0 if verified else 0.0,
        affected_surfaces=SURFACE_DEPENDENCIES["example.minimal"],
    )
    return fact, verification


def _finding(fact: FactRecordV2) -> dict:
    return {
        "finding_id": f"deterministic-salvage:{fact.field}",
        "classification": "BLOCKED_MISSING_EVIDENCE",
        "blocked_category": "agent_fixable",
        "field": fact.field,
        "detail": fact.value,
        "required_action": (
            "supply a current-revision repository or structured-knowledge candidate and "
            "rerun deterministic revalidation"
        ),
    }


def salvage_product_truth_candidate(
    base_facts: ProductFactsV2,
    snapshot: RepositorySnapshotV1,
    candidate: dict,
) -> DeterministicTruthSalvageV1:
    """Treat candidate prose as hints and re-prove every accepted field."""

    truth = ProductTruthPolicy.model_validate(candidate)
    observed_at = datetime.now(UTC).isoformat()
    example_fact, local_verification = _verified_example_fact(snapshot, truth, observed_at)
    entry = require_listed(base_facts.org_repo)
    acquisition_fact = reconcile_acquisition_fact(
        entry,
        base_facts.selected_fact("installation.verified_acquisition"),
        local_verification,
        observed_at=observed_at,
    )
    native_formats = extract_aspose_org_formats(
        snapshot.root_path,
        platform=entry.platform,
        family=entry.family,
        source_revision=snapshot.source_revision,
    )
    technical = {
        "product.capabilities": evidence_fact_candidate(
            snapshot.root_path,
            snapshot.source_revision,
            observed_at,
            "product.capabilities",
            truth.capabilities,
            allow_partial=True,
        ),
        "product.formats": directional_format_fact_from_verified_evidence(
            source_revision=snapshot.source_revision,
            specifications=truth.formats,
            example_fact=example_fact,
            native_extraction=native_formats,
        ),
        "product.limitations": limitation_fact_candidate(
            snapshot.root_path,
            snapshot.source_revision,
            observed_at,
            truth.limitations,
            allow_partial=True,
        ),
    }
    grounded = _replace_selected(base_facts, technical)
    platform = grounded.selected_fact("product.platforms")
    platforms = platform.value if isinstance(platform.value, list) else [platform.value]
    platform_name = next((str(value).strip() for value in platforms if str(value).strip()), "")
    audience = FactRecordV2(
        fact_id=descriptive_fact_id("product.audience", "platform-derived"),
        field="product.audience",
        value=[f"Developers using {ecosystem_display_label(platform_name)}."],
        source=platform.source,
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        supporting_fact_ids=[platform.fact_id],
        affected_surfaces=SURFACE_DEPENDENCIES["product.audience"],
    )
    problem_fallback = derive_grounded_problem_fallback(
        grounded,
        snapshot.source_revision,
        observed_at,
    )
    problems = (
        problem_fallback[1].model_copy(
            update={
                "fact_id": descriptive_fact_id("product.problems_solved", "capability-derived"),
                "source": grounded.selected_fact("product.capabilities").source,
            }
        )
        if problem_fallback is not None
        else FactRecordV2(
            fact_id=descriptive_fact_id("product.problems_solved", "salvage-blocked"),
            field="product.problems_solved",
            value={"evidence_failures": ["no verified capability fact to derive from"]},
            source=FactSourceV2(
                source_type="mechanical_repository",
                location=f"repository://{base_facts.org_repo}",
                source_revision=snapshot.source_revision,
            ),
            verification_state="blocked",
            authoritative_owner="repository-owner",
            confidence=0.0,
            affected_surfaces=SURFACE_DEPENDENCIES["product.problems_solved"],
        )
    )
    replacements = {
        **technical,
        "product.audience": audience,
        "product.problems_solved": problems,
        "example.minimal": example_fact,
        "installation.verified_acquisition": acquisition_fact,
    }
    facts = _replace_selected(base_facts, replacements)
    findings = [
        _finding(fact)
        for fact in replacements.values()
        if fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
    ]
    encoded = json.dumps(candidate, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return DeterministicTruthSalvageV1(
        facts=facts,
        candidate_sha256=hashlib.sha256(encoded).hexdigest(),
        reused_fields=sorted(
            field
            for field, fact in replacements.items()
            if fact.verification_state in {"verified", "policy_approved"}
            and not fact.has_unresolved_conflict
        ),
        findings=findings,
    )
