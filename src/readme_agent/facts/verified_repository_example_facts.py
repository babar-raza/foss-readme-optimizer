"""Project compile-verified repository examples into one accepted fact."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id
from readme_agent.facts.verified_repository_examples import (
    MAX_VERIFIED_REPOSITORY_EXAMPLE_ATTEMPTS,
)
from readme_agent.registry.models import MinimalExamplePolicy

VerifyExampleFn = Callable[[MinimalExamplePolicy], LocalProductVerificationV1 | None]


def compiled_repository_examples_fact(
    candidates: Iterable[MinimalExamplePolicy],
    *,
    org_repo: str,
    source_revision: str | None,
    observed_at: str | None,
    verify_example_fn: VerifyExampleFn,
    known_verifications: dict[str, LocalProductVerificationV1] | None = None,
) -> FactRecordV2 | None:
    """Return all bounded examples that compile against the immutable source tree."""

    verified: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    known = known_verifications or {}
    for candidate in candidates:
        identity = (candidate.language, candidate.code.rstrip() + "\n")
        if identity in seen:
            continue
        seen.add(identity)
        if len(seen) > MAX_VERIFIED_REPOSITORY_EXAMPLE_ATTEMPTS:
            break
        result = known.get(candidate.code.rstrip() + "\n") or verify_example_fn(candidate)
        if (
            result is None
            or not result.truth_eligible
            or result.outcome not in {"SOURCE_BUILD_VERIFIED", "SOURCE_TREE_VERIFIED"}
            or (
                source_revision is not None
                and getattr(result, "source_revision", source_revision) != source_revision
            )
        ):
            continue
        verified.append(
            {
                "title": candidate.class_name,
                "language": candidate.language,
                "code": candidate.code.rstrip() + "\n",
                "evidence_paths": list(candidate.evidence_paths),
                "static_api_verified": True,
                "runtime_verified": False,
                "verification_outcome": result.outcome,
                "public_api_sha256": result.fact_projection().get("public_api_sha256"),
            }
        )
    if not verified:
        return None
    return FactRecordV2(
        fact_id=descriptive_fact_id("repository.examples", "compiled-repository-examples"),
        field="repository.examples",
        value={"inline_examples": verified},
        source=FactSourceV2(
            source_type="mechanical_test",
            location=f"local-product-verification://{org_repo}/repository-examples",
            source_revision=source_revision,
            retrieved_at=observed_at,
        ),
        verification_state="verified",
        authoritative_owner="repository-owner",
        confidence=1.0,
        affected_surfaces=SURFACE_DEPENDENCIES["repository.examples"],
    )


__all__ = ["compiled_repository_examples_fact"]
