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
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.api_reference",
                    "parameters": {"complete_namespace_tables": True},
                }
            ]
        },
    )

    assert errors == [
        "visitor.api.empty:API-reference premise contradicts complete collapsed namespace tables"
    ]


def test_action_led_capability_rows_do_not_overrule_qualitative_value_review() -> None:
    candidate = """# Product

## Key Capabilities

- **Create 3D primitives** - Construct standard 3D shapes directly in Python.
- **Define animations with keyframes** - Build animations using keyframe support.
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.capabilities.inventory",
        section="Key Capabilities",
        premise="Bullets are class or method inventory fragments instead of developer tasks.",
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.key_capabilities",
                    "parameters": {"action_led_same_line_rows": True},
                }
            ]
        },
    )

    assert errors == []


def test_approved_mermaid_styling_and_invisible_layout_are_not_repair_findings() -> None:
    candidate = """# Product

## At a Glance

```mermaid
flowchart LR
  subgraph CORE["Core Capabilities"]
    direction TB
    C1["Create scenes"]
    C2["Export models"]
    C1 ~~~ C2
  end
  PRODUCT["Product"] --> CORE
  CORE --> O1["Output"]
  classDef capability fill:#F7F9FC,stroke:#AAB7C4;
  class C1,C2 capability;
  style CORE fill:#FFFFFF,stroke:#5F7791
```
"""
    contract = {
        "configured_standards": [
            {
                "standard_id": "readme.at_a_glance_mermaid",
                "parameters": {
                    "rendered_internal_capability_connectors": "none",
                    "invisible_layout_constraints": "allowed",
                    "styling_directives": "allowed",
                },
            }
        ]
    }

    style_errors = validate_configured_standard_premise(
        finding_id="visitor.mermaid.style",
        section="at-a-glance",
        premise="Remove all classDef, style, and class directives because they are not permitted.",
        candidate_text=candidate,
        visitor_contract=contract,
    )
    connector_errors = validate_configured_standard_premise(
        finding_id="visitor.mermaid.connectors",
        section="at-a-glance",
        premise="Replace internal capability connectors and remove tildes between C1 and C2.",
        candidate_text=candidate,
        visitor_contract=contract,
    )

    assert style_errors == [
        "visitor.mermaid.style:Mermaid-style premise contradicts configured presentation"
    ]
    assert connector_errors == [
        "visitor.mermaid.connectors:internal-connector premise contradicts configured invisible "
        "layout constraints"
    ]


def test_verified_output_coverage_disproves_treating_target_as_minimum() -> None:
    candidate = """# Product

## At a Glance

```mermaid
flowchart LR
  I1["Input"] --> PRODUCT["Product"]
  PRODUCT --> CORE["Core Capabilities"]
  CORE --> O1["First output"]
  O2["Second output"]
  O3["Third output"]
```
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.mermaid.outputs",
        section="at-a-glance",
        premise=(
            "The contract requires 5 target outputs; three makes the diagram "
            "incomplete and noncompliant."
        ),
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.at_a_glance_mermaid",
                    "parameters": {
                        "minimum_outputs": 1,
                        "target_outputs": 5,
                        "output_coverage": "all_selected_verified",
                    },
                }
            ]
        },
    )

    assert errors == [
        "visitor.mermaid.outputs:Mermaid target-output premise contradicts verified-coverage "
        "contract"
    ]


def test_complete_api_tables_do_not_overrule_qualitative_grouping_review() -> None:
    candidate = """# Product

## API Reference

The package documents 10 public types across two namespaces.

<details>
<summary>View public API by namespace</summary>

### Product Namespace (`product`)

| Type | Description |
| --- | --- |
| `Scene` | Represents a scene and supports loading content. |

</details>
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.api.grouping",
        section="api-reference",
        premise=(
            "The section does not clarify which APIs are most relevant and only states how many "
            "types exist. Group namespaces by functional area and list representative classes."
        ),
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.api_reference",
                    "parameters": {"complete_namespace_tables": True},
                }
            ]
        },
    )

    assert errors == []


def test_complete_api_tables_do_not_overrule_description_quality_review() -> None:
    candidate = """# Product

## API Reference

<details>
<summary>View public API by namespace</summary>

### Product Namespace (`product`)

| Type | Description |
| --- | --- |
| `Scene` | Scene. |

</details>
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.api.descriptions",
        section="api-reference",
        premise=(
            "The API reference is present but remains unhelpful without meaningful "
            "descriptions of what each type does."
        ),
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.api_reference",
                    "parameters": {"complete_namespace_tables": True},
                }
            ]
        },
    )

    assert errors == []


def test_action_led_capability_rows_do_not_disprove_bare_label_value_finding() -> None:
    candidate = """# Product

## Key Capabilities

- **Create 3D primitives** - Construct standard 3D shapes directly in Python.
- **Define animations with keyframes** - Build animations using keyframe support.
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.capabilities.labels",
        section="key-capabilities",
        premise=(
            "Bullets are bare feature labels. Rewrite to start with a strong action verb and add "
            "concrete value because the second lacks product-specific value explanation."
        ),
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.key_capabilities",
                    "parameters": {"action_led_same_line_rows": True},
                }
            ]
        },
    )

    assert errors == []


def test_action_led_capability_rows_disprove_bare_label_only_finding() -> None:
    candidate = """# Product

## Key Capabilities

- **Create scenes** - Build scenes in Python.
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.capabilities.bare-label",
        section="key-capabilities",
        premise="The bullet is a bare feature label.",
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.key_capabilities",
                    "parameters": {"action_led_same_line_rows": True},
                }
            ]
        },
    )

    assert errors == [
        "visitor.capabilities.bare-label:bare-label premise contradicts parsed action-led "
        "capability rows"
    ]


def test_complete_api_tables_disprove_unclosed_and_placeholder_premises() -> None:
    candidate = """# Product

## API Reference

The package documents public types. See Documentation & Resources for the full reference.

<details>
<summary>View public API by namespace</summary>

### Product Namespace (`product`)

| Type | Description |
| --- | --- |
| `Scene` | Loads and saves product documents. |

</details>
"""
    contract = {
        "configured_standards": [
            {
                "standard_id": "readme.api_reference",
                "parameters": {"complete_namespace_tables": True},
            }
        ]
    }

    for premise in (
        "The incomplete and unclosed details block contains no actual namespace table content.",
        "Replace the placeholder reference to 'Documentation & Resources' with an actual "
        "namespace table or direct API listing.",
    ):
        assert validate_configured_standard_premise(
            finding_id="visitor.api.invalid",
            section="api-reference",
            premise=premise,
            candidate_text=candidate,
            visitor_contract=contract,
        ) == [
            "visitor.api.invalid:API-reference premise contradicts complete collapsed "
            "namespace tables"
        ]


def test_full_document_secondary_example_structure_disproves_packet_limited_premises() -> None:
    candidate = """# Product

## Quick Start

```python
print("ready")
```

## Additional Examples

The examples below demonstrate loading and exporting product documents.

<details>
<summary>View additional examples and results</summary>

### Export a Document

```python
print("export")
```

</details>
"""
    contract = {
        "configured_standards": [
            {
                "standard_id": "readme.primary_example",
                "parameters": {
                    "secondary_examples": "collapsed_below_primary",
                    "secondary_examples_intro": "workflow_preview",
                },
            }
        ]
    }

    for premise in (
        "Secondary examples are not collapsed below a primary example and it lacks a primary "
        "example.",
        "The HTML <details> block, which violates Markdown integrity, needs a Markdown-only "
        "collapsible structure.",
        "The section has no workflow preview.",
    ):
        assert validate_configured_standard_premise(
            finding_id="visitor.examples.invalid",
            section="additional-examples",
            premise=premise,
            candidate_text=candidate,
            visitor_contract=contract,
        ) == [
            "visitor.examples.invalid:secondary-example premise contradicts parsed "
            "full-document contract"
        ]


def test_complete_product_specific_capability_rows_disprove_fragment_premises() -> None:
    candidate = (
        "# Aspose.3D FOSS for Python\n\n## Key Capabilities\n\n"
        "- **Create 3D primitives** - Construct standard geometric shapes using dedicated "
        "constructors provided by Aspose.3D FOSS for Python.\n"
        "- **Define animated sequences** - Build animation timelines using keyframes to control "
        "property changes over time for 3D entities.\n"
    )
    contract = {
        "configured_standards": [
            {
                "standard_id": "readme.key_capabilities",
                "parameters": {
                    "action_led_same_line_rows": True,
                    "developer_value_explanation": "required",
                },
            }
        ]
    }

    for premise in (
        "Bullets are incomplete sentence fragments that omit the developer-facing outcome.",
        "The section reads like a raw inventory list and not just a description of API usage.",
        "It uses internal terminology instead of verified product vocabulary.",
    ):
        assert validate_configured_standard_premise(
            finding_id="visitor.capabilities.invalid",
            section="key-capabilities",
            premise=premise,
            candidate_text=candidate,
            visitor_contract=contract,
        ) == [
            "visitor.capabilities.invalid:capability-value premise contradicts parsed complete "
            "same-line rows"
        ]


def test_category_level_structural_premises_are_checked_against_full_document() -> None:
    candidate = """# Product

## Quick Start

```python
print("ready")
```

## Additional Examples

The examples below demonstrate an export workflow.

<details>
<summary>View additional examples and results</summary>

### Export

```python
print("export")
```

</details>

## API Reference

<details>
<summary>View public API by namespace</summary>

### Product Namespace (`product`)

| Type | Description |
| --- | --- |
| `Scene` | Loads and saves product documents. |

</details>
"""
    contract = {
        "configured_standards": [
            {
                "standard_id": "readme.primary_example",
                "parameters": {
                    "secondary_examples": "collapsed_below_primary",
                    "secondary_examples_intro": "workflow_preview",
                },
            },
            {
                "standard_id": "readme.api_reference",
                "parameters": {"complete_namespace_tables": True},
            },
        ]
    }
    example_errors = validate_configured_standard_premise(
        finding_id="visitor.examples.structural",
        section="additional-examples",
        premise=(
            "The section presents multiple examples without a primary workflow and collapsed "
            "secondary examples."
        ),
        candidate_text=candidate,
        visitor_contract=contract,
    )
    api_errors = validate_configured_standard_premise(
        finding_id="visitor.api.structural",
        section="api-reference",
        premise="The API Reference is incomplete and lacks a structured navigable listing.",
        candidate_text=candidate,
        visitor_contract=contract,
    )

    assert example_errors == [
        "visitor.examples.structural:secondary-example premise contradicts parsed full-document "
        "contract"
    ]
    assert api_errors == [
        "visitor.api.structural:API-reference premise contradicts complete collapsed namespace "
        "tables"
    ]


def test_approved_mermaid_line_breaks_and_link_style_disprove_forbidden_syntax_premise() -> None:
    candidate = """# Product

## At a Glance

```mermaid
flowchart LR
  PRODUCT["Product<br/>for Python"] --> CORE["Core<br/>Capabilities"]
  CORE --> O1["PDF<br/>Format"]
  linkStyle 0,1 stroke:#526D82,stroke-width:2px
```
"""
    contract = {
        "configured_standards": [
            {
                "standard_id": "readme.at_a_glance_mermaid",
                "parameters": {"styling_directives": "allowed"},
            }
        ]
    }

    for premise in (
        "HTML line breaks in node labels are not aligned with the canonical visual grammar; "
        "replace them.",
        "The linkStyle directive is not permitted; remove it.",
    ):
        assert validate_configured_standard_premise(
            finding_id="visitor.mermaid.syntax",
            section="at-a-glance",
            premise=premise,
            candidate_text=candidate,
            visitor_contract=contract,
        ) == [
            "visitor.mermaid.syntax:Mermaid-syntax premise contradicts configured rendered visual"
        ]


def test_configured_mermaid_group_label_and_internal_layout_direction_are_not_defects() -> None:
    candidate = """# Product

## At a Glance

```mermaid
flowchart LR
  PRODUCT["Product"]
  subgraph CORE["Core Capabilities"]
    direction TB
    C1["Create scenes"]
    C2["Export models"]
    C1 ~~~ C2
  end
  PRODUCT --> CORE
  CORE --> O1["Output"]
```
"""
    contract = {
        "configured_standards": [
            {
                "standard_id": "readme.at_a_glance_mermaid",
                "parameters": {
                    "capability_group_label": "Core Capabilities",
                    "internal_direction_directives": "layout_only",
                },
            }
        ]
    }

    label_errors = validate_configured_standard_premise(
        finding_id="visitor.mermaid.label",
        section="at-a-glance",
        premise=(
            "The Mermaid diagram uses the 'Core Capabilities' group label; rename 'CORE' "
            "to avoid an internal group label."
        ),
        candidate_text=candidate,
        visitor_contract=contract,
    )
    direction_errors = validate_configured_standard_premise(
        finding_id="visitor.mermaid.direction",
        section="at-a-glance",
        premise=(
            "The Mermaid diagram uses 'direction TB' inside subgraphs, which implies an ordered "
            "workflow; remove it."
        ),
        candidate_text=candidate,
        visitor_contract=contract,
    )

    assert label_errors == [
        "visitor.mermaid.label:Mermaid-group-label premise contradicts configured presentation"
    ]
    assert direction_errors == [
        "visitor.mermaid.direction:Mermaid-layout-direction premise contradicts configured "
        "presentation"
    ]


def test_capability_value_parser_does_not_override_another_section() -> None:
    candidate = """# Product

## At a Glance

```mermaid
flowchart LR
  PRODUCT["Product"] --> CORE["Core Capabilities"]
```

## Key Capabilities

- **Create 3D primitives** - Construct standard 3D shapes directly in Python applications.
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.mermaid.wording",
        section="at-a-glance",
        premise="The internal Core Capabilities terminology lacks developer value.",
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.key_capabilities",
                    "parameters": {
                        "action_led_same_line_rows": True,
                        "developer_value_explanation": "required",
                    },
                }
            ]
        },
    )

    assert errors == []


def test_grouped_mermaid_edges_disprove_per_node_and_undirected_edge_premises() -> None:
    candidate = """# Product

## At a Glance

```mermaid
flowchart LR
  I1["First"]
  I2["Second"]
  PRODUCT["Product"]
  subgraph CORE["Core Capabilities"]
    C1["Create scenes"]
  end
  I1 --> PRODUCT
  PRODUCT --> CORE
  CORE --> O1["Output"]
```
"""
    contract = {
        "configured_standards": [
            {
                "standard_id": "readme.at_a_glance_mermaid",
                "parameters": {
                    "minimum_inputs": 1,
                    "input_to_product_edges": 1,
                    "product_to_capabilities_edges": 1,
                    "directional_workflow": True,
                },
            }
        ]
    }

    undirected_errors = validate_configured_standard_premise(
        finding_id="visitor.mermaid.product-core",
        section="at-a-glance",
        premise=(
            "The diagram omits a required undirected connector between PRODUCT and CORE; "
            "replace PRODUCT --> CORE."
        ),
        candidate_text=candidate,
        visitor_contract=contract,
    )
    input_errors = validate_configured_standard_premise(
        finding_id="visitor.mermaid.inputs",
        section="at-a-glance",
        premise=("The diagram has missing input arrows for I2 and violates minimum_inputs=2."),
        candidate_text=candidate,
        visitor_contract=contract,
    )

    assert undirected_errors == [
        "visitor.mermaid.product-core:Mermaid product-to-capabilities premise contradicts "
        "configured topology"
    ]
    assert input_errors == [
        "visitor.mermaid.inputs:Mermaid input-edge premise contradicts configured grouped topology"
    ]


def test_workflow_preview_disproves_raw_task_list_premise() -> None:
    candidate = """# Product

## Additional Examples

The examples below demonstrate loading OBJ files with materials, exporting a scene to binary
GLTF, converting a parametric primitive to a mesh, and building a cube for 3MF export.

<details>
<summary>View additional examples and results</summary>

### Export a Scene

```python
print("ready")
```

</details>
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.examples.intro",
        section="additional-examples",
        premise=(
            "The opening lacks a natural, developer-facing overview and reads like a raw task "
            "list. Rewrite it rather than a task list."
        ),
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.primary_example",
                    "parameters": {"secondary_examples_intro": "workflow_preview"},
                }
            ]
        },
    )

    assert errors == [
        "visitor.examples.intro:secondary-example intro premise contradicts parsed workflow preview"
    ]
