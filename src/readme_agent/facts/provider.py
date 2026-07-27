"""Collect repository and policy evidence into one ProductFactsV2 result."""

from __future__ import annotations

from datetime import UTC, datetime

from readme_agent import paths
from readme_agent.errors import NotAllowlistedError
from readme_agent.facts.acquisition import select_acquisition
from readme_agent.facts.context import current_product_facts
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.facts.migration import SURFACE_DEPENDENCIES, migrate_product_facts_v1
from readme_agent.facts.policy_evidence import evidence_failures
from readme_agent.facts.repository_ingestion import ingest_repository_product_facts
from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.root_roles import classify_package_root_roles
from readme_agent.facts.schema import ProductFactsV1
from readme_agent.facts.schema_v2 import (
    FactRecordV2,
    FactSourceType,
    FactSourceV2,
    descriptive_fact_id,
)
from readme_agent.profile.cached import get_or_build_profile
from readme_agent.registry.loader import load_policy, require_listed
from readme_agent.registry.models import ProductEntry
from readme_agent.repository_snapshot import (
    current_repository_snapshot,
    local_fact_verification_allowed,
)


def _acquisition_fact(
    entry: ProductEntry,
    source_revision: str | None,
    observed_at: str | None,
    local_verification: LocalProductVerificationV1 | None,
    unavailable_detail: str,
) -> FactRecordV2:
    """Select one receipt-backed registry or isolated source acquisition."""

    if source_revision is None:
        return FactRecordV2(
            fact_id=descriptive_fact_id("installation.verified_acquisition", "missing-revision"),
            field="installation.verified_acquisition",
            value={
                "method": "unresolved",
                "outcome": "BLOCKED_LOCAL_VERIFICATION",
                "detail": "immutable source revision is required for acquisition truth",
                "truth_eligible": False,
            },
            source=FactSourceV2(
                source_type="mechanical_repository",
                location=f"repository://{entry.org_repo}",
                retrieved_at=observed_at,
            ),
            verification_state="blocked",
            authoritative_owner="repository-owner",
            confidence=0.0,
            affected_surfaces=SURFACE_DEPENDENCIES["installation.verified_acquisition"],
        )
    decision = select_acquisition(
        entry=entry,
        source_revision=source_revision,
        local_verification=local_verification,
        unavailable_detail=unavailable_detail,
    )
    receipt = decision.registry_receipt
    source_type: FactSourceType = (
        "external_registry" if decision.outcome == "REGISTRY_VERIFIED" else "mechanical_test"
    )
    location = (
        receipt.request_url
        if receipt is not None
        else f"local-product-verification://{entry.org_repo}"
    )
    qualifiers = {
        "REGISTRY_VERIFIED": f"registry-{decision.method}",
        "SOURCE_BUILD_VERIFIED": "disposable-source-build",
        "NOT_PUBLISHED": "source-build-required",
        "BLOCKED_NETWORK": "blocked-registry",
        "CAPABILITY_GAP": "capability-gap",
    }
    qualifier = qualifiers.get(decision.outcome, "blocked-source-build")
    return FactRecordV2(
        fact_id=descriptive_fact_id("installation.verified_acquisition", qualifier),
        field="installation.verified_acquisition",
        value=decision.model_dump(mode="json"),
        source=FactSourceV2(
            source_type=source_type,
            location=location,
            source_revision=source_revision,
            retrieved_at=observed_at,
        ),
        verification_state="verified" if decision.truth_eligible else "blocked",
        authoritative_owner="repository-owner",
        confidence=1.0 if decision.truth_eligible else 0.0,
        affected_surfaces=SURFACE_DEPENDENCIES["installation.verified_acquisition"],
    )


def _local_verification_facts(
    org_repo: str,
    source_revision: str | None,
    observed_at: str | None,
    root,
    policy,
    entry: ProductEntry,
) -> tuple[list[FactRecordV2], dict | None]:
    """Package-acquisition verification (`installation.verified_acquisition`) and local
    minimal-example verification (`example.minimal`) are two independent questions --
    "is this package published on its authoritative registry" never needed a
    `product_truth.minimal_example` to answer, so it must not be skipped just because no
    example has been authored yet. Found live 2026-07-25 running the portfolio-wide
    local-proposal pipeline (Level-5 program): every one of the 28 non-pilot repos, none of
    which have `product_truth` authored, was silently getting NO acquisition fact at all
    (not even the honest `source_build` fallback) -- the whole function used to return
    `[], None` before ever reaching the acquisition check below."""
    truth = policy.product_truth
    source = FactSourceV2(
        source_type="mechanical_test",
        location=f"local-product-verification://{org_repo}",
        source_revision=source_revision,
        retrieved_at=observed_at,
    )

    facts: list[FactRecordV2] = []
    local_result = None
    if truth is not None:
        snapshot = current_repository_snapshot(org_repo)
        failures = evidence_failures(
            root,
            truth.minimal_example.evidence_paths,
            truth.minimal_example.required_symbols,
        )
        if snapshot is not None and local_fact_verification_allowed() and not failures:
            local_result = verify_local_product_example(snapshot, truth.minimal_example)
        if local_result is None:
            example_outcome = "BLOCKED_LOCAL_VERIFICATION"
            example_detail = (
                "; ".join(failures)
                if failures
                else "local build/example execution is disabled for this execution profile"
            )
        else:
            example_outcome = local_result.outcome
            example_detail = local_result.detail
        example_verified = (
            local_result is not None
            and local_result.truth_eligible
            and example_outcome == "SOURCE_BUILD_VERIFIED"
        )
        facts.append(
            FactRecordV2(
                fact_id=descriptive_fact_id("example.minimal", "compiled-policy-example"),
                field="example.minimal",
                value={
                    "language": truth.minimal_example.language,
                    "class_name": truth.minimal_example.class_name,
                    "code": truth.minimal_example.code,
                    "verification_outcome": example_outcome,
                    "verification_detail": example_detail,
                    **(
                        local_result.fact_projection()
                        if local_result is not None
                        else {
                            "verified_public_symbols": [],
                            "public_api_sha256": None,
                            "python_package": None,
                            "typescript_package": None,
                            "rust_package": None,
                            "rust_formats": [],
                            "rust_source_dependency": None,
                        }
                    ),
                },
                source=source,
                verification_state="verified" if example_verified else "blocked",
                authoritative_owner="repository-owner",
                confidence=1.0 if example_verified else 0.0,
                affected_surfaces=SURFACE_DEPENDENCIES["example.minimal"],
            )
        )
    else:
        example_outcome = "BLOCKED_LOCAL_VERIFICATION"
        example_detail = (
            "no product_truth.minimal_example configured for this policy profile -- "
            "nothing to compile/run locally yet"
        )
        example_verified = False

    # The "aspose {family} foss" rule: a genuinely published package is verified against its
    # AUTHORITATIVE registry and its install claim is kept, never stripped in favor of a
    # source-build substitute the package doesn't need. Only when the package is genuinely not
    # published does an isolated source-build remain eligible as the acquisition path. A
    # network-blocked registry check fails closed rather than masquerading as unpublished; see
    # foss_coordinate.py and the ground-truth evidence bundle. This
    # check runs regardless of whether product_truth exists -- see the function's own docstring.
    acquisition = _acquisition_fact(
        entry,
        source_revision,
        observed_at,
        local_result,
        example_detail,
    )
    facts.append(acquisition)
    return facts, (local_result.model_dump(mode="json") if local_result is not None else None)


def collect_product_facts(
    org_repo: str,
    *,
    prior_upstream_revision: str | None = None,
    prior_profile_result: dict | None = None,
) -> dict:
    """Re-derive facts through the allow-list, policy, and repository seams."""

    entry = require_listed(org_repo)
    if entry.policy_profile is None:
        raise NotAllowlistedError(f"{org_repo} has no policy_profile configured")
    policy = load_policy(entry.policy_profile)
    profile = get_or_build_profile(
        entry,
        prior_upstream_revision=prior_upstream_revision,
        prior_profile_result=prior_profile_result,
    )
    snapshot = current_repository_snapshot(org_repo)
    root = (
        snapshot.root_path
        if snapshot is not None
        else paths.baseline_dir(entry.org, entry.repo_name)
    )
    source_revision = snapshot.source_revision if snapshot is not None else profile.source_revision
    observed_at = None if source_revision is not None else datetime.now(UTC).isoformat()
    package_root_roles = classify_package_root_roles(
        entry,
        profile,
        root,
        source_revision,
    )

    required = policy.required_elements
    result = {
        "org_repo": org_repo,
        "family": entry.family,
        "platform": entry.platform,
        "ecosystem": entry.ecosystem,
        "policy_profile": entry.policy_profile,
        "declared_license": required.license_mentioned.detected_license,
        "products_org_link": required.products_org_link.model_dump(),
        "products_com_link": required.products_com_link.model_dump(),
        "relationship_talking_points": required.relationship_explained.talking_points,
        "secondary_links": policy.secondary_links,
        "word_limit": policy.block.word_limit.model_dump(),
        "prohibited_terms": policy.block.prohibited_terms,
        "link_whitelist_domains": policy.block.link_whitelist_domains,
        "detected_ecosystems": [
            ecosystem.model_dump() for ecosystem in profile.detected_ecosystems
        ],
        "unresolved_manifests": profile.unresolved_manifests,
        "package_roots": [root.model_dump() for root in profile.package_roots],
        "package_root_roles": package_root_roles.model_dump(mode="json"),
        "surface_ownership": policy.surface_ownership.model_dump(mode="json"),
        "source": {
            "identity_and_policy": (
                f"data/products.json + config/policies/{entry.policy_profile}.yml"
            ),
            "detected_ecosystems": "live repository clone (repository inspection)",
            "unresolved_manifests": "live repository clone (repository inspection)",
            "package_roots": "live repository clone (repository inspection)",
            "package_root_roles": (
                "deterministic classification of immutable repository package roots"
            ),
        },
    }
    product_facts_v1 = ProductFactsV1.from_capability_results(result)
    product_facts_v2 = migrate_product_facts_v1(
        product_facts_v1,
        source_revision=source_revision,
        observed_at=observed_at,
    )
    candidates = [
        fact
        for fact in product_facts_v2.facts
        if fact.verification_state != "missing"
        and fact.field
        not in {
            "product.identity",
            "product.platforms",
            "installation.coordinates",
            "installation.verified_acquisition",
            "release.state",
            "product.compatibility",
            "product.license",
            "example.minimal",
            "product.audience",
            "product.problems_solved",
            "product.capabilities",
            "product.formats",
            "product.limitations",
        }
    ]
    candidates.extend(
        ingest_repository_product_facts(
            entry,
            policy,
            profile,
            root,
            source_revision,
            observed_at,
            root_roles=package_root_roles,
        )
    )
    local_candidates, local_verification = _local_verification_facts(
        org_repo,
        source_revision,
        observed_at,
        root,
        policy,
        entry,
    )
    candidates.extend(local_candidates)
    resolved = resolve_product_facts(
        org_repo,
        candidates,
        missing_source=FactSourceV2(
            source_type="mechanical_repository",
            location=f"repository://{org_repo}",
            source_revision=source_revision,
            retrieved_at=observed_at,
        ),
        missing_field_surfaces=SURFACE_DEPENDENCIES,
        package_root_roles=package_root_roles,
    )
    active_facts = current_product_facts(org_repo)
    if active_facts is not None:
        identity_revision = active_facts.selected_fact("product.identity").source.source_revision
        if source_revision is not None and identity_revision != source_revision:
            raise RuntimeError(
                "run-scoped product facts revision does not match the immutable repository "
                f"snapshot: {identity_revision!r} != {source_revision!r}"
            )
        resolved = active_facts
    result["product_facts_v2"] = resolved.model_dump(mode="json")
    result["local_product_verification"] = local_verification or {
        "outcome": "NOT_RUN",
        "detail": "local build/example verification was not executed",
    }
    return result
