"""Offline tests for readme/reconciliation.py's drift classifier (Wave 6,
decisions #38/#39). No git, no network -- pure text/hash logic against the
real markers.py span model."""

from readme_agent.readme.facts import sha256_text
from readme_agent.readme.markers import upsert_span
from readme_agent.readme.reconciliation import classify

PLAIN_README = "# Widget\n\nWidget is a library for doing widget things.\n"
WITH_SPAN = upsert_span(PLAIN_README, "resources", "See https://products.example.org", "deadbeef")


class TestClassifyFirstObservation:
    def test_no_prior_state_is_first_observation(self):
        result = classify(
            current_readme_text=PLAIN_README,
            prior_stripped_text_hash=None,
            prior_owned_span_present=False,
        )
        assert result.classification == "FIRST_OBSERVATION"
        assert result.stripped_text_hash == sha256_text(PLAIN_README)
        assert result.owned_span_present_now is False


class TestClassifyNoChange:
    def test_identical_content_is_no_change(self):
        prior_hash = sha256_text(PLAIN_README)
        result = classify(
            current_readme_text=PLAIN_README,
            prior_stripped_text_hash=prior_hash,
            prior_owned_span_present=False,
        )
        assert result.classification == "NO_CHANGE"

    def test_owned_span_content_alone_does_not_count_as_change(self):
        """Stripping the owned span before hashing means editing only the
        content *inside* the span must not register as upstream drift --
        that's this tool's own render output, not something upstream did."""
        prior_hash = sha256_text(PLAIN_README)  # stripped hash computed pre-span
        result = classify(
            current_readme_text=WITH_SPAN,
            prior_stripped_text_hash=prior_hash,
            prior_owned_span_present=False,
        )
        assert result.classification == "NO_CHANGE"
        assert result.owned_span_present_now is True


class TestClassifyUpstreamChanged:
    def test_edited_prose_outside_span_is_upstream_changed(self):
        prior_hash = sha256_text(PLAIN_README)
        edited = PLAIN_README + "\nA new paragraph a maintainer added.\n"
        result = classify(
            current_readme_text=edited,
            prior_stripped_text_hash=prior_hash,
            prior_owned_span_present=False,
        )
        assert result.classification == "UPSTREAM_CHANGED"


class TestClassifyOwnedSpanLost:
    def test_span_removed_with_otherwise_unchanged_prose_is_span_lost(self):
        """The exact scenario decision #38 calls out: remove_span() is a
        no-op once the span is already absent, so a naive stripped-hash
        comparison alone would silently miss this -- owned_span_present_now
        vs. prior_owned_span_present is what actually catches it."""
        prior_hash = sha256_text(PLAIN_README)  # stripped hash, span was present before
        # Upstream deletes the span entirely -- what remains is just the plain prose.
        result = classify(
            current_readme_text=PLAIN_README,
            prior_stripped_text_hash=prior_hash,
            prior_owned_span_present=True,
        )
        assert result.classification == "OWNED_SPAN_LOST"
        assert result.owned_span_present_now is False


class TestClassifyMixedChange:
    def test_span_lost_and_prose_changed_is_mixed_change(self):
        prior_hash = sha256_text(PLAIN_README)
        edited = PLAIN_README + "\nSomething upstream also changed.\n"
        result = classify(
            current_readme_text=edited,
            prior_stripped_text_hash=prior_hash,
            prior_owned_span_present=True,
        )
        assert result.classification == "MIXED_CHANGE"
        assert result.owned_span_present_now is False
