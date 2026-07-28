"""Typed contracts and label safety for factual README headers and diagrams."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

_UNSAFE_LABEL = re.compile(
    r"(?i)(?:<!--|-->|%%|<|>|[{};`]|:::|javascript:|"
    r"ignore\b.{0,40}\binstructions?\b|system\s+prompt)"
)


def safe_mermaid_label(value: object, *, limit: int = 80) -> str | None:
    """Return one bounded data-only Mermaid label or reject unsafe syntax/instructions."""

    label = " ".join(str(value).split()).strip()
    if not label or _UNSAFE_LABEL.search(label):
        return None
    label = label.replace('"', "'").replace("[", "(").replace("]", ")")
    return label[:limit].rstrip()


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReadmeBadgeV1(_StrictModel):
    badge_id: str
    kind: Literal["version", "package", "download", "license"]
    alt_text: str = Field(min_length=1)
    image_url: str = Field(min_length=1)
    target_url: str | None = None
    fact_ids: list[str] = Field(min_length=1)


class MermaidNodeV1(_StrictModel):
    node_id: str
    role: Literal["product", "audience", "problem", "capability", "format"]
    label: str = Field(min_length=1, max_length=96)
    fact_ids: list[str] = Field(min_length=1)


class ReadmeHeaderVisualV1(_StrictModel):
    schema_version: Literal[1] = 1
    title: str = Field(min_length=1, max_length=120)
    title_fact_ids: list[str] = Field(min_length=1)
    badges: list[ReadmeBadgeV1] = Field(default_factory=list)
    badge_markdown: str = ""
    diagram_nodes: list[MermaidNodeV1] = Field(min_length=2)
    mermaid_source: str = Field(min_length=1)
    mermaid_markdown: str = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> ReadmeHeaderVisualV1:
        badge_ids = [badge.badge_id for badge in self.badges]
        node_ids = [node.node_id for node in self.diagram_nodes]
        if len(badge_ids) != len(set(badge_ids)):
            raise ValueError("README header contains duplicate badge IDs")
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("README Mermaid graph contains duplicate node IDs")
        return self

    @property
    def badge_fact_ids(self) -> list[str]:
        return sorted({fact_id for badge in self.badges for fact_id in badge.fact_ids})

    @property
    def diagram_fact_ids(self) -> list[str]:
        return sorted({fact_id for node in self.diagram_nodes for fact_id in node.fact_ids})

    @property
    def all_fact_ids(self) -> list[str]:
        return sorted(
            set(self.title_fact_ids) | set(self.badge_fact_ids) | set(self.diagram_fact_ids)
        )


class HeaderVisualValidationV1(_StrictModel):
    valid: bool
    checks: dict[str, bool]
    errors: list[str] = Field(default_factory=list)
