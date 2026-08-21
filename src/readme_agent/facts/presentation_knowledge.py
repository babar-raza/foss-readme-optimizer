"""Reverify imported presentation hints against the current repository snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from readme_agent.facts.evidence_polarity import (
    EvidencePolarityAssessmentV1,
    ExpectedEvidencePolarity,
    assess_evidence_polarity,
)
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.presentation_knowledge_schema import (
    PresentationKnowledgeCatalogV1,
    PresentationKnowledgeDispositionV1,
    PresentationKnowledgeHintV1,
    PresentationKnowledgeSelectionV1,
)
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id

_SOURCE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".cxx",
    ".go",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".py",
    ".rs",
    ".ts",
    ".tsx",
}
_NOISE_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "target",
}


class _SourceIndex:
    """One bounded text index reused by every hint for a repository snapshot."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.texts: dict[Path, str] = {}
        for path in sorted(self.root.rglob("*")):
            if (
                not path.is_file()
                or path.suffix.casefold() not in _SOURCE_SUFFIXES
                or _NOISE_PARTS & {part.casefold() for part in path.relative_to(self.root).parts}
            ):
                continue
            try:
                if path.stat().st_size > 4_000_000:
                    continue
                self.texts[path.resolve()] = path.read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue

    def paths_containing(self, anchor: str, preferred: Path) -> list[Path]:
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(anchor)}(?![A-Za-z0-9_])")
        matches = [path for path, text in self.texts.items() if pattern.search(text)]
        return sorted(matches, key=lambda path: (path != preferred, path.as_posix()))


def _catalog(path: Path) -> tuple[PresentationKnowledgeCatalogV1, str]:
    payload = path.read_bytes()
    return (
        PresentationKnowledgeCatalogV1.model_validate(json.loads(payload)),
        hashlib.sha256(payload).hexdigest(),
    )


def _safe_evidence_path(root: Path, relative: str) -> Path | None:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if not candidate.is_file() or candidate.name.casefold().startswith("readme"):
        return None
    return candidate


def _verify_hint(
    hint: PresentationKnowledgeHintV1,
    *,
    root: Path,
    index: _SourceIndex,
    fact_id: str,
    source_revision: str | None,
    observed_at: str | None,
) -> tuple[list[EvidencePolarityAssessmentV1] | None, str]:
    preferred = _safe_evidence_path(root, hint.evidence_path)
    if preferred is None:
        return None, "cited current-source evidence path is missing, unsafe, or a README"
    preferred_text = index.texts.get(preferred)
    if preferred_text is None:
        return None, "cited evidence path is not an indexed source file"
    if not any(anchor in preferred_text for anchor in hint.anchors):
        return None, "cited evidence file contains none of the hint's technical anchors"

    expected: ExpectedEvidencePolarity = (
        "explicit_constraint" if hint.field == "product.limitations" else "positive_implementation"
    )
    assessments: list[EvidencePolarityAssessmentV1] = []
    for anchor in hint.anchors:
        accepted = None
        for path in index.paths_containing(anchor, preferred):
            relative = path.relative_to(root.resolve()).as_posix()
            assessment = assess_evidence_polarity(
                root=root,
                evidence_paths=[relative],
                anchor=anchor,
                fact_id=fact_id,
                claim_text=hint.text,
                expected_polarity=expected,
                source_revision=source_revision,
                observed_at=observed_at,
            )
            if assessment is not None and assessment.accepted:
                accepted = assessment
                break
        if accepted is None:
            return None, f"technical anchor is not directionally proven in current source: {anchor}"
        assessments.append(accepted)
    return assessments, "all technical anchors are proven in current source"


def presentation_knowledge_facts(
    family: str,
    platform: str,
    *,
    root: Path,
    source_revision: str | None,
    observed_at: str | None,
    catalog_path: Path,
) -> tuple[list[FactRecordV2], PresentationKnowledgeSelectionV1]:
    """Return only current-source-proven fallback facts plus every disposition."""

    catalog, catalog_sha256 = _catalog(catalog_path)
    hints = [
        hint
        for hint in catalog.hints
        if hint.family.casefold() == family.casefold()
        and hint.platform.casefold() == platform.casefold()
    ]
    index = _SourceIndex(root)
    dispositions: list[PresentationKnowledgeDispositionV1] = []
    values: dict[str, list[str]] = {"product.capabilities": [], "product.limitations": []}
    assessments: dict[str, list[EvidencePolarityAssessmentV1]] = {
        "product.capabilities": [],
        "product.limitations": [],
    }
    evidence_paths: dict[str, set[str]] = {
        "product.capabilities": set(),
        "product.limitations": set(),
    }
    for hint in hints:
        fact_id = descriptive_fact_id(hint.field, "presentation-knowledge")
        verified, reason = _verify_hint(
            hint,
            root=root,
            index=index,
            fact_id=fact_id,
            source_revision=source_revision,
            observed_at=observed_at,
        )
        accepted = verified is not None
        dispositions.append(
            PresentationKnowledgeDispositionV1(
                hint_id=f"{hint.family}/{hint.platform}/{hint.unit_id}",
                field=hint.field,
                status="accepted" if accepted else "rejected",
                reason=reason,
            )
        )
        if verified is None:
            continue
        values[hint.field].append(hint.text)
        assessments[hint.field].extend(verified)
        evidence_paths[hint.field].update(item.source_path for item in verified)

    facts: list[FactRecordV2] = []
    for field in ("product.capabilities", "product.limitations"):
        selected_values = list(dict.fromkeys(values[field]))
        if not selected_values:
            continue
        facts.append(
            FactRecordV2(
                fact_id=descriptive_fact_id(field, "presentation-knowledge"),
                field=field,
                value=selected_values,
                source=FactSourceV2(
                    source_type="mechanical_repository",
                    location="repository://" + ",".join(sorted(evidence_paths[field])),
                    source_revision=source_revision,
                    retrieved_at=observed_at,
                ),
                verification_state="verified",
                authoritative_owner="repository-owner",
                confidence=1.0,
                evidence_assessments=assessments[field],
                affected_surfaces=SURFACE_DEPENDENCIES[field],
            )
        )
    accepted_count = sum(item.status == "accepted" for item in dispositions)
    return facts, PresentationKnowledgeSelectionV1(
        family=family,
        platform=platform,
        catalog_sha256=catalog_sha256,
        considered=len(dispositions),
        accepted=accepted_count,
        rejected=len(dispositions) - accepted_count,
        dispositions=dispositions,
    )


__all__ = ["presentation_knowledge_facts"]
