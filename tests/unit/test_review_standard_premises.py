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


def test_source_installation_disproves_blind_requests_for_unstated_acquisition_facts() -> None:
    candidate = """# Aspose.3D FOSS for Python

## Installation

Aspose.3D FOSS for Python is acquired by building from source. This approach is useful when you
need to integrate the library directly into a custom build pipeline or work with a specific source
revision.

Install `aspose-3d-foss` directly from the repository source. The detached checkout pins these
instructions to the documented source revision.

```bash
git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python.git
cd Aspose.3D-FOSS-for-Python
git checkout --detach ee05c1ba9153ef5916b7a108406c794f2e464d01
python -m pip install .
```
"""

    premises = {
        "visitor.install.alternatives": (
            "The section does not clarify whether building from source is the only acquisition "
            "method. Clarify whether it is one of multiple options and mention alternatives "
            "such as PyPI."
        ),
        "visitor.install.terminology": (
            "Uses internal terminology 'detached checkout' and 'pins'. Replace it with plain "
            "language explaining why a specific source revision is used."
        ),
        "visitor.install.revision": (
            "The code block lacks context: no explanation of the checkout hash. Add a sentence "
            "explaining the specific commit hash and how it relates to version stability or "
            "reproducibility."
        ),
    }

    errors = {
        finding_id: validate_configured_standard_premise(
            finding_id=finding_id,
            section="installation",
            premise=premise,
            candidate_text=candidate,
            visitor_contract={},
        )
        for finding_id, premise in premises.items()
    }

    assert any(
        "conflicts with blind-review visible-fact authority" in error
        for error in errors["visitor.install.alternatives"]
    )
    assert any(
        "Git-terminology premise contradicts" in error
        for error in errors["visitor.install.terminology"]
    )
    assert any(
        "revision-context premise contradicts" in error
        for error in errors["visitor.install.revision"]
    )
    assert any(
        "revision-outcome premise conflicts with" in error
        for error in errors["visitor.install.revision"]
    )


def test_source_installation_allows_visible_prose_clarity_finding_without_new_facts() -> None:
    candidate = """# Product

## Installation

Install from the repository source at a documented source revision.

```bash
git clone https://github.com/example/product.git
git checkout --detach 0123456789abcdef
python -m pip install .
```
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.install.wording",
        section="installation",
        premise=(
            "The introductory sentence repeats the word source. Rewrite the visible sentence "
            "more concisely without adding technical claims."
        ),
        candidate_text=candidate,
        visitor_contract={},
    )

    assert errors == []


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


def test_verified_output_coverage_disproves_observed_expects_wording() -> None:
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
        finding_id="visitor.mermaid.outputs-observed",
        section="at-a-glance",
        premise=(
            "The output group has only three outputs while the contract expects five verified "
            "outputs. Add two outputs to meet the target_outputs=5 requirement."
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
        "visitor.mermaid.outputs-observed:Mermaid target-output premise contradicts "
        "verified-coverage contract"
    ]


def test_verified_output_coverage_disproves_specified_missing_target_wording() -> None:
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
        finding_id="visitor.mermaid.outputs-specified",
        section="at-a-glance",
        premise=(
            "The contract specifies target_outputs=5, so O4 and O5 are missing. "
            "Add two missing output nodes to match the configured target_outputs=5."
        ),
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.at_a_glance_mermaid",
                    "parameters": {
                        "minimum_outputs": 0,
                        "target_outputs": 5,
                        "output_coverage": "all_selected_verified",
                    },
                }
            ]
        },
    )

    assert errors == [
        "visitor.mermaid.outputs-specified:Mermaid target-output premise contradicts "
        "verified-coverage contract"
    ]


def test_allowed_corporate_styling_disproves_speculative_alignment_finding() -> None:
    candidate = """# Product

## At a Glance

```mermaid
flowchart LR
  I1["Input"] --> PRODUCT["Product"]
  PRODUCT --> CORE["Core Capabilities"]
  O1["Output"]
  CORE --> O1
  classDef product fill:#1F4E79,color:#FFFFFF;
  class PRODUCT product;
```
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.mermaid.styling-observed",
        section="at-a-glance",
        premise=(
            "The styling directives may not align with the corporate-capability-landscape "
            "visual grammar."
        ),
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.at_a_glance_mermaid",
                    "parameters": {
                        "visual_grammar": "corporate-capability-landscape",
                        "styling_directives": "allowed",
                    },
                }
            ]
        },
    )

    assert errors == [
        "visitor.mermaid.styling-observed:Mermaid-style premise contradicts configured presentation"
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


def test_product_bound_action_led_rows_disprove_generic_inventory_premise() -> None:
    candidate = (
        "# Aspose.3D FOSS for Python\n\n"
        "## Key Capabilities\n\n"
        "- **Create 3D primitives** - Construct Box, Cylinder, and Sphere shapes with "
        "Aspose.3D FOSS for Python in application workflows.\n"
        "- **Define animated sequences** - Build keyframe sequences with Aspose.3D FOSS "
        "for Python to control object transformations over time.\n"
    )

    errors = validate_configured_standard_premise(
        finding_id="visitor.capabilities.generic",
        section="key-capabilities",
        premise=(
            "Bullet items read like generic class inventory fragments instead of concrete "
            "developer-facing tasks using verified product vocabulary."
        ),
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

    assert errors == [
        "visitor.capabilities.generic:generic-capability premise contradicts product-bound "
        "action-led rows"
    ]


def test_product_bound_rows_disprove_observed_internal_inventory_wording() -> None:
    candidate = (
        "# Aspose.3D FOSS for Python\n\n"
        "## Key Capabilities\n\n"
        "- **Create 3D primitives** - Construct common 3D shapes such as Box, Cylinder, "
        "Sphere, Plane, Dish, Circle, Ellipse, and Frustum using dedicated primitive classes "
        "provided by Aspose.3D FOSS for Python.\n"
        "- **Define animated sequences** - Build animation sequences using the built-in "
        "keyframe support in Aspose.3D FOSS for Python to control how 3D objects transform "
        "over time.\n"
    )

    errors = validate_configured_standard_premise(
        finding_id="visitor.capabilities.observed",
        section="key-capabilities",
        premise=(
            "Bullets read as internal class/library inventory rather than developer-facing "
            "tasks. Rewrite to express concrete, action-led developer tasks."
        ),
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

    assert errors == [
        "visitor.capabilities.observed:generic-capability premise contradicts product-bound "
        "action-led rows"
    ]


def test_complete_capability_rows_disprove_missing_developer_value_premise() -> None:
    candidate = (
        "# Aspose.3D FOSS for Python\n\n"
        "## Key Capabilities\n\n"
        "- **Create 3D primitives** - Construct standard geometric shapes such as Box, "
        "Cylinder, and Sphere using built-in primitive classes to build scene geometry quickly.\n"
        "- **Define animated sequences** - Build animation timelines using keyframe support "
        "to control how 3D objects transform over time, enabling dynamic scene behavior.\n"
    )

    errors = validate_configured_standard_premise(
        finding_id="visitor.capabilities.value",
        section="key-capabilities",
        premise=(
            "Key capabilities are phrased as bare feature labels without developer-facing "
            "value explanations."
        ),
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

    assert errors == [
        "visitor.capabilities.value:capability-value premise contradicts parsed complete "
        "same-line rows"
    ]


def test_configured_core_to_first_output_edge_disproves_group_rewire_premise() -> None:
    candidate = """# Aspose.3D FOSS for Python

## At a Glance

```mermaid
flowchart LR
  subgraph INPUTS["Inputs & Formats"]
    I1["OBJ Format"]
  end
  PRODUCT["Aspose.3D FOSS for Python"]
  subgraph CORE["Core Capabilities"]
    C1["Create primitives"]
  end
  subgraph OUTPUTS["Outputs"]
    O1["GLTF Format"]
  end
  I1 --> PRODUCT
  PRODUCT --> CORE
  CORE --> O1
```
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.mermaid.output-group",
        section="at-a-glance",
        premise=(
            "The Mermaid diagram connects individual output O1 instead of the OUTPUTS group, "
            "violating group-level topology. Replace CORE --> O1 with CORE ~~~ OUTPUTS."
        ),
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.at_a_glance_mermaid",
                    "parameters": {
                        "directional_workflow": True,
                        "capabilities_to_outputs_edges": 1,
                    },
                }
            ]
        },
    )

    assert errors == [
        "visitor.mermaid.output-group:Mermaid capabilities-to-outputs premise contradicts "
        "configured grouped topology"
    ]


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
        "Secondary examples lack a required workflow-preview intro before the collapsed block.",
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


def test_api_reference_details_premise_is_not_rejected_by_unrelated_example_contract() -> None:
    """PWD-012: a genuine API-reference finding must not be silently discarded because it
    happens to share vocabulary ("lacks", "<details>") with the unrelated secondary-example
    contract check -- that check must only ever fire for findings actually scoped to
    additional-examples, exactly like every other section-specific check in this module."""

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

<details>
<summary>View public API by namespace</summary>

### Second Namespace (`second`)

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
        ]
    }

    errors = validate_configured_standard_premise(
        finding_id="visitor.api.second-namespace-empty",
        section="api-reference",
        premise=(
            "The Second Namespace collapsed <details> block is without a populated table, "
            "unlike the Product Namespace above."
        ),
        candidate_text=candidate,
        visitor_contract=contract,
    )

    assert errors == []


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
        "The animation row uses generic terms without specifying what the user can achieve.",
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


def test_directional_mermaid_topology_disproves_undirected_core_output_finding() -> None:
    candidate = """# Product

## At a Glance

```mermaid
flowchart LR
  I1["Input"] --> PRODUCT["Product"]
  PRODUCT --> CORE["Core Capabilities"]
  O1["Output"]
  CORE --> O1
```
"""

    errors = validate_configured_standard_premise(
        finding_id="visitor.mermaid.core-output",
        section="at-a-glance",
        premise=(
            "The diagram lacks an explicit undirected connector between the CORE group and the "
            "OUTPUTS group. Add exactly one undirected connector (~~~) between them."
        ),
        candidate_text=candidate,
        visitor_contract={
            "configured_standards": [
                {
                    "standard_id": "readme.at_a_glance_mermaid",
                    "parameters": {
                        "directional_workflow": True,
                        "capabilities_to_outputs_edges": 1,
                    },
                }
            ]
        },
    )

    assert errors == [
        "visitor.mermaid.core-output:Mermaid capabilities-to-outputs premise contradicts "
        "configured topology"
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


def test_real_fp03_preview_and_capability_findings_are_disproved() -> None:
    candidate = (
        "# Aspose.3D FOSS for Python\n\n## Key Capabilities\n\n"
        "- **Create 3D primitives** - Construct common 3D shapes such as Box, Cylinder, "
        "Sphere, Plane, Dish, Circle, Ellipse, and Frustum using built-in primitive classes.\n"
        "- **Define animated scenes** - Build animations using the built-in animation system "
        "with keyframe support to control object properties over time.\n\n"
        "## Additional Examples\n\n"
        "The examples below demonstrate loading OBJ files with materials, exporting a scene to "
        "binary GLTF, converting a parametric primitive to a mesh, and building a cube and "
        "exporting it to 3MF.\n\n"
        "<details>\n<summary>View additional examples and results</summary>\n\n"
        '### Export a Scene\n\n```python\nprint("ready")\n```\n\n</details>\n'
    )
    contract = {
        "configured_standards": [
            {
                "standard_id": "readme.key_capabilities",
                "parameters": {
                    "action_led_same_line_rows": True,
                    "developer_value_explanation": "required",
                    "content_density": "bounded_by_verified_facts",
                },
            },
            {
                "standard_id": "readme.primary_example",
                "parameters": {"secondary_examples_intro": "workflow_preview"},
            },
        ]
    }

    premises = (
        (
            "key-capabilities",
            "Capabilities read like a class inventory rather than developer-facing value "
            "statements.",
            "capability-value premise contradicts parsed complete same-line rows",
        ),
        (
            "key-capabilities",
            "The second capability omits what developers can achieve with keyframe animation.",
            "capability-value premise contradicts parsed complete same-line rows",
        ),
        (
            "additional-examples",
            "Missing workflow preview intro before secondary examples; current paragraph is a "
            "generic list summary, not a configured workflow preview.",
            "secondary-example intro premise contradicts parsed workflow preview",
        ),
        (
            "additional-examples",
            "The current introduction reads like a raw fact list rather than a natural, "
            "developer-facing workflow preview. Replace the generic summary line instead of "
            "the natural workflow preview.",
            "secondary-example intro premise contradicts parsed workflow preview",
        ),
        (
            "key-capabilities",
            "The section is incomplete. Add at least three additional capability bullets that "
            "describe concrete developer-facing tasks.",
            "capability-count premise exceeds verified-fact-bounded density",
        ),
        (
            "key-capabilities",
            "The second bullet describes animation mechanics without clarifying the "
            "developer-facing outcome or use case.",
            "capability-value premise contradicts parsed complete same-line rows",
        ),
    )
    for index, (section, premise, expected) in enumerate(premises):
        finding_id = f"visitor.fp03.{index}"
        assert validate_configured_standard_premise(
            finding_id=finding_id,
            section=section,
            premise=premise,
            candidate_text=candidate,
            visitor_contract=contract,
        ) == [f"{finding_id}:{expected}"]
