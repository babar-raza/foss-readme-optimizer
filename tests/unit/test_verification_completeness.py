"""Wave 8: `verification/completeness.py::check_evidence_complete()` -- the
concrete meaning of "evidence completeness gates" from Wave 8's Build
Checklist line: a domain reporting a non-`ERROR` status without its own
documented detail keys present is flagged, not silently trusted."""

from readme_agent.capabilities import domains
from readme_agent.verification.completeness import check_evidence_complete


class TestCheckEvidenceComplete:
    def test_error_prefixed_status_is_exempt(self):
        missing = check_evidence_complete(
            domains.README_RECONCILIATION, "ERROR:execution_error:boom", {}
        )
        assert missing == []

    def test_none_status_is_exempt(self):
        missing = check_evidence_complete(domains.README_RECONCILIATION, None, {})
        assert missing == []

    def test_complete_details_reports_nothing_missing(self):
        missing = check_evidence_complete(
            domains.README_RECONCILIATION, "NO_CHANGE", {"license_claim": "MIT"}
        )
        assert missing == []

    def test_missing_expected_key_is_reported(self):
        missing = check_evidence_complete(domains.README_RECONCILIATION, "NO_CHANGE", {})
        assert missing == ["license_claim"]

    def test_single_expected_key_domain_reports_it_when_missing(self):
        missing = check_evidence_complete(
            domains.CROSS_SURFACE_VALIDATION, "NO_CHANGE", {"stale_sibling_data": {}}
        )
        assert missing == ["inconsistencies"]

    def test_cross_surface_validation_reports_both_expected_keys_when_missing(self):
        missing = check_evidence_complete(domains.CROSS_SURFACE_VALIDATION, "NO_CHANGE", {})
        assert missing == ["inconsistencies", "stale_sibling_data"]

    def test_a_domain_with_several_expected_keys_reports_all_missing_ones_sorted(self):
        missing = check_evidence_complete(
            domains.README_PRESENTATION, "NO_CHANGE", {"written": True}
        )
        assert missing == sorted(
            {"render_status", "llm_called", "llm_calls", "fresh_fingerprint", "committed"}
        )

    def test_an_unregistered_domain_reports_nothing_missing(self):
        missing = check_evidence_complete("some_future_domain", "NO_CHANGE", {})
        assert missing == []
