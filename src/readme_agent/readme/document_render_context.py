"""Shared immutable input context for README section operation planners."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.document_structure import Heading


@dataclass(frozen=True)
class DocumentRenderContext:
    """One source-bound view consumed by independent section planners."""

    org_repo: str
    source_text: str
    inner_text: str
    source: bytes
    facts: ProductFactsV2
    base_revision: str
    headings: list[Heading]

    def byte_offset(self, character_offset: int) -> int:
        """Translate a source character offset to presentation-inner UTF-8 bytes."""

        return len(self.inner_text[:character_offset].encode("utf-8"))

    def h2(self, *titles: str) -> Heading | None:
        """Return the first level-two heading with one normalized title."""

        normalized = {title.casefold() for title in titles}
        return next(
            (
                heading
                for heading in self.headings
                if heading.level == 2 and heading.title.strip().casefold() in normalized
            ),
            None,
        )
