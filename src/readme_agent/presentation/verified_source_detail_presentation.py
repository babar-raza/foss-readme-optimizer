"""Choose visible or collapsible shells for routed verified source detail."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent.presentation.template_schema import load_repository_presentation_template
from readme_agent.readme.document_structure import heading_identity


@dataclass(frozen=True)
class SourceDetailPresentationV1:
    """Structural wrapper and insertion mode for one canonical destination."""

    leading: str
    trailing: str
    insert_before_existing_details_close: bool = False


def source_detail_presentation(
    target_title: str,
    summary: str,
    *,
    target_exists: bool,
    section_text: str = "",
) -> SourceDetailPresentationV1:
    """Keep visitor-critical detail visible and fold only contract-approved secondary detail."""

    if not target_exists:
        return SourceDetailPresentationV1(leading=f"## {target_title}\n\n", trailing="")

    contract = load_repository_presentation_template()
    always_visible = {
        heading_identity(contract.headings[slot])
        for slot in contract.invariants.always_visible_slots
    }
    if heading_identity(target_title) in always_visible:
        return SourceDetailPresentationV1(leading="", trailing="")

    if "</details>" in section_text.casefold():
        return SourceDetailPresentationV1(
            leading="",
            trailing="",
            insert_before_existing_details_close=True,
        )

    return SourceDetailPresentationV1(
        leading=f"<details>\n<summary>{summary}</summary>\n\n",
        trailing="</details>\n\n",
    )
