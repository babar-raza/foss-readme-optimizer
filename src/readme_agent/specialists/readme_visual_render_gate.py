"""Apply the official Mermaid render gate before deterministic promotion."""

from __future__ import annotations

from readme_agent.readme.document_plan import ReadmeDocumentPlanV1
from readme_agent.verification.mermaid_render import verify_official_mermaid_render


def apply_official_visual_render_gate(
    presentation_plan_record: dict,
    verification: dict,
) -> dict:
    """Return deterministic validation enriched with geometry-bound render proof."""

    document_plan = ReadmeDocumentPlanV1.model_validate(
        presentation_plan_record["readme_document_plan"]
    )
    visual = document_plan.header_visuals
    if visual is None or not visual.mermaid_source:
        return {
            **verification,
            "official_mermaid_render": {
                "status": "not_applicable",
                "reason": "candidate has no evidence-supported Mermaid diagram",
            },
        }
    proof = verify_official_mermaid_render(visual)
    return {
        **verification,
        "official_mermaid_render": {
            "status": "passed",
            **proof.model_dump(mode="json"),
        },
    }
