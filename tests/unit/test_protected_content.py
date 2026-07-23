"""Markdown-aware protection for commands, examples, limitations, and owned spans."""

from readme_agent.facts.protected_content import (
    fingerprint_protected_content,
    validate_protected_content,
)

_BASELINE = """# Widget

Use the `WidgetClient` API.

## Installation

```bash
pip install widget
```

## Known limitations

Streaming mode does not support encrypted files.
"""


def test_fingerprint_captures_all_protected_categories():
    snapshot = fingerprint_protected_content(_BASELINE)
    categories = {fragment.category for fragment in snapshot.fragments}

    assert categories == {
        "technical_terminology",
        "command",
        "example",
        "limitation",
    }


def test_removing_command_example_or_limitation_fails():
    before = fingerprint_protected_content(_BASELINE)
    after = fingerprint_protected_content("# Widget\n\nUse the API.\n")

    decision = validate_protected_content(before, after)

    assert decision.valid is False
    assert {"command", "example", "limitation"} <= {loss.category for loss in decision.losses}


def test_changing_only_agent_owned_span_preserves_maintainer_fingerprint():
    baseline = (
        _BASELINE
        + '\n<!-- readme-agent:resources hash="sha256:abc" schema="2" -->\n'
        + "Old resources\n<!-- readme-agent:resources:end -->\n"
    )
    changed = (
        _BASELINE
        + '\n<!-- readme-agent:resources hash="sha256:def" schema="2" -->\n'
        + "New resources\n<!-- readme-agent:resources:end -->\n"
    )

    decision = validate_protected_content(
        fingerprint_protected_content(baseline),
        fingerprint_protected_content(changed),
    )

    assert decision.valid is True


def test_maintainer_authored_change_fails_even_if_code_fragments_survive():
    changed = _BASELINE.replace("# Widget", "# Better Widget")
    decision = validate_protected_content(
        fingerprint_protected_content(_BASELINE),
        fingerprint_protected_content(changed),
    )

    assert decision.valid is False
    assert any(loss.category == "maintainer_region" for loss in decision.losses)
