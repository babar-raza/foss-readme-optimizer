"""LLM-gated specialist-domain skip mechanism (Wave 8.6, literal `ORC-003`
reversal, built on the revision-stamping/coverage prerequisites in
`state/domain_state.py`).

Only ever offers the LLM a choice among domains a deterministic diff+
boundary gate has ALREADY cleared as genuinely safe to skip -- this module
can only ever narrow the skip set, never expand it. Three of the nine
registered domains (`GITHUB_GENERATED_SURFACE_AUDIT`, `PACKAGE_RELEASE_AUDIT`,
`METADATA_PRESENTATION`) detect changes via live GitHub API state with no
git-diff-correlated signal at all, and two (`CROSS_SURFACE_VALIDATION`,
`INDEPENDENT_VERIFICATION`) dispatch nothing of their own and must always run
last, reading every sibling's *this-run* state -- none of these five are ever
candidates here; a build-time assertion below enforces that.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from string import Template

from readme_agent.capabilities import domains
from readme_agent.capabilities._visual_asset_ops import (
    IMAGE_EXTENSIONS,
    VISUAL_ASSET_SEARCH_DIRS,
)
from readme_agent.errors import LLMError
from readme_agent.gitsafety.clone import diff_changed_paths
from readme_agent.inspection.file_inventory import (
    COMMUNITY_FILENAMES,
    LICENSE_FILENAMES,
    README_FILENAMES,
)
from readme_agent.llm import prompt_registry
from readme_agent.llm.planner_client import PlannerClient
from readme_agent.state.schema import DomainStateV1

# The only domains a diff can plausibly say anything about: their own
# detection signal is the cloned repo's file content, not live API state.
CANDIDATE_DOMAINS: tuple[str, ...] = (
    domains.README_RECONCILIATION,
    domains.COMMUNITY_FILES_PRESENTATION,
    domains.README_PRESENTATION,
    domains.VISUAL_PREPARATION,
)

_NEVER_CANDIDATES = frozenset(
    {
        domains.GITHUB_GENERATED_SURFACE_AUDIT,
        domains.PACKAGE_RELEASE_AUDIT,
        domains.METADATA_PRESENTATION,
        domains.CROSS_SURFACE_VALIDATION,
        domains.INDEPENDENT_VERIFICATION,
    }
)
assert not (set(CANDIDATE_DOMAINS) & _NEVER_CANDIDATES), (
    "CANDIDATE_DOMAINS must never include a domain with no diff-correlated signal "
    "(the three live-API-only audits) or an aggregation-only domain (cross_surface_"
    "validation/independent_verification) -- see this module's own docstring"
)

# Wave 8.6: no operational history yet to justify a different value -- mirrors
# ESCALATION_ALERT_THRESHOLD's/DOSSIER_TOKEN_BUDGET's own precedent reasoning.
# Revisit once OPS-011's agentic-loop golden-set exists.
MAX_CONSECUTIVE_SKIPS = 3


@dataclass
class SkipPlan:
    skip_domains: frozenset[str] = field(default_factory=frozenset)
    reasons: dict[str, str] = field(default_factory=dict)
    forced_run_domains: dict[str, str] = field(default_factory=dict)


def _path_matches_domain(path: str, domain: str) -> bool:
    """Root-level-only match, mirroring `inspection/file_inventory.py::
    scan()`'s own root-only lookup for README/LICENSE/community files."""
    parts = path.split("/")
    basename = parts[-1].lower()
    if domain in (domains.README_RECONCILIATION, domains.README_PRESENTATION):
        return len(parts) == 1 and basename in README_FILENAMES
    if domain == domains.COMMUNITY_FILES_PRESENTATION:
        return len(parts) == 1 and basename in (LICENSE_FILENAMES | COMMUNITY_FILENAMES)
    if domain == domains.VISUAL_PREPARATION:
        top_dir = parts[0] if len(parts) > 1 else "."
        ext = "." + basename.rsplit(".", 1)[-1] if "." in basename else ""
        return top_dir in VISUAL_ASSET_SEARCH_DIRS and ext in IMAGE_EXTENSIONS
    return True  # unreachable: domain is always one of the three above, asserted at import time


def _domain_diff_signal(domain: str, changed_paths: list[str]) -> bool:
    return any(_path_matches_domain(path, domain) for path in changed_paths)


def decide_skips(
    *,
    org_repo: str,
    baseline_path: Path,
    prior_domain_states: dict[str, DomainStateV1],
    current_revision: str,
    specialist_selection_client: PlannerClient | None,
) -> SkipPlan:
    """Per candidate domain, in order: (1) already at the consecutive-skip
    boundary -> forced run, never offered; (2) no prior accept -> forced
    run; (3) diff against the domain's own last-accepted revision is
    undeterminable (`None`) -> forced run, fail closed; (4) diff shows a
    matching path changed -> forced run, never offered. Only domains
    surviving all four go to one single-shot LLM call; on any failure,
    malformed response, or no client configured, the skip set is empty
    (fail closed). Final enforcement, never trusting the LLM's raw claim:
    `skip_domains = requested ∩ eligible`."""
    plan = SkipPlan()
    eligible: list[str] = []

    for domain in CANDIDATE_DOMAINS:
        prior = prior_domain_states.get(domain)
        if prior is not None and prior.consecutive_skip_count >= MAX_CONSECUTIVE_SKIPS:
            plan.forced_run_domains[domain] = "max_consecutive_skips_reached"
            continue
        if prior is None or prior.upstream_revision_at_accept is None:
            plan.forced_run_domains[domain] = "no_prior_accept"
            continue
        changed_paths = diff_changed_paths(
            baseline_path, prior.upstream_revision_at_accept, current_revision
        )
        if changed_paths is None:
            plan.forced_run_domains[domain] = "diff_undeterminable"
            continue
        if _domain_diff_signal(domain, changed_paths):
            plan.forced_run_domains[domain] = "diff_shows_relevant_change"
            continue
        eligible.append(domain)

    if not eligible or specialist_selection_client is None:
        return plan

    manifest = prompt_registry.get("specialist_selection_turn")
    if manifest is None or manifest.user_template is None:
        return plan  # fail closed -- no prompt, no skip

    tool_schema = {
        "type": "function",
        "function": {
            "name": "select_specialists_to_skip",
            "description": "Choose which of the eligible specialist domains to skip this run.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skip_domains": {
                        "type": "array",
                        "items": {"type": "string", "enum": list(eligible)},
                    }
                },
                "required": [],
            },
        },
    }
    messages = [
        {"role": "system", "content": manifest.system.strip()},
        {
            "role": "user",
            "content": Template(manifest.user_template)
            .substitute(org_repo=org_repo, eligible_domains=", ".join(eligible))
            .strip(),
        },
    ]

    try:
        turn = specialist_selection_client.plan(messages, [tool_schema])
    except LLMError:
        return plan  # fail closed
    if turn.tool_call is None:
        return plan
    function = turn.tool_call.get("function", {})
    try:
        arguments = json.loads(function.get("arguments") or "{}")
    except json.JSONDecodeError:
        return plan
    requested = arguments.get("skip_domains")
    if not isinstance(requested, list):
        return plan

    # Final enforcement boundary: never trust the LLM's raw claim, even
    # though the tool schema's own `enum` already restricts it -- a
    # defensive second check against the exact same `eligible` set this
    # function itself computed.
    accepted_skips = {d for d in requested if isinstance(d, str)} & set(eligible)
    plan.skip_domains = frozenset(accepted_skips)
    for domain in accepted_skips:
        plan.reasons[domain] = "llm_selected"
    return plan
