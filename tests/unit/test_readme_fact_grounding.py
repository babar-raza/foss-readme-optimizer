"""Literal README fact-grounding controls."""

from readme_agent.readme.fact_grounding import find_literal_fact_match


def test_short_license_token_matches_only_as_a_complete_token():
    match = find_literal_fact_match(
        "[![License: MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE)",
        "MIT",
    )

    assert match is not None
    assert match.phrase == "MIT"


def test_short_fact_does_not_match_inside_an_unrelated_word():
    assert find_literal_fact_match("Commit changes after review.", "MIT") is None
