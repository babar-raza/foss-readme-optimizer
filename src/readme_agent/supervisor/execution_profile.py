"""Execution profiles (Wave 9.4, 2026-07-22 convergence-sprint plan) -- the explicit, typed
replacement for "which CLI flags happened to be passed" as the thing that decides what a
`supervise` invocation is allowed to do. Mirrors `capabilities/schema.py::CapabilityManifest`'s
style: a typed, registry-validated contract, not ad hoc argument-checking scattered across
`commands.py`.

Five profiles, matching local development vs. GitHub Actions production, and observe-only vs.
proposal-preparing vs. (future) fully-applying intent:

- `local_inspect` / `local_dry_run`: interactive/manual use, never fail-closed on durable-state
  trouble (a human is present to notice and retry).
- `github_observe` / `github_proposal` / `github_apply`: unattended GitHub Actions runs, always
  fail-closed on durable-state trouble (`RUN-005`) -- there is no human present mid-run to notice
  a silent degrade to ephemeral state.

`github_apply` is declared distinctly from `github_proposal` even though today's actual mutating
capabilities (`commit_readme_write`, `open_presentation_pr`) both stop at "prepare/open a PR" --
there is no capability yet that completes a further "apply" step (e.g. Wave 15's repository-
settings writes). The two profiles already differ in `allowed_permission_classes`/triggers so that
distinction is real, not cosmetic, the moment such a capability exists; they are not silently
merged into one profile now for convenience.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from readme_agent.capabilities.schema import PermissionClass

ExecutionProfileName = Literal[
    "local_inspect",
    "local_dry_run",
    "github_observe",
    "github_proposal",
    "github_apply",
]

Trigger = Literal["cli_manual", "workflow_dispatch", "schedule", "repository_dispatch"]


class ExecutionProfileV1(BaseModel):
    name: ExecutionProfileName
    requires_durable_state: bool
    fail_closed_on_state_failure: bool
    allowed_permission_classes: list[PermissionClass]
    require_evidence_bundle: bool
    require_independent_verification: bool
    allowed_triggers: list[Trigger]
    rollback: str
    allows_domain_bypass: bool
    """Whether `supervise --domain X` (a single-specialist run bypassing the planner loop and
    `supervise_repo()`'s own convergence/lock machinery) is permitted under this profile. Only
    the local, interactive profiles allow it -- a `github_*` profile must never let one CLI flag
    skip the lock/evidence/verification path a production run is supposed to always go through."""


_PROFILES: dict[ExecutionProfileName, ExecutionProfileV1] = {
    "local_inspect": ExecutionProfileV1(
        name="local_inspect",
        requires_durable_state=False,
        fail_closed_on_state_failure=False,
        allowed_permission_classes=["read_only_local", "read_only_network"],
        require_evidence_bundle=False,
        require_independent_verification=False,
        allowed_triggers=["cli_manual"],
        rollback="none needed -- read-only",
        allows_domain_bypass=True,
    ),
    "local_dry_run": ExecutionProfileV1(
        name="local_dry_run",
        requires_durable_state=False,
        fail_closed_on_state_failure=False,
        allowed_permission_classes=["read_only_local", "read_only_network", "local_write"],
        require_evidence_bundle=True,
        require_independent_verification=False,
        allowed_triggers=["cli_manual"],
        rollback="local work-clone commit only, never pushed (docs/safety-model.md)",
        allows_domain_bypass=True,
    ),
    "github_observe": ExecutionProfileV1(
        name="github_observe",
        requires_durable_state=True,
        fail_closed_on_state_failure=True,
        allowed_permission_classes=["read_only_local", "read_only_network"],
        require_evidence_bundle=True,
        require_independent_verification=False,
        allowed_triggers=["workflow_dispatch", "schedule"],
        rollback="none needed -- read-only",
        allows_domain_bypass=False,
    ),
    "github_proposal": ExecutionProfileV1(
        name="github_proposal",
        requires_durable_state=True,
        fail_closed_on_state_failure=True,
        allowed_permission_classes=[
            "read_only_local",
            "read_only_network",
            "local_write",
            "remote_write",
        ],
        require_evidence_bundle=True,
        require_independent_verification=True,
        allowed_triggers=["workflow_dispatch", "schedule"],
        rollback=(
            "revert/close the prepared branch or PR (open_presentation_pr); never a default-"
            "branch write"
        ),
        allows_domain_bypass=False,
    ),
    "github_apply": ExecutionProfileV1(
        name="github_apply",
        requires_durable_state=True,
        fail_closed_on_state_failure=True,
        allowed_permission_classes=[
            "read_only_local",
            "read_only_network",
            "local_write",
            "remote_write",
        ],
        require_evidence_bundle=True,
        require_independent_verification=True,
        allowed_triggers=["workflow_dispatch"],
        rollback=(
            "same as github_proposal today -- no capability yet completes a further apply step "
            "beyond preparing/opening a PR; kept as a distinct profile so one already exists once "
            "such a capability (e.g. Wave 15 settings writes) is built"
        ),
        allows_domain_bypass=False,
    ),
}


def get_profile(name: ExecutionProfileName) -> ExecutionProfileV1:
    return _PROFILES[name]


def is_github_profile(name: ExecutionProfileName) -> bool:
    return name.startswith("github_")
