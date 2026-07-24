"""Validate policy-selected technical assertions against immutable repository files."""

from __future__ import annotations

from pathlib import Path

from readme_agent.facts.migration import SURFACE_DEPENDENCIES
from readme_agent.facts.schema_v2 import (
    FactRecordV2,
    FactSourceV2,
    descriptive_fact_id,
)
from readme_agent.registry.models import EvidenceBackedProductFact


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
    contents = [path.read_text(encoding="utf-8-sig", errors="replace") for path in evidence_paths]
    for symbol in required_symbols:
        if not any(symbol in content for content in contents):
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
    for specification in specifications:
        failures.extend(
            evidence_failures(
                root,
                specification.evidence_paths,
                specification.required_symbols,
            )
        )
        values.append(specification.value)
        locations.extend(specification.evidence_paths)
    return FactRecordV2(
        fact_id=descriptive_fact_id(field_name, "repository-evidence"),
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
        affected_surfaces=SURFACE_DEPENDENCIES[field_name],
    )
