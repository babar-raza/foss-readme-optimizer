"""Prove the action-led capability rule accepts real verbs and still rejects labels."""

from __future__ import annotations

import pytest

from readme_agent.readme.capability_semantics import (
    capability_action_verb,
    is_action_led_capability_title,
)


@pytest.mark.parametrize(
    "title",
    [
        # PF05 typescript canary: rejected before the vocabulary was widened,
        # costing five provider calls over three section-authoring attempts.
        "Triangulate polygonal geometry",
        "Tessellate curved surfaces",
        "Subdivide mesh faces",
        "Extrude 2D profiles",
        "Deform skinned meshes",
        "Scale scene units",
        "Translate node positions",
    ],
)
def test_geometry_titles_are_action_led(title: str) -> None:
    assert is_action_led_capability_title(title)


@pytest.mark.parametrize(
    "title",
    [
        "Read and write cell values",
        "Convert 3D scenes",
        "Apply cell styles",
        "Export mesh data",
        "Merge cell ranges and apply number formats",
        "Manage hyperlinks and defined names",
        "Configure page setup and print settings",
    ],
)
def test_previously_accepted_titles_still_pass(title: str) -> None:
    """Widening the vocabulary must never regress an already-accepted title."""

    assert is_action_led_capability_title(title)


@pytest.mark.parametrize(
    "title",
    [
        # Bare labels and noun phrases: the rule exists to reject these, and a
        # wider verb list must not let them through.
        "Configuration",
        "Lifecycle management",
        "Support",
        "Operations",
        "Validation",
        "Cell values and formulas",
        "Document properties",
        "Mesh geometry",
        "Workbook metadata",
    ],
)
def test_non_action_titles_are_still_rejected(title: str) -> None:
    assert not is_action_led_capability_title(title)


def test_action_verb_is_reported_for_a_matched_title() -> None:
    assert capability_action_verb("Triangulate polygonal geometry") is not None
    assert capability_action_verb("Mesh geometry") is None
