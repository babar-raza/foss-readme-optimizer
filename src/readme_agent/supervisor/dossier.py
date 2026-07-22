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

import json
from string import Template
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from readme_agent.llm.prompt_schema import PromptManifest
    from readme_agent.state.schema import DomainStateV1

MAX_SUMMARY_CHARS = 400


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


def render_turn_context(
    manifest: "PromptManifest",
    *,
    org_repo: str,
    turn_number: int,
    max_turns: int,
    tried_capability_ids: list[str],
    bootstrap_result: dict,
    dossier: dict[str, str],
) -> str:
    assert manifest.turn_context_template is not None, (
        f"prompt {manifest.prompt_id!r} has no turn_context_template"
    )
    return (
        Template(manifest.turn_context_template)
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
