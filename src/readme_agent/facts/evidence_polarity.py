"""Classify revision-bound claim evidence as implementation or constraint proof."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ExpectedEvidencePolarity = Literal["positive_implementation", "explicit_constraint"]
ObservedEvidencePolarity = Literal[
    "positive_implementation",
    "explicit_constraint",
    "ambiguous_occurrence",
]

_CONSTRAINT_CUE = re.compile(
    r"(?:\b(?:cannot|deprecated|experimental|incomplete|limited|limitation|"
    r"not|only|out\s+of\s+scope|partial|requires?|unavailable|unsupported)\b|"
    r"(?:NotImplemented|NotSupported|Unsupported)[A-Za-z0-9_]*Exception)",
    re.IGNORECASE,
)
_CODE_CONTEXT_CONSTRAINT_CUE = re.compile(
    r"(?:NotImplemented|NotSupported|Unsupported)[A-Za-z0-9_]*(?:Error|Exception)",
    re.IGNORECASE,
)
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_+-]*")
_IDENTIFIER_PART = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\d|\b)|[A-Z]?[a-z]+|[A-Z]+|\d+")
_DEICTIC_CONSTRAINT = re.compile(
    r"\bthis\s+(?:feature|operation|method|format|path|mode|option)\b",
    re.IGNORECASE,
)
_NON_SUBJECT_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "available",
    "be",
    "but",
    "by",
    "can",
    "cannot",
    "class",
    "could",
    "deprecated",
    "does",
    "feature",
    "for",
    "format",
    "from",
    "functionality",
    "in",
    "incomplete",
    "is",
    "limited",
    "limitation",
    "may",
    "method",
    "mode",
    "must",
    "not",
    "only",
    "or",
    "operation",
    "option",
    "out",
    "partial",
    "path",
    "public",
    "requires",
    "scope",
    "should",
    "supported",
    "the",
    "this",
    "to",
    "unavailable",
    "unsupported",
    "version",
    "void",
    "with",
}
_CONTEXT_RADIUS = 4
_CODE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
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
_CODE_IMPLEMENTATION_CUE = re.compile(
    r"(?:\b(?:class|const|def|enum|fn|func|impl|interface|method|pub|public|"
    r"static|struct|trait|type|var|void)\b|=>|[A-Za-z_][A-Za-z0-9_]*\s*\()"
)
_COMMENT_ONLY = re.compile(r"^\s*(?://+|/\*|\*|#|<!--)")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidencePolarityAssessmentV1(_StrictModel):
    """One exact anchor and its bounded repository context."""

    schema_version: Literal[1] = 1
    fact_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1)
    expected_polarity: ExpectedEvidencePolarity
    observed_polarity: ObservedEvidencePolarity
    source_path: str = Field(min_length=1)
    source_revision: str | None = None
    observed_at: str | None = None
    line_number: int = Field(ge=1)
    anchor: str = Field(min_length=1)
    exact_excerpt: str = Field(min_length=1)
    context_excerpt: str = Field(min_length=1)
    accepted: bool
    reason: str = Field(min_length=1)


def _subject_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for word in _WORD.findall(value):
        identifier_parts = _IDENTIFIER_PART.findall(word.replace("_", " "))
        for candidate in [word, *identifier_parts]:
            normalized = candidate.casefold()
            if len(normalized) < 3 or normalized in _NON_SUBJECT_WORDS:
                continue
            tokens.add(normalized)
            if len(normalized) > 4 and normalized.endswith("s") and not normalized.endswith("ss"):
                tokens.add(normalized[:-1])
            if len(normalized) > 6 and normalized.endswith("ing"):
                tokens.add(normalized[:-3])
    return tokens


def _find_anchors(content: str, anchor: str) -> list[tuple[int, str, str]]:
    lines = content.splitlines()
    occurrences: list[tuple[int, str, str]] = []
    for index, line in enumerate(lines):
        if anchor in line:
            start = max(0, index - _CONTEXT_RADIUS)
            end = min(len(lines), index + _CONTEXT_RADIUS + 1)
            occurrences.append(
                (
                    index + 1,
                    line.strip(),
                    "\n".join(lines[start:end]).strip(),
                )
            )
    return occurrences


def _positive_implementation_occurrence(path: Path, exact_excerpt: str) -> bool:
    """Reject prose/comment occurrence as proof that behavior is implemented."""

    if path.suffix.casefold() not in _CODE_SUFFIXES:
        return False
    if _COMMENT_ONLY.search(exact_excerpt):
        return False
    return _CODE_IMPLEMENTATION_CUE.search(exact_excerpt) is not None


def _classify_occurrence(
    *,
    path: Path,
    exact_excerpt: str,
    context_excerpt: str,
) -> ObservedEvidencePolarity:
    if _CONSTRAINT_CUE.search(exact_excerpt) or (
        _positive_implementation_occurrence(path, exact_excerpt)
        and _CODE_CONTEXT_CONSTRAINT_CUE.search(context_excerpt)
    ):
        return "explicit_constraint"
    if _positive_implementation_occurrence(path, exact_excerpt):
        return "positive_implementation"
    return "ambiguous_occurrence"


def _subject_is_bound(
    *,
    claim_text: str,
    anchor: str,
    context_excerpt: str,
    observed_polarity: ObservedEvidencePolarity,
) -> bool:
    claim_subjects = _subject_tokens(claim_text)
    anchor_subjects = _subject_tokens(anchor)
    if claim_subjects & anchor_subjects:
        return True
    return bool(
        observed_polarity == "explicit_constraint"
        and _DEICTIC_CONSTRAINT.search(anchor)
        and claim_subjects & _subject_tokens(context_excerpt)
    )


def assess_evidence_polarity(
    *,
    root: Path,
    evidence_paths: list[str],
    anchor: str,
    fact_id: str,
    claim_text: str,
    expected_polarity: ExpectedEvidencePolarity,
    source_revision: str | None,
    observed_at: str | None,
) -> EvidencePolarityAssessmentV1 | None:
    """Assess exact occurrences and prefer one that directionally proves the claim."""

    resolved_root = root.resolve()
    rejected: list[EvidencePolarityAssessmentV1] = []
    for relative_path in evidence_paths:
        candidate = (resolved_root / relative_path).resolve()
        try:
            candidate.relative_to(resolved_root)
        except ValueError:
            continue
        if not candidate.is_file():
            continue
        content = candidate.read_text(encoding="utf-8-sig", errors="replace")
        for line_number, exact_excerpt, context_excerpt in _find_anchors(content, anchor):
            observed_polarity = _classify_occurrence(
                path=candidate,
                exact_excerpt=exact_excerpt,
                context_excerpt=context_excerpt,
            )
            accepted = observed_polarity == expected_polarity
            reason = (
                f"observed {observed_polarity} matches expected {expected_polarity}"
                if accepted
                else f"observed {observed_polarity} contradicts expected {expected_polarity}"
            )
            if accepted and not _subject_is_bound(
                claim_text=claim_text,
                anchor=anchor,
                context_excerpt=context_excerpt,
                observed_polarity=observed_polarity,
            ):
                accepted = False
                reason = "directional evidence anchor does not identify the claimed subject"
            assessment = EvidencePolarityAssessmentV1(
                fact_id=fact_id,
                claim_text=claim_text,
                expected_polarity=expected_polarity,
                observed_polarity=observed_polarity,
                source_path=relative_path.replace("\\", "/"),
                source_revision=source_revision,
                observed_at=observed_at,
                line_number=line_number,
                anchor=anchor,
                exact_excerpt=exact_excerpt,
                context_excerpt=context_excerpt,
                accepted=accepted,
                reason=reason,
            )
            if accepted:
                return assessment
            rejected.append(assessment)
    return rejected[0] if rejected else None
