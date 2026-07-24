"""Shared, deterministic re-derivation helpers for Wave 8's independent
verifier -- callable by both `capabilities/verify_readme_candidate.py` (8b)
and `specialists/independent_verification.py` (8c). "Independent" means never
trusting a caller's claimed `status`/`needs_write`/`final_text` at face
value -- re-derive ground truth from a fresh read of the actual current
on-disk work clone and the repo's own configured policy, and compare. This
is the concrete fix for the already-known defect: `specialists/readme_
presentation.py::_commit_node()` durably accepted a `BLOCKED_VALIDATION_
FAILED` candidate's `facts_hash` because nothing re-checked the claimed
`status` before accepting it.

Known, stated simplification: gap re-detection uses the policy's own
*declared* license (`policy.required_elements.license_mentioned.
detected_license`), not a full re-run of live SPDX/manifest/LICENSE-file
detection (`license.auditor.detect_license()`, which `orchestrator.py`'s own
render path uses) -- re-deriving that here would require duplicating
ecosystem-specific manifest parsing. In the normal, correctly-configured
case these agree (a policy is configured to declare the license the repo
actually has); if they diverge, that is exactly the kind of cross-surface
inconsistency `community_files_presentation`/`cross_surface_validation`
already exist to catch (Wave 7e/7f), not this module's job to re-detect.
"""

import hashlib

from readme_agent import paths
from readme_agent.errors import NotAllowlistedError
from readme_agent.facts.provider import collect_product_facts
from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.inspection import file_inventory
from readme_agent.readme.document_renderer import build_readme_document_candidate
from readme_agent.readme.document_validation import validate_readme_document_candidate
from readme_agent.readme.gap_detector import detect as detect_gaps
from readme_agent.readme.markers import find_presentation_span
from readme_agent.registry.loader import load_policy, require_listed
from readme_agent.repository_snapshot import current_repository_snapshot
from readme_agent.validation import registry as validation_registry
from readme_agent.validation.context import ValidationContext


def compute_verification_token(
    org_repo: str, facts_hash: str, fresh_fingerprint: str, nonce: str
) -> str:
    """TC-15 (decision #46, `F3`): a deterministic token binding a real
    `accept` verdict to the exact candidate it was computed for, replacing
    the plain literal string `"accept"` `commit_readme_write.py::precheck()`
    used to compare against. `specialists/readme_presentation.py::
    _verify_node` computes this ONLY after `independently_verify_readme_
    candidate()` actually returned `verdict == "accept"` for these exact
    `facts_hash`/`fresh_fingerprint` values; `commit_readme_write.py::
    precheck()` re-derives the same value from its own arguments and rejects
    on any mismatch.

    Named plainly, not oversold: this is a same-process consistency check
    against an accidental wiring bug (a future code path that skips
    `_verify_node` and hardcodes a literal `"accept"`, the exact class `F3`
    found real and already-shipped) -- not a cryptographic secret or a
    defense against a deliberately adversarial caller who could read this
    same source file and reimplement the formula. `GOVERNANCE.md`'s own
    capability-lifecycle rule 7 ("graph structure is a reliability layer, not
    a security boundary") is the reason a real check was needed here at all;
    this is that check, scoped honestly to the threat it actually closes.

    `nonce` (TC-28, decision #46's own deferred scope from TC-15): a value
    freshly generated once per `_verify_node` call (one per specialist `run()`
    invocation), never persisted or reused across separate runs. Closes the
    one gap TC-15's own docstring already named honestly: without it, a
    token computed for a given `facts_hash`/`fresh_fingerprint` in one run
    would still be valid if replayed (e.g. read back out of durably-persisted
    evidence/state) into a LATER, separate run for content that happens to
    hash the same way. With a fresh nonce every run, a replayed token from an
    earlier run can never match the nonce `precheck()` re-derives against in
    the current one."""
    canonical = f"{org_repo}:{facts_hash}:{fresh_fingerprint}:{nonce}:accept"
    return hashlib.sha256(canonical.encode()).hexdigest()


# `render_readme_candidate.execute()`'s own produced `status` values
# (`orchestrator.py::ReadmeCandidate.status`) that are legitimate when no
# write is needed.
_NO_WRITE_ELIGIBLE_STATUSES = frozenset({"COMPLIANT_NO_CHANGE"})
_WRITE_ELIGIBLE_STATUS = "GENERATED"


def _verify_presentation_candidate(org_repo: str, final_text: str) -> dict:
    facts_result = collect_product_facts(org_repo)
    facts = ProductFactsV2.model_validate(facts_result["product_facts_v2"])
    identity = facts.selected_fact("product.identity")
    source_revision = identity.source.source_revision
    if source_revision is None:
        return {
            "verdict": "reject",
            "reason": "product identity has no immutable source revision",
            "checks": {"immutable_source_revision": False},
            "requirement_map": {},
        }
    snapshot = current_repository_snapshot(org_repo)
    if snapshot is not None:
        source_path = (
            snapshot.root_path / snapshot.readme_path
            if snapshot.readme_path is not None
            else snapshot.root_path / "README.md"
        )
    else:
        entry = require_listed(org_repo)
        source_path = paths.baseline_dir(entry.org, entry.repo_name) / "README.md"
    source_text = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
    expected, plan = build_readme_document_candidate(
        org_repo,
        source_text,
        facts,
        base_revision=source_revision,
    )
    validation = validate_readme_document_candidate(
        source_text,
        final_text,
        plan,
        facts,
    )
    checks = {"candidate_matches_independent_render": expected == final_text, **validation.checks}
    if expected != final_text or not validation.valid:
        return {
            "verdict": "reject",
            "reason": "; ".join(
                (["candidate differs from independent render"] if expected != final_text else [])
                + validation.errors
            ),
            "checks": checks,
            "requirement_map": {},
        }
    return {
        "verdict": "accept",
        "reason": None,
        "checks": checks,
        "requirement_map": {
            "immutable_snapshot": True,
            "fact_backed_document_plan": True,
            "verified_example": validation.checks["verified_example_present"],
            "protected_content": validation.checks["protected_content"],
        },
    }


def independently_verify_readme_candidate(
    org_repo: str, final_text: str, status: str, needs_write: bool
) -> dict:
    """Returns `{"verdict": "accept"|"reject", "reason": str | None,
    "checks": dict[str, bool], "requirement_map": dict[str, bool]}`
    (`verification/schema.py::VerificationVerdictV1`'s shape, as a plain
    dict). Raises `NotAllowlistedError` for a genuine registry/config
    problem (unlisted repo, no `policy_profile`) -- that is a caller/config
    error, not a candidate-content rejection, and is deliberately NOT
    reported as a `"reject"` verdict so it is never conflated with
    `classify_verification()`'s `"verification_rejected"` classification."""
    entry = require_listed(org_repo)
    if entry.policy_profile is None:
        raise NotAllowlistedError(f"{org_repo} has no policy_profile configured yet")
    policy = load_policy(entry.policy_profile)

    work_path = paths.work_dir(entry.org, entry.repo_name)
    inventory = file_inventory.scan(work_path)
    readme_path = inventory.readme_path or (work_path / "README.md")
    current_on_disk_text = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

    actual_needs_write = final_text != current_on_disk_text
    if actual_needs_write != needs_write:
        return {
            "verdict": "reject",
            "reason": (
                f"claimed needs_write={needs_write} does not match the independently "
                f"observed comparison of final_text against the current on-disk README "
                f"(actual={actual_needs_write})"
            ),
            "checks": {"needs_write_matches": False},
            "requirement_map": {},
        }

    presentation_candidate = find_presentation_span(final_text) is not None
    if not needs_write:
        if status not in _NO_WRITE_ELIGIBLE_STATUSES:
            return {
                "verdict": "reject",
                "reason": (
                    f"needs_write is False but claimed status={status!r} is not one of "
                    f"{sorted(_NO_WRITE_ELIGIBLE_STATUSES)}"
                ),
                "checks": {"needs_write_matches": True},
                "requirement_map": {},
            }
        if presentation_candidate:
            result = _verify_presentation_candidate(org_repo, final_text)
            result["checks"]["needs_write_matches"] = True
            return result
        return {
            "verdict": "accept",
            "reason": None,
            "checks": {"needs_write_matches": True},
            "requirement_map": {},
        }

    if presentation_candidate:
        if status != _WRITE_ELIGIBLE_STATUS:
            return {
                "verdict": "reject",
                "reason": f"needs_write is True but claimed status={status!r} is not GENERATED",
                "checks": {"needs_write_matches": True},
                "requirement_map": {},
            }
        result = _verify_presentation_candidate(org_repo, final_text)
        result["checks"]["needs_write_matches"] = True
        return result

    declared_license = policy.required_elements.license_mentioned.detected_license
    gap_report = detect_gaps(final_text, detected_license=declared_license)
    ctx = ValidationContext(
        readme_text=final_text,
        baseline_readme_text=current_on_disk_text,
        policy=policy,
        pre_render_gap_report=gap_report,
        detected_license=declared_license,
    )
    results = validation_registry.run_all(ctx)
    hard_failures = validation_registry.hard_failures(results)

    if status != _WRITE_ELIGIBLE_STATUS:
        return {
            "verdict": "reject",
            "reason": f"needs_write is True but claimed status={status!r} is not GENERATED",
            "checks": {"needs_write_matches": True},
            "requirement_map": {},
        }
    if hard_failures:
        rule_names = [r.rule_name for r in hard_failures]
        return {
            "verdict": "reject",
            "reason": (
                f"claimed status=GENERATED but independent re-validation found "
                f"{len(hard_failures)} hard failure(s): {rule_names}"
            ),
            "checks": {"needs_write_matches": True, "validation_passed": False},
            "requirement_map": {},
        }

    requirement_map = {
        "license_mentioned": gap_report.license_mentioned,
        "products_org_link": gap_report.products_org_link,
        "products_com_link": gap_report.products_com_link,
        "relationship_explained": gap_report.relationship_explained,
    }
    return {
        "verdict": "accept",
        "reason": None,
        "checks": {"needs_write_matches": True, "validation_passed": True},
        "requirement_map": requirement_map,
    }
