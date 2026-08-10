"""Revalidate historical product-truth candidates without provider calls."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.evidence.writer import verify_sha256sums
from readme_agent.facts.acquisition_facts import reconcile_acquisition_fact
from readme_agent.facts.example_branding import (
    full_product_display_name,
    normalize_example_display_literals,
)
from readme_agent.facts.example_quality import generated_example_quality_failures
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.format_direction import directional_format_fact_from_verified_evidence
from readme_agent.facts.interpretive_resolution import replace_selected_for_regrounding
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.policy_evidence import (
    evidence_fact_candidate,
    evidence_failures,
    limitation_fact_candidate,
)
from readme_agent.facts.problem_grounding import derive_grounded_problem_fallback
from readme_agent.facts.render_views import ecosystem_display_label
from readme_agent.facts.repository_format_extraction import extract_repository_format_directions
from readme_agent.facts.schema_v2 import (
    FactRecordV2,
    FactSourceV2,
    ProductFactsV2,
    descriptive_fact_id,
)
from readme_agent.facts.verified_repository_examples import (
    bounded_local_verification_detail,
    select_verified_repository_example,
)
from readme_agent.registry.loader import require_listed
from readme_agent.registry.models import MinimalExamplePolicy, ProductTruthPolicy
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
    """Load an exact candidate or a checksum-valid historical hint candidate."""

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
    historical_dirs = [
        historical_dir
        for historical_dir in sorted(repository_bundle_dir.iterdir(), reverse=True)
        if (
            historical_dir != bundle_dir
            and historical_dir.is_dir()
            and len(historical_dir.name) == 40
            and all(character in "0123456789abcdef" for character in historical_dir.name)
        )
    ]
    # Prefer a README-identical hint. If the README alone moved, an older candidate is
    # still non-authoritative input: salvage_product_truth_candidate re-proves every
    # accepted field against the current immutable repository snapshot.
    for historical_dir in historical_dirs:
        candidate = _load_bound_candidate(
            historical_dir,
            org_repo=org_repo,
            expected_revision=historical_dir.name,
            expected_readme_sha256=current_readme_sha256,
        )
        if candidate is not None:
            return candidate
    for historical_dir in historical_dirs:
        candidate = _load_bound_candidate(
            historical_dir,
            org_repo=org_repo,
            expected_revision=historical_dir.name,
            expected_readme_sha256=None,
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
    return replace_selected_for_regrounding(facts, replacements)


def _repository_enriched_technical_facts(
    base_facts: ProductFactsV2,
    technical: dict[str, FactRecordV2],
) -> dict[str, FactRecordV2]:
    """Project exact repository extension facts into the selected product fields."""

    try:
        detail = base_facts.selected_fact("repository.capability_details")
    except KeyError:
        detail = None
    try:
        implementation = base_facts.selected_fact("repository.implementation_components")
    except KeyError:
        implementation = None
    try:
        boundaries = base_facts.selected_fact("repository.verified_boundaries")
    except KeyError:
        boundaries = None
    try:
        source_limitations = base_facts.selected_fact("product.limitations")
    except KeyError:
        source_limitations = None
    try:
        format_directions = base_facts.selected_fact("repository.format_directions")
    except KeyError:
        format_directions = None
    try:
        public_api = base_facts.selected_fact("api.public_surface")
    except KeyError:
        public_api = None
    detail_value = (
        detail.value
        if detail is not None
        and detail.verification_state == "verified"
        and not detail.has_unresolved_conflict
        and isinstance(detail.value, dict)
        else {}
    )
    boundary_value = (
        boundaries.value
        if boundaries is not None
        and boundaries.verification_state == "verified"
        and not boundaries.has_unresolved_conflict
        and isinstance(boundaries.value, dict)
        else {}
    )

    def extension_fact(
        field: str,
        values: list[str],
        extension: FactRecordV2,
        *,
        include_primary_source: bool = True,
    ) -> FactRecordV2:
        primary = technical[field]
        locations = sorted(
            {
                extension.source.location,
                *([primary.source.location] if include_primary_source else []),
            }
        )
        return FactRecordV2(
            fact_id=descriptive_fact_id(field, "repository-extension"),
            field=field,
            value=values,
            source=FactSourceV2(
                source_type="mechanical_repository",
                location=";".join(locations),
                source_revision=extension.source.source_revision,
                retrieved_at=extension.source.retrieved_at,
            ),
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=SURFACE_DEPENDENCIES[field],
        )

    capability_extensions = [
        extension
        for extension in (detail, implementation)
        if extension is not None
        and extension.verification_state == "verified"
        and not extension.has_unresolved_conflict
        and isinstance(extension.value, dict)
        and isinstance(extension.value.get("capability_groups"), list)
    ]
    detailed = list(
        dict.fromkeys(
            str(item.get("label") or "").strip()
            for extension in capability_extensions
            for item in extension.value["capability_groups"]
            if isinstance(item, dict) and str(item.get("label") or "").strip()
        )
    )
    api_capabilities: list[str] = []
    if (
        public_api is not None
        and public_api.verification_state == "verified"
        and not public_api.has_unresolved_conflict
        and isinstance(public_api.value, dict)
    ):
        api_names = {
            str(export).casefold()
            for module in public_api.value.get("modules", [])
            if isinstance(module, dict) and isinstance(module.get("exports"), list)
            for export in module["exports"]
            if isinstance(export, str)
        }
        api_names.update(
            str(item.get("name") or "").casefold()
            for item in public_api.value.get("classes", [])
            if isinstance(item, dict) and str(item.get("name") or "").strip()
        )
        export_formats = [
            label
            for token, label in (("csv", "CSV"), ("json", "JSON"), ("markdown", "Markdown"))
            if any(
                name in api_names for name in (f"save_workbook_as_{token}", f"{token}saveoptions")
            )
        ]
        if len(export_formats) >= 2:
            api_capabilities.append(
                "Export workbooks to "
                + ", ".join(export_formats[:-1])
                + f", and {export_formats[-1]}"
            )
        if {"encrypt_xlsx", "decrypt_xlsx"}.issubset(api_names) or {
            "agileencryptionparameters",
            "standardencryptionparameters",
        }.intersection(api_names):
            api_capabilities.append(
                "Encrypt and decrypt XLSX workbooks with AES password protection"
            )
    detailed.extend(item for item in api_capabilities if item not in detailed)
    capability_source = capability_extensions[0] if capability_extensions else public_api
    if detailed and capability_source is not None:
        existing = technical["product.capabilities"].value
        existing = existing if isinstance(existing, list) else [existing]
        capabilities = list(dict.fromkeys([*detailed, *(str(item) for item in existing)]))
        technical["product.capabilities"] = extension_fact(
            "product.capabilities", capabilities, capability_source
        )

    if detail is not None:
        input_formats = detail_value.get("input_formats")
        output_formats = detail_value.get("output_formats")
        directional = [
            *(f"Input format: {item}" for item in input_formats or []),
            *(f"Output format: {item}" for item in output_formats or []),
        ]
        if directional:
            technical["product.formats"] = extension_fact(
                "product.formats",
                list(dict.fromkeys(directional)),
                detail,
                include_primary_source=False,
            )

    direction_value = (
        format_directions.value
        if format_directions is not None
        and format_directions.verification_state == "verified"
        and not format_directions.has_unresolved_conflict
        and isinstance(format_directions.value, dict)
        else {}
    )
    raw_directions = direction_value.get("directions")
    if format_directions is not None and isinstance(raw_directions, list):
        supported = {
            (str(item.get("direction")), str(item.get("format")).casefold()): str(
                item.get("format")
            )
            for item in raw_directions
            if isinstance(item, dict)
            and item.get("direction") in {"input", "output"}
            and str(item.get("format") or "").strip()
        }
        current = technical["product.formats"].value
        refined: list[str] = []
        for value in current if isinstance(current, list) else []:
            match = re.match(r"(?i)^(input|output)\s+format:\s*([A-Za-z0-9]+)", str(value))
            if match is None:
                continue
            direction, token = match.group(1).casefold(), match.group(2).casefold()
            canonical = supported.get((direction, token))
            if canonical is not None:
                refined.append(f"{direction.title()} format: {canonical}")
        if refined:
            technical["product.formats"] = extension_fact(
                "product.formats",
                list(dict.fromkeys(refined)),
                format_directions,
            )

    if (
        source_limitations is not None
        and source_limitations.verification_state == "verified"
        and not source_limitations.has_unresolved_conflict
        and isinstance(source_limitations.value, list)
        and source_limitations.value
    ):
        # A current-revision repository collector outranks the candidate draft. In
        # particular, an empty drafted limitations list must never erase explicit
        # source constraints that the base graph already proved.
        technical["product.limitations"] = source_limitations

    verified_boundaries = boundary_value.get("boundaries")
    if boundaries is not None and isinstance(verified_boundaries, list):
        limitations = [str(item).strip() for item in verified_boundaries if str(item).strip()]
        if limitations:
            technical["product.limitations"] = extension_fact(
                "product.limitations", limitations, boundaries
            )
    return technical


def _verified_example_fact(
    snapshot: RepositorySnapshotV1,
    truth: ProductTruthPolicy,
    base_facts: ProductFactsV2,
    observed_at: str,
) -> tuple[FactRecordV2, LocalProductVerificationV1 | None]:
    example = truth.minimal_example
    fact, verification = _example_fact_for_candidate(
        snapshot,
        example,
        base_facts,
        observed_at,
    )
    if fact.verification_state == "verified" or not local_fact_verification_allowed():
        return fact, verification
    isolated_execution = getattr(verification, "isolated_execution", None)
    if (
        verification is not None
        and getattr(verification, "ecosystem", None) == "python"
        and isolated_execution is not None
        and isolated_execution.return_code in {20, 21}
    ):
        return fact, verification
    selection = select_verified_repository_example(
        snapshot.root_path,
        source_revision=snapshot.source_revision,
        requested=example,
        verify_example_fn=lambda candidate: verify_local_product_example(snapshot, candidate),
    )
    if selection.outcome not in {"VERIFIED", "TERMINAL_PRODUCT_FAILURE"}:
        return fact, verification
    assert selection.example is not None
    assert selection.verification is not None
    return _example_fact_for_candidate(
        snapshot,
        selection.example,
        base_facts,
        observed_at,
        repository_authored=True,
        preverified_result=selection.verification,
    )


def _example_fact_for_candidate(
    snapshot: RepositorySnapshotV1,
    example: MinimalExamplePolicy,
    base_facts: ProductFactsV2,
    observed_at: str,
    *,
    repository_authored: bool = False,
    preverified_result: LocalProductVerificationV1 | None = None,
) -> tuple[FactRecordV2, LocalProductVerificationV1 | None]:
    identity = base_facts.selected_fact("product.identity")
    identity_value = identity.value if isinstance(identity.value, dict) else {}
    product_name = str(identity_value.get("product_name") or "").strip()
    normalized_code = normalize_example_display_literals(
        example.code,
        product_name=product_name,
        full_display_name=full_product_display_name(base_facts),
    )
    if normalized_code != example.code:
        example = example.model_copy(update={"code": normalized_code})
    failures = evidence_failures(
        snapshot.root_path,
        example.evidence_paths,
        example.required_symbols,
        allow_partial_symbols=True,
    )
    failures.extend(generated_example_quality_failures(example.language, example.code))
    verification = preverified_result
    if verification is None and not failures and local_fact_verification_allowed():
        verification = verify_local_product_example(snapshot, example)
    if failures:
        detail = "; ".join(failures)
    elif verification is None:
        detail = "local example verification is disabled for this execution profile"
    else:
        detail = bounded_local_verification_detail(verification)
    verified = bool(
        verification is not None
        and verification.truth_eligible
        and verification.outcome in {"SOURCE_BUILD_VERIFIED", "SOURCE_TREE_VERIFIED"}
    )
    isolated_execution = (
        getattr(verification, "isolated_execution", None) if verification is not None else None
    )
    product_source_failure = bool(
        verification is not None
        and getattr(verification, "ecosystem", None) == "python"
        and isolated_execution is not None
        and isolated_execution.return_code in {20, 21}
    )
    repairable_by_example_change = bool(
        verification is not None
        and verification.outcome == "BUILD_FAILED"
        and (
            getattr(verification, "ecosystem", None) != "python"
            or isolated_execution is None
            or isolated_execution.return_code == 22
        )
    )
    fact_variant = (
        ("repository-example" if verified else "repository-example-blocked")
        if repository_authored
        else ("compiled-salvaged-example" if verified else "salvaged-example-blocked")
    )
    value = {
        "language": example.language,
        "class_name": example.class_name,
        "code": example.code,
        "verification_outcome": (
            verification.outcome if verification is not None else "BLOCKED_LOCAL_VERIFICATION"
        ),
        "verification_detail": detail,
        "repairable_by_example_change": repairable_by_example_change,
        "blocked_category": "infra_external" if product_source_failure else "agent_fixable",
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
            fact_variant,
        ),
        field="example.minimal",
        value=value,
        source=FactSourceV2(
            source_type="mechanical_repository" if repository_authored else "mechanical_test",
            location=(
                "repository://" + ",".join(example.evidence_paths)
                if repository_authored
                else "local-verifier://example.minimal"
            ),
            source_revision=snapshot.source_revision,
        ),
        verification_state="verified" if verified else "blocked",
        authoritative_owner="repository-owner",
        confidence=1.0 if verified else 0.0,
        affected_surfaces=SURFACE_DEPENDENCIES["example.minimal"],
    )
    return fact, verification


def _finding(
    fact: FactRecordV2,
    *,
    blocked_category_override: Literal["infra_external"] | None = None,
) -> dict:
    value = fact.value if isinstance(fact.value, dict) else {}
    blocked_category = blocked_category_override or str(
        value.get("blocked_category") or "agent_fixable"
    )
    return {
        "finding_id": f"deterministic-salvage:{fact.field}",
        "classification": "BLOCKED_MISSING_EVIDENCE",
        "blocked_category": blocked_category,
        "field": fact.field,
        "detail": fact.value,
        "required_action": (
            "repair the product-owned source/import defect and publish a new source revision"
            if blocked_category == "infra_external"
            else "supply a current-revision repository or structured-knowledge candidate and "
            "rerun deterministic revalidation"
        ),
    }


def _dependent_product_source_block_category(
    fact: FactRecordV2,
    example_fact: FactRecordV2,
    source_revision: str,
) -> Literal["infra_external"] | None:
    """Propagate only the same-revision terminal source-build failure dependency."""

    example_value = example_fact.value if isinstance(example_fact.value, dict) else {}
    fact_value = fact.value if isinstance(fact.value, dict) else {}
    if (
        example_value.get("blocked_category") == "infra_external"
        and example_fact.source.source_revision == source_revision
        and fact.field == "installation.verified_acquisition"
        and fact_value.get("source_revision") == source_revision
        and fact_value.get("method") == "source_build"
        and fact_value.get("outcome") == "BUILD_FAILED"
    ):
        return "infra_external"
    return None


def salvage_product_truth_candidate(
    base_facts: ProductFactsV2,
    snapshot: RepositorySnapshotV1,
    candidate: dict,
) -> DeterministicTruthSalvageV1:
    """Treat candidate prose as hints and re-prove every accepted field."""

    truth = ProductTruthPolicy.model_validate(candidate)
    observed_at = datetime.now(UTC).isoformat()
    example_fact, local_verification = _verified_example_fact(
        snapshot,
        truth,
        base_facts,
        observed_at,
    )
    entry = require_listed(base_facts.org_repo)
    acquisition_fact = reconcile_acquisition_fact(
        entry,
        base_facts.selected_fact("installation.verified_acquisition"),
        local_verification,
        observed_at=observed_at,
    )
    native_formats = extract_repository_format_directions(
        snapshot.root_path,
        platform=entry.ecosystem or entry.platform,
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
    technical = _repository_enriched_technical_facts(base_facts, technical)
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
        _finding(
            fact,
            blocked_category_override=_dependent_product_source_block_category(
                fact,
                example_fact,
                snapshot.source_revision,
            ),
        )
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
