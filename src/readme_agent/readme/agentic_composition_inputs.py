"""Build canonical input bindings for initial and reviewer-directed composition."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

from readme_agent.facts.prompt_projection import prompt_fact_value
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.agentic_composition_models import ReadmeCompositionRepairRequestV1
from readme_agent.readme.fact_grounding_views import fact_strings

_MAX_PROMPT_API_ITEMS = 16
_MAX_PROMPT_ASSET_PATHS = 5
_MAX_PROMPT_LIST_ITEMS = 12
_MAX_COMPACT_DEPTH = 3
_MAX_SCALAR_STRING_CHARS = 500


def _compact_scalar(value: Any) -> Any:
    """Bound one leaf string -- a native execution transcript
    (`compiled_consumer.isolated_execution.stdout` and its like) is
    structurally indistinguishable from any other string field, so length
    alone, not a known field name, is what separates useful short evidence
    from a receipt that duplicates evidence already checksum-bound in
    `ProductFactsV2` and can add hundreds of thousands of prompt tokens."""

    if isinstance(value, str) and len(value) > _MAX_SCALAR_STRING_CHARS:
        return value[:_MAX_SCALAR_STRING_CHARS] + f"... [{len(value)} chars total, truncated]"
    return value


def _compact_nested_value(value: Any, *, depth: int = 0) -> Any:
    """Schema-agnostic bounding for one arbitrary ecosystem's nested
    evidence sub-object (a package layout, a compiled-consumer proof, a
    format-evidence record, ...): keep scalars as-is (bounding long
    strings), bound long lists, and recurse into nested dicts/lists up to a
    shallow depth. Every ecosystem's own sub-object survives identically
    through this one rule -- no per-platform branch decides which fields to
    keep."""

    if isinstance(value, dict):
        if depth >= _MAX_COMPACT_DEPTH:
            return {
                key: _compact_scalar(val)
                for key, val in value.items()
                if not isinstance(val, (dict, list))
            }
        return {key: _compact_nested_value(val, depth=depth + 1) for key, val in value.items()}
    if isinstance(value, list):
        if depth >= _MAX_COMPACT_DEPTH:
            return [_compact_scalar(val) for val in value if not isinstance(val, (dict, list))][
                :_MAX_PROMPT_LIST_ITEMS
            ]
        return [_compact_nested_value(item, depth=depth + 1) for item in value][
            :_MAX_PROMPT_LIST_ITEMS
        ]
    return _compact_scalar(value)


def _normalized_implementation(value: Any) -> str:
    """Collapse either real shape's raw implementation signal to one shared
    3-value vocabulary -- `curated_python_public_surface.py` uses `bool |
    None` per member; `composer_factpack.py`'s aspose-detection shape (the
    other 6 platforms) uses the `ApiImplementationState` string literal at
    class level. Never a per-platform branch: which shape a class carries
    is a data question (`_member_implemented_values` below), not a
    field-name-based guess here."""

    if value is True or value == "implemented":
        return "implemented"
    if value is False or value == "stubbed":
        return "stubbed"
    return "unknown"


def _member_implemented_values(item: dict) -> list[Any]:
    """Raw, per-item implementation signal(s) for one class, whichever real
    shape it carries. `members` (Python's per-member `implemented`) is
    preferred when present; otherwise falls back to the class-level `state.
    implemented` the aspose-detection shape provides instead (that shape
    has no per-member granularity at all -- `aspose_detectors.py::
    _resolve_implementation` always returns `"unknown"` today, so this
    correctly surfaces `"unknown"` rather than fabricating per-member
    detail the corpus never had)."""

    members = item.get("members")
    if isinstance(members, list):
        return [member.get("implemented") for member in members if isinstance(member, dict)]
    if item.get("methods") or item.get("properties"):
        state = item.get("state")
        return [state.get("implemented") if isinstance(state, dict) else None]
    return []


def _class_state_summary(item: dict) -> dict[str, Any]:
    """Owner review (2026-08-20), check 2: visibility/reachability/
    implementation must survive this compaction, not just bare names --
    otherwise no downstream consumer (deterministic renderer or an LLM
    authoring/reviewing call) can tell a proven-real class from one whose
    implementation is merely unknown, and `implemented=unknown` could end
    up authorizing capability prose with nothing to stop it. `visibility`/
    `reachable` come from the aspose-detection shape's class-level `state`
    when present; `implementation_states` is the normalized, deduplicated
    set of every implementation signal found for this class (see
    `_member_implemented_values`) -- `["unknown"]` is a first-class,
    honest answer, never omitted to look cleaner."""

    raw_state = item.get("state")
    state = raw_state if isinstance(raw_state, dict) else {}
    summary: dict[str, Any] = {"name": item.get("name")}
    if state.get("visibility") is not None:
        summary["visibility"] = state.get("visibility")
    if state.get("reachable") is not None:
        summary["reachable"] = state.get("reachable")
    implementation_states = _unique_strings(
        _normalized_implementation(raw) for raw in _member_implemented_values(item)
    )
    if implementation_states:
        summary["implementation_states"] = implementation_states
    return summary


def compact_prompt_fact_value(field: str, value: Any) -> Any:
    """Keep author/reviewer evidence useful without copying native inventories.

    The full fact value remains checksum-bound in ``ProductFactsV2``. This view is
    deliberately lossy: it exposes representative public symbols and asset counts,
    while source trees, per-file hashes, and verifier transcripts stay in evidence.
    """

    projected = prompt_fact_value(field, value)
    if field == "api.public_surface" and isinstance(projected, dict):
        modules = projected.get("modules") or []
        classes = projected.get("classes") or []
        exports = _unique_strings(
            export
            for module in modules
            if isinstance(module, dict)
            for export in module.get("exports") or []
        )
        class_summaries: list[dict[str, Any]] = []
        seen_class_names: set[str] = set()
        for item in classes:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name or name in seen_class_names:
                continue
            seen_class_names.add(name)
            class_summaries.append(_class_state_summary(item))
        member_surfaces = _unique_strings(
            member.get("surface") or member.get("name")
            for item in classes
            if isinstance(item, dict)
            for member in item.get("members") or []
            if isinstance(member, dict)
        )
        return {
            "module_names": _unique_strings(
                module.get("module") for module in modules if isinstance(module, dict)
            )[:_MAX_PROMPT_API_ITEMS],
            "representative_exports": exports[:_MAX_PROMPT_API_ITEMS],
            "representative_classes": class_summaries[:_MAX_PROMPT_API_ITEMS],
            "representative_member_surfaces": member_surfaces[:_MAX_PROMPT_API_ITEMS],
            "inventory_counts": {
                "modules": len(modules),
                "exports": len(exports),
                "classes": len(classes),
                "member_surfaces": len(member_surfaces),
            },
            "projection_bounded": any(
                count > _MAX_PROMPT_API_ITEMS
                for count in (len(exports), len(class_summaries), len(member_surfaces))
            ),
        }
    if field == "development.assets" and isinstance(projected, dict):
        compact_groups: dict[str, dict[str, Any]] = {}
        for group_name, group in projected.items():
            if not isinstance(group, dict):
                continue
            paths = [
                str(item.get("path"))
                for item in group.get("representative_paths") or []
                if isinstance(item, dict) and item.get("path")
            ]
            compact_groups[str(group_name)] = {
                "count": group.get("count"),
                "inventory_sha256": group.get("inventory_sha256"),
                "representative_paths": paths[:_MAX_PROMPT_ASSET_PATHS],
            }
        return compact_groups
    if field == "example.minimal" and isinstance(projected, dict):
        # Generic, schema-driven projection: every key `prompt_fact_value`
        # already let through (language/code/verification.../ecosystem
        # metadata for whichever platform this repository is -- python_
        # package, typescript_package, rust_package, compiled_consumer,
        # ...) survives compaction identically, bounded by the same shared
        # rule. No per-ecosystem key name is special-cased here; a platform
        # this repository does not use simply never has that key present.
        return {
            key: _compact_nested_value(val) for key, val in projected.items() if val is not None
        }
    return projected


def _unique_strings(values: Iterable[object]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value is not None and str(value)))


_MAX_PROTECTED_LITERALS = 24
_MAX_CORROBORATION_ANCHORS = 12
_NEGATIVE_POLARITY_FIELDS = frozenset({"product.limitations", "aspose.limitation_claims"})


def _fact_polarity(fact: FactRecordV2) -> str:
    """Whether this fact asserts a positive capability or an explicit
    constraint/limitation -- reuses `evidence_polarity.py`'s own vocabulary
    (`positive_implementation`/`explicit_constraint`) rather than inventing
    a parallel one. Prefers a real, per-anchor observed polarity when this
    fact carries one; otherwise falls back to the same field-name rule
    `schema_v2.py::FactRecordV2._bind_directional_evidence` already uses."""

    if fact.evidence_assessments:
        observed = {assessment.observed_polarity for assessment in fact.evidence_assessments}
        if len(observed) == 1:
            return next(iter(observed))
    return (
        "explicit_constraint"
        if fact.field in _NEGATIVE_POLARITY_FIELDS
        else "positive_implementation"
    )


def _fact_corroboration(fact: FactRecordV2) -> dict:
    """Owner review (2026-08-20), correction 5: corroboration is distinct
    from `verification_state` -- verification_state answers "is this fact's
    current status trustworthy"; corroboration answers "how many
    independent, real signals actually back it, and does anything
    disagree." Real per-anchor evidence citations (source path + line
    number only, never the full excerpt -- that duplicates `protected_
    literals`/the evidence bundle) plus resolved/unresolved competing-source
    conflict counts, generic across every ecosystem since `FactRecordV2`
    carries `evidence_assessments`/`conflicts` identically regardless of
    platform."""

    assessments = fact.evidence_assessments or []
    accepted = [assessment for assessment in assessments if assessment.accepted]
    return {
        "evidence_assessment_count": len(assessments),
        "accepted_evidence_anchors": [
            {"source_path": assessment.source_path, "line_number": assessment.line_number}
            for assessment in accepted[:_MAX_CORROBORATION_ANCHORS]
        ],
        "has_unresolved_conflict": fact.has_unresolved_conflict,
        "resolved_conflict_count": sum(
            1 for conflict in fact.conflicts if conflict.status != "unresolved"
        ),
    }


def composition_fact_payloads(
    facts: ProductFactsV2,
    accepted_fact_ids: set[str],
) -> list[dict]:
    """Project accepted facts into a compact authoring packet.

    The complete provenance graph and native-tool receipts remain authoritative in
    ``ProductFactsV2`` and the evidence bundle. The model needs only selected values,
    compact provenance, and stable citation IDs; sending compiled-consumer transcripts
    duplicates evidence and can add hundreds of thousands of prompt tokens.

    Every accepted fact carries its verification state, corroboration (how many real
    evidence anchors and competing-source conflicts back it -- distinct from
    verification state), and polarity explicitly (never left for the author to infer
    from field name alone), its exact protected literals (the citable-verbatim strings
    `readme/fact_grounding.py::find_literal_fact_match` would bind a claim against --
    never paraphrased), and whatever ecosystem-specific metadata `compact_prompt_fact_value`
    preserves generically for this platform.
    """

    payloads = []
    for fact in facts.facts:
        if fact.fact_id not in accepted_fact_ids:
            continue
        compacted_value = compact_prompt_fact_value(fact.field, fact.value)
        # Derived from the already-compacted value, not the raw fact --
        # a protected literal is a string the author actually sees and
        # should quote verbatim, never a bounded-out native transcript
        # leaking back in through a second field.
        payloads.append(
            {
                "fact_id": fact.fact_id,
                "field": fact.field,
                "value": compacted_value,
                "verification_state": fact.verification_state,
                "corroboration": _fact_corroboration(fact),
                "polarity": _fact_polarity(fact),
                "protected_literals": fact_strings(compacted_value)[:_MAX_PROTECTED_LITERALS],
                "source": {
                    "source_type": fact.source.source_type,
                    "location": fact.source.location,
                    "source_revision": fact.source.source_revision,
                },
                "supporting_fact_ids": fact.supporting_fact_ids,
            }
        )
    return payloads


_MAX_DO_NOT_CLAIM_ITEMS = 24


def do_not_claim_payloads(facts: ProductFactsV2) -> list[dict]:
    """Bounded, explicit "never claim this" guidance: a fact this run's own
    resolver marked `conflicting` (an unresolved disagreement between
    equally-authoritative sources) or that otherwise carries an unresolved
    conflict record. Deliberately not the full unaccepted-fact set -- only
    genuinely negative/contradicted evidence, so the author sees a short,
    actionable list rather than corpus noise. No unresolved, stale,
    synthetic-only, or contradicted evidence is ever in `accepted_fact_ids`
    to begin with (the resolver/selection gates upstream already enforce
    that); this is a positive, visible warning on top, not the boundary
    itself."""

    items = [
        {
            "fact_id": fact.fact_id,
            "field": fact.field,
            "reason": (
                "conflicting_evidence"
                if fact.verification_state == "conflicting"
                else "unresolved_conflict"
            ),
        }
        for fact in facts.facts
        if fact.verification_state == "conflicting" or fact.has_unresolved_conflict
    ]
    return items[:_MAX_DO_NOT_CLAIM_ITEMS]


def independent_repair_hints(request: ReadmeCompositionRepairRequestV1 | None) -> str:
    """Render one stable, source-bound reviewer instruction block."""

    if request is None:
        return ""
    return (
        "INDEPENDENT REVIEW REPAIR. The prior candidate was rejected. "
        "Address only the bounded findings below, preserve the named content, "
        "and still obey every deterministic section disposition and fact-ID constraint:\n"
        + json.dumps(request.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
    )


def composition_input_payload(
    *,
    org_repo: str,
    source_text: str,
    facts_payload: list[dict],
    assessment_payload: dict,
    phrase_options: list[dict],
    authoring_hints: str,
    do_not_claim: list[dict] | None = None,
) -> dict:
    """Return the exact canonical payload whose hash binds an authoring plan.

    `do_not_claim` defaults to an explicit empty list, never omitted, so a
    caller that has not yet computed it is visible in the hashed payload
    shape rather than silently absent from it.
    """

    return {
        "org_repo": org_repo,
        "source_text": source_text,
        "accepted_facts": facts_payload,
        "assessment": assessment_payload,
        "overview_phrase_options": phrase_options,
        "repair_hints_section": authoring_hints,
        "do_not_claim": do_not_claim or [],
    }


def composition_input_sha256(payload: dict) -> str:
    """Hash a canonical authoring input without relying on serialization order."""

    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def truncation_repair_hint(*, attempt: int) -> str:
    """Answer a truncated forced tool call with brevity, not with more instructions."""

    return (
        f"REPAIR ATTEMPT {attempt}. Your previous submission was cut off before it "
        "finished writing -- the response ran out of space and could not be parsed. "
        "Call submit_readme_composition_plan again with the same structure and the same "
        "fact IDs, but write noticeably less: shorter section rationales, shorter "
        "opening_summary, fewer diagram nodes where a role allows it, and no optional "
        "elaboration. Completeness of the required fields matters more than detail in "
        "any one of them."
    )
