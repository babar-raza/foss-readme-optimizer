"""Project relevance-filtered imported SEO keywords into a ProductFactsV2
fact record, with a full keep/drop disposition for lineage evidence.

Split out from `composer_factpack.py` (already past this repo's own
~300-line module-size guideline) as its own single-responsibility module,
per `plans/GOVERNANCE.md`'s "no monoliths" rule.

This is the operational half of `aspose_detectors.detect_relevant_seo_
keywords()`: prompt/metadata *visibility* of the raw keyword list already
existed (`aspose.seo_keywords`, declared surfaces `metadata.topics`/
`readme.opening`) without any downstream consumer actually reading it
(confirmed: `capabilities/propose_metadata_changes.py`'s topic proposal
only ever derives desired topics from `{ecosystem, platform}`). Real
capability-title generation (`presentation/verified_template_capability_
seo.py`) is a separately-tuned deterministic regex cascade grounded in
verified format/capability facts, not this keyword list; rewiring it to
consume free-text SEO phrases is a larger, higher-risk change than this
session covers -- an explicit, logged gap, not a silent one (see
`aspose_knowledge_selection.py`'s module docstring neighbor,
`knowledge_application_evidence.py`, for where the disposition this module
produces is surfaced).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.aspose_detectors import (
    RelevantSeoKeywordsDetectionV1,
    detect_relevant_seo_keywords,
)
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id


class SeoKeywordDispositionV1(BaseModel):
    """One imported SEO keyword's keep/drop decision -- the negative-match
    accounting the "no keyword stuffing" / "repository relevance before
    imported suggestions" requirement depends on being inspectable, not
    merely asserted."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    keyword: str
    kept: bool
    drop_reason: str | None = None


def seo_keyword_dispositions(
    family: str, platform: str, *, data_root: Path
) -> tuple[SeoKeywordDispositionV1, ...]:
    detection = detect_relevant_seo_keywords(family, platform, data_root=data_root)
    kept = [SeoKeywordDispositionV1(keyword=kw, kept=True) for kw in detection.keywords]
    wrong_platform = [
        SeoKeywordDispositionV1(keyword=kw, kept=False, drop_reason="wrong_platform")
        for kw in detection.dropped_wrong_platform
    ]
    ungrounded = [
        SeoKeywordDispositionV1(keyword=kw, kept=False, drop_reason="ungrounded")
        for kw in detection.dropped_ungrounded
    ]
    cap_exceeded = [
        SeoKeywordDispositionV1(keyword=kw, kept=False, drop_reason="cap_exceeded")
        for kw in detection.dropped_cap_exceeded
    ]
    return tuple(kept + wrong_platform + ungrounded + cap_exceeded)


def relevant_seo_keyword_fact_record(
    family: str, platform: str, *, data_root: Path
) -> FactRecordV2 | None:
    """`None` when no relevant keyword survives filtering -- never a hollow
    fact record. Distinct field name (`aspose.relevant_seo_keywords`) from
    the existing raw `aspose.seo_keywords` so nothing currently reading the
    unfiltered field regresses; this is a strict, additive refinement."""

    detection: RelevantSeoKeywordsDetectionV1 = detect_relevant_seo_keywords(
        family, platform, data_root=data_root
    )
    if not detection.keywords:
        return None
    return FactRecordV2(
        fact_id=descriptive_fact_id("aspose.relevant_seo_keywords", "aspose-knowledge"),
        field="aspose.relevant_seo_keywords",
        value=list(detection.keywords),
        source=FactSourceV2(
            source_type="approved_documentation",
            location=f"data/imported:{family}/{platform}",
            retrieved_at=datetime.now(UTC).isoformat(),
        ),
        verification_state="unverified",
        authoritative_owner="aspose.org",
        confidence=0.6,
        affected_surfaces=["metadata.topics", "readme.opening"],
    )


__all__ = [
    "SeoKeywordDispositionV1",
    "relevant_seo_keyword_fact_record",
    "seo_keyword_dispositions",
]
