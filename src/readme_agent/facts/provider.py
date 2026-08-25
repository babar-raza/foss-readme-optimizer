"""Collect repository and policy evidence into one ProductFactsV2 result."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from readme_agent import paths
from readme_agent.errors import NotAllowlistedError
from readme_agent.facts import dotnet_example_verifier
from readme_agent.facts.acquisition_facts import collect_acquisition_fact
from readme_agent.facts.aspose_knowledge_selection import knowledge_claim_fact_records
from readme_agent.facts.aspose_seo_keyword_facts import relevant_seo_keyword_fact_record
from readme_agent.facts.catalog_documentation import catalog_documentation_fact
from readme_agent.facts.composer_factpack import aspose_fact_records, build_aspose_detection_bundle
from readme_agent.facts.context import current_product_facts
from readme_agent.facts.dependency_snapshot import dependency_snapshot_fact_record
from readme_agent.facts.knowledge_canonical_projection import (
    augment_canonical_formats_with_knowledge,
    project_knowledge_into_canonical_facts,
)
from readme_agent.facts.local_verification import verify_local_product_example
from readme_agent.facts.migration import SURFACE_DEPENDENCIES, migrate_product_facts_v1
from readme_agent.facts.platform_audience import derive_platform_audience
from readme_agent.facts.policy_evidence import evidence_failures
from readme_agent.facts.presentation_knowledge import presentation_knowledge_facts
from readme_agent.facts.problem_grounding import derive_grounded_problem_fallback
from readme_agent.facts.repository_examples import (
    ExampleLanguage,
    repository_readme_example_candidates,
    repository_source_example_candidates,
)
from readme_agent.facts.repository_format_facts import repository_format_fact_candidate
from readme_agent.facts.repository_ingestion import ingest_repository_product_facts
from readme_agent.facts.resolution import resolve_product_facts
from readme_agent.facts.root_role_schema import PackageRootRoleInventoryV1
from readme_agent.facts.root_roles import classify_package_root_roles
from readme_agent.facts.schema import ProductFactsV1
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id
from readme_agent.facts.verified_repository_example_facts import (
    compiled_repository_examples_fact,
)
from readme_agent.facts.verified_repository_examples import (
    bounded_local_verification_detail,
    select_verified_repository_example,
)
from readme_agent.profile.cached import get_or_build_profile
from readme_agent.registry.loader import load_policy, require_listed
from readme_agent.registry.models import ProductEntry
from readme_agent.repository_snapshot import (
    current_repository_snapshot,
    local_fact_verification_allowed,
)


def _local_verification_facts(
    org_repo: str,
    source_revision: str | None,
    observed_at: str | None,
    root,
    policy,
    entry: ProductEntry,
    manifest_coordinate: dict[str, str] | None = None,
    root_roles: PackageRootRoleInventoryV1 | None = None,
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
    snapshot = current_repository_snapshot(org_repo)
    ecosystem = getattr(entry, "ecosystem", None)

    def verify_example(example):
        if snapshot is None:
            return None
        if ecosystem == "net":
            selected_manifest = (
                root_roles.selected_product_manifest_path if root_roles is not None else None
            )
            return verify_local_product_example(
                snapshot,
                example,
                isolated_verifier=lambda active_snapshot, active_example: (
                    dotnet_example_verifier.verify(
                        active_snapshot,
                        active_example,
                        selected_product_manifest_path=selected_manifest,
                    )
                ),
            )
        return verify_local_product_example(snapshot, example)

    example = truth.minimal_example if truth is not None else None
    example_origin = "policy" if example is not None else "repository"
    failures: list[str] = []
    if example is not None:
        failures = evidence_failures(
            root,
            example.evidence_paths,
            example.required_symbols,
        )
        if snapshot is not None and local_fact_verification_allowed() and not failures:
            local_result = verify_example(example)
    raw_example_language = getattr(example, "language", None) or (
        "dotnet" if ecosystem == "net" else ecosystem
    )
    supported_example_languages = {
        "cpp",
        "dotnet",
        "go",
        "java",
        "python",
        "rust",
        "typescript",
    }
    example_language = (
        cast(ExampleLanguage, raw_example_language)
        if raw_example_language in supported_example_languages
        else None
    )
    repository_candidates = []
    if (
        example_language is not None
        and ecosystem in {"cpp", "go", "java", "net", "rust", "typescript"}
        and snapshot is not None
        and local_fact_verification_allowed()
    ):
        repository_candidates = [
            *repository_source_example_candidates(root, example_language),
            *repository_readme_example_candidates(root, example_language),
        ]
        if repository_candidates and (local_result is None or not local_result.truth_eligible):
            selection = select_verified_repository_example(
                root,
                source_revision=source_revision,
                requested=repository_candidates[0],
                verify_example_fn=verify_example,
            )
            if selection.outcome in {"VERIFIED", "TERMINAL_PRODUCT_FAILURE"}:
                assert selection.example is not None
                assert selection.verification is not None
                example = selection.example
                example_origin = "repository"
                local_result = selection.verification
                failures = []
            elif (
                selection.outcome == "NO_VERIFIED_CANDIDATE"
                and selection.last_attempted_example is not None
                and selection.last_attempted_verification is not None
            ):
                example = selection.last_attempted_example
                example_origin = "repository"
                local_result = selection.last_attempted_verification
                failures = []
    if example is not None:
        if local_result is None:
            example_outcome = "BLOCKED_LOCAL_VERIFICATION"
            example_detail = (
                "; ".join(failures)
                if failures
                else "local build/example execution is disabled for this execution profile"
            )
        else:
            example_outcome = local_result.outcome
            example_detail = bounded_local_verification_detail(local_result)
        example_verified = (
            local_result is not None
            and local_result.truth_eligible
            and example_outcome in {"SOURCE_BUILD_VERIFIED", "SOURCE_TREE_VERIFIED"}
        )
        facts.append(
            FactRecordV2(
                fact_id=descriptive_fact_id(
                    "example.minimal", f"compiled-{example_origin}-example"
                ),
                field="example.minimal",
                value={
                    "language": example.language,
                    "class_name": example.class_name,
                    "code": example.code,
                    "verification_outcome": example_outcome,
                    "verification_detail": example_detail,
                    **(
                        local_result.fact_projection()
                        if local_result is not None
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

    if (
        ecosystem != "python"
        and snapshot is not None
        and local_fact_verification_allowed()
        and repository_candidates
    ):
        known_verifications = (
            {example.code.rstrip() + "\n": local_result}
            if example is not None and local_result is not None
            else {}
        )
        repository_examples = compiled_repository_examples_fact(
            repository_candidates,
            org_repo=org_repo,
            source_revision=source_revision,
            observed_at=observed_at,
            verify_example_fn=verify_example,
            known_verifications=known_verifications,
        )
        if repository_examples is not None:
            facts.append(repository_examples)

    # The "aspose {family} foss" rule: a genuinely published package is verified against its
    # AUTHORITATIVE registry and its install claim is kept, never stripped in favor of a
    # source-build substitute the package doesn't need. Only when the package is genuinely not
    # published does an isolated source-build remain eligible as the acquisition path. A
    # network-blocked registry check fails closed rather than masquerading as unpublished; see
    # foss_coordinate.py and the ground-truth evidence bundle. This
    # check runs regardless of whether product_truth exists -- see the function's own docstring.
    acquisition = collect_acquisition_fact(
        entry,
        source_revision,
        observed_at,
        local_result,
        example_detail,
        manifest_coordinate,
    )
    facts.append(acquisition)
    return facts, (local_result.model_dump(mode="json") if local_result is not None else None)


def collect_product_facts(
    org_repo: str,
    *,
    prior_upstream_revision: str | None = None,
    prior_profile_result: dict | None = None,
    knowledge_claims_data_root: Path | None = None,
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
            snapshot=snapshot,
        )
    )
    if documentation_fact := catalog_documentation_fact(entry):
        candidates.append(documentation_fact)
    manifest_coordinate = None
    for fact in candidates:
        if (
            fact.field == "installation.coordinates"
            and fact.verification_state == "verified"
            and isinstance(fact.value, list)
        ):
            selected = next(
                (
                    coordinate
                    for coordinate in fact.value
                    if isinstance(coordinate, dict)
                    and coordinate.get("ecosystem") == entry.ecosystem
                ),
                None,
            )
            if selected is not None:
                keys = ("group_id", "artifact_id") if entry.ecosystem == "java" else ("name",)
                projected = {
                    key: str(selected[key]) for key in keys if selected.get(key) is not None
                }
                if len(projected) == len(keys):
                    manifest_coordinate = projected
                    break
    local_candidates, local_verification = _local_verification_facts(
        org_repo,
        source_revision,
        observed_at,
        root,
        policy,
        entry,
        manifest_coordinate,
        package_root_roles,
    )
    candidates.extend(local_candidates)
    if source_revision is not None:
        format_fact = repository_format_fact_candidate(
            root,
            source_revision=source_revision,
            family=entry.family,
            platform=entry.ecosystem or entry.platform,
            specifications=(policy.product_truth.formats if policy.product_truth else []),
            candidates=candidates,
        )
        if format_fact is not None:
            candidates.append(format_fact)
    candidates.append(dependency_snapshot_fact_record(root, entry.ecosystem or "unknown"))
    aspose_data_root = Path.cwd() / "data" / "imported"
    if aspose_data_root.is_dir():
        aspose_bundle = build_aspose_detection_bundle(
            entry.family, entry.platform, data_root=aspose_data_root, clone_cache=root
        )
        candidates.extend(
            aspose_fact_records(
                aspose_bundle, family=entry.family, platform=entry.platform, clone_cache=root
            )
        )
        knowledge_records = knowledge_claim_fact_records(
            entry.family,
            entry.platform,
            data_root=knowledge_claims_data_root or aspose_data_root,
            clone_cache=root,
            source_revision=source_revision,
        )
        candidates.extend(knowledge_records)
        candidates = augment_canonical_formats_with_knowledge(candidates)
        candidates.extend(project_knowledge_into_canonical_facts(candidates))
        seo_fact = relevant_seo_keyword_fact_record(
            entry.family, entry.platform, data_root=aspose_data_root
        )
        if seo_fact is not None:
            candidates.append(seo_fact)
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
    presentation_selection = None
    presentation_catalog = Path.cwd() / "data" / "imported" / "presentation_knowledge.json"
    if presentation_catalog.is_file():
        presentation_fallbacks, presentation_selection = presentation_knowledge_facts(
            entry.family,
            entry.platform,
            root=root,
            source_revision=source_revision,
            observed_at=observed_at,
            catalog_path=presentation_catalog,
        )
        selection_fact = FactRecordV2(
            fact_id=descriptive_fact_id(
                "aspose.presentation_knowledge_selection",
                f"{entry.family}-{entry.platform}",
            ),
            field="aspose.presentation_knowledge_selection",
            value=presentation_selection.model_dump(mode="json"),
            source=FactSourceV2(
                source_type="mechanical_repository",
                location="repository://presentation-knowledge-reverification",
                source_revision=source_revision,
                retrieved_at=observed_at,
            ),
            verification_state="verified",
            authoritative_owner="repository-owner",
            confidence=1.0,
            affected_surfaces=["evidence.knowledge"],
        )
        eligible_fallbacks = [
            fact
            for fact in presentation_fallbacks
            if resolved.selected_fact(fact.field).verification_state
            not in {"verified", "policy_approved"}
        ]
        candidates.extend([selection_fact, *eligible_fallbacks])
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
    derived_facts: list[FactRecordV2] = []
    if (
        resolved.selected_fact("product.audience").verification_state
        not in {"verified", "policy_approved"}
        and (audience_fact := derive_platform_audience(resolved)) is not None
    ):
        derived_facts.append(audience_fact)
    problem_fallback = derive_grounded_problem_fallback(
        resolved,
        source_revision,
        observed_at,
        max_statements=2 if entry.ecosystem == "net" else 4,
    )
    if (
        resolved.selected_fact("product.problems_solved").verification_state
        not in {"verified", "policy_approved"}
        and problem_fallback is not None
    ):
        _claims, problem_fact = problem_fallback
        derived_facts.append(problem_fact)
    if derived_facts:
        candidates.extend(derived_facts)
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
    if presentation_selection is not None:
        result["presentation_knowledge_selection"] = presentation_selection.model_dump(mode="json")
    result["local_product_verification"] = local_verification or {
        "outcome": "NOT_RUN",
        "detail": "local build/example verification was not executed",
    }
    return result
