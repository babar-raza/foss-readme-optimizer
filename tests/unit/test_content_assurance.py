"""Assurance isolation across lifecycle, proposal, effect, and portfolio state."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from readme_agent.capabilities.effect_identity import build_effect_identity
from readme_agent.errors import StateBackendError
from readme_agent.registry.loader import load_products
from readme_agent.state.assurance import AssuranceBoundProposalIdentityV1
from readme_agent.state.backend import SaveResult
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.readme_poc_lifecycle import (
    switch_content_assurance,
    transition_readme_poc_status,
    transition_trusted_readme_poc_status,
)
from readme_agent.state.schema import OpenProposalV1, RunStateV2
from readme_agent.supervisor.mission_goal_guard import derive_lifecycle_scoreboard

_HASH = "a" * 64


class _MemoryBackend:
    def __init__(self) -> None:
        self.records: dict[str, RunStateV2] = {}

    def load(self, org_repo: str) -> RunStateV2 | None:
        record = self.records.get(org_repo)
        return deepcopy(record) if record is not None else None

    def save(
        self,
        org_repo: str,
        state: RunStateV2,
        expected_version: int | None,
    ) -> SaveResult:
        current = self.records.get(org_repo)
        current_version = current.state_version if current is not None else None
        if current_version != expected_version:
            return SaveResult("stale", current_version)
        saved = state.model_copy(
            update={"org_repo": org_repo, "state_version": (current_version or 0) + 1}
        )
        self.records[org_repo] = saved
        return SaveResult("saved", saved.state_version)


def test_assurance_switch_reopens_and_clears_only_derived_acceptance() -> None:
    backend = _MemoryBackend()
    org_repo = "org/repo"
    backend.records[org_repo] = RunStateV2(
        org_repo=org_repo,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            status="AGENT_APPROVED",
            source_revision="1" * 40,
            facts_hash=_HASH,
            assessment_hash="b" * 64,
            presentation_plan_hash="c" * 64,
            candidate_hash="d" * 64,
            prompt_hash="e" * 64,
        ),
    )

    switched = switch_content_assurance(
        backend,
        org_repo,
        "trusted_inherited",
        observed_by="test",
        reason="enter trusted POC",
    )

    assert switched.content_assurance == "trusted_inherited"
    assert switched.status == "PROFILED"
    assert switched.source_revision == "1" * 40
    assert switched.facts_hash is None
    assert switched.candidate_hash is None
    assert switched.assurance_history[-1].from_status == "AGENT_APPROVED"
    assert switched.assurance_history[-1].to_status == "PROFILED"


def test_trusted_lifecycle_cannot_enter_verified_approval() -> None:
    backend = _MemoryBackend()
    org_repo = "org/repo"
    backend.records[org_repo] = RunStateV2(
        org_repo=org_repo,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            content_assurance="trusted_inherited",
            status="PROFILED",
            source_revision="1" * 40,
        ),
    )

    with pytest.raises(StateBackendError, match="verified README lifecycle transition rejected"):
        transition_readme_poc_status(
            backend,
            org_repo,
            "AGENT_APPROVED",
            observed_by="test",
            reason="illegal promotion",
        )

    advanced = transition_trusted_readme_poc_status(
        backend,
        org_repo,
        "TRUSTED_FACTS_EXTRACTING",
        observed_by="test",
        reason="legal trusted progression",
    )
    assert advanced.status == "TRUSTED_FACTS_EXTRACTING"


def test_trusted_identity_cannot_claim_verified_proposal_kind() -> None:
    with pytest.raises(ValidationError, match="trusted_readme_transform"):
        AssuranceBoundProposalIdentityV1(
            content_assurance="trusted_inherited",
            org_repo="org/repo",
            source_revision="1" * 40,
            candidate_hash=_HASH,
            facts_hash=_HASH,
            proposal_kind="verified_repository_presentation",
        )
    with pytest.raises(ValidationError, match="trusted_readme_transform"):
        OpenProposalV1(
            domain="readme_presentation",
            content_assurance="trusted_inherited",
            proposal_kind="verified_repository_presentation",
        )


def test_effect_identity_is_assurance_sensitive() -> None:
    common = {
        "effect_type": "open_presentation_pr",
        "org_repo": "org/repo",
        "facts_hash": _HASH,
        "fresh_fingerprint": "f" * 64,
        "final_text": "# Product\n",
    }
    verified = build_effect_identity(**common, content_assurance="repository_verified")
    trusted = build_effect_identity(**common, content_assurance="trusted_inherited")

    assert verified.canonical_json() != trusted.canonical_json()


def test_trusted_portfolio_status_never_increments_verified_approval() -> None:
    backend = _MemoryBackend()
    entry = load_products()[0]
    org_repo = entry.org_repo
    backend.records[org_repo] = RunStateV2(
        org_repo=org_repo,
        readme_poc_lifecycle=ReadmePocLifecycleStateV2(
            content_assurance="trusted_inherited",
            status="TRUSTED_TRANSFORM_APPROVED",
            source_revision="1" * 40,
        ),
    )

    scoreboard = derive_lifecycle_scoreboard(backend)

    assert scoreboard.trusted_transform_approved == 1
    assert scoreboard.agent_approved == 0
    assert scoreboard.no_op_proven == 0
