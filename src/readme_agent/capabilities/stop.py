"""TC-17 (decision #46, `AGT-006`): a real, registered, schema-validated
capability the planner may call to signal "no further capability would
usefully progress this run" -- distinct from the planner's ordinary stop
signal (an explicit turn with no tool call at all, `convergence.py`'s own
module docstring). Before this capability existed, a planner that tried to
call something named "stop" (a plausible model habit for a tool-calling
agent, and the exact hallucination `AGT-006` already logged) fell through to
`dispatcher.py`'s ordinary `rejected_unknown_capability` path -- identical,
in telemetry, to any other hallucinated/misspelled capability name. That
made "the model tried to stop but named it wrong" and "the model
hallucinated something unrelated" indistinguishable after the fact.

Registering this doesn't stop the hallucination -- a model can still emit no
tool call, or `stop`, or neither correctly. It makes the first two
observable and separable in evidence/telemetry, which is a prerequisite for
ever measuring how often each happens (Phase 13 §13.4 Pillar A.1) and for
`supervisor/loop.py`'s own code-computed termination backstop (Pillar A.2)
to have a clean signal to build on.

Deliberately NOT dispatched through the ordinary `dispatch_tool_call()`/
`dispatch_gated_effect()` path -- `supervisor/loop.py`'s planner-turn
handling recognizes `capability_id == STOP_CAPABILITY_ID` and treats it
exactly like the planner's own no-tool-call stop (same `final_status()`
call), before any dispatch machinery ever sees it. `execute()` below exists
only so this capability is a real, callable, testable member of the
registry (and so a direct `dispatch_tool_call()` call -- e.g. from a test,
or a future caller that doesn't special-case it -- gets a sane, honest
result rather than an accidental crash), not because the normal planner
loop is expected to reach it.
"""

from readme_agent.capabilities.schema import CapabilityManifest

CAPABILITY_ID = "stop"

MANIFEST = CapabilityManifest(
    capability_id=CAPABILITY_ID,
    version="1",
    name="Stop",
    purpose="Signal that no further capability would usefully progress this run -- call this "
    "instead of guessing at an unrelated capability name when you have nothing productive "
    "left to investigate. Equivalent to ending your turn with no tool call at all.",
    category="control",
    owner="readme_agent.supervisor.loop",
    execution_type="deterministic_tool",
    optional_inputs={"reason": "string"},
    produced_outputs={"stopped": "boolean", "reason": "string"},
    required_permissions=["read_only_local"],
    side_effect_class="read_only_local",
    allowed_domains=[],  # unscoped -- general-planner-visible
    tools_used=[],
    failure_modes=[],
    rollback_behavior="not applicable -- no side effect, nothing to roll back",
    tests=["tests/unit/test_capabilities.py"],
    requirement_ids=["AGT-006"],
)


def execute(reason: str = "") -> dict:
    return {"stopped": True, "reason": reason}
