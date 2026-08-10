"""Prove routed verified source detail follows the public visibility contract."""

from readme_agent.presentation.verified_source_detail_presentation import (
    source_detail_presentation,
)


def test_visitor_critical_source_detail_remains_visible() -> None:
    for title in ("Key Capabilities", "Scope and Limitations", "Development and Testing"):
        presentation = source_detail_presentation(
            title,
            "View more",
            target_exists=True,
            section_text="Canonical public content.\n",
        )

        assert presentation.leading == ""
        assert presentation.trailing == ""
        assert not presentation.insert_before_existing_details_close


def test_secondary_source_detail_uses_one_collapsible_shell() -> None:
    presentation = source_detail_presentation(
        "Additional Examples",
        "View Additional Source Examples",
        target_exists=True,
        section_text="Canonical examples.\n",
    )

    assert presentation.leading == (
        "<details>\n<summary>View Additional Source Examples</summary>\n\n"
    )
    assert presentation.trailing == "</details>\n\n"
    assert not presentation.insert_before_existing_details_close


def test_secondary_source_detail_reuses_an_existing_details_shell() -> None:
    presentation = source_detail_presentation(
        "API Reference",
        "View Additional API Details",
        target_exists=True,
        section_text="<details>\n<summary>API</summary>\n\nExisting.\n</details>\n",
    )

    assert presentation.leading == ""
    assert presentation.trailing == ""
    assert presentation.insert_before_existing_details_close


def test_missing_destination_creates_a_visible_canonical_heading() -> None:
    presentation = source_detail_presentation(
        "Development and Testing",
        "View Development Details",
        target_exists=False,
    )

    assert presentation.leading == "## Development and Testing\n\n"
    assert presentation.trailing == ""
