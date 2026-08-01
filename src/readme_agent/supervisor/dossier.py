"""Bounded, uniformly-summarized planner dossier (AGT-008, Wave 8.5).

Replaces `supervisor/loop.py`'s former special-casing where 8 of 9 specialist
domains were reduced to a bare `accepted_status` enum and only
`independent_verification` got its full `details` payload. Every domain now
gets the same treatment: a bounded (<=400 char) summary, with full detail
still available on demand via the `get_domain_findings` capability
(`capabilities/get_domain_findings.py`) rather than force-fed into every turn.

No mandatory per-specialist `planner_summary` field is required -- a generic
fallback (this module) gets nearly all the value with zero changes to any of
the 9 specialist modules. A specialist MAY optionally override by writing
`details["_planner_summary"]` itself; nothing does yet.
"""

import hashlib
import json
from string import Template
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from readme_agent.state.schema import DomainStateV1

MAX_SUMMARY_CHARS = 400
MAX_CAPABILITY_RESULT_CHARS = 2_000
MAX_RESULT_KEYS = 40
MAX_DECISION_FIELDS = 40
MAX_DECISION_FIELD_CHARS = 200
_DECISION_FIELD_NAMES = frozenset(
    {
        "accepted_status",
        "blocked_reason",
        "candidate_hash",
        "changed",
        "complete",
        "error",
        "executable",
        "facts_hash",
        "outcome",
        "reason",
        "source_revision",
        "status",
        "valid",
        "verdict",
        "verified",
    }
)


def summarize_domain(domain: str, state: "DomainStateV1 | None") -> str:
    if state is None:
        return "not yet run"
    details = state.details or {}
    override = details.get("_planner_summary")
    if isinstance(override, str) and override:
        return override[:MAX_SUMMARY_CHARS]
    if details:
        return json.dumps(details, sort_keys=True, default=str)[:MAX_SUMMARY_CHARS]
    return state.accepted_status or "unknown"


def build_initial_dossier(specialist_results: "dict[str, DomainStateV1]") -> dict[str, str]:
    return {
        domain: summarize_domain(domain, result) for domain, result in specialist_results.items()
    }


def bounded_capability_result(capability_id: str, result: dict | None) -> dict | None:
    """Keep small results verbatim and replace large payloads with a decision receipt."""

    canonical = json.dumps(result, sort_keys=True, separators=(",", ":"), default=str)
    if len(canonical) <= MAX_CAPABILITY_RESULT_CHARS:
        return result
    top_level_keys = sorted(str(key) for key in result) if result is not None else []
    return {
        "capability_id": capability_id,
        "decision_fields": _decision_fields(result),
        "full_result_available_via": "durable task evidence or get_domain_findings",
        "payload_omitted": True,
        "result_chars": len(canonical),
        "result_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "result_type": type(result).__name__,
        "top_level_key_count": len(top_level_keys),
        "top_level_keys": top_level_keys[:MAX_RESULT_KEYS],
    }


def _decision_fields(value: object) -> dict[str, object]:
    fields: dict[str, object] = {}

    def visit(current: object, path: str, depth: int) -> None:
        if len(fields) >= MAX_DECISION_FIELDS or depth > 3:
            return
        if isinstance(current, dict):
            for key in sorted(current, key=str):
                child = current[key]
                child_path = f"{path}.{key}" if path else str(key)
                if str(key) in _DECISION_FIELD_NAMES and isinstance(
                    child, (str, int, float, bool, type(None))
                ):
                    fields[child_path] = (
                        child[:MAX_DECISION_FIELD_CHARS] if isinstance(child, str) else child
                    )
                elif depth < 3:
                    visit(child, child_path, depth + 1)
                if len(fields) >= MAX_DECISION_FIELDS:
                    return
        elif isinstance(current, list) and depth < 3:
            for index, child in enumerate(current[:5]):
                visit(child, f"{path}[{index}]", depth + 1)
                if len(fields) >= MAX_DECISION_FIELDS:
                    return

    visit(value, "", 0)
    return fields


def render_turn_context(
    turn_context_template: str,
    *,
    org_repo: str,
    turn_number: int,
    max_turns: int,
    tried_capability_ids: list[str],
    bootstrap_result: dict,
    dossier: dict[str, str],
) -> str:
    return (
        Template(turn_context_template)
        .substitute(
            org_repo=org_repo,
            turn_number=turn_number,
            max_turns=max_turns,
            tried_capabilities=", ".join(tried_capability_ids) or "none yet",
            bootstrap_result=json.dumps(bootstrap_result),
            specialist_summaries=json.dumps(dossier, sort_keys=True),
        )
        .strip()
    )
