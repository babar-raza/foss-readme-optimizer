"""Render canonical fact-backed limitation groups for the verified template."""

from __future__ import annotations

from dataclasses import dataclass

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.knowledge_claim_presentation import knowledge_limitation_items
from readme_agent.readme.limitation_semantics import public_limitations_equivalent
from readme_agent.readme.public_limitations import public_limitation_phrases


@dataclass(frozen=True)
class VerifiedLimitationGroupV1:
    """One deterministic limitation group and the fact field that authorizes it."""

    heading: str
    fact_field: str
    items: tuple[str, ...]

    @property
    def markdown(self) -> str:
        """Return the exact public Markdown rendered for the group."""

        return f"### {self.heading}\n\n" + "\n".join(self.items)


def verified_limitation_groups(facts: ProductFactsV2) -> tuple[VerifiedLimitationGroupV1, ...]:
    """Return deduplicated deterministic limitation groups from accepted facts."""

    product_limitations = public_limitation_phrases(facts)
    groups: list[VerifiedLimitationGroupV1] = []
    if product_limitations:
        groups.append(
            VerifiedLimitationGroupV1(
                heading="Feature and Workflow Boundaries",
                fact_field="product.limitations",
                items=tuple(f"- {item}" for item in product_limitations),
            )
        )

    knowledge_limitations: list[str] = []
    for item in knowledge_limitation_items(facts):
        public_text = item.markdown.removeprefix("- ")
        if any(
            public_limitations_equivalent(public_text, existing) for existing in product_limitations
        ):
            continue
        if any(
            public_limitations_equivalent(public_text, existing.removeprefix("- "))
            for existing in knowledge_limitations
        ):
            continue
        knowledge_limitations.append(item.markdown)
    if knowledge_limitations:
        groups.append(
            VerifiedLimitationGroupV1(
                heading="API Member Gaps",
                fact_field="aspose.limitation_claims",
                items=tuple(knowledge_limitations),
            )
        )
    return tuple(groups)
