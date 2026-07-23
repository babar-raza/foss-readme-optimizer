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

import re
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import AfterValidator, BaseModel, Field

# Wave 11.4 (`CAP-008`): the concrete "reject invalid repo refs" check --
# every capability's `org_repo` argument is a bare `str` today, with no
# structural validation beyond presence (`dispatcher.py`'s own missing-
# argument check). A malformed value (no slash, empty org/repo segment)
# previously sailed past that check and failed deep inside `require_listed()`/
# `clone_baseline()` as a generic exception, surfacing only as an opaque
# `execution_error`. `OrgRepoRef` is a real, reusable Pydantic-validated
# type any `input_model` below can use to fail fast, with a clear reason.
_ORG_REPO_PATTERN = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")


def _validate_org_repo_shape(value: str) -> str:
    if not _ORG_REPO_PATTERN.match(value):
        raise ValueError(f"org_repo must look like 'org/repo', got {value!r}")
    return value


OrgRepoRef = Annotated[str, AfterValidator(_validate_org_repo_shape)]


class OrgRepoOnlyInputV1(BaseModel):
    """The shared `input_model` for every read-only capability whose sole
    LLM-visible argument is `org_repo` (`get_product_facts`,
    `profile_repository`, `verify_package_acquisition`, ...) -- one
    canonical model instead of three near-identical one-field ones. A
    capability's own wiring-only kwargs (e.g. `prior_upstream_revision`)
    are deliberately absent here, matching their existing exclusion from
    `required_inputs`/`optional_inputs` -- this model describes exactly
    the dispatcher-validated, LLM-visible argument surface."""

    org_repo: OrgRepoRef


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
    "remote_write",  # writes remotely; explicitly gated (open_presentation_pr is the first)
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
    # Wave 8c (requirement mapping): which `plans/requirements.md` IDs this
    # capability's own output is evidence for -- a coarse, honest "was the
    # evidence-producing capability exercised and did it succeed," not a
    # semantic judgment of whether the prose acceptance text is satisfied
    # (that distinction stays a human `IMPLEMENTED` call). Empty here in
    # Wave 8a (schema-only, added early since it's a safe additive default,
    # matching the existing "declare the field before any capability uses
    # it" convention `execution_type="validator"` already established) --
    # populated per capability in Wave 8c. `tests/unit/test_capabilities.py`'s
    # own drift test asserts every declared ID here actually exists in
    # `plans/requirements.md` (`GOV-015`: reuses `plans/investigations/tools/
    # extract_requirements.py`'s own proven row-matching regex, not a second
    # hand-rolled parser).
    requirement_ids: list[str] = Field(default_factory=list)

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

    # Wave 11.4 (`CAP-008`): additive alongside the flat `required_inputs`/
    # `optional_inputs`/`produced_outputs` maps above -- a real Pydantic
    # model for a capability that wants structural (not just presence)
    # argument validation, without forcing a breaking rewrite of all
    # already-registered capabilities at once. `None` (the default for
    # every capability that predates this field) preserves the exact
    # existing flat-map-only behavior below and in `dispatcher.py` --
    # deliberately retrofitted onto only this session's own new/touched
    # capabilities first (`get_product_facts`, `profile_repository`,
    # `verify_package_acquisition`), not all 22+ at once.
    input_model: type[BaseModel] | None = None
    output_model: type[BaseModel] | None = None

    # Wave 13.3 (`AUTH-004`): additive, empty-by-default alongside
    # side_effect_class -- empty means "not yet authorization-scoped" (mirrors
    # allowed_domains' own "empty = unscoped" convention), never "this
    # capability needs no authorization by design". A non-empty list names
    # which `authorization.schema.EffectClass` values a real dispatch of this
    # capability must satisfy (all of them) via `authorization.registry.
    # authorized_for()`, checked by `effect_ledger.py::dispatch_gated_effect()`
    # before even a pending ledger entry is written. Kept as bare `str` here,
    # not the `EffectClass` Literal type, to avoid a schema.py <->
    # authorization/schema.py import cycle (authorization/schema.py already
    # imports `OrgRepoRef` from this module) -- membership is validated once,
    # at capability-registration time, by `registry.py`.
    effect_classes: list[str] = Field(default_factory=list)

    def to_tool_schema(self) -> dict:
        """OpenAI-style function tool schema. Prefers `input_model.
        model_json_schema()` when declared (a real nested-structure schema,
        not just a flat type-name map) -- falls back to the flat
        `required_inputs`/`optional_inputs` maps exactly as before for
        every capability that doesn't declare one (L6: native tool-calling,
        proven reliable against llm.professionalize.com in Wave 1).

        The generated schema's own top-level `description` (Pydantic's
        default: the model's docstring, an internal-implementation-detail
        explanation, not LLM-facing copy) is dropped -- `function.
        description` below, from this manifest's own `purpose` field, is
        already the single authoritative description; a second, redundant
        one nested inside `parameters` would only be noise."""
        if self.input_model is not None:
            parameters = self.input_model.model_json_schema()
            parameters.pop("description", None)
        else:
            properties = {
                name: {"type": type_name}
                for name, type_name in {**self.required_inputs, **self.optional_inputs}.items()
            }
            parameters = {
                "type": "object",
                "properties": properties,
                "required": sorted(self.required_inputs),
            }
        return {
            "type": "function",
            "function": {
                "name": self.capability_id,
                "description": self.purpose,
                "parameters": parameters,
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
