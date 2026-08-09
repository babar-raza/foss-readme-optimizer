"""Stable candidate review anchor contract."""

from readme_agent.specialists.review_candidate_anchors import (
    bind_candidate_review_anchors,
    build_candidate_review_anchors,
)


def test_candidate_review_anchors_are_stable_exact_and_non_overlapping() -> None:
    candidate = (
        "# Widget\n\n"
        "A focused library.\n\n"
        "## Quick start\n\n"
        "- Install the package\n"
        "- Run the example\n\n"
        "```python\n"
        'print("done")\n'
        "```\n"
    )

    first = build_candidate_review_anchors(candidate)
    second = build_candidate_review_anchors(candidate)

    assert first == second
    assert {item.text for item in first} == {
        "# Widget",
        "A focused library.",
        "## Quick start",
        "- Install the package\n- Run the example",
        '```python\nprint("done")\n```',
    }
    ranges = [(item.start_line, item.end_line_exclusive) for item in first]
    assert all(
        left_end <= right_start
        for (left_start, left_end), (right_start, right_end) in zip(
            ranges,
            ranges[1:],
            strict=False,
        )
    )


def test_candidate_review_anchor_binding_replaces_only_a_known_selected_block() -> None:
    candidate = "# Widget\n\nA focused library.\n"
    anchors = build_candidate_review_anchors(candidate)
    paragraph = next(item for item in anchors if item.text == "A focused library.")
    value = {
        "findings": [
            {
                "candidate_anchor_id": paragraph.anchor_id,
                "quoted_candidate_span": "A focused ...",
            }
        ]
    }

    bound = bind_candidate_review_anchors(value, anchors)

    assert bound["findings"][0]["quoted_candidate_span"] == paragraph.text


def test_oversized_api_table_is_split_without_omission_or_unbounded_anchor() -> None:
    rows = [
        f"| `Type{index}` | Describes public API behavior number {index}. |" for index in range(500)
    ]
    table = "\n".join(["| Type | Description |", "| --- | --- |", *rows])
    candidate = f"# Widget\n\n## API Reference\n\n{table}\n"

    anchors = build_candidate_review_anchors(candidate)
    table_anchors = [anchor for anchor in anchors if anchor.text.startswith("| ")]

    assert len(table_anchors) > 1
    assert all(len(anchor.text) <= 12_000 for anchor in table_anchors)
    assert "\n".join(anchor.text for anchor in table_anchors) == table
