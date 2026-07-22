"""Permission-aware dispatcher (sprint Task 4.2) -- promotes Wave 1 spike's
proven inline dispatch logic (plans/investigations/tools/prove_agentic_loop.py)
into reusable, tested production code. A bad request is data the caller
inspects (DispatchResult), never a crash or a silent no-op -- the model
never gets unrestricted execution."""

import json
from dataclasses import dataclass
from typing import Literal

from readme_agent.capabilities import registry
from readme_agent.capabilities.schema import CapabilityGap, PermissionClass

Outcome = Literal[
    "executed",
    "rejected_unknown_capability",
    "rejected_permission_denied",
    "rejected_domain_denied",
    "rejected_invalid_arguments",
    "rejected_precondition_failed",
    "execution_error",
]


@dataclass
class DispatchResult:
    outcome: Outcome
    result: dict | None = None
    gap: CapabilityGap | None = None
    error: str | None = None


def dispatch_tool_call(
    tool_call: dict,
    allowed_permissions: set[PermissionClass],
    caller_domain: str | None = None,
    extra_kwargs: dict | None = None,
) -> DispatchResult:
    """tool_call is the OpenAI tool-call shape proven live in Wave 1:
    {"id": ..., "function": {"name": ..., "arguments": "<json string>"}}.

    caller_domain (Decision #33, `CAP-006`) is supplied only by
    deterministic graph-wiring code -- never by anything the LLM outputs,
    same never-trust-the-LLM's-own-claims posture as every other check
    here. This is the actual enforcement boundary for specialist/agent
    domain isolation: a framework's per-node tool-offer scoping (e.g.
    LangGraph, Wave 6+) reduces wrong-tool-call *rate*, but nothing about it
    is a hard guarantee -- a wiring bug, a stale tool list, or a
    hand-authored call straight into this function all silently bypass it.
    This check is the one point every call path must cross regardless.

    extra_kwargs (AGT-008/Wave 8.5): the one deliberate, narrow exception to
    decision #26(b)'s "capabilities are stateless" rule -- supplied only by
    wiring code (e.g. `supervisor/loop.py::_dispatch_and_record()`), never
    derived from the LLM's own tool-call arguments, and merged *last* so a
    key collision with an LLM-hallucinated argument of the same name fails
    loudly (`TypeError` at the call site, caught by the `except Exception`
    below as a normal `execution_error`) rather than one silently shadowing
    the other. Used today only by `get_domain_findings`, which needs a live
    `state_backend` no LLM tool-call argument could ever legitimately carry."""
    function = tool_call.get("function", {})
    capability_id = function.get("name")
    raw_arguments = function.get("arguments")

    try:
        arguments = (
            json.loads(raw_arguments) if isinstance(raw_arguments, str) else (raw_arguments or {})
        )
    except json.JSONDecodeError as e:
        return DispatchResult(outcome="rejected_invalid_arguments", error=f"invalid JSON: {e}")

    manifest = registry.get(capability_id)
    if manifest is None:
        gap = CapabilityGap(
            requested_capability_id=capability_id,
            requested_need=f"tool call requested unknown capability {capability_id!r}",
            org_repo=arguments.get("org_repo"),
            reason="no registered capability matches this capability_id",
            evidence={"tool_call": tool_call},
        )
        return DispatchResult(outcome="rejected_unknown_capability", gap=gap)

    if manifest.side_effect_class not in allowed_permissions:
        return DispatchResult(
            outcome="rejected_permission_denied",
            error=(
                f"{capability_id!r} requires {manifest.side_effect_class!r}, not in allowed "
                f"permissions {sorted(allowed_permissions)}"
            ),
        )

    if manifest.allowed_domains and caller_domain not in manifest.allowed_domains:
        return DispatchResult(
            outcome="rejected_domain_denied",
            error=(
                f"{capability_id!r} is scoped to {sorted(manifest.allowed_domains)}, caller "
                f"domain {caller_domain!r} is not a member"
            ),
        )

    missing = sorted(set(manifest.required_inputs) - set(arguments))
    if missing:
        return DispatchResult(
            outcome="rejected_invalid_arguments", error=f"missing required arguments: {missing}"
        )

    executor = registry.get_executor(capability_id)
    if executor is None:  # unreachable in practice -- registry always pairs manifest+executor
        return DispatchResult(
            outcome="execution_error",
            error=f"internal: {capability_id!r} has a manifest but no registered executor",
        )

    try:
        result = executor(**arguments, **(extra_kwargs or {}))
    except Exception as e:  # noqa: BLE001 -- any wrapped-function failure becomes a typed outcome
        return DispatchResult(outcome="execution_error", error=f"{type(e).__name__}: {e}")

    return DispatchResult(outcome="executed", result=result)
