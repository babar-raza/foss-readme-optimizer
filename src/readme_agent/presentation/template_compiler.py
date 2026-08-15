"""Compile bound presentation slots into one canonical README structure."""

from __future__ import annotations

import hashlib
import re

from readme_agent.presentation.template_schema import (
    BoundTemplateContentV1,
    PresentationTemplateInputV1,
    RepositoryPresentationTemplateV1,
    TemplateProfile,
    TemplateSlot,
    load_repository_presentation_template,
)
from readme_agent.readme.document_structure import github_anchor, parse_headings

_BADGE = re.compile(r"(?:!\[[^\]]+\]\([^)]+\)|\[!\[[^\]]+\]\([^)]+\)\]\([^)]+\))")


def select_density_profile(
    source_line_count: int,
    *,
    configured_profile: TemplateProfile | None = None,
    template: RepositoryPresentationTemplateV1 | None = None,
) -> TemplateProfile:
    """Select by source size unless an explicit profile supersedes the automatic choice."""

    if configured_profile is not None:
        return configured_profile
    contract = template or load_repository_presentation_template()
    for name in ("compact", "standard"):
        profile = contract.profiles[name]
        assert profile.maximum_source_lines is not None
        if source_line_count <= profile.maximum_source_lines:
            return name
    return "extended"


def _included_sections(
    template_input: PresentationTemplateInputV1,
    contract: RepositoryPresentationTemplateV1,
) -> list[tuple[TemplateSlot, BoundTemplateContentV1]]:
    unknown = set(template_input.sections) - set(contract.section_order)
    if unknown:
        raise ValueError(f"template input contains unknown slots: {sorted(unknown)}")
    included: list[tuple[TemplateSlot, BoundTemplateContentV1]] = []
    for slot in contract.section_order:
        if slot == "navigation":
            continue
        content = template_input.sections.get(slot)
        if content is None:
            if slot in contract.required_slots:
                raise ValueError(f"template input is missing required slot {slot!r}")
            continue
        if content.source_kind == "omitted":
            if slot in contract.required_slots and not (content.omission_reason or "").startswith(
                "Working-condition presentation:"
            ):
                raise ValueError(f"required template slot {slot!r} cannot be omitted")
            continue
        included.append((slot, content))
    return included


def _navigation(
    included: list[tuple[TemplateSlot, BoundTemplateContentV1]],
    contract: RepositoryPresentationTemplateV1,
) -> str:
    labels = [contract.headings[slot] for slot, _ in included]
    return "\n".join(f"- [{label}](#{github_anchor(label)})" for label in labels)


def compile_repository_presentation(
    template_input: PresentationTemplateInputV1,
    *,
    template: RepositoryPresentationTemplateV1 | None = None,
) -> str:
    """Compile one bound input without inventing, rewriting, or interpreting product prose."""

    contract = template or load_repository_presentation_template()
    profile = select_density_profile(
        template_input.source_line_count,
        configured_profile=template_input.profile,
        template=contract,
    )
    included = _included_sections(template_input, contract)
    badge_count = len(_BADGE.findall(template_input.badges.markdown))
    if badge_count < contract.invariants.minimum_badges:
        raise ValueError("template badge row has no applicable bound badge")

    title = " ".join(template_input.title.markdown.split())
    if not title or title.startswith("#"):
        raise ValueError("template title must be plain full product identity text")
    blocks = [
        f"# {title}",
        template_input.badges.markdown.strip(),
        template_input.summary.markdown.strip(),
        "## Navigation\n\n" + _navigation(included, contract),
    ]
    collapse = set(contract.profiles[profile].collapse_slots)
    for slot, content in included:
        body = content.markdown.strip()
        if slot in collapse and body.count("\n") >= 12 and "<details>" not in body:
            raise ValueError(f"long {slot!r} content must use a collapsible details block")
        blocks.append(f"## {contract.headings[slot]}\n\n{body}")
    candidate = "\n\n".join(blocks).rstrip() + "\n"

    headings = parse_headings(candidate)
    if [heading.title for heading in headings if heading.level == 1] != [title]:
        raise ValueError("compiled template must contain exactly the bound H1")
    return candidate


def compiled_slot_blocks(
    template_input: PresentationTemplateInputV1,
    *,
    template: RepositoryPresentationTemplateV1 | None = None,
) -> dict[str, str]:
    """Return each included slot's exact compiled block text, keyed by its
    heading -- the same block text `compile_repository_presentation` joins
    into the candidate, computed the same way, never altering that
    function's own behavior (this is an additive sibling, called only
    after a `compile_repository_presentation` call on the same input has
    already succeeded).

    Callers use this to locate a slot's freshly-compiled content in the
    *final* candidate by exact substring search, which stays correct even
    when a later step (verified-source-preservation splicing) inserts
    additional blocks and shifts byte offsets downstream -- unlike a
    byte-offset computed at this stage, a substring search re-locates the
    content wherever it ends up.
    """

    contract = template or load_repository_presentation_template()
    profile = select_density_profile(
        template_input.source_line_count,
        configured_profile=template_input.profile,
        template=contract,
    )
    included = _included_sections(template_input, contract)
    collapse = set(contract.profiles[profile].collapse_slots)
    blocks: dict[str, str] = {}
    for slot, content in included:
        body = content.markdown.strip()
        if slot in collapse and body.count("\n") >= 12 and "<details>" not in body:
            continue
        blocks[contract.headings[slot]] = f"## {contract.headings[slot]}\n\n{body}"
    return blocks


def presentation_input_hash(template_input: PresentationTemplateInputV1) -> str:
    """Hash every bound slot independently of runtime serialization order."""

    return hashlib.sha256(
        template_input.model_dump_json(exclude_none=True).encode("utf-8")
    ).hexdigest()
