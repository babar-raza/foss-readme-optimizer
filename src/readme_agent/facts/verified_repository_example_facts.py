"""Project compile-verified repository examples into one accepted fact."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable

from readme_agent.facts.example_verification_schema import LocalProductVerificationV1
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id
from readme_agent.facts.verified_repository_examples import (
    MAX_VERIFIED_REPOSITORY_EXAMPLE_ATTEMPTS,
)
from readme_agent.registry.models import MinimalExamplePolicy

VerifyExampleFn = Callable[[MinimalExamplePolicy], LocalProductVerificationV1 | None]


def _exact_compiler_failure(
    candidate: MinimalExamplePolicy,
    result: LocalProductVerificationV1,
) -> dict[str, object] | None:
    """Return bounded negative evidence only for the exact isolated compiled consumer."""

    proof = getattr(result, "compiled_consumer", None)
    execution = getattr(result, "isolated_execution", None)
    diagnostic = getattr(result, "example_compile", None)
    combined = "\n".join((diagnostic.stdout, diagnostic.stderr)) if diagnostic else ""
    normalized_diagnostic = combined.replace("\\", "/").casefold()
    if (
        result.outcome != "BUILD_FAILED"
        or proof is None
        or execution is None
        or diagnostic is None
        or proof.accepted
        or proof.source_revision != result.source_revision
        or proof.org_repo != result.org_repo
        or proof.example_sha256 != hashlib.sha256(candidate.code.encode("utf-8")).hexdigest()
        or proof.isolated_execution != execution
        or not execution.truth_eligible
        or not execution.cleanup.complete
        or execution.return_code == 0
        or execution.timed_out
        or execution.oom_killed
        or diagnostic.return_code != execution.return_code
        or ".readme-agent/" not in normalized_diagnostic
    ):
        return None
    return {
        "compiled_consumer_example_sha256": proof.example_sha256,
        "isolated_input_sha256": execution.input_sha256,
        "compiler_diagnostic_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
    }


def compiled_repository_examples_fact(
    candidates: Iterable[MinimalExamplePolicy],
    *,
    org_repo: str,
    source_revision: str | None,
    observed_at: str | None,
    verify_example_fn: VerifyExampleFn,
    known_verifications: dict[str, LocalProductVerificationV1] | None = None,
    preverified_examples: Iterable[dict[str, object]] = (),
) -> FactRecordV2 | None:
    """Return all bounded examples that compile against the immutable source tree."""

    verified: list[dict[str, object]] = [dict(item) for item in preverified_examples]
    withheld: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = {
        (str(item.get("language")), str(item.get("code")).rstrip() + "\n")
        for item in verified
        if item.get("language") and item.get("code")
    }
    attempted = 0
    known = known_verifications or {}
    for candidate in candidates:
        identity = (candidate.language, candidate.code.rstrip() + "\n")
        if identity in seen:
            continue
        seen.add(identity)
        attempted += 1
        if attempted > MAX_VERIFIED_REPOSITORY_EXAMPLE_ATTEMPTS:
            break
        result = known.get(candidate.code.rstrip() + "\n") or verify_example_fn(candidate)
        if result is None or (
            source_revision is not None
            and getattr(result, "source_revision", source_revision) != source_revision
        ):
            continue
        if not result.truth_eligible or result.outcome not in {
            "SOURCE_BUILD_VERIFIED",
            "SOURCE_TREE_VERIFIED",
        }:
            negative = _exact_compiler_failure(candidate, result)
            if negative is not None:
                withheld.append(
                    {
                        "title": candidate.class_name,
                        "language": candidate.language,
                        "code": candidate.code.rstrip() + "\n",
                        "evidence_paths": list(candidate.evidence_paths),
                        "static_api_verified": False,
                        "execution_verified": False,
                        "verification_outcome": result.outcome,
                        "validation_reason": result.detail,
                        **negative,
                    }
                )
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
        value={"inline_examples": verified, "withheld_inline_examples": withheld},
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
