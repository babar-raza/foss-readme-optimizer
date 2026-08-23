"""Full-candidate structural contradictions for bounded visitor-review premises."""

from readme_agent.specialists.review_standard_premises import (
    validate_configured_standard_premise,
)


def test_complete_collapsed_api_reference_disproves_empty_packet_premise() -> None:
    candidate = """# Product

## API Reference

The package documents one public type.

<details>
<summary>View public API by namespace</summary>

### Product Namespace (`product`)

| Type | Description |
| --- | --- |
| `Scene` | Represents a public scene and supports loading content. |

</details>
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.api.empty",
        section="api-reference",
        premise="The collapsed <details> block contains no visible content.",
        candidate_text=candidate,
        visitor_contract={},
    )

    assert errors == [
        "visitor.api.empty:API-reference premise contradicts complete collapsed namespace tables"
    ]


def test_action_led_capability_rows_disprove_inventory_fragment_premise() -> None:
    candidate = """# Product

## Key Capabilities

- **Create 3D primitives** - Construct standard 3D shapes directly in Python.
- **Define animations with keyframes** - Build animations using keyframe support.
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.capabilities.inventory",
        section="key-capabilities",
        premise="Bullets are class or method inventory fragments instead of developer tasks.",
        candidate_text=candidate,
        visitor_contract={},
    )

    assert errors == [
        "visitor.capabilities.inventory:capability premise contradicts action-led same-line "
        "behavior rows"
    ]
