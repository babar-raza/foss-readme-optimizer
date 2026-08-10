"""Compute typed candidate observations that a quality reviewer may not reinterpret."""

from __future__ import annotations

import re
from typing import Literal

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, model_validator

MechanicalCheckId = Literal[
    "document.h1_blocks",
    "document.duplicate_h2_headings",
    "document.required_h2_prefix",
    "header.badge_rows",
    "quick_start.fenced_blocks",
    "quick_start.max_nonblank_code_lines",
]
MECHANICAL_CHECK_IDS: tuple[MechanicalCheckId, ...] = (
    "document.h1_blocks",
    "document.duplicate_h2_headings",
    "document.required_h2_prefix",
    "header.badge_rows",
    "quick_start.fenced_blocks",
    "quick_start.max_nonblank_code_lines",
)
MechanicalOperator = Literal["eq", "lte"]
MechanicalValue = int | bool


class MechanicalObservationV1(BaseModel):
    """One parser-derived value and its configured compliance result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    check_id: MechanicalCheckId
    observed_value: MechanicalValue
    configured_operator: MechanicalOperator
    configured_value: MechanicalValue
    compliant: bool

    @model_validator(mode="after")
    def _compliance_matches_values(self) -> MechanicalObservationV1:
        expected = (
            self.observed_value == self.configured_value
            if self.configured_operator == "eq"
            else int(self.observed_value) <= int(self.configured_value)
        )
        if self.compliant is not expected:
            raise ValueError("mechanical observation compliance disagrees with values")
        return self


def build_candidate_mechanical_observations(
    candidate_text: str,
    visitor_contract: dict,
) -> tuple[MechanicalObservationV1, ...]:
    """Return configured parser observations for one exact README candidate."""

    standards = {
        str(item.get("standard_id")): item.get("parameters") or {}
        for item in visitor_contract.get("configured_standards", [])
        if isinstance(item, dict)
    }
    observations: list[MechanicalObservationV1] = []
    header = standards.get("readme.header")
    if header is not None and header.get("brand_contract_version"):
        observations.append(
            _observation(
                check_id="document.h1_blocks",
                observed_value=_h1_block_count(candidate_text),
                configured_operator="eq",
                configured_value=1,
            )
        )
        observations.append(
            _observation(
                check_id="document.duplicate_h2_headings",
                observed_value=_duplicate_h2_heading_count(candidate_text),
                configured_operator="eq",
                configured_value=0,
            )
        )
        required_h2_prefix = header.get("required_h2_prefix")
        if isinstance(required_h2_prefix, list) and required_h2_prefix:
            observations.append(
                _observation(
                    check_id="document.required_h2_prefix",
                    observed_value=_h2_prefix_matches(candidate_text, required_h2_prefix),
                    configured_operator="eq",
                    configured_value=True,
                )
            )
    badges = standards.get("readme.badges")
    if badges is not None and isinstance(badges.get("badge_rows"), int):
        observations.append(
            _observation(
                check_id="header.badge_rows",
                observed_value=visible_header_badge_row_count(candidate_text),
                configured_operator="lte",
                configured_value=int(badges["badge_rows"]),
            )
        )
    primary_example = standards.get("readme.primary_example")
    if primary_example is not None:
        maximum_fences = primary_example.get("maximum_fenced_blocks")
        if isinstance(maximum_fences, int):
            observations.append(
                _observation(
                    check_id="quick_start.fenced_blocks",
                    observed_value=quick_start_fence_count(candidate_text),
                    configured_operator="lte",
                    configured_value=maximum_fences,
                )
            )
        maximum_code_lines = primary_example.get("maximum_nonblank_code_lines")
        if isinstance(maximum_code_lines, int):
            observations.append(
                _observation(
                    check_id="quick_start.max_nonblank_code_lines",
                    observed_value=quick_start_max_nonblank_code_lines(candidate_text),
                    configured_operator="lte",
                    configured_value=maximum_code_lines,
                )
            )
    return tuple(observations)


def render_candidate_mechanical_observations(
    candidate_text: str,
    visitor_contract: dict,
) -> list[dict]:
    """Render stable JSON-ready observations for the blind reviewer."""

    return [
        observation.model_dump(mode="json")
        for observation in build_candidate_mechanical_observations(
            candidate_text,
            visitor_contract,
        )
    ]


def quick_start_fence_count(candidate_text: str) -> int:
    """Count fenced examples inside the actual Quick start H2 only."""

    return sum(
        token.type == "fence"
        for token in MarkdownIt("commonmark").parse(_quick_start_body(candidate_text))
    )


def quick_start_max_nonblank_code_lines(candidate_text: str) -> int:
    """Return the largest visible code-block line count in the Quick start H2."""

    counts = [
        sum(bool(line.strip()) for line in token.content.splitlines())
        for token in MarkdownIt("commonmark").parse(_quick_start_body(candidate_text))
        if token.type == "fence"
    ]
    return max(counts, default=0)


def visible_header_badge_row_count(candidate_text: str) -> int:
    """Count visible badge-bearing lines before the opening prose begins."""

    lines = candidate_text.replace("\r\n", "\n").splitlines()
    if not lines or not lines[0].startswith("# "):
        return 0
    count = 0
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("[![", "![")) and _line_contains_badge_image(stripped):
            count += 1
            continue
        break
    return count


_MARKDOWN_IMAGE_TARGET = re.compile(r"!\[[^\]]*\]\((?P<target>[^\s)]+)")


def _line_contains_badge_image(line: str) -> bool:
    """Distinguish trust/status badges from product banners and other visuals."""

    for match in _MARKDOWN_IMAGE_TARGET.finditer(line):
        target = match.group("target").casefold()
        if (
            "img.shields.io/" in target
            or target.endswith("/badge.svg")
            or ("/badge/" in target and target.endswith(".svg"))
        ):
            return True
    return False


def _observation(
    *,
    check_id: MechanicalCheckId,
    observed_value: MechanicalValue,
    configured_operator: MechanicalOperator,
    configured_value: MechanicalValue,
) -> MechanicalObservationV1:
    compliant = (
        observed_value == configured_value
        if configured_operator == "eq"
        else int(observed_value) <= int(configured_value)
    )
    return MechanicalObservationV1(
        check_id=check_id,
        observed_value=observed_value,
        configured_operator=configured_operator,
        configured_value=configured_value,
        compliant=compliant,
    )


def _h1_block_count(candidate_text: str) -> int:
    return sum(
        token.type == "heading_open" and token.tag == "h1"
        for token in MarkdownIt("commonmark").parse(candidate_text)
    )


def _duplicate_h2_heading_count(candidate_text: str) -> int:
    headings: dict[str, int] = {}
    tokens = MarkdownIt("commonmark").parse(candidate_text)
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.tag != "h2":
            continue
        if index + 1 >= len(tokens) or tokens[index + 1].type != "inline":
            continue
        title = tokens[index + 1].content.strip().casefold()
        if title:
            headings[title] = headings.get(title, 0) + 1
    return sum(max(0, count - 1) for count in headings.values())


def _h2_prefix_matches(candidate_text: str, required_prefix: list[object]) -> bool:
    titles: list[str] = []
    tokens = MarkdownIt("commonmark").parse(candidate_text)
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.tag != "h2":
            continue
        if index + 1 < len(tokens) and tokens[index + 1].type == "inline":
            titles.append(tokens[index + 1].content.strip().casefold())
    expected = [str(title).strip().casefold() for title in required_prefix]
    return titles[: len(expected)] == expected


def _quick_start_body(candidate_text: str) -> str:
    heading = re.search(r"(?mi)^##[ \t]+Quick start[ \t]*$", candidate_text)
    if heading is None:
        return ""
    next_h2 = re.search(r"(?m)^##[ \t]+", candidate_text[heading.end() :])
    end = len(candidate_text) if next_h2 is None else heading.end() + next_h2.start()
    return candidate_text[heading.end() : end]
