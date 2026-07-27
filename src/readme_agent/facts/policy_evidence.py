"""Validate policy-selected technical assertions against immutable repository files."""

from __future__ import annotations

import re
from pathlib import Path

from readme_agent.facts.evidence_polarity import (
    EvidencePolarityAssessmentV1,
    ExpectedEvidencePolarity,
    assess_evidence_polarity,
)
from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import (
    FactRecordV2,
    FactSourceV2,
    descriptive_fact_id,
)
from readme_agent.registry.models import EvidenceBackedProductFact

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def safe_evidence_paths(root: Path, paths: list[str]) -> tuple[list[Path], list[str]]:
    """Resolve only existing files contained by the immutable snapshot root."""

    root = root.resolve()
    resolved: list[Path] = []
    failures: list[str] = []
    for relative in paths:
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            failures.append(f"evidence path escapes snapshot: {relative}")
            continue
        if not candidate.is_file():
            failures.append(f"evidence file missing: {relative}")
            continue
        resolved.append(candidate)
    return resolved, failures


def evidence_failures(
    root: Path,
    paths: list[str],
    required_symbols: list[str],
) -> list[str]:
    """Reject escaped/missing evidence and absent required symbols."""

    evidence_paths, failures = safe_evidence_paths(root, paths)
    if not required_symbols:
        failures.append("required evidence symbol missing: at least one exact anchor is required")
        return failures
    contents = [path.read_text(encoding="utf-8-sig", errors="replace") for path in evidence_paths]
    for symbol in required_symbols:
        if not symbol.strip():
            failures.append("required evidence symbol missing: blank anchors are invalid")
            continue
        if _IDENTIFIER.fullmatch(symbol):
            pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(symbol)}(?![A-Za-z0-9_])")
            found = any(pattern.search(content) is not None for content in contents)
        else:
            found = any(symbol in content for content in contents)
        if not found:
            failures.append(f"required evidence symbol missing: {symbol}")
    return failures


def evidence_fact_candidate(
    root: Path,
    source_revision: str | None,
    observed_at: str | None,
    field_name: str,
    specifications: list[EvidenceBackedProductFact],
) -> FactRecordV2:
    """Create one verified or narrowly blocked technical fact candidate."""

    values: list[str] = []
    locations: list[str] = []
    failures: list[str] = []
    assessments: list[EvidencePolarityAssessmentV1] = []
    fact_id = descriptive_fact_id(field_name, "repository-evidence")
    expected_polarity: ExpectedEvidencePolarity | None = None
    if field_name == "product.capabilities":
        expected_polarity = "positive_implementation"
    elif field_name == "product.limitations":
        expected_polarity = "explicit_constraint"
    for specification in specifications:
        structural_failures = evidence_failures(
            root,
            specification.evidence_paths,
            specification.required_symbols,
        )
        failures.extend(structural_failures)
        if not structural_failures and expected_polarity is not None:
            for anchor in specification.required_symbols:
                assessment = assess_evidence_polarity(
                    root=root,
                    evidence_paths=specification.evidence_paths,
                    anchor=anchor,
                    fact_id=fact_id,
                    claim_text=specification.value,
                    expected_polarity=expected_polarity,
                    source_revision=source_revision,
                    observed_at=observed_at,
                )
                if assessment is None:
                    failures.append(f"polarity evidence anchor unresolved: {anchor}")
                else:
                    assessments.append(assessment)
                    if not assessment.accepted:
                        failures.append(f"{assessment.reason}: {specification.value}")
        values.append(specification.value)
        locations.extend(specification.evidence_paths)
    return FactRecordV2(
        fact_id=fact_id,
        field=field_name,
        value={"assertions": values, "evidence_failures": failures} if failures else values,
        source=FactSourceV2(
            source_type="mechanical_repository",
            location="repository://" + ",".join(sorted(set(locations))),
            source_revision=source_revision,
            retrieved_at=observed_at,
        ),
        verification_state="blocked" if failures else "verified",
        authoritative_owner="repository-owner",
        confidence=0.0 if failures else 1.0,
        evidence_assessments=assessments or None,
        affected_surfaces=SURFACE_DEPENDENCIES[field_name],
    )


def limitation_fact_candidate(
    root: Path,
    source_revision: str | None,
    observed_at: str | None,
    specifications: list[EvidenceBackedProductFact],
) -> FactRecordV2:
    """Require explicit constraint evidence before accepting a drafted limitation.

    An API symbol proves that a feature exists; it does not prove that the
    feature is absent, incomplete, or otherwise limited. Agent-drafted
    limitations therefore need an exact evidence anchor that itself expresses
    a constraint. An empty limitations list remains an honest verified result.
    """

    return evidence_fact_candidate(
        root,
        source_revision,
        observed_at,
        "product.limitations",
        specifications,
    )
