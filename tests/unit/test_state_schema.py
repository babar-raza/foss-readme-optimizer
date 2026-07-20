"""Offline validation tests for `state/schema.py` (Wave 4, `MEM-001`;
`domain_states` is `MEM-004`, Decision #34). No git, no network -- pure
pydantic validation."""

import json

import pytest
from pydantic import ValidationError

from readme_agent.state.schema import CapabilityOutputCacheEntry, DomainStateV1, RunStateV1


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
