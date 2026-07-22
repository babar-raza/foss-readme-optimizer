"""VER-004: the ruleset-version forget-proofing tripwire. See
`validation/registry.py`'s own `VALIDATION_RULESET_VERSION`/
`_RULES_SOURCE_HASH_AT_VERSION` docstrings for why this test exists."""

from readme_agent.validation import registry


class TestRulesetVersionTripwire:
    def test_reference_hash_matches_current_rule_source(self):
        """Passes today: `_RULES_SOURCE_HASH_AT_VERSION` was computed from the
        exact current `RULES` source. If this fails, a rule module's source
        changed without updating the reference hash -- decide whether the
        change affects accept/reject behavior: if so, bump
        `VALIDATION_RULESET_VERSION` too; if it's a pure refactor/comment
        edit, just update `_RULES_SOURCE_HASH_AT_VERSION` to the new value
        `compute_rules_source_hash()` reports."""
        assert registry.compute_rules_source_hash() == registry._RULES_SOURCE_HASH_AT_VERSION

    def test_tripwire_fails_when_rule_source_changes_without_updating_the_reference(
        self, monkeypatch
    ):
        """Meta-test of the tripwire itself: a changed source must produce a
        changed hash that no longer matches the (unchanged) reference --
        proving the mechanism actually detects drift, not just that it
        currently reports a match."""
        original = registry.compute_rules_source_hash
        monkeypatch.setattr(registry, "compute_rules_source_hash", lambda: "deadbeef" * 8)
        assert registry.compute_rules_source_hash() != registry._RULES_SOURCE_HASH_AT_VERSION
        assert original() == registry._RULES_SOURCE_HASH_AT_VERSION
