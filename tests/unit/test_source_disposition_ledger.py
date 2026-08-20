"""Regressions for `commands_poc.py::build_source_disposition_ledger`'s
candidate-destination lookup -- the real defect observed identically on all
three 2026-08-20 calibration repositories (Note, Barcode, 3D): a case/wording
mismatch and a heading-granularity mismatch between the source README's own
heading spelling and the template contract's canonical slot titles."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from readme_agent.commands_poc import _disposition_acceptance, build_source_disposition_ledger
from readme_agent.repository_snapshot import RepositorySnapshotV1, SnapshotProvenanceV1


def _snapshot(root: Path, readme_text: str) -> RepositorySnapshotV1:
    (root / "README.md").write_text(readme_text, encoding="utf-8", newline="")
    readme_sha256 = hashlib.sha256(readme_text.encode("utf-8")).hexdigest()
    return RepositorySnapshotV1(
        org_repo="example-org/Example",
        source_revision="a" * 40,
        snapshot_root=str(root.resolve()),
        readme_path="README.md",
        readme_sha256=readme_sha256,
        inventory_sha256="b" * 64,
        captured_at=datetime.now(tz=UTC).isoformat(),
        provenance=SnapshotProvenanceV1(
            clone_url="https://github.com/example-org/Example.git",
            git_tree_sha256="b" * 64,
        ),
    )


def _render(final_text: str, compiled_slot_blocks: dict[str, str]) -> dict:
    return {
        "final_text": final_text,
        "readme_document_plan": {
            "claim_accountability": {"claims": []},
            "compiled_slot_blocks": compiled_slot_blocks,
        },
    }


def test_case_wording_drift_on_a_genuine_top_level_slot_resolves_a_target(tmp_path):
    """Real 3D/Note shape: source spells the heading in sentence case; the
    contract's compiled slot title is title case."""

    readme = "# Example\n\n## Key capabilities\n\nSupports A and B.\n"
    compiled_blocks = {"Key Capabilities": "## Key Capabilities\n\nSupports A and B.\n"}
    candidate = f"# Example\n\n{compiled_blocks['Key Capabilities']}"

    ledger = build_source_disposition_ledger(
        "example-org/Example", _snapshot(tmp_path, readme), _render(candidate, compiled_blocks)
    )

    unit = next(u for u in ledger["units"] if "Key capabilities" in u["unit"])
    assert unit["disposition"] == "VERIFIED_MERGED"
    assert unit["target"] == "Key Capabilities"
    valid, errors = _disposition_acceptance(ledger)
    assert valid, errors


def test_h3_child_beneath_a_mapped_h2_resolves_to_its_parent_slot(tmp_path):
    """Real Barcode/Note/3D shape: `compiled_slot_blocks()` only has entries
    at top-level slot granularity; an H3 sub-heading must resolve to its
    enclosing H2 slot, never fail as an unresolved unit of its own."""

    readme = (
        "# Example\n\n"
        "## Dependencies\n\n"
        "### Native and System Requirements\n\n"
        "A native toolchain is required.\n"
    )
    compiled_blocks = {
        "Dependencies": (
            "## Dependencies\n\n"
            "### Native and System Requirements\n\n"
            "A native toolchain is required.\n"
        )
    }
    candidate = f"# Example\n\n{compiled_blocks['Dependencies']}"

    ledger = build_source_disposition_ledger(
        "example-org/Example", _snapshot(tmp_path, readme), _render(candidate, compiled_blocks)
    )

    unit = next(u for u in ledger["units"] if "Native and System Requirements" in u["unit"])
    assert unit["disposition"] == "VERIFIED_MERGED"
    assert unit["target"] == "Dependencies"
    valid, errors = _disposition_acceptance(ledger)
    assert valid, errors


def test_duplicate_subheading_names_under_different_parents_are_distinguished(tmp_path):
    readme = (
        "# Example\n\n"
        "## Installation\n\n"
        "### Prerequisites\n\n"
        "Python 3.11+.\n\n"
        "## Development and Testing\n\n"
        "### Prerequisites\n\n"
        "A local Docker daemon.\n"
    )
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

    ledger = build_source_disposition_ledger(
        "example-org/Example", _snapshot(tmp_path, readme), _render(candidate, compiled_blocks)
    )

    prereq_units = [u for u in ledger["units"] if "Prerequisites" in u["unit"]]
    assert len(prereq_units) == 2
    targets = {u["target"] for u in prereq_units}
    assert targets == {"Installation", "Development and Testing"}
    valid, errors = _disposition_acceptance(ledger)
    assert valid, errors


def test_verified_omission_stays_non_content_without_a_destination_error(tmp_path):
    """A source unit the accountability map explicitly marks
    `verified_omission` must resolve NON_CONTENT (no target required) and
    must never be reported as a missing-destination error."""

    readme = "# Example\n\n## Legacy Section\n\nAn intentionally superseded paragraph.\n"
    body = "An intentionally superseded paragraph."
    start = readme.index(body)
    render = _render("# Example\n\n## Key Capabilities\n\nSupports A.\n", {})
    render["readme_document_plan"]["claim_accountability"]["claims"] = [
        {
            "stage": "source",
            "source_byte_start": start,
            "source_byte_end": start + len(body),
            "expected_disposition": "verified_omission",
            "rationale": "policy-superseded: this claim is no longer accurate and is dropped",
        }
    ]

    ledger = build_source_disposition_ledger(
        "example-org/Example", _snapshot(tmp_path, readme), render
    )

    unit = next(u for u in ledger["units"] if "Legacy Section" in u["unit"])
    assert unit["disposition"] == "NON_CONTENT"
    valid, errors = _disposition_acceptance(ledger)
    assert valid, errors


def test_genuine_unexplained_content_loss_is_still_reported_as_an_error(tmp_path):
    """Regression guard: the identity-aware target lookup must never launder
    a genuinely dropped, unaccounted-for source unit into a false positive."""

    readme = "# Example\n\n## Orphaned Section\n\nThis paragraph has vanished from the candidate.\n"
    candidate = "# Example\n\nCompletely different content with no trace of the original section.\n"

    ledger = build_source_disposition_ledger(
        "example-org/Example", _snapshot(tmp_path, readme), _render(candidate, {})
    )

    unit = next(u for u in ledger["units"] if "Orphaned Section" in u["unit"])
    assert unit["disposition"] == "UNVERIFIABLE_DROPPED"
    valid, errors = _disposition_acceptance(ledger)
    assert not valid
    assert any(
        "Orphaned Section" in error or "UNVERIFIABLE_DROPPED" in error for error in errors
    ) or (ledger["summary"]["UNVERIFIABLE_DROPPED"] >= 1)


def test_ledger_units_carry_source_byte_ranges(tmp_path):
    readme = "# Example\n\n## Key capabilities\n\nSupports A and B.\n"
    compiled_blocks = {"Key Capabilities": "## Key Capabilities\n\nSupports A and B.\n"}
    candidate = f"# Example\n\n{compiled_blocks['Key Capabilities']}"

    ledger = build_source_disposition_ledger(
        "example-org/Example", _snapshot(tmp_path, readme), _render(candidate, compiled_blocks)
    )

    unit = next(u for u in ledger["units"] if "Key capabilities" in u["unit"])
    assert isinstance(unit["source_byte_start"], int)
    assert isinstance(unit["source_byte_end"], int)
    assert unit["source_byte_end"] > unit["source_byte_start"]
    assert unit["heading_path"] == ["Example", "Key capabilities"]
