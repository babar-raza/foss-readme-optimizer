"""Per-domain evidence-completeness gate (Wave 8) -- the concrete meaning
this project gives "evidence completeness gates" from the Build Checklist's
one-line Wave 8 description: a domain reporting a non-`ERROR` status without
its own documented detail keys present is flagged, not silently trusted.

Data, not a special-cased `if`-chain: `_EXPECTED_DETAIL_KEYS` is sourced
directly from each domain-producing capability's own declared
`produced_outputs` (the authoritative, typed output contract already in
`CapabilityManifest`) -- not hand-guessed. `readme_reconciliation` and
`cross_surface_validation` have no capability of their own (the former reads
`classify_upstream_change`'s ad hoc `license_claim` fact, the latter reads
sibling state directly), so their entries are the one or two `details` keys
their own specialist module unconditionally sets, confirmed by direct read.
"""

from readme_agent.capabilities import domains

_EXPECTED_DETAIL_KEYS: dict[str, frozenset[str]] = {
    domains.README_RECONCILIATION: frozenset({"license_claim"}),
    domains.GITHUB_GENERATED_SURFACE_AUDIT: frozenset(
        {
            "contributors_count",
            "primary_language",
            "languages",
            "stargazers_count",
            "forks_count",
            "watchers_count",
            "open_issues_count",
        }
    ),
    domains.PACKAGE_RELEASE_AUDIT: frozenset(
        {"releases_count", "latest_release_tag", "latest_release_name", "handoff_findings"}
    ),
    domains.METADATA_PRESENTATION: frozenset(
        {
            "current_description",
            "current_homepage",
            "current_topics",
            "proposed_description",
            "proposed_homepage",
            "proposed_topics",
            "has_proposal",
        }
    ),
    domains.COMMUNITY_FILES_PRESENTATION: frozenset(
        {
            "present_files",
            "recognized_files",
            "community_profile_health_percentage",
            "presence_recognition_gaps",
            "missing_files",
            "prepared_candidates",
            "detected_license",
        }
    ),
    domains.CROSS_SURFACE_VALIDATION: frozenset({"inconsistencies", "stale_sibling_data"}),
    domains.README_PRESENTATION: frozenset(
        {"render_status", "llm_called", "llm_calls", "fresh_fingerprint", "written", "committed"}
    ),
    domains.VISUAL_PREPARATION: frozenset(
        {
            "existing_asset_found",
            "width",
            "height",
            "format",
            "size_bytes",
            "size_within_reasonable_bounds",
            "concerns",
            "alt_text",
            "license_status",
        }
    ),
    # Wave 8.6: sourced from compare_against_presentation_standard's own
    # declared produced_outputs.
    domains.PRESENTATION_BENCHMARKING: frozenset({"criteria_results", "overall_summary"}),
}


def check_evidence_complete(domain: str, accepted_status: str | None, details: dict) -> list[str]:
    """Returns the list of expected detail keys missing from `details` -- an
    empty list means complete. A domain with no entry in the table (a future
    domain this file hasn't been updated for yet) is never silently trusted
    as complete -- returns its full expected set as "missing" would be wrong
    too (it has none registered), so it correctly reports nothing missing
    only because nothing is expected of an unregistered domain; the
    `specialists/registry.py::_build()` completeness gate is what actually
    guarantees every real domain has a registered specialist, this function
    only ever runs against already-known domains in practice.

    An `ERROR:`-prefixed (or `None`) `accepted_status` is exempt -- a
    domain that failed isn't expected to have produced complete findings,
    and flagging it here would just duplicate the failure signal
    `consecutive_failure_count`/`last_failure_reason` already carries."""
    if accepted_status is None or accepted_status.startswith("ERROR:"):
        return []
    expected = _EXPECTED_DETAIL_KEYS.get(domain, frozenset())
    return sorted(expected - set(details))
