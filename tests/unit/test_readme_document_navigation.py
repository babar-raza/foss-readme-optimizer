"""Complete-navigation binding for verified README operations."""

from readme_agent.readme.document_navigation import finalize_navigation_operations
from readme_agent.readme.document_operations import apply_document_operations, build_operation


def test_final_navigation_includes_headings_added_outside_its_owner() -> None:
    source_text = "# Widget\n\n## Usage\n\nUse it.\n\n## License\n\nMIT.\n"
    source = source_text.encode("utf-8")
    insertion = source_text.index("## Usage")
    operation = build_operation(
        operation_id="readme.overview-navigation-and-acquisition",
        operation="insert_before",
        source=source,
        start=insertion,
        end=insertion,
        replacement=(
            "## Navigation\n\n"
            "- [At a glance](#at-a-glance)\n"
            "- [Usage](#usage)\n\n"
            "## At a glance\n\n"
            "A useful widget.\n\n"
        ),
        fact_ids=[],
        treatment="additive",
        rationale="Add the governed opening.",
    )

    finalized = finalize_navigation_operations(source, [operation])
    candidate = apply_document_operations(source, finalized).decode("utf-8")

    assert "- [At a glance](#at-a-glance)" in candidate
    assert "- [Usage](#usage)" in candidate
    assert "- [License](#license)" in candidate
    assert finalized[0].replacement_sha256 != operation.replacement_sha256
