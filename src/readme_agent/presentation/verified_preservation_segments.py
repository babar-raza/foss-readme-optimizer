"""Apply exact candidate splices while rebasing generated provenance coordinates."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent.readme.document_plan import CandidateContentProvenanceV1
from readme_agent.readme.document_structure import github_anchor, heading_identity, parse_headings


@dataclass(frozen=True)
class CandidateEdit:
    byte_start: int
    byte_end: int
    replacement: str


def apply_edit(markdown: str, edit: CandidateEdit) -> str:
    encoded = markdown.encode("utf-8")
    return (
        encoded[: edit.byte_start] + edit.replacement.encode("utf-8") + encoded[edit.byte_end :]
    ).decode("utf-8")


def navigation_edit(markdown: str) -> CandidateEdit:
    headings = [heading for heading in parse_headings(markdown) if heading.level == 2]
    navigations = [
        heading for heading in headings if heading_identity(heading.title) == "navigation"
    ]
    if len(navigations) != 1:
        raise ValueError("source-preserving composition requires exactly one Navigation H2")
    navigation = navigations[0]
    labels = [heading.title for heading in headings if heading is not navigation]
    body = "\n" + "\n".join(f"- [{label}](#{github_anchor(label)})" for label in labels) + "\n\n"
    return CandidateEdit(
        byte_start=len(markdown[: navigation.heading_end].encode("utf-8")),
        byte_end=len(markdown[: navigation.section_end].encode("utf-8")),
        replacement=body,
    )


def rebase_provenance(
    provenance: list[CandidateContentProvenanceV1],
    edit: CandidateEdit,
    candidate_after: str,
) -> list[CandidateContentProvenanceV1]:
    """Rebase exact generated spans through one byte-coordinate edit."""

    delta = len(edit.replacement.encode("utf-8")) - (edit.byte_end - edit.byte_start)
    rebased: list[CandidateContentProvenanceV1] = []
    for binding in provenance:
        if binding.candidate_byte_end <= edit.byte_start:
            rebased.append(binding)
            continue
        if edit.byte_end <= binding.candidate_byte_start:
            rebased.append(
                binding.model_copy(
                    update={
                        "candidate_byte_start": binding.candidate_byte_start + delta,
                        "candidate_byte_end": binding.candidate_byte_end + delta,
                    }
                )
            )
            continue
        if binding.provenance_id != "template.navigation":
            raise ValueError(
                f"source-preservation splice overlaps generated provenance: {binding.provenance_id}"
            )
        navigation = next(
            heading
            for heading in parse_headings(candidate_after)
            if heading.level == 2 and heading_identity(heading.title) == "navigation"
        )
        body = candidate_after[navigation.heading_end : navigation.section_end]
        body_start = navigation.heading_end + len(body) - len(body.lstrip())
        body_end = navigation.heading_end + len(body.rstrip())
        rebased.append(
            binding.model_copy(
                update={
                    "candidate_byte_start": len(candidate_after[:body_start].encode("utf-8")),
                    "candidate_byte_end": len(candidate_after[:body_end].encode("utf-8")),
                }
            )
        )
    return rebased
