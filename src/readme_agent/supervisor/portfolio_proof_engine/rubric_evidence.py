"""Interpret current candidate evidence for the governed 30-point rubric."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

from readme_agent.supervisor.portfolio_proof_engine.acceptance_contract import (
    benchmark_acceptance_proven,
    replay_attestation_proven,
    replay_bound_rubric_evaluation,
    rubric_acceptance_binding_current,
)
from readme_agent.supervisor.portfolio_proof_engine.evidence_bundle import EvidenceBundleV1

_CURRENT_REQUIRED_CHECKS = frozenset(
    {
        "candidate_matches_independent_render",
        "source_document_hash",
        "candidate_is_marker_free",
        "candidate_has_no_comments",
        "facts_hash_matches",
        "template_hash_matches",
        "candidate_hash_matches",
        "source_span_hashes",
        "fact_citations",
        "api_capability_wording_has_implementation_evidence",
        "document_reconstruction",
        "composition_lineage",
        "protected_content",
        "verified_example_present",
        "verified_overview_present",
        "verified_limitations_present",
        "example_assurance_claims_supported",
        "no_introduced_duplicate_headings",
        "header_visuals",
        "enterprise_edition_terminology",
        "contextual_links",
        "claim_accountability_complete",
        "claim_accountability_gaps_visible",
        "presentation_lint",
        "public_candidate_quality",
        "aspose_checks_no_blocking_errors",
        "needs_write_matches",
    }
)
_ACCEPTED_FACT_STATES = frozenset({"verified", "policy_approved"})
_HEX_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def deterministic_accepts(bundle: EvidenceBundleV1) -> bool:
    validation = bundle.deterministic_validation
    if not validation:
        return False
    if "verdict" in validation:
        checks = validation.get("checks")
        return (
            validation.get("verdict") == "accept"
            and isinstance(checks, dict)
            and _CURRENT_REQUIRED_CHECKS <= checks.keys()
            and all(checks[name] is True for name in _CURRENT_REQUIRED_CHECKS)
        )
    return validation.get("valid") is True and not validation.get("errors")


def current_check(bundle: EvidenceBundleV1, name: str) -> bool | None:
    checks = (bundle.deterministic_validation or {}).get("checks")
    if not isinstance(checks, dict) or name not in checks:
        return None
    return checks[name] is True and deterministic_accepts(bundle)


def _selected_fact(bundle: EvidenceBundleV1, field: str) -> dict | None:
    facts = bundle.facts
    if not facts:
        return None
    selected = facts.get("selected_fact_ids")
    records = facts.get("facts")
    if not isinstance(selected, dict) or not isinstance(records, list):
        return None
    selected_id = selected.get(field)
    return next(
        (
            record
            for record in records
            if isinstance(record, dict)
            and record.get("field") == field
            and record.get("fact_id") == selected_id
        ),
        None,
    )


def accepted_fact(bundle: EvidenceBundleV1, field: str) -> bool | None:
    fact = _selected_fact(bundle, field)
    if fact is None:
        return None
    conflicts = fact.get("conflicts") or []
    unresolved = [
        conflict
        for conflict in conflicts
        if not isinstance(conflict, dict)
        or conflict.get("status") not in {"resolved", "resolved_by_precedence"}
    ]
    return fact.get("verification_state") in _ACCEPTED_FACT_STATES and not unresolved


def accepted_facts(bundle: EvidenceBundleV1, fields: Iterable[str]) -> bool | None:
    outcomes = [accepted_fact(bundle, field) for field in fields]
    if any(outcome is None for outcome in outcomes):
        return None
    return all(outcomes)


def claim_map_complete(bundle: EvidenceBundleV1) -> bool | None:
    claim_map, facts, candidate = bundle.claim_map, bundle.facts, bundle.candidate_readme
    if claim_map is None or facts is None or candidate is None:
        return None
    claims = claim_map.get("claims")
    selected = facts.get("selected_fact_ids")
    if not isinstance(claims, list) or not claims or not isinstance(selected, dict):
        return False
    candidate_bytes = candidate.encode("utf-8")
    candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()
    if claim_map.get("candidate_sha256") != candidate_hash:
        return False
    selected_ids = set(selected.values())
    for claim in claims:
        if not isinstance(claim, dict) or claim.get("fact_id") not in selected_ids:
            return False
        if claim.get("verification_state") not in _ACCEPTED_FACT_STATES:
            return False
        start, end = claim.get("byte_start"), claim.get("byte_end")
        if not isinstance(start, int) or not isinstance(end, int) or not (0 <= start < end):
            return False
        if end > len(candidate_bytes):
            return False
        if hashlib.sha256(candidate_bytes[start:end]).hexdigest() != claim.get("claim_text_sha256"):
            return False
    return deterministic_accepts(bundle)


def example_truth(bundle: EvidenceBundleV1) -> bool | None:
    fact = _selected_fact(bundle, "example.minimal")
    if fact is None:
        return None
    if fact.get("verification_state") != "verified" or fact.get("conflicts"):
        return False
    value = fact.get("value")
    if not isinstance(value, dict):
        return False
    outcome = str(value.get("verification_outcome") or "")
    return bool(outcome and outcome not in {"UNVERIFIED", "FAILED"}) and (
        current_check(bundle, "verified_example_present") is True
        and current_check(bundle, "example_assurance_claims_supported") is True
    )


def api_truth(bundle: EvidenceBundleV1) -> bool | None:
    return _all_known(
        accepted_fact(bundle, "api.public_surface"),
        current_check(bundle, "api_capability_wording_has_implementation_evidence"),
        current_check(bundle, "claim_accountability_complete"),
    )


def checks_complete(bundle: EvidenceBundleV1) -> bool | None:
    coverage = bundle.check_coverage
    if coverage is None:
        return None
    entries = coverage.get("entries")
    if not isinstance(entries, list) or not entries:
        return False
    blocking = [entry for entry in entries if isinstance(entry, dict) and entry.get("blocking")]
    return bool(blocking) and all(entry.get("outcome") == "pass" for entry in blocking)


def review_accepts(record: dict | None) -> bool | None:
    if not record:
        return None
    nested_result = record.get("result")
    result = nested_result if isinstance(nested_result, dict) else record
    return result.get("verdict") == "ACCEPT" if "verdict" in result else None


def review_supports(record: dict | None, *, sections: tuple[str, ...]) -> bool | None:
    if record is None:
        return None
    accepts = review_accepts(record)
    if accepts is not True:
        return accepts
    nested_result = record.get("result")
    result = nested_result if isinstance(nested_result, dict) else record
    findings = result.get("findings")
    if not isinstance(findings, list):
        return None
    supported = {
        str(finding.get("section", "")).split("/", maxsplit=1)[0]
        for finding in findings
        if isinstance(finding, dict) and finding.get("disposition") == "supports_acceptance"
    }
    return all(section in supported for section in sections)


def reconciliation_complete(bundle: EvidenceBundleV1, unit_kind: str) -> bool | None:
    report, source = bundle.reconciliation, bundle.source_readme
    if report is None or source is None:
        return None
    entries = report.get("entries")
    if not isinstance(entries, list):
        return False
    source_bytes = source.encode("utf-8")
    if report.get("source_bytes") != len(source_bytes):
        return False
    cursor = 0
    for entry in sorted(entries, key=lambda item: item.get("source_byte_start", -1)):
        if not isinstance(entry, dict) or entry.get("source_byte_start") != cursor:
            return False
        end = entry.get("source_byte_end")
        if not isinstance(end, int) or end <= cursor or end > len(source_bytes):
            return False
        cursor = end
    if cursor != len(source_bytes):
        return False
    spans = _source_unit_spans(source, unit_kind)
    return all(_span_is_covered(start, end, entries) for start, end in spans)


def reconciliation_integrity(bundle: EvidenceBundleV1) -> bool | None:
    complete = reconciliation_complete(bundle, "content")
    if complete is not True:
        return complete
    assert bundle.reconciliation is not None
    for entry in bundle.reconciliation["entries"]:
        disposition = entry.get("disposition")
        if disposition in {"preserved", "relocated"}:
            if entry.get("final_byte_start") is None or entry.get("final_byte_end") is None:
                return False
        elif disposition in {"corrected", "superseded", "omitted"}:
            if not entry.get("rationale") or not entry.get("evidence"):
                return False
        else:
            return False
    return True


def sealed_inputs(bundle: EvidenceBundleV1) -> bool | None:
    manifest, revision, plan, source = (
        bundle.manifest,
        bundle.snapshot_revision,
        bundle.document_plan,
        bundle.source_readme,
    )
    if not manifest or not revision or not plan or source is None:
        return None
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return all(
        (
            manifest.get("source_revision")
            == revision.get("source_revision")
            == bundle.source_revision,
            revision.get("readme_sha256") == plan.get("source_sha256") == source_hash,
            _is_hash(manifest.get("facts_hash")),
            _is_hash(manifest.get("candidate_stage_dependency_key")),
            _is_hash(manifest.get("prompt_registry_content_hash")),
            isinstance(manifest.get("prompt_dependency_hashes"), dict),
        )
    )


def exact_byte_binding(bundle: EvidenceBundleV1) -> bool | None:
    if bundle.candidate_readme is None or not bundle.manifest:
        return None
    actual = hashlib.sha256(bundle.candidate_readme.encode("utf-8")).hexdigest()
    records = [bundle.manifest, bundle.claim_map, bundle.factual_review, bundle.visitor_review]
    hashes = [
        record.get("candidate_hash") or record.get("candidate_sha256")
        for record in records
        if record is not None
    ]
    return (
        bool(hashes)
        and all(value == actual for value in hashes)
        and bundle.candidate_hash == actual
    )


def repeatable_acceptance(bundle: EvidenceBundleV1) -> bool | None:
    proof = bundle.no_op_proof
    if proof is None:
        return None
    return all(
        (
            proof.get("verdict") == "NO_OP_PROVEN",
            proof.get("candidate_hash") == bundle.candidate_hash,
            proof.get("patch_created") is False,
            proof.get("duplicate_bundle_created") is False,
            proof.get("llm_accounting_status") == "EXACT",
            proof.get("new_provider_call_count") == 0,
            isinstance(proof.get("acceptance_binding"), dict),
        )
    )


def _all_known(*outcomes: bool | None) -> bool | None:
    if any(outcome is None for outcome in outcomes):
        return None
    return all(outcomes)


def _is_hash(value: object) -> bool:
    return isinstance(value, str) and bool(_HEX_SHA256.fullmatch(value))


def _span_is_covered(start: int, end: int, entries: list[dict]) -> bool:
    cursor = start
    for entry in entries:
        entry_start, entry_end = entry.get("source_byte_start"), entry.get("source_byte_end")
        if not isinstance(entry_start, int) or not isinstance(entry_end, int):
            return False
        if entry_end <= cursor:
            continue
        if entry_start > cursor:
            return False
        cursor = min(end, entry_end)
        if cursor == end:
            return True
    return cursor == end


def _source_unit_spans(source: str, unit_kind: str) -> list[tuple[int, int]]:
    patterns = {
        "content": r"\S+",
        "structure": r"(?m)^(?:#{1,6}\s|[-*+]\s|\|.*\||<details>|<summary>).+$",
        "code": r"(?ms)^```[^\n]*\n.*?^```[ \t]*$",
        "media": r"!\[[^\]]*\]\([^\n)]+\)|<img\b[^>]*>",
    }
    pattern = patterns.get(unit_kind)
    if pattern is None:
        return []
    spans: list[tuple[int, int]] = []
    for match in re.finditer(pattern, source, flags=re.IGNORECASE if unit_kind == "media" else 0):
        start = len(source[: match.start()].encode("utf-8"))
        end = len(source[: match.end()].encode("utf-8"))
        spans.append((start, end))
    return spans


__all__ = [
    "accepted_fact",
    "accepted_facts",
    "api_truth",
    "benchmark_acceptance_proven",
    "checks_complete",
    "claim_map_complete",
    "current_check",
    "deterministic_accepts",
    "exact_byte_binding",
    "example_truth",
    "reconciliation_complete",
    "reconciliation_integrity",
    "repeatable_acceptance",
    "replay_attestation_proven",
    "replay_bound_rubric_evaluation",
    "review_accepts",
    "review_supports",
    "rubric_acceptance_binding_current",
    "sealed_inputs",
]
