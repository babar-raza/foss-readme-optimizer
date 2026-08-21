"""Reverify imported presentation hints against the current repository snapshot."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from markdown_it import MarkdownIt

from readme_agent.facts.evidence_polarity import (
    EvidencePolarityAssessmentV1,
    ExpectedEvidencePolarity,
    assess_evidence_polarity,
)
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.presentation_hint_anchors import technical_anchors
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


def _public_text(value: str) -> str:
    """Remove producer wrapping without changing the imported wording."""

    return " ".join(value.split())


def _section_bullets(source: str, heading: str) -> list[str]:
    """Return top-level list items from one level-two CommonMark section."""

    lines = source.splitlines()
    tokens = MarkdownIt("commonmark").parse(source)
    section_start: int | None = None
    section_end = len(lines)
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.tag != "h2" or token.map is None:
            continue
        title = tokens[index + 1].content if index + 1 < len(tokens) else ""
        if section_start is None and title.strip().casefold() == heading.casefold():
            section_start = token.map[1]
            continue
        if section_start is not None:
            section_end = token.map[0]
            break
    if section_start is None:
        return []

    bullets: list[str] = []
    list_depth = 0
    for token in tokens:
        if token.map is not None and (token.map[0] < section_start or token.map[0] >= section_end):
            continue
        if token.type in {"bullet_list_open", "ordered_list_open"}:
            list_depth += 1
            continue
        if token.type in {"bullet_list_close", "ordered_list_close"}:
            list_depth = max(0, list_depth - 1)
            continue
        if token.type != "list_item_open" or list_depth != 1 or token.map is None:
            continue
        raw = "\n".join(lines[token.map[0] : token.map[1]])
        cleaned = re.sub(r"^\s*(?:[-+*]|\d+[.)])\s+", "", raw, count=1)
        cleaned = _public_text(cleaned)
        if cleaned:
            bullets.append(cleaned)
    return bullets


def _repository_readme_hints(
    root: Path,
    *,
    family: str,
    platform: str,
    index: _SourceIndex,
) -> list[PresentationKnowledgeHintV1]:
    """Treat current README statements as hints and bind them to non-README evidence paths."""

    readme = next(
        (
            path
            for path in (root / "README.md", root / "Readme.md", root / "readme.md")
            if path.is_file()
        ),
        None,
    )
    if readme is None:
        return []
    source = readme.read_text(encoding="utf-8-sig", errors="replace")
    source_sha256 = hashlib.sha256(readme.read_bytes()).hexdigest()
    hints: list[PresentationKnowledgeHintV1] = []
    for heading, field in (
        ("Key Capabilities", "product.capabilities"),
        ("Scope and Limitations", "product.limitations"),
    ):
        for offset, text in enumerate(_section_bullets(source, heading), start=1):
            anchors = technical_anchors(text)
            if not anchors:
                continue
            evidence_paths = index.paths_containing(anchors[0], root / "__no_preferred_source__")
            evidence_path = (
                evidence_paths[0].relative_to(root.resolve()).as_posix()
                if evidence_paths
                else readme.relative_to(root).as_posix()
            )
            hints.append(
                PresentationKnowledgeHintV1(
                    family=family,
                    platform=platform,
                    unit_id=f"source-readme-{heading.casefold().replace(' ', '-')}-{offset:04d}",
                    field=field,  # type: ignore[arg-type]
                    text=text,
                    evidence_path=evidence_path,
                    anchors=anchors,
                    source_file_sha256=source_sha256,
                )
            )
    return hints


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
                claim_text=_public_text(hint.text),
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
    catalog_ids = {(hint.field, _public_text(hint.text)) for hint in hints}
    hints.extend(
        hint
        for hint in _repository_readme_hints(
            root,
            family=family,
            platform=platform,
            index=index,
        )
        if (hint.field, _public_text(hint.text)) not in catalog_ids
    )
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
        values[hint.field].append(_public_text(hint.text))
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
