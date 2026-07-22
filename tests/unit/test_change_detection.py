"""Offline tests for `state/change_detection.py::classify_surface()` --
Wave 7's shared "did this specialist's tracked surface change" primitive,
extracted from `readme/reconciliation.py::classify()`'s general shape so
every new specialist's classify-first check reuses one tested
implementation instead of six independent reimplementations. Covers the
same edge cases decision #38 already found the hard way for the README-
specific version (fresh-runner/first-observation handling), proven once
here, generically, rather than per specialist.

`readme/reconciliation.py`'s own test suite (test_reconciliation.py)
continues to prove the README-specific translation layer on top of this;
it is unchanged and still passes unmodified, proving this extraction was
zero-behavior-change."""

from readme_agent.state.change_detection import classify_surface

FP_A = "fingerprint-a"
FP_B = "fingerprint-b"


class TestFirstObservation:
    def test_no_prior_fingerprint_is_first_observation(self):
        result = classify_surface(current_fingerprint=FP_A, prior_fingerprint=None)
        assert result.classification == "FIRST_OBSERVATION"
        assert result.current_fingerprint == FP_A
        assert "no prior accepted state" in result.notes[0]

    def test_first_observation_regardless_of_marker_presence(self):
        """The fresh-runner case decision #38 found the hard way for the
        README-specific version: absence of prior state must always mean
        FIRST_OBSERVATION, never something that looks like a real change or
        a lost marker -- there is nothing to have lost yet."""
        result = classify_surface(
            current_fingerprint=FP_A,
            prior_fingerprint=None,
            prior_marker_present=True,
            marker_present_now=False,
        )
        assert result.classification == "FIRST_OBSERVATION"


class TestNoChange:
    def test_identical_fingerprint_and_marker_still_present_is_no_change(self):
        result = classify_surface(current_fingerprint=FP_A, prior_fingerprint=FP_A)
        assert result.classification == "NO_CHANGE"

    def test_no_marker_concept_at_all_still_reports_no_change(self):
        """A specialist with no owned-marker concept passes True/True
        (the defaults) -- marker_lost can never be true, degrading cleanly
        to a plain fingerprint comparison."""
        result = classify_surface(current_fingerprint=FP_A, prior_fingerprint=FP_A)
        assert result.marker_present_now is True
        assert result.classification == "NO_CHANGE"


class TestChanged:
    def test_different_fingerprint_with_marker_still_present_is_changed(self):
        result = classify_surface(
            current_fingerprint=FP_B,
            prior_fingerprint=FP_A,
            prior_marker_present=True,
            marker_present_now=True,
        )
        assert result.classification == "CHANGED"


class TestMarkerLost:
    def test_same_fingerprint_but_marker_disappeared_is_marker_lost_not_no_change(self):
        """The exact bug class decision #38 found once already, generalized:
        a naive fingerprint-only comparison can't distinguish "marker
        removed" from "nothing changed" when removal happens to reproduce a
        fingerprint the pre-marker content already had -- this must never
        silently misclassify as NO_CHANGE."""
        result = classify_surface(
            current_fingerprint=FP_A,
            prior_fingerprint=FP_A,
            prior_marker_present=True,
            marker_present_now=False,
        )
        assert result.classification == "MARKER_LOST"

    def test_marker_lost_only_fires_when_prior_marker_was_actually_present(self):
        result = classify_surface(
            current_fingerprint=FP_A,
            prior_fingerprint=FP_A,
            prior_marker_present=False,
            marker_present_now=False,
        )
        assert result.classification == "NO_CHANGE"


class TestMixedChange:
    def test_different_fingerprint_and_marker_lost_is_mixed_change(self):
        result = classify_surface(
            current_fingerprint=FP_B,
            prior_fingerprint=FP_A,
            prior_marker_present=True,
            marker_present_now=False,
        )
        assert result.classification == "MIXED_CHANGE"
