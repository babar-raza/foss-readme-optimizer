"""Project and reconcile package-acquisition decisions as ProductFactsV2 records."""

from readme_agent.facts.acquisition import reconcile_acquisition, select_acquisition
from readme_agent.facts.acquisition_schema import AcquisitionDecisionV1
from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import (
    FactRecordV2,
    FactSourceType,
    FactSourceV2,
    descriptive_fact_id,
)
from readme_agent.registry.models import ProductEntry


def acquisition_fact_from_decision(
    decision: AcquisitionDecisionV1,
    *,
    observed_at: str | None,
) -> FactRecordV2:
    """Bind one acquisition decision and its receipt into a fact record."""

    receipt = decision.registry_receipt
    source_type: FactSourceType = (
        "external_registry" if decision.outcome == "REGISTRY_VERIFIED" else "mechanical_test"
    )
    location = (
        receipt.request_url
        if receipt is not None
        else f"local-product-verification://{decision.org_repo}"
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
            source_revision=decision.source_revision,
            retrieved_at=observed_at,
        ),
        verification_state="verified" if decision.truth_eligible else "blocked",
        authoritative_owner="repository-owner",
        confidence=1.0 if decision.truth_eligible else 0.0,
        affected_surfaces=SURFACE_DEPENDENCIES["installation.verified_acquisition"],
    )


def collect_acquisition_fact(
    entry: ProductEntry,
    source_revision: str | None,
    observed_at: str | None,
    local_verification: LocalProductVerificationV1 | None,
    unavailable_detail: str,
    manifest_coordinate: dict[str, str] | None,
) -> FactRecordV2:
    """Select registry/source-build truth and return its fact projection."""

    if source_revision is None:
        org_repo = getattr(entry, "org_repo", f"{entry.org}/{entry.repo_name}")
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
                location=f"repository://{org_repo}",
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
        manifest_coordinate=manifest_coordinate,
    )
    return acquisition_fact_from_decision(decision, observed_at=observed_at)


def reconcile_acquisition_fact(
    entry: ProductEntry,
    prior_fact: FactRecordV2,
    local_verification: LocalProductVerificationV1 | None,
    *,
    observed_at: str | None,
) -> FactRecordV2:
    """Reconcile a sealed registry decision after isolated source proof is available."""

    if prior_fact.field != "installation.verified_acquisition":
        raise ValueError("prior fact is not an acquisition fact")
    prior = AcquisitionDecisionV1.model_validate(prior_fact.value)
    decision = reconcile_acquisition(
        entry=entry,
        prior=prior,
        local_verification=local_verification,
    )
    return acquisition_fact_from_decision(decision, observed_at=observed_at)
