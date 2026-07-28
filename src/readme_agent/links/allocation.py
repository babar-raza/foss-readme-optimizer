"""Measure README content and resolve configured-or-automatic link ceilings."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Literal

from markdown_it import MarkdownIt
from markdown_it.token import Token
from pydantic import BaseModel, ConfigDict, Field

from readme_agent.registry.models import LinkAllocationPolicyV1

_URL = re.compile(r"https?://[^\s<>()\]]+", re.IGNORECASE)
_WORD = re.compile(r"\b[\w][\w.+#-]*\b", re.UNICODE)


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ContentUnitMeasurementV1(_StrictFrozenModel):
    """Deterministic measurement of the pre-link candidate."""

    schema_version: Literal[1] = 1
    visible_prose_words: int = Field(ge=0)
    verified_code_blocks: int = Field(ge=0)
    verified_code_units: int = Field(ge=0)
    total_content_units: int = Field(ge=0)


class ResolvedLinkBudgetV1(_StrictFrozenModel):
    """Concrete ceilings used by selection and final occurrence validation."""

    schema_version: Literal[1] = 1
    mode: Literal["auto", "configured"]
    measurement: ContentUnitMeasurementV1
    max_total: int = Field(ge=0)
    domain_maxima: dict[Literal["aspose.org", "aspose.com"], int]
    surface_maxima: dict[
        Literal["products", "docs", "kb", "blog", "reference"],
        int,
    ]


def code_sha256(code: str) -> str:
    """Return the normalized code digest used to recognize verified examples."""

    normalized = code.replace("\r\n", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _inline_visible_words(children: list[Token]) -> int:
    words = 0
    for child in children:
        if child.type == "image":
            continue
        if child.type not in {"text", "code_inline"}:
            continue
        without_urls = _URL.sub(" ", child.content)
        words += len(_WORD.findall(without_urls))
    return words


def measure_readme_content_units(
    markdown: str,
    *,
    verified_code_sha256s: set[str] | None = None,
) -> ContentUnitMeasurementV1:
    """Count visible prose plus 100 units per accepted exact code example."""

    verified = verified_code_sha256s or set()
    prose_words = 0
    verified_blocks = 0
    for token in MarkdownIt("commonmark").parse(markdown):
        if token.type == "inline" and token.children:
            prose_words += _inline_visible_words(token.children)
            continue
        if token.type != "fence" or token.info.strip().casefold() == "mermaid":
            continue
        if code_sha256(token.content) in verified:
            verified_blocks += 1
    code_units = verified_blocks * 100
    return ContentUnitMeasurementV1(
        visible_prose_words=prose_words,
        verified_code_blocks=verified_blocks,
        verified_code_units=code_units,
        total_content_units=prose_words + code_units,
    )


def _automatic_total(units: int) -> int:
    if units <= 600:
        return 2
    if units <= 1_200:
        return 3
    if units <= 2_000:
        return 4
    if units <= 3_000:
        return 5
    return 6


def resolve_link_budget(
    policy: LinkAllocationPolicyV1,
    markdown: str,
    *,
    verified_code_sha256s: set[str] | None = None,
) -> ResolvedLinkBudgetV1:
    """Resolve exact ceilings; configured values replace every automatic value."""

    measurement = measure_readme_content_units(
        markdown,
        verified_code_sha256s=verified_code_sha256s,
    )
    if policy.mode == "configured":
        assert policy.max_total is not None
        assert policy.domain_maxima is not None
        assert policy.surface_maxima is not None
        return ResolvedLinkBudgetV1(
            mode="configured",
            measurement=measurement,
            max_total=policy.max_total,
            domain_maxima={
                "aspose.org": policy.domain_maxima.aspose_org,
                "aspose.com": policy.domain_maxima.aspose_com,
            },
            surface_maxima={
                "products": policy.surface_maxima.products,
                "docs": policy.surface_maxima.docs,
                "kb": policy.surface_maxima.kb,
                "blog": policy.surface_maxima.blog,
                "reference": policy.surface_maxima.reference,
            },
        )
    total = _automatic_total(measurement.total_content_units)
    return ResolvedLinkBudgetV1(
        mode="auto",
        measurement=measurement,
        max_total=total,
        domain_maxima={
            "aspose.org": math.ceil(total / 2),
            "aspose.com": math.ceil((2 * total) / 3),
        },
        surface_maxima={
            "products": min(2, total),
            "docs": min(2, total),
            "kb": min(2, total),
            "blog": min(1, total),
            "reference": min(2, total),
        },
    )
