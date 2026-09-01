"""Vendored aspose.org format-name-casing check: "ONE" must not self-trigger a
casing-inconsistency finding purely from coinciding with the ordinary English
number word "one"."""

from __future__ import annotations

import sys

sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline")
sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline/lib")
sys.path.insert(0, "src/readme_agent/vendored_asposeorg/scripts/pipeline/commands/foss")
import readme_refresh_checks as vendored  # noqa: E402


def test_one_the_english_word_is_not_flagged_as_inconsistent_casing() -> None:
    """PWD-045: `aspose-email-foss/Aspose.Email-FOSS-for-Python`'s real candidate --
    an email library with no OneNote relevance -- reads "...supports one of the
    following..." (lowercase prose) somewhere, and "ONE" all-caps somewhere else
    (e.g. emphasis or a heading), purely coincidentally. "ONE" is a real registry
    format token (OneNote) but is overwhelmingly the ordinary English word here."""

    text = (
        "# Aspose.Email FOSS for Python\n\n"
        "## Quick Start\n\n"
        "Configure ONE of the following transports before sending mail.\n\n"
        "This library supports one delivery mechanism per message.\n"
    )

    findings = vendored.check_format_name_casing(text, None)

    assert not any(f.get("format") == "ONE" for f in findings)


def test_genuine_format_casing_inconsistency_is_still_caught() -> None:
    """Negative control: a real casing inconsistency for an unrelated format word
    must still be caught -- the fix only stoplists "ONE", it does not weaken the
    check generally."""

    text = (
        "# Product\n\n"
        "## Key Capabilities\n\n"
        "Reads XLSX workbooks. Writes Xlsx files. Supports xlsx round-tripping.\n"
    )

    findings = vendored.check_format_name_casing(text, None)

    assert any(f.get("format") == "XLSX" for f in findings)


def test_pre_fix_one_reproduces_the_real_bug_shape(monkeypatch) -> None:
    """Negative control for the stoplist fix itself: with "ONE" removed from the
    stoplist (restoring the pre-fix set), the exact real-bug-shaped text above
    reproduces the false positive."""

    pre_fix_stoplist = vendored._GENERIC_ACRONYM_STOPLIST - {"ONE"}
    monkeypatch.setattr(vendored, "_GENERIC_ACRONYM_STOPLIST", pre_fix_stoplist)

    text = (
        "# Aspose.Email FOSS for Python\n\n"
        "## Quick Start\n\n"
        "Configure ONE of the following transports before sending mail.\n\n"
        "This library supports one delivery mechanism per message.\n"
    )

    findings = vendored.check_format_name_casing(text, None)

    assert any(f.get("format") == "ONE" for f in findings)
