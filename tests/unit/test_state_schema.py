"""Offline validation tests for `state/schema.py` (Wave 4, `MEM-001`;
`domain_states` is `MEM-004`, Decision #34). No git, no network -- pure
pydantic validation."""

import json

import pytest
from pydantic import ValidationError

from readme_agent.state.schema import (
    CapabilityOutputCacheEntry,
    DomainStateV1,
    HandoffFindingV1,
    OpenProposalV1,
    RunStateV1,
)


class TestOpenProposalV1:
    """`PRL-002` (decision #46): the state shape a future `remote_write`
    PR-opener capability (`TC-08`, not yet built) will target -- exists
    ahead of that capability so its design has a real schema, not a
    retrofit. See the model's own docstring for why neither `pending` nor
    `applied` on `CapabilityOutputCacheEntry` can represent "open PR."""

    def test_defaults_to_open_state(self):
        proposal = OpenProposalV1(domain="readme_presentation")
        assert proposal.state == "open"
        assert proposal.pr_number is None

    def test_round_trips_through_json(self):
        proposal = OpenProposalV1(
            domain="readme_presentation",
            pr_number=47,
            pr_url="https://github.com/acme/widget/pull/47",
            branch_name="readme-agent/presentation-acme-widget",
            state="open",
            facts_hash="abc123",
            opened_at="2026-07-22T00:00:00+00:00",
        )
        reloaded = OpenProposalV1.model_validate_json(proposal.model_dump_json())
        assert reloaded == proposal

    def test_rejects_an_invalid_state(self):
        with pytest.raises(ValidationError):
            OpenProposalV1(domain="readme_presentation", state="not_a_real_state")

    def test_run_state_v1_open_proposals_defaults_empty_and_deserializes_old_records(self):
        """A `RunStateV1` written before this field existed must deserialize
        cleanly as "no open proposals recorded" -- the same additive-field
        contract every other field added to this model after Wave 4 already
        relies on."""
        old_record_json = json.dumps({"org_repo": "acme/widget", "state_version": 3})
        state = RunStateV1.model_validate_json(old_record_json)
        assert state.open_proposals == {}

    def test_run_state_v1_carries_open_proposals_keyed_by_domain(self):
        state = RunStateV1(
            org_repo="acme/widget",
            open_proposals={
                "readme_presentation": OpenProposalV1(domain="readme_presentation", pr_number=1)
            },
        )
        assert state.open_proposals["readme_presentation"].pr_number == 1


class TestHandoffFindingV1:
    """Wave 7c: the minimal, one-way handoff record for a product-agent-owned
    surface -- deliberately NOT a bidirectional ack/reject/rerun state
    machine (decision #37 already reversed that framing for the same reason:
    no real receiving system exists)."""

    def test_minimal_finding_is_valid(self):
        finding = HandoffFindingV1(surface="packages", anomaly="install path did not resolve")
        assert finding.surface == "packages"
        assert finding.evidence == {}
        assert finding.detected_at  # default_factory populated it

    def test_has_no_ack_reject_rerun_fields(self):
        """The deliberate design constraint, checked mechanically: this
        model must never grow the bidirectional state-machine fields the
        rejected surface-model-doc framing described."""
        field_names = set(HandoffFindingV1.model_fields)
        assert field_names == {"surface", "anomaly", "evidence", "detected_at"}
        assert "ack" not in field_names
        assert "status" not in field_names

    def test_round_trips_through_json(self):
        finding = HandoffFindingV1(
            surface="packages",
            anomaly="install path did not resolve",
            evidence={"registry": "maven_central"},
        )
        restored = HandoffFindingV1.model_validate_json(finding.model_dump_json())
        assert restored == finding


class TestCapabilityOutputCacheEntry:
    def test_minimal_entry_is_valid(self):
        entry = CapabilityOutputCacheEntry(
            capability_id="profile_repository",
            fingerprint="abc123",
            result={"detected_ecosystems": []},
        )
        assert entry.capability_id == "profile_repository"
        assert entry.cached_at  # default_factory populated it

    def test_missing_required_field_rejected(self):
        with pytest.raises(ValidationError):
            CapabilityOutputCacheEntry(capability_id="x", result={})  # no fingerprint


class TestRunStateV1:
    def test_minimal_state_defaults(self):
        state = RunStateV1(org_repo="aspose-pdf-foss/Aspose.PDF-FOSS-for-Java")
        assert state.state_version == 0
        assert state.accepted_facts_hash is None
        assert state.accepted_status is None
        assert state.capability_outputs == []
        assert state.domain_states == {}

    def test_full_state_round_trips_through_json(self):
        state = RunStateV1(
            org_repo="aspose-pdf-foss/Aspose.PDF-FOSS-for-Java",
            state_version=3,
            accepted_facts_hash="deadbeef",
            accepted_status="GENERATED",
            upstream_revision_at_accept="0123456789abcdef",
            upstream_content_fingerprint_at_accept="cafef00d",
            last_run_id="20260719-000000-aaaa",
            last_run_timestamp="2026-07-19T00:00:00+00:00",
            capability_outputs=[
                CapabilityOutputCacheEntry(
                    capability_id="profile_repository",
                    fingerprint="abc123",
                    result={"ok": True},
                )
            ],
        )
        restored = RunStateV1.model_validate_json(state.model_dump_json())
        assert restored == state

    def test_missing_org_repo_rejected(self):
        with pytest.raises(ValidationError):
            RunStateV1()

    def test_missing_content_fingerprint_key_on_old_blob_defaults_to_none(self):
        """Decision #38: a durable record written before this field existed
        must round-trip cleanly, with the field defaulting to `None` rather
        than requiring a migration -- this is exactly what makes the very
        next `generate_repo()` call for that repo correctly re-validate once
        (fingerprint mismatch against `None`) instead of crashing."""
        old_blob_json = json.dumps(
            {
                "org_repo": "acme/widget",
                "state_version": 5,
                "accepted_facts_hash": "deadbeef",
                "accepted_status": "GENERATED",
            }
        )
        restored = RunStateV1.model_validate_json(old_blob_json)
        assert restored.upstream_content_fingerprint_at_accept is None


class TestDomainStateV1:
    def test_minimal_domain_state_defaults(self):
        ds = DomainStateV1(domain="readme")
        assert ds.accepted_facts_hash is None
        assert ds.accepted_status is None
        assert ds.owned_span_present_at_accept is False

    def test_owned_span_present_at_accept_round_trips(self):
        """Decision #39: needed because `remove_span` is a no-op once a span
        is already absent -- without this field, a real OWNED_SPAN_LOST could
        silently misclassify as NO_CHANGE (see test_reconciliation.py)."""
        ds = DomainStateV1(domain="readme_reconciliation", owned_span_present_at_accept=True)
        restored = DomainStateV1.model_validate_json(ds.model_dump_json())
        assert restored == ds

    def test_missing_owned_span_present_key_on_old_blob_defaults_to_false(self):
        old_blob_json = '{"domain": "readme_reconciliation", "accepted_status": "NO_CHANGE"}'
        restored = DomainStateV1.model_validate_json(old_blob_json)
        assert restored.owned_span_present_at_accept is False

    def test_details_defaults_empty_and_round_trips(self):
        """Wave 7: the generic structured-payload escape hatch every new
        specialist uses instead of inventing its own incompatible workaround
        (matches CapabilityOutputCacheEntry.result/SupervisorStateV1.
        task_graph_snapshot's existing plain-dict convention)."""
        assert DomainStateV1(domain="metadata_presentation").details == {}

        ds = DomainStateV1(
            domain="metadata_presentation",
            accepted_status="PROPOSED",
            details={"proposed_topics": ["pdf", "java"], "current_description": "A PDF library"},
        )
        restored = DomainStateV1.model_validate_json(ds.model_dump_json())
        assert restored == ds
        assert restored.details["proposed_topics"] == ["pdf", "java"]

    def test_missing_details_key_on_old_blob_defaults_to_empty_dict(self):
        old_blob_json = '{"domain": "readme_reconciliation", "accepted_status": "NO_CHANGE"}'
        restored = DomainStateV1.model_validate_json(old_blob_json)
        assert restored.details == {}


class TestRunStateV1DomainStates:
    """MEM-004/Decision #34 -- per-domain accepted state, additive alongside
    RunStateV1's existing flat fields (not deprecated -- see schema.py)."""

    def test_domain_states_round_trips_through_json(self):
        state = RunStateV1(
            org_repo="acme/widget",
            domain_states={
                "readme": DomainStateV1(domain="readme", accepted_status="GENERATED"),
                "metadata": DomainStateV1(domain="metadata", accepted_status="COMPLIANT_NO_CHANGE"),
            },
        )
        restored = RunStateV1.model_validate_json(state.model_dump_json())
        assert restored == state

    def test_missing_domain_states_key_on_old_blob_defaults_cleanly(self):
        """Simulates an already-pushed pre-change blob (Wave 4's live-proof
        data) that predates this field entirely -- must round-trip without
        a migration step."""
        old_blob_json = json.dumps(
            {
                "org_repo": "acme/widget",
                "state_version": 3,
                "accepted_facts_hash": "deadbeef",
                "accepted_status": "GENERATED",
            }
        )
        restored = RunStateV1.model_validate_json(old_blob_json)
        assert restored.domain_states == {}
        assert restored.accepted_facts_hash == "deadbeef"
