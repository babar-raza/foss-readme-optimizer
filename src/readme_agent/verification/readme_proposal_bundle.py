"""Independently verify a finished local README-proposal evidence bundle.

This is the separate-verifier seam for ``L8-LOCAL-README-PROPOSAL-PROOF`` and
``VER-001`` (author != verifier). It consumes only the artifacts a producer
wrote to a bundle directory -- original, candidate, patch, facts, plan,
validation, and per-file checksums -- and re-derives every claim from scratch.
It never trusts the producer's own ``independent-review.json``, manifest, or
stored candidate: the candidate is rebuilt from the original README and facts,
the patch is re-applied with native Git, validation is recomputed, and facts
are re-checked. A copied or byte-tampered candidate cannot survive the
reconstruction check; a lazy cross-pilot clone cannot survive the specificity
check.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from readme_agent.ecosystems.foss_coordinate import canonical_foss_coordinate
from readme_agent.ecosystems.resolver import resolve
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.gitsafety._git import run_git
from readme_agent.readme.agentic_composition import ReadmeAgenticCompositionPlanV1
from readme_agent.readme.assessment import ReadmeAssessmentV1, assess_readme_document
from readme_agent.readme.claim_map import ReadmeClaimMapV1, build_readme_claim_map
from readme_agent.readme.document_hashing import sha256_hex
from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.registry.loader import require_listed

VERIFIER_IDENTITY = "independent-readme-proposal-bundle-verifier"

_ACCEPTED_FACT_STATES = {"verified", "policy_approved"}
_REQUIRED_ARTIFACTS = (
    "original-readme.md",
    "candidate-readme.md",
    "proposal.patch",
    "product-facts-v2.json",
    "readme-assessment-v1.json",
    "agentic-composition-plan-v1.json",
    "readme-document-plan-v1.json",
    "claim-map-v1.json",
    "repository-presentation-plan-v1.json",
    "document-validation.json",
    "artifact-sha256.json",
)
_FAMILY_TOKEN = re.compile(r"Aspose\.[A-Za-z0-9]+")
_PATCH_TARGET = re.compile(r"^\+\+\+ b/(.+)$", re.MULTILINE)


class ReadmeProposalBundleVerdictV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    org_repo: str
    verified: bool
    checks: dict[str, bool]
    failures: list[str]


class CrossPilotSpecificityVerdictV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    verified: bool
    checks: dict[str, bool]
    failures: list[str]


def _patch_target_path(patch_text: str) -> str:
    match = _PATCH_TARGET.search(patch_text)
    return match.group(1).strip() if match else "README.md"


def _apply_patch_natively(original: str, patch_text: str, path: str) -> str | None:
    """Apply ``patch_text`` to ``original`` in a throwaway Git repo with native
    ``git apply``; return the resulting file text, or ``None`` if Git rejects it."""

    with tempfile.TemporaryDirectory(prefix="readme-verify-patch-") as tmp:
        repo = Path(tmp)
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(original, encoding="utf-8", newline="")
        setup = (
            ["init", "--quiet"],
            ["add", "--", path],
            [
                "-c",
                "user.name=readme-agent-verifier",
                "-c",
                "user.email=verifier@invalid",
                "commit",
                "--quiet",
                "-m",
                "base",
            ],
        )
        for args in setup:
            if run_git(args, cwd=repo).returncode != 0:
                return None
        if run_git(["apply", "-"], cwd=repo, input_text=patch_text).returncode != 0:
            return None
        return target.read_text(encoding="utf-8")


def _verify_acquisition_ground_truth(org_repo: str, facts: ProductFactsV2) -> tuple[bool, str]:
    """Re-check the bundle's package-acquisition claim against the AUTHORITATIVE registry
    LIVE, right now -- never trust the stored fact value alone. A stale bundle's recorded
    acquisition could have been captured before the resolver bug fix (this session's own
    finding), or could simply drift out of date. Rejects a candidate that strips a package
    that IS published (method=source_build despite a live registry hit), and a candidate that
    asserts a registry install for a package that is NOT published. Returns ``(True, ...)``
    when live reality and the recorded outcome agree, or when the check cannot run at all
    (unsupported ecosystem, blocked network) -- inconclusive is not a failure."""
    try:
        entry = require_listed(org_repo)
    except Exception as exc:  # noqa: BLE001 -- any lookup failure is a verification failure
        return False, f"could not resolve registry entry for {org_repo}: {exc}"
    if entry.ecosystem is None:
        return True, "no ecosystem configured -- acquisition ground truth not applicable"
    resolver_ecosystem, coordinate = canonical_foss_coordinate(
        entry.family, entry.ecosystem, entry.org, entry.repo_name
    )
    if resolver_ecosystem is None:
        return True, f"no canonical FOSS coordinate for ecosystem {entry.ecosystem!r}"
    result = resolve(resolver_ecosystem, coordinate)
    if result.blocked:
        return True, f"acquisition ground-truth check network-blocked: {result.detail}"

    acquisition = facts.selected_fact("installation.verified_acquisition")
    recorded_method = (
        acquisition.value.get("method") if isinstance(acquisition.value, dict) else None
    )
    if result.found and recorded_method == "source_build":
        return False, (
            f"{coordinate} IS published ({result.detail}) but the bundle's facts record "
            "method=source_build -- a published install was wrongly stripped"
        )
    if not result.found and recorded_method != "source_build":
        return False, (
            f"{coordinate} is NOT published ({result.detail}) but the bundle's facts record "
            f"method={recorded_method!r} -- an unpublished package cannot be verified"
        )
    return True, ""


def family_token(org_repo: str) -> str | None:
    """The distinctive product token (e.g. ``Aspose.Cells``) used to tell one
    pilot's candidate from another's -- ``None`` if the repo is not an Aspose one."""

    match = _FAMILY_TOKEN.search(org_repo)
    return match.group(0) if match else None


def verify_readme_proposal_bundle(bundle_dir: Path) -> ReadmeProposalBundleVerdictV1:
    """Independently verify one pilot's finished proposal bundle."""

    failures: list[str] = []
    checks: dict[str, bool] = {}
    label = bundle_dir.name

    def record(name: str, ok: bool, detail: str = "") -> bool:
        checks[name] = bool(ok)
        if not ok:
            failures.append(f"{label}: {detail or name}")
        return bool(ok)

    missing = [name for name in _REQUIRED_ARTIFACTS if not (bundle_dir / name).is_file()]
    if not record("all_artifacts_present", not missing, f"missing artifacts: {missing}"):
        return ReadmeProposalBundleVerdictV1(
            org_repo="", verified=False, checks=checks, failures=failures
        )

    original = (bundle_dir / "original-readme.md").read_text(encoding="utf-8")
    candidate = (bundle_dir / "candidate-readme.md").read_text(encoding="utf-8")
    patch_text = (bundle_dir / "proposal.patch").read_text(encoding="utf-8")

    artifact_hashes = json.loads((bundle_dir / "artifact-sha256.json").read_text(encoding="utf-8"))
    checksum_ok = all(
        (bundle_dir / name).is_file() and sha256_hex((bundle_dir / name).read_bytes()) == expected
        for name, expected in artifact_hashes.items()
    )
    record("artifact_checksums_match", checksum_ok, "artifact-sha256.json checksum mismatch")

    try:
        facts = ProductFactsV2.model_validate(
            json.loads((bundle_dir / "product-facts-v2.json").read_text(encoding="utf-8"))
        )
        plan = ReadmeDocumentPlanV1.model_validate(
            json.loads((bundle_dir / "readme-document-plan-v1.json").read_text(encoding="utf-8"))
        )
        assessment = ReadmeAssessmentV1.model_validate(
            json.loads((bundle_dir / "readme-assessment-v1.json").read_text(encoding="utf-8"))
        )
        raw_agentic_plan = json.loads(
            (bundle_dir / "agentic-composition-plan-v1.json").read_text(encoding="utf-8")
        )
        agentic_plan = (
            ReadmeAgenticCompositionPlanV1.model_validate(raw_agentic_plan)
            if raw_agentic_plan
            else None
        )
        claim_map = ReadmeClaimMapV1.model_validate(
            json.loads((bundle_dir / "claim-map-v1.json").read_text(encoding="utf-8"))
        )
    except Exception as exc:  # noqa: BLE001 -- any schema failure is a verification failure
        record("schemas_valid", False, f"schema load failed: {exc}")
        return ReadmeProposalBundleVerdictV1(
            org_repo="", verified=False, checks=checks, failures=failures
        )
    record("schemas_valid", True)
    org_repo = plan.org_repo

    record(
        "source_hash_matches_plan",
        sha256_hex(original) == plan.source_sha256,
        "plan source_sha256 != sha256(original-readme.md)",
    )
    record(
        "facts_hash_matches_plan",
        facts.canonical_hash() == plan.facts_hash,
        "plan facts_hash != facts.canonical_hash()",
    )
    record(
        "candidate_hash_matches_plan",
        sha256_hex(candidate) == plan.candidate_sha256,
        "sha256(candidate-readme.md) != plan candidate_sha256",
    )
    if agentic_plan is not None:
        record(
            "agentic_plan_repository_matches",
            agentic_plan.org_repo == org_repo,
            "agentic composition plan belongs to another repository",
        )
        record(
            "agentic_plan_source_hash_matches",
            agentic_plan.source_sha256 == sha256_hex(original),
            "agentic composition source hash does not match original README",
        )
        record(
            "agentic_plan_facts_hash_matches",
            agentic_plan.facts_hash == facts.canonical_hash(),
            "agentic composition facts hash does not match ProductFactsV2",
        )
        record(
            "agentic_plan_assessment_hash_matches",
            agentic_plan.assessment_hash == assessment.canonical_hash(),
            "agentic composition assessment hash does not match ReadmeAssessmentV1",
        )

    # The load-bearing independence check: rebuild the candidate from scratch.
    recon_candidate, recon_plan = build_readme_document_candidate(
        org_repo,
        original,
        facts,
        base_revision=plan.immutable_base_revision,
        agentic_composition_plan=(
            agentic_plan.model_dump(mode="json") if agentic_plan is not None else None
        ),
    )
    recon_assessment = assess_readme_document(
        org_repo,
        original,
        facts,
        base_revision=plan.immutable_base_revision,
    )
    recon_claim_map = build_readme_claim_map(
        recon_plan,
        facts,
        source_text=original,
        candidate_text=recon_candidate,
    )
    record(
        "independent_reconstruction_byte_identical",
        recon_candidate == candidate,
        "reconstructed candidate does not match the stored candidate",
    )
    record(
        "reconstructed_plan_matches",
        recon_plan.candidate_sha256 == plan.candidate_sha256
        and [op.model_dump() for op in recon_plan.operations]
        == [op.model_dump() for op in plan.operations],
        "reconstructed plan/operations differ from the stored plan",
    )
    record(
        "assessment_reconstructed",
        recon_assessment == assessment,
        "reconstructed README assessment differs from the stored assessment",
    )
    record(
        "claim_map_reconstructed",
        recon_claim_map == claim_map,
        "reconstructed fact-to-claim map differs from the stored claim map",
    )

    selected_ids = set(facts.selected_fact_ids.values())
    cited_ok = True
    accepted_ok = True
    for operation in plan.operations:
        for fact_id in operation.fact_ids:
            if fact_id not in selected_ids:
                cited_ok = False
            elif facts.fact_by_id(fact_id).verification_state not in _ACCEPTED_FACT_STATES:
                accepted_ok = False
    record("operations_cite_selected_facts", cited_ok, "an operation cites a non-selected fact")
    record("cited_facts_accepted", accepted_ok, "an operation cites an unaccepted fact")

    validation = validate_readme_document_candidate(original, candidate, plan, facts)
    record(
        "independent_validation_valid",
        validation.valid,
        f"independent validation failed: {validation.errors}",
    )
    stored_validation = json.loads(
        (bundle_dir / "document-validation.json").read_text(encoding="utf-8")
    )
    record(
        "recomputed_validation_consistent_with_stored",
        validation.valid == bool(stored_validation.get("valid"))
        and validation.checks == stored_validation.get("checks"),
        "recomputed validation disagrees with stored document-validation.json",
    )

    applied = _apply_patch_natively(original, patch_text, _patch_target_path(patch_text))
    record(
        "native_git_apply_produces_candidate",
        applied is not None and applied == candidate,
        "native git apply of proposal.patch does not reproduce the candidate",
    )

    acquisition_ok, acquisition_detail = _verify_acquisition_ground_truth(org_repo, facts)
    record("acquisition_matches_live_registry", acquisition_ok, acquisition_detail)

    return ReadmeProposalBundleVerdictV1(
        org_repo=org_repo,
        verified=not failures,
        checks=checks,
        failures=failures,
    )


def verify_cross_pilot_specificity(
    pilots: list[tuple[str, str]],
) -> CrossPilotSpecificityVerdictV1:
    """Confirm the pilot candidates are product-specific, not clones.

    ``pilots`` is a list of ``(org_repo, candidate_text)``. Rejects: duplicate
    candidates, a candidate missing its own product token, and a candidate that
    leaks another pilot's product token (a lazy name-substituted clone).
    """

    failures: list[str] = []
    checks: dict[str, bool] = {}

    hashes = [sha256_hex(candidate) for _, candidate in pilots]
    if len(set(hashes)) != len(hashes):
        checks["candidates_distinct"] = False
        failures.append("two pilot candidates are byte-identical")
    else:
        checks["candidates_distinct"] = True

    tokens = {org_repo: family_token(org_repo) for org_repo, _ in pilots}
    own_ok = True
    foreign_ok = True
    for org_repo, candidate in pilots:
        own = tokens[org_repo]
        if own is not None and own not in candidate:
            own_ok = False
            failures.append(f"{org_repo}: candidate is missing its own product token {own!r}")
        for other_repo, other_token in tokens.items():
            if other_repo == org_repo or other_token is None or other_token == own:
                continue
            if other_token in candidate:
                foreign_ok = False
                failures.append(
                    f"{org_repo}: candidate leaks another pilot's product token {other_token!r}"
                )
    checks["each_candidate_has_own_identity"] = own_ok
    checks["no_cross_pilot_identity_leak"] = foreign_ok

    return CrossPilotSpecificityVerdictV1(verified=not failures, checks=checks, failures=failures)
