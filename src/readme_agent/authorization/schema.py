"""Wave 13.2 (`AUTH-001`-`003`): the effect-class taxonomy and
authorization-record schema the Execution Readiness plan names as the
replacement for a synchronous, per-instance human confirmation (`GOV-018`/
`GOV-023`, evolved for real in Wave 13.7) -- a human grants/renews a
bounded, reviewable `AuthorizationRecordV1` asynchronously (a reviewable
config change, not a runtime prompt); every action within its bounds
proceeds autonomously, evidenced in `RunManifestV2` (Wave 13.1); anything
outside it produces a `CapabilityGap`, never invented authority.

`EffectClass` is additive alongside, not a replacement for,
`capabilities/schema.py::PermissionClass` (the existing 4-value
`read_only_local`/`read_only_network`/`local_write`/`remote_write` enum
that already gates every dispatch). `side_effect_class` keeps deciding
*whether* a dispatch is mutating at all; `EffectClass` decides *which*
authorization record a mutating dispatch must additionally satisfy. Do not
remove or repurpose the existing field."""

from typing import Literal

from pydantic import BaseModel, Field

from readme_agent.capabilities.schema import OrgRepoRef

EffectClass = Literal[
    "STATE_REF_WRITE",
    "EVIDENCE_WRITE",
    "PR_BRANCH_PUSH",
    "PR_CREATE_OR_UPDATE",
    "DEFAULT_BRANCH_WRITE",
    "REPOSITORY_SETTINGS_WRITE",
    "PACKAGE_PUBLICATION",
    "MANUAL_UI_PREPARATION",
]


class AuthorizationRecordV1(BaseModel):
    """A human-authored, human-reviewed grant of bounded autonomous write
    authority for one repository. `authorization/registry.py::
    authorized_for()` is the only intended reader -- a capability never
    constructs or infers one for itself (`AUTH-004`)."""

    repository: OrgRepoRef
    effect_classes: list[EffectClass]
    branch_pattern: str
    allowed_surfaces: list[str] = Field(default_factory=list)
    # ISO 8601 timestamp; `None` means no expiration -- discouraged (a
    # human-authored record SHOULD set one) but not itself forbidden here;
    # `authorized_for()` is where an expiry is actually enforced.
    expiration: str | None = None
    # Upper bound on a proposal's own change size (e.g. lines changed);
    # `None` means no limit declared, not "unlimited by design" -- a
    # capability that cares about this SHOULD treat `None` as "ask a human."
    max_change_size: int | None = None
    required_validators: list[str] = Field(default_factory=list)
    required_verifier: str | None = None
    approving_identity: str
    rollback: str
