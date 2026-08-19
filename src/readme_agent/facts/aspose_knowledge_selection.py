"""Bounded, relevance-based selection over the imported aspose.org knowledge
corpus, plus the per-claim disposition ledger that makes the selection
inspectable.

This is the layer `FACT-*`/`L8-*` "verify against authoritative ground
truth, never trust a capability's output... as if it were reality"
(`docs/architecture.md`, "Trust and reconciliation doctrine") applies to for
third-party imported knowledge specifically:

* the full corpus (97k+ claims across 31 product bundles) is never handed to
  a prompt or a fact graph wholesale -- only a small, per-section-relevant,
  confidence-ranked slice is selected (`_MAX_SELECTED_PER_KIND`);
* every claim considered for one product/platform gets exactly one
  disposition (`selected` or `rejected` with a reason) -- there is no
  silent-drop path;
* a claim's bundle staleness (`aspose_knowledge_claims.assess_bundle_
  freshness`) caps its confidence and blocks `verified`/`policy_approved`
  status unless independently corroborated by current, live repository
  evidence (today: license-file detection) -- current repository evidence
  always wins on conflict, and an uncorroborated stale claim is carried at
  reduced, `unverified` confidence rather than discarded outright, since a
  few days' staleness on an otherwise-accurate API/feature claim is common
  and still useful supplementary evidence, not proof of falsehood.

Two claim kinds are deliberately never selected here, with an explicit
disposition reason rather than silent omission: `dependency` (already
produced by `aspose_detectors.detect_dependency_claims` /
`composer_factpack.aspose_fact_records`'s existing `aspose.dependency_claims`
field -- selecting it again here would create two divergent paths for the
same evidence) and `api`/`api_class`/`api_method`/`api_field` (the
structured, per-language `api_surface.json` already covers this need through
`aspose.public_surface`/`api.public_surface` with real per-member signatures;
the free-text `claims.json` API claims are a strictly weaker projection of
the same ground truth).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.aspose_detectors import detect_license_file
from readme_agent.facts.aspose_knowledge_claims import (
    BundleFreshness,
    ImportedKnowledgeClaimV1,
    KnowledgeClaimKind,
    assess_bundle_freshness,
    claims_by_kind,
    load_bundle_provenance,
    load_knowledge_claims,
)
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id

# One selectable field + intended section per render-mapped claim kind.
# `dependency`/`api*` are intentionally absent (see module docstring).
_KIND_FIELD_MAP: dict[KnowledgeClaimKind, tuple[str, str, list[str]]] = {
    "feature": ("aspose.feature_claims", "Key Capabilities", ["readme.capabilities"]),
    "format_support": (
        "aspose.format_support_claims",
        "Key Capabilities",
        ["readme.capabilities", "readme.at_a_glance"],
    ),
    "format": (
        "aspose.format_support_claims",
        "Key Capabilities",
        ["readme.capabilities", "readme.at_a_glance"],
    ),
    "install": ("aspose.install_claims", "Installation", ["readme.installation"]),
    "license": ("aspose.license_claims", "License", ["readme.license"]),
    "limitation": (
        "aspose.limitation_claims",
        "Scope and Limitations",
        ["readme.limitations"],
    ),
    "troubleshoot": (
        "aspose.troubleshoot_claims",
        "Development and Testing",
        ["readme.development"],
    ),
}

_NEVER_SELECTED_REASON: dict[KnowledgeClaimKind, str] = {
    "dependency": "kind_covered_by_existing_dependency_claims_field",
    "api": "kind_covered_by_api_surface_field",
    "api_class": "kind_covered_by_api_surface_field",
    "api_method": "kind_covered_by_api_surface_field",
    "api_field": "kind_covered_by_api_surface_field",
}

_MAX_SELECTED_PER_KIND = 8
_MIN_CONFIDENCE = 0.5
_STALE_CONFIDENCE_MULTIPLIER = 0.5
_MIN_CONFIDENCE_FLOOR = 0.1


class KnowledgeClaimDispositionV1(BaseModel):
    """One considered claim's complete accountability record -- the unit the
    knowledge-application evidence artifact (`knowledge_application_evidence.py`)
    is built from. Every claim this repo's fact pipeline considers for one
    product/platform gets exactly one of these; there is no code path that
    drops a claim without recording why."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    global_claim_id: str
    family: str
    platform: str
    kind: KnowledgeClaimKind
    source_revision: str | None
    freshness: BundleFreshness
    intended_section: str | None
    accepted: bool
    rejection_reason: str | None = None
    resulting_fact_field: str | None = None
    verification_state: Literal["verified", "unverified"] | None = None
    confidence: float | None = None


class KnowledgeSelectionResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    family: str
    platform: str
    source_revision: str | None
    bundle_repo_sha: str | None
    freshness: BundleFreshness
    dispositions: tuple[KnowledgeClaimDispositionV1, ...]
    fact_records: tuple[FactRecordV2, ...]

    @property
    def selected_count(self) -> int:
        return sum(1 for d in self.dispositions if d.accepted)

    @property
    def rejected_count(self) -> int:
        return sum(1 for d in self.dispositions if not d.accepted)


def _license_corroborated(claims: tuple[ImportedKnowledgeClaimV1, ...], clone_cache: Path) -> bool:
    """The one cheap, real, independently-sourced corroboration this repo can
    currently perform for imported `license` claims: does the current clone
    actually contain MIT license text? (`detect_license_file` re-reads the
    clone fresh every call -- current evidence, not cached imported data.)
    Every imported `license` claim observed in this corpus reads "Licensed
    under MIT" except one repository-specific exception (`note`, a split
    license) -- an exact MIT-text match is a deliberately narrow, honest
    corroboration signal, not a general license classifier."""

    if not claims:
        return False
    mit_claimed = any("mit" in claim.text.casefold() for claim in claims)
    if not mit_claimed:
        return False
    return detect_license_file(clone_cache) is not None


def _claim_verification(
    claim: ImportedKnowledgeClaimV1,
    *,
    freshness: BundleFreshness,
    corroborated: bool,
) -> tuple[Literal["verified", "unverified"], float]:
    if corroborated:
        return "verified", min(1.0, claim.confidence)
    if freshness == "current":
        # Still third-party-sourced, non-mechanical evidence -- capped below
        # what a mechanically-verified repository fact could reach, per the
        # "never silently promote imported claims to truth" requirement.
        return "unverified", min(0.6, claim.confidence)
    scaled = max(_MIN_CONFIDENCE_FLOOR, claim.confidence * _STALE_CONFIDENCE_MULTIPLIER)
    return "unverified", scaled


def select_knowledge_claims(
    family: str,
    platform: str,
    *,
    data_root: Path,
    clone_cache: Path,
    source_revision: str | None,
) -> KnowledgeSelectionResultV1:
    """Load, freshness-assess, corroborate, and bound-select imported
    knowledge claims for one product/platform. Deterministic: identical
    corpus + identical `source_revision` always produce identical
    dispositions and fact records (selection ranks by confidence then
    `claim_id`, never by insertion order or randomness)."""

    all_claims = load_knowledge_claims(family, platform, data_root=data_root)
    provenance = load_bundle_provenance(family, platform, data_root=data_root)
    freshness = assess_bundle_freshness(provenance, current_repo_sha=source_revision)
    license_claims = claims_by_kind(all_claims, "license")
    corroborated_license = _license_corroborated(license_claims, clone_cache)

    dispositions: list[KnowledgeClaimDispositionV1] = []
    fact_records: list[FactRecordV2] = []
    retrieved_at = datetime.now(UTC).isoformat()

    present_kinds = {claim.kind for claim in all_claims}
    for kind in sorted(present_kinds - set(_KIND_FIELD_MAP)):
        reason = _NEVER_SELECTED_REASON.get(kind, "kind_not_render_mapped")  # type: ignore[arg-type]
        for claim in claims_by_kind(all_claims, kind):  # type: ignore[arg-type]
            dispositions.append(
                KnowledgeClaimDispositionV1(
                    global_claim_id=claim.global_claim_id,
                    family=family,
                    platform=platform,
                    kind=claim.kind,
                    source_revision=source_revision,
                    freshness=freshness,
                    intended_section=None,
                    accepted=False,
                    rejection_reason=reason,
                )
            )

    # Group by target FIELD, not by raw `kind` -- `format`/`format_support`
    # deliberately share one field (`aspose.format_support_claims`); emitting
    # a fact record per kind instead of per field would produce two records
    # with the same descriptive fact_id, which ProductFactsV2 rejects as a
    # duplicate. The selection cap and corroboration rule apply per field.
    fields_present = sorted(
        {mapping[0] for kind, mapping in _KIND_FIELD_MAP.items() if kind in present_kinds}
    )
    for field in fields_present:
        field_kinds = [k for k, m in _KIND_FIELD_MAP.items() if m[0] == field]
        _, section, surfaces = _KIND_FIELD_MAP[field_kinds[0]]
        field_claims: list[ImportedKnowledgeClaimV1] = []
        for kind in field_kinds:
            field_claims.extend(claims_by_kind(all_claims, kind))  # type: ignore[arg-type]
        corroborated_field = "license" in field_kinds and corroborated_license
        ranked = sorted(field_claims, key=lambda c: (-c.confidence, c.kind, c.claim_id))
        selected_for_field: list[tuple[ImportedKnowledgeClaimV1, float]] = []
        for claim in ranked:
            state, confidence = _claim_verification(
                claim, freshness=freshness, corroborated=corroborated_field
            )
            if confidence < _MIN_CONFIDENCE and not corroborated_field:
                dispositions.append(
                    KnowledgeClaimDispositionV1(
                        global_claim_id=claim.global_claim_id,
                        family=family,
                        platform=platform,
                        kind=claim.kind,
                        source_revision=source_revision,
                        freshness=freshness,
                        intended_section=section,
                        accepted=False,
                        rejection_reason="below_confidence_threshold",
                        resulting_fact_field=field,
                        verification_state=state,
                        confidence=confidence,
                    )
                )
                continue
            if len(selected_for_field) >= _MAX_SELECTED_PER_KIND:
                dispositions.append(
                    KnowledgeClaimDispositionV1(
                        global_claim_id=claim.global_claim_id,
                        family=family,
                        platform=platform,
                        kind=claim.kind,
                        source_revision=source_revision,
                        freshness=freshness,
                        intended_section=section,
                        accepted=False,
                        rejection_reason="exceeds_selection_cap",
                        resulting_fact_field=field,
                        verification_state=state,
                        confidence=confidence,
                    )
                )
                continue
            selected_for_field.append((claim, confidence))
            dispositions.append(
                KnowledgeClaimDispositionV1(
                    global_claim_id=claim.global_claim_id,
                    family=family,
                    platform=platform,
                    kind=claim.kind,
                    source_revision=source_revision,
                    freshness=freshness,
                    intended_section=section,
                    accepted=True,
                    resulting_fact_field=field,
                    verification_state=state,
                    confidence=confidence,
                )
            )

        if not selected_for_field:
            continue
        verified_any = any(
            _claim_verification(claim, freshness=freshness, corroborated=corroborated_field)[0]
            == "verified"
            for claim, _ in selected_for_field
        )
        fact_records.append(
            FactRecordV2(
                fact_id=descriptive_fact_id(field, "aspose-knowledge"),
                field=field,
                value=[
                    {
                        "claim_id": claim.global_claim_id,
                        "kind": claim.kind,
                        "text": claim.text,
                        "confidence": confidence,
                    }
                    for claim, confidence in selected_for_field
                ],
                source=FactSourceV2(
                    source_type="approved_documentation",
                    location=f"data/imported:{family}/{platform}",
                    source_revision=provenance.repo_sha if provenance else None,
                    retrieved_at=retrieved_at,
                ),
                verification_state="verified" if verified_any else "unverified",
                authoritative_owner="aspose.org",
                confidence=max(c for _, c in selected_for_field),
                affected_surfaces=surfaces,
            )
        )

    return KnowledgeSelectionResultV1(
        family=family,
        platform=platform,
        source_revision=source_revision,
        bundle_repo_sha=provenance.repo_sha if provenance else None,
        freshness=freshness,
        dispositions=tuple(dispositions),
        fact_records=tuple(fact_records),
    )


def knowledge_claim_fact_records(
    family: str,
    platform: str,
    *,
    data_root: Path,
    clone_cache: Path,
    source_revision: str | None,
) -> list[FactRecordV2]:
    """Thin wiring seam for `facts/provider.py`: the fact records only,
    discarding the disposition ledger (recomputed separately, cheaply, and
    deterministically for evidence by `knowledge_application_evidence.py` --
    this is pure in-memory JSON filtering, no LLM/network work, so calling
    `select_knowledge_claims` twice per run costs nothing material)."""

    return list(
        select_knowledge_claims(
            family,
            platform,
            data_root=data_root,
            clone_cache=clone_cache,
            source_revision=source_revision,
        ).fact_records
    )


__all__ = [
    "KnowledgeClaimDispositionV1",
    "KnowledgeSelectionResultV1",
    "knowledge_claim_fact_records",
    "select_knowledge_claims",
]
