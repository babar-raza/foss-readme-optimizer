"""Independent acceptance-axis and portfolio publication controls."""

import pytest

from readme_agent.errors import StateBackendError
from readme_agent.state.backend import SaveResult
from readme_agent.state.lifecycle_schema import ReadmePocLifecycleStateV2
from readme_agent.state.migrations import ensure_run_state_v2
from readme_agent.state.readme_poc_acceptance import (
    record_factual_validity,
    record_presentation_validity,
)
from readme_agent.state.readme_poc_publication import (
    record_human_acceptance,
    record_publication_eligibility,
)
from readme_agent.state.schema import RunStateV2


class _Backend:
    def __init__(self) -> None:
        self.states: dict[str, RunStateV2] = {}

    def load(self, org_repo: str) -> RunStateV2 | None:
        return self.states.get(org_repo)

    def save(self, org_repo: str, state, expected_version: int | None) -> SaveResult:
        current = self.states.get(org_repo)
        current_version = current.state_version if current else None
        if current_version != expected_version:
            return SaveResult("stale", current_version)
        version = (current_version or 0) + 1
        self.states[org_repo] = ensure_run_state_v2(state).model_copy(
            update={"org_repo": org_repo, "state_version": version}
        )
        return SaveResult("saved", version)


class TestIndependentAcceptanceAxes:
    @staticmethod
    def _seed(backend: _Backend, org_repo: str, suffix: str) -> None:
        backend.states[org_repo] = RunStateV2(
            org_repo=org_repo,
            state_version=0,
            readme_poc_lifecycle=ReadmePocLifecycleStateV2(
                status="NO_OP_PROVEN",
                source_revision=suffix * 40,
                facts_hash=suffix * 64,
                candidate_hash=("f" if suffix != "f" else "e") * 64,
                fact_acceptance_contract_hash="d" * 64,
            ),
        )

    @staticmethod
    def _validate_and_accept(
        backend: _Backend,
        org_repo: str,
        suffix: str,
        presentation_version: str,
    ) -> None:
        state = backend.load(org_repo)
        assert state is not None
        lifecycle = state.readme_poc_lifecycle
        assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
        record_factual_validity(
            backend,
            org_repo,
            status="VALID",
            source_revision=suffix * 40,
            facts_hash=suffix * 64,
            acceptance_contract_hash="d" * 64,
            evidence_identity=f"facts:{org_repo}",
            observed_by="fact-verifier",
            reason="repository facts accepted",
        )
        record_presentation_validity(
            backend,
            org_repo,
            status="VALID",
            source_revision=suffix * 40,
            candidate_hash=lifecycle.candidate_hash or "",
            presentation_version=presentation_version,
            component_manifest_hash="8" * 64,
            evidence_identity=f"presentation:{org_repo}",
            observed_by="independent-reviewer",
            reason="candidate accepted",
        )
        for boundary in ("calibration", "representative_cohort", "final_portfolio"):
            record_human_acceptance(
                backend,
                org_repo,
                source_revision=suffix * 40,
                presentation_version=presentation_version,
                boundary=boundary,
                decision="ACCEPTED",
                reviewer_identity="human-owner",
                evidence_identity=f"review:{org_repo}:{boundary}",
                reason=f"accepted at {boundary}",
            )

    def test_all_axes_persist_separately_and_portfolio_eligibility_is_dynamic(self):
        backend = _Backend()
        self._seed(backend, "org/first", "a")
        self._seed(backend, "org/second", "b")
        self._validate_and_accept(backend, "org/first", "a", "1" * 64)
        self._validate_and_accept(backend, "org/second", "b", "2" * 64)

        eligible = record_publication_eligibility(
            backend,
            "org/first",
            admitted_repositories=["org/second", "org/first"],
            registry_revision="registry-v1",
            evidence_identity="portfolio-review-v1",
            observed_by="gate-c-guard",
        )

        assert eligible.publication_eligibility.status == "ELIGIBLE"
        assert eligible.publication_eligibility.admitted_repositories == [
            "org/first",
            "org/second",
        ]
        assert eligible.factual_validity.status == "VALID"
        assert eligible.presentation_validity.status == "VALID"
        assert [item.boundary for item in eligible.human_acceptance_history] == [
            "calibration",
            "representative_cohort",
            "final_portfolio",
        ]

    def test_new_presentation_version_makes_prior_human_acceptance_stale(self):
        backend = _Backend()
        self._seed(backend, "org/repo", "a")
        self._validate_and_accept(backend, "org/repo", "a", "1" * 64)
        state = backend.load("org/repo")
        assert state is not None
        lifecycle = state.readme_poc_lifecycle
        assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
        record_presentation_validity(
            backend,
            "org/repo",
            status="VALID",
            source_revision="a" * 40,
            candidate_hash=lifecycle.candidate_hash or "",
            presentation_version="3" * 64,
            component_manifest_hash="9" * 64,
            evidence_identity="presentation:new",
            observed_by="independent-reviewer",
            reason="new presentation approved",
        )

        ineligible = record_publication_eligibility(
            backend,
            "org/repo",
            admitted_repositories=["org/repo"],
            registry_revision="registry-v2",
            evidence_identity="portfolio-review-v2",
            observed_by="gate-c-guard",
        )

        assert ineligible.publication_eligibility.status == "INELIGIBLE"
        assert ineligible.publication_eligibility.rejection_reasons == [
            "org/repo:final_human_acceptance_missing_or_stale",
            "portfolio:calibration_acceptance_missing_or_stale",
            "portfolio:representative_cohort_acceptance_missing_or_stale",
        ]
        assert len(ineligible.human_acceptance_history) == 3

    def test_agent_only_or_missing_repository_acceptance_fails_closed(self):
        backend = _Backend()
        self._seed(backend, "org/agent-only", "a")
        state = backend.load("org/agent-only")
        assert state is not None
        lifecycle = state.readme_poc_lifecycle
        assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
        record_factual_validity(
            backend,
            "org/agent-only",
            status="VALID",
            source_revision="a" * 40,
            facts_hash="a" * 64,
            acceptance_contract_hash="d" * 64,
            evidence_identity="facts:agent-only",
            observed_by="fact-verifier",
            reason="valid facts",
        )
        record_presentation_validity(
            backend,
            "org/agent-only",
            status="VALID",
            source_revision="a" * 40,
            candidate_hash=lifecycle.candidate_hash or "",
            presentation_version="1" * 64,
            component_manifest_hash="8" * 64,
            evidence_identity="agent-verdict",
            observed_by="independent-agent",
            reason="agent approved only",
        )

        ineligible = record_publication_eligibility(
            backend,
            "org/agent-only",
            admitted_repositories=["org/agent-only", "org/missing"],
            registry_revision="registry-v3",
            evidence_identity="portfolio-review-v3",
            observed_by="gate-c-guard",
        )

        assert ineligible.publication_eligibility.status == "INELIGIBLE"
        assert "org/agent-only:final_human_acceptance_missing_or_stale" in (
            ineligible.publication_eligibility.rejection_reasons
        )
        assert "org/missing:missing_current_lifecycle" in (
            ineligible.publication_eligibility.rejection_reasons
        )

    def test_final_acceptance_alone_cannot_skip_calibration_and_cohort_boundaries(self):
        backend = _Backend()
        self._seed(backend, "org/repo", "a")
        state = backend.load("org/repo")
        assert state is not None
        lifecycle = state.readme_poc_lifecycle
        assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
        record_factual_validity(
            backend,
            "org/repo",
            status="VALID",
            source_revision="a" * 40,
            facts_hash="a" * 64,
            acceptance_contract_hash="d" * 64,
            evidence_identity="facts",
            observed_by="fact-verifier",
            reason="valid",
        )
        record_presentation_validity(
            backend,
            "org/repo",
            status="VALID",
            source_revision="a" * 40,
            candidate_hash=lifecycle.candidate_hash or "",
            presentation_version="1" * 64,
            component_manifest_hash="8" * 64,
            evidence_identity="agent-review",
            observed_by="independent-agent",
            reason="agent approved",
        )
        record_human_acceptance(
            backend,
            "org/repo",
            source_revision="a" * 40,
            presentation_version="1" * 64,
            boundary="final_portfolio",
            decision="ACCEPTED",
            reviewer_identity="human-owner",
            evidence_identity="final-only",
            reason="final acceptance cannot collapse earlier boundaries",
        )

        ineligible = record_publication_eligibility(
            backend,
            "org/repo",
            admitted_repositories=["org/repo"],
            registry_revision="registry-v4",
            evidence_identity="portfolio-review-v4",
            observed_by="gate-c-guard",
        )

        assert ineligible.publication_eligibility.status == "INELIGIBLE"
        assert ineligible.publication_eligibility.rejection_reasons == [
            "portfolio:calibration_acceptance_missing_or_stale",
            "portfolio:representative_cohort_acceptance_missing_or_stale",
        ]

    def test_agent_approval_without_no_op_cannot_receive_human_acceptance(self):
        backend = _Backend()
        self._seed(backend, "org/repo", "a")
        state = backend.load("org/repo")
        assert state is not None
        lifecycle = state.readme_poc_lifecycle
        assert isinstance(lifecycle, ReadmePocLifecycleStateV2)
        backend.states["org/repo"] = state.model_copy(
            update={
                "readme_poc_lifecycle": lifecycle.model_copy(update={"status": "AGENT_APPROVED"})
            }
        )
        record_factual_validity(
            backend,
            "org/repo",
            status="VALID",
            source_revision="a" * 40,
            facts_hash="a" * 64,
            acceptance_contract_hash="d" * 64,
            evidence_identity="facts",
            observed_by="fact-verifier",
            reason="valid",
        )
        record_presentation_validity(
            backend,
            "org/repo",
            status="VALID",
            source_revision="a" * 40,
            candidate_hash=lifecycle.candidate_hash or "",
            presentation_version="1" * 64,
            component_manifest_hash="8" * 64,
            evidence_identity="agent-review",
            observed_by="independent-agent",
            reason="agent approved",
        )

        with pytest.raises(StateBackendError, match="completed independent local proof"):
            record_human_acceptance(
                backend,
                "org/repo",
                source_revision="a" * 40,
                presentation_version="1" * 64,
                boundary="final_portfolio",
                decision="ACCEPTED",
                reviewer_identity="human-owner",
                evidence_identity="premature-review",
                reason="must be rejected",
            )
