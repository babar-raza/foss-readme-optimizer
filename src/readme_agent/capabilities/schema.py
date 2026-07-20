"""Typed capability contracts (sprint Task 3.1, `CAP-001`/`CAP-004`) and the
`CapabilityGap` record (`CAP-003`/`GAP-001`). Mirrors `registry/models.py`'s
pydantic style -- these are validated external contracts, not internal return
values (contrast `validation/result.py`'s plain-dataclass `RuleResult`).

Field-population policy: every field the sprint's Section 7 Task 3.1 lists
exists here now, so later waves never need a breaking schema change to add
real values to a field this project already declared. Fields with no
meaningful value yet stay `None`/empty and say which wave gives them one --
see the docstring "not yet meaningful" notes below. Nothing is faked to fill
a field early.
"""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ExecutionType = Literal[
    "deterministic_tool",
    "agentic_analysis",
    "agentic_planning",
    "specialist_workflow",
    "read_only_audit",
    "gated_effector",
    "validator",
    "manual_delivery_preparation",
]

# Minimal, explicit permission classes (GOVERNANCE.md "Capability and
# agentic-component lifecycle", rule 5: explicit and minimal -- nothing
# defaults to a broader class "in case it's needed later"). Reused for both
# `required_permissions` (what a capability needs) and `side_effect_class`
# (the single highest-impact one) rather than two near-duplicate enums.
PermissionClass = Literal[
    "read_only_local",  # reads an already-cloned baseline/work clone, no extra network
    "read_only_network",  # live read-only network call beyond the git clone itself
    "local_write",  # writes into the local work clone (never pushed -- safety-model.md)
    "remote_write",  # would write to a remote system -- explicitly gated, none yet
]

CapabilityStatus = Literal["active", "experimental", "deprecated"]


class CapabilityManifest(BaseModel):
    capability_id: str
    version: str
    name: str
    purpose: str
    category: str
    owner: str
    execution_type: ExecutionType
    status: CapabilityStatus = "active"

    # Input/output contract. Values are JSON-schema-ish type names ("string",
    # "boolean", "integer", ...) -- enough to build a tool-calling schema
    # (see to_tool_schema()) without a second, parallel schema language.
    required_inputs: dict[str, str] = Field(default_factory=dict)
    optional_inputs: dict[str, str] = Field(default_factory=dict)
    produced_outputs: dict[str, str] = Field(default_factory=dict)

    preconditions: list[str] = Field(default_factory=list)
    required_permissions: list[PermissionClass] = Field(default_factory=list)
    side_effect_class: PermissionClass = "read_only_local"

    # Caller-identity axis (`CAP-006`, Decision #33) -- orthogonal to
    # side_effect_class's blast-radius axis. Empty = unscoped, callable by
    # any caller (the unchanged meaning for every capability shipped through
    # Wave 4). Non-empty = only a caller whose declared domain
    # (`domains.py::KNOWN_DOMAINS`) is a member may invoke this capability,
    # checked independently by the dispatcher, regardless of what
    # side_effect_class/allowed_permissions would otherwise permit. Not a
    # closed enum, see `domains.py` -- registry.py validates membership at
    # build time.
    allowed_domains: list[str] = Field(default_factory=list)

    tools_used: list[str] = Field(default_factory=list)
    validators: list[str] = Field(default_factory=list)  # none exist yet
    failure_modes: list[str] = Field(default_factory=list)
    rollback_behavior: str | None = None
    tests: list[str] = Field(default_factory=list)

    # Not yet meaningful -- Wave 3's RepositoryProfile/archetype model gives
    # these real values; empty means "no restriction expressed yet", not
    # "compatible with everything".
    supported_archetypes: list[str] = Field(default_factory=list)
    supported_languages: list[str] = Field(default_factory=list)
    supported_build_systems: list[str] = Field(default_factory=list)
    supported_package_managers: list[str] = Field(default_factory=list)
    supported_registries: list[str] = Field(default_factory=list)

    # Not yet meaningful -- only relevant for LLM-backed capabilities, none
    # of which exist yet (all three Wave 2 capabilities are deterministic).
    model_route: str | None = None
    context_budget: int | None = None

    # Not yet meaningful -- Wave 5 owns cache/fingerprint reuse (decision
    # #26(d)) and evidence-writing integration; no retry policy is built
    # beyond whatever the wrapped function already does.
    cache_policy: str | None = None
    idempotency_inputs: list[str] = Field(default_factory=list)
    retry_policy: str | None = None
    evidence_outputs: list[str] = Field(default_factory=list)

    supersedes: str | None = None  # None until something is actually superseded

    def to_tool_schema(self) -> dict:
        """OpenAI-style function tool schema, built from required/optional
        inputs -- the single source of truth for both dispatch validation
        and what the model is offered (L6: native tool-calling, proven
        reliable against llm.professionalize.com in Wave 1)."""
        properties = {
            name: {"type": type_name}
            for name, type_name in {**self.required_inputs, **self.optional_inputs}.items()
        }
        return {
            "type": "function",
            "function": {
                "name": self.capability_id,
                "description": self.purpose,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": sorted(self.required_inputs),
                },
            },
        }


class CapabilityGap(BaseModel):
    """A capability need with no compatible match -- `CAP-003`/`GAP-001`:
    an explicit record, never a silent skip. `GAP-002`'s
    `PARTIAL_WITH_CAPABILITY_GAP` final-run-status is a separate, run-level
    concept this record does not itself define -- that belongs to whoever
    owns a "run" (Wave 5's supervisor)."""

    gap_id: str = Field(default_factory=lambda: uuid4().hex)
    requested_capability_id: str | None = None
    requested_need: str
    org_repo: str | None = None
    reason: str
    evidence: dict = Field(default_factory=dict)
    detected_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
