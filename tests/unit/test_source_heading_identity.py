"""Regressions for the disposition-ledger heading-identity resolver."""

from __future__ import annotations

from readme_agent.readme.source_heading_identity import (
    canonical_heading_key,
    resolve_disposition_target,
)


def test_canonical_heading_key_ignores_case_whitespace_and_trailing_punctuation():
    assert canonical_heading_key("Key capabilities") == canonical_heading_key("Key Capabilities")
    assert canonical_heading_key("  Quick   start  ") == canonical_heading_key("Quick start")
    assert canonical_heading_key("License:") == canonical_heading_key("License")


def test_canonical_heading_key_never_unifies_distinct_wording():
    assert canonical_heading_key("Documentation & Resources") != canonical_heading_key(
        "Documentation and Resources"
    )


def test_case_and_wording_drift_on_a_genuine_top_level_slot_resolves():
    """The real 3D/Note failure mode: source spells the heading in sentence
    case, the contract's canonical slot title is title case."""

    compiled_blocks = {"Key Capabilities": "## Key Capabilities\n\nSupports A and B.\n"}
    candidate = f"# Example\n\n{compiled_blocks['Key Capabilities']}"

    target = resolve_disposition_target(("Key capabilities",), compiled_blocks, candidate)

    assert target == "Key Capabilities"


def test_h3_child_beneath_a_mapped_h2_resolves_to_its_parent_slot():
    """The real Barcode/Note/3D failure mode: `compiled_slot_blocks()` is only
    keyed at top-level slot granularity, so an H3 sub-heading can never be a
    key on its own -- it must resolve to its enclosing H2 slot instead."""

    compiled_blocks = {
        "Dependencies": (
            "## Dependencies\n\n"
            "### Native and System Requirements\n\n"
            "A native toolchain is required.\n"
        )
    }
    candidate = f"# Example\n\n{compiled_blocks['Dependencies']}"

    target = resolve_disposition_target(
        ("Dependencies", "Native and System Requirements"),
        compiled_blocks,
        candidate,
    )

    assert target == "Dependencies"


def test_h3_child_not_actually_placed_in_its_named_parent_does_not_resolve():
    """A nested unit must not be credited merely because SOME ancestor name
    matches a slot -- its own leaf text must genuinely appear in that slot's
    compiled block, never guessed from the parent match alone."""

    compiled_blocks = {"Dependencies": "## Dependencies\n\nNo native toolchain required.\n"}
    candidate = f"# Example\n\n{compiled_blocks['Dependencies']}"

    target = resolve_disposition_target(
        ("Dependencies", "Native and System Requirements"),
        compiled_blocks,
        candidate,
    )

    assert target == ""


def test_duplicate_subheading_names_under_different_parents_resolve_independently():
    compiled_blocks = {
        "Installation": "## Installation\n\n### Prerequisites\n\nPython 3.11+.\n",
        "Development and Testing": (
            "## Development and Testing\n\n### Prerequisites\n\nA local Docker daemon.\n"
        ),
    }
    candidate = (
        f"# Example\n\n{compiled_blocks['Installation']}\n"
        f"{compiled_blocks['Development and Testing']}"
    )

    install_target = resolve_disposition_target(
        ("Installation", "Prerequisites"), compiled_blocks, candidate
    )
    dev_target = resolve_disposition_target(
        ("Development and Testing", "Prerequisites"), compiled_blocks, candidate
    )

    assert install_target == "Installation"
    assert dev_target == "Development and Testing"


def test_relocated_content_resolves_via_content_fallback_when_no_heading_matches():
    """Content genuinely reframed under a differently-titled section: the
    source heading name itself does not match any contract slot, but the
    unit's own retained block text landed, verbatim, inside exactly one
    compiled slot -- content-identity match, not name-identity."""

    compiled_blocks = {
        "Key Capabilities": (
            "## Key Capabilities\n\n"
            "Reads and writes the OneNote binary format with full fidelity.\n"
        )
    }
    candidate = f"# Example\n\n{compiled_blocks['Key Capabilities']}"

    target = resolve_disposition_target(
        ("Old Format Support Section",),
        compiled_blocks,
        candidate,
        content_snippets=("Reads and writes the OneNote binary format with full fidelity.",),
    )

    assert target == "Key Capabilities"


def test_relocated_content_ambiguous_across_multiple_slots_fails_closed():
    compiled_blocks = {
        "Key Capabilities": "## Key Capabilities\n\nShared exact wording appears here too.\n",
        "Scope and Limitations": (
            "## Scope and Limitations\n\nShared exact wording appears here too.\n"
        ),
    }
    candidate = (
        f"# Example\n\n{compiled_blocks['Key Capabilities']}\n"
        f"{compiled_blocks['Scope and Limitations']}"
    )

    target = resolve_disposition_target(
        ("Old Section",),
        compiled_blocks,
        candidate,
        content_snippets=("Shared exact wording appears here too.",),
    )

    assert target == ""


def test_genuinely_unaccounted_heading_fails_closed():
    compiled_blocks = {"Key Capabilities": "## Key Capabilities\n\nSupports A and B.\n"}
    candidate = f"# Example\n\n{compiled_blocks['Key Capabilities']}"

    target = resolve_disposition_target(("Some Unrelated Heading",), compiled_blocks, candidate)

    assert target == ""


def test_colliding_canonical_slot_titles_refuse_to_resolve_anything():
    """A template-contract inconsistency (two distinct slot keys that
    canonicalize to the same identity) must never be silently resolved by
    picking one -- the whole slot index is refused."""

    compiled_blocks = {
        "Key Capabilities": "## Key Capabilities\n\nA.\n",
        "key capabilities": "## key capabilities\n\nB.\n",
    }
    candidate = (
        f"# Example\n\n{compiled_blocks['Key Capabilities']}\n{compiled_blocks['key capabilities']}"
    )

    target = resolve_disposition_target(("Key Capabilities",), compiled_blocks, candidate)

    assert target == ""


def test_slot_block_not_present_in_candidate_fails_closed_even_on_a_name_match():
    compiled_blocks = {"Key Capabilities": "## Key Capabilities\n\nSupports A and B.\n"}
    candidate = "# Example\n\nSomething else entirely.\n"

    target = resolve_disposition_target(("Key Capabilities",), compiled_blocks, candidate)

    assert target == ""


def test_empty_heading_path_fails_closed():
    compiled_blocks = {"Key Capabilities": "## Key Capabilities\n\nSupports A and B.\n"}

    target = resolve_disposition_target((), compiled_blocks, "irrelevant")

    assert target == ""
