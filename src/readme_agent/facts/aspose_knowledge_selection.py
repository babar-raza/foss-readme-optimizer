"""Bounded, relevance-based selection over the imported aspose.org knowledge
corpus, plus the per-claim disposition ledger that makes the selection
inspectable.

This is the layer `FACT-*`/`L8-*` "verify against authoritative ground
truth, never trust a capability's output... as if it were reality"
(`docs/architecture.md`, "Trust and reconciliation doctrine") applies to for
third-party imported knowledge specifically:

* the full corpus (97k+ claims across 31 product bundles) is never handed to
  a prompt or a fact graph wholesale -- only a small, per-section-relevant
  slice is selected (`_MAX_SELECTED_PER_KIND`), ranked by real signals, not
  confidence alone: repository corroboration, whether the current README
  already states it, and product-relevant search intent all inform order
  before confidence and claim id break remaining ties (`_relevance_sort_key`);
* every raw claims.json record gets exactly one outcome -- a valid,
  considered claim, or a typed load finding
  (`aspose_knowledge_claims.load_knowledge_claims_with_findings`) -- and
  every considered claim then gets exactly one selection disposition
  (`selected` or `rejected` with a reason); there is no silent-drop path
  anywhere in this pipeline;
* **a stale or unknown-revision claim can never become output-eligible
  (selected into a fact record) without independent corroboration from
  current, live repository evidence -- confidence scaling alone is never
  sufficient.** Corroboration is real for every claim family that can
  affect output, not only license: `license` claims are compared against
  the current LICENSE file through this repo's own proven SPDX classifier
  (`license/auditor.py::classify_license_text`); every other kind is
  corroborated through `knowledge_evidence_verification.py`'s item-level,
  polarity-aware content check -- the cited evidence's actual code region
  (or, for LLM-enriched claims, its cited prose snippet) is inspected, never
  merely whether the cited file exists. A positive capability claim whose
  cited implementation is a stub (`raise NotImplementedError` or
  equivalent) is a **conflict**, not a corroboration, exactly the same as a
  genuine SPDX mismatch: current repository evidence always wins, and the
  claim is rejected outright, never merely downgraded. The mirror case also
  holds: a `limitation` claim whose cited implementation is that same stub
  is corroborated. An uncorroborated `current`-freshness claim is still
  carried at reduced, `unverified` confidence (a few days' staleness on an
  otherwise-accurate claim is common and still useful supplementary
  evidence) -- but an uncorroborated `stale`/`unknown`-revision claim is
  never selected, at any confidence.
* **one verified item can never promote its unverified siblings.** When a
  field's selected items are a genuine mix of verified and unverified (the
  expected outcome now that corroboration is polarity-aware, not merely
  file-existence-based), selection emits two separate `FactRecordV2`
  records for that field -- one holding only the verified items
  (`aspose-knowledge` qualifier, `verification_state="verified"`, the one
  the resolver picks as that field's authorizing fact) and one holding only
  the unverified items (`aspose-knowledge-supporting` qualifier,
  `verification_state="unverified"`, visible as supporting context but
  never the resolver's selected fact and therefore never composition- or
  claim-map-eligible). A field that is homogeneously verified or
  homogeneously unverified still emits exactly one record, under the
  original `aspose-knowledge` qualifier, unchanged from before.

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

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from readme_agent.facts.aspose_detectors import detect_relevant_seo_keywords
from readme_agent.facts.aspose_knowledge_claims import (
    BundleFreshness,
    ImportedKnowledgeClaimV1,
    KnowledgeBundleProvenanceV1,
    KnowledgeClaimKind,
    KnowledgeLoadFindingV1,
    assess_bundle_freshness,
    claims_by_kind,
    load_bundle_provenance,
    load_knowledge_claims_with_findings,
)
from readme_agent.facts.knowledge_evidence_verification import evidence_content_signal
from readme_agent.facts.schema_v2 import FactRecordV2, FactSourceV2, descriptive_fact_id
from readme_agent.license.auditor import classify_license_text

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
    corroboration: Literal["corroborated", "conflict", "uncorroborated"]
    intended_section: str | None
    accepted: bool
    rejection_reason: str | None = None
    resulting_fact_field: str | None = None
    verification_state: Literal["verified", "unverified"] | None = None
    confidence: float | None = None
    already_in_readme: bool = False


class KnowledgeSelectionResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    family: str
    platform: str
    source_revision: str | None
    bundle_repo_sha: str | None
    freshness: BundleFreshness
    load_findings: tuple[KnowledgeLoadFindingV1, ...]
    dispositions: tuple[KnowledgeClaimDispositionV1, ...]
    fact_records: tuple[FactRecordV2, ...]

    @property
    def selected_count(self) -> int:
        return sum(1 for d in self.dispositions if d.accepted)

    @property
    def rejected_count(self) -> int:
        return sum(1 for d in self.dispositions if not d.accepted)


def _find_license_text(clone_cache: Path) -> str | None:
    """Real current-repository LICENSE file content, whatever license it
    actually states -- the same glob convention as `aspose_detectors.py::
    detect_license_file`, but returning full text for SPDX classification
    rather than a narrow MIT-only boolean."""

    if not clone_cache.is_dir():
        return None
    candidates = (
        list(clone_cache.glob("LICENSE*"))
        + list(clone_cache.glob("*/LICENSE*"))
        + list(clone_cache.glob("license/LICENSE*"))
    )
    for candidate in candidates:
        if candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
    return None


ClaimCorroboration = Literal["corroborated", "conflict", "uncorroborated"]

# The imported corpus's license claims are terse summary labels
# ("Licensed under MIT"), never full license document text -- confirmed by
# direct inspection of every distinct license-claim string across all 31
# bundles (exactly two: "Licensed under MIT" and "Licensed under
# LicenseRef-Aspose-Split", the latter a non-SPDX proprietary reference that
# correctly has no entry here and therefore never corroborates).
# `license/auditor.py::classify_license_text` is built for full LICENSE file
# prose (it looks for a heading-style phrase like "MIT License"), so it
# applies correctly to the *current repository's* LICENSE file below, but
# not to these short claim labels -- this mapping is the terse-label side of
# the same real SPDX identifiers, not a reinvention of the classifier.
_LICENSE_CLAIM_PREFIX_RE = re.compile(r"^licensed under\s+(.+)$", re.IGNORECASE)
_CLAIM_LICENSE_TOKEN_TO_SPDX: dict[str, str] = {
    "mit": "MIT",
    "apache-2.0": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "gpl-3.0": "GPL-3.0",
    "gplv3": "GPL-3.0",
    "bsd-3-clause": "BSD-3-Clause",
    "bsd-2-clause": "BSD-2-Clause",
    "isc": "ISC",
    "mpl-2.0": "MPL-2.0",
}


def _claimed_license_spdx(claim_text: str) -> str | None:
    match = _LICENSE_CLAIM_PREFIX_RE.match(claim_text.strip())
    token = match.group(1).strip() if match else claim_text.strip()
    return _CLAIM_LICENSE_TOKEN_TO_SPDX.get(token.casefold())


def _license_claim_corroboration(
    claim: ImportedKnowledgeClaimV1, clone_cache: Path
) -> ClaimCorroboration:
    """Real SPDX comparison: the claimed license (parsed from its terse
    corpus label) and the current repository's actual LICENSE file
    (classified through this repo's own proven full-text classifier,
    `license/auditor.py::classify_license_text`) are resolved independently,
    then compared. A genuine mismatch is a conflict -- current repository
    evidence always wins -- not merely a downgrade."""

    claimed_spdx = _claimed_license_spdx(claim.text)
    if claimed_spdx is None:
        return "uncorroborated"
    current_text = _find_license_text(clone_cache)
    if current_text is None:
        return "uncorroborated"
    current_spdx = classify_license_text(current_text)
    if current_spdx is None:
        return "uncorroborated"
    return "corroborated" if current_spdx == claimed_spdx else "conflict"


def _content_claim_corroboration(
    claim: ImportedKnowledgeClaimV1, clone_cache: Path
) -> ClaimCorroboration:
    """Every non-license claim family's real corroboration path:
    item-level, polarity-aware content verification
    (`knowledge_evidence_verification.evidence_content_signal`) of the
    claim's own cited evidence, never mere file existence. A `limitation`
    claim expects negative (stub/constraint) evidence; every other kind
    expects positive (real implementation) evidence. Agreement corroborates;
    disagreement is a genuine conflict (current repository evidence always
    wins, exactly like the license path's SPDX mismatch); no resolvable
    signal at all stays uncorroborated."""

    signal = evidence_content_signal(claim.evidence, clone_cache, claim_kind=claim.kind)
    if signal == "unresolved":
        return "uncorroborated"
    expects_negative = claim.kind == "limitation"
    observed_negative = signal == "negative"
    return "corroborated" if observed_negative == expects_negative else "conflict"


def _claim_corroboration(claim: ImportedKnowledgeClaimV1, clone_cache: Path) -> ClaimCorroboration:
    if claim.kind == "license":
        return _license_claim_corroboration(claim, clone_cache)
    return _content_claim_corroboration(claim, clone_cache)


def _claim_eligibility(
    claim: ImportedKnowledgeClaimV1,
    *,
    freshness: BundleFreshness,
    corroboration: ClaimCorroboration,
) -> tuple[bool, Literal["verified", "unverified"], float, str | None]:
    """Returns (output_eligible, verification_state, confidence, ineligibility_reason).

    Current repository evidence always wins on conflict: a corroboration
    mismatch rejects the claim outright, regardless of freshness or
    confidence. Absent a conflict, a claim is output-eligible only when it
    is either independently corroborated, or the bundle itself is `current`
    -- a stale/unknown-revision, uncorroborated claim is never
    output-eligible at any confidence (confidence scaling alone is never
    sufficient, per this module's own contract)."""

    if corroboration == "conflict":
        return False, "unverified", claim.confidence, "conflicts_with_current_repository_evidence"
    if corroboration == "corroborated":
        return True, "verified", min(1.0, claim.confidence), None
    if freshness == "current":
        # Still third-party-sourced, non-mechanical evidence -- capped below
        # what a mechanically-verified repository fact could reach, per the
        # "never silently promote imported claims to truth" requirement.
        return True, "unverified", min(0.6, claim.confidence), None
    reason = (
        "stale_revision_uncorroborated"
        if freshness == "stale_revision"
        else "unknown_revision_uncorroborated"
    )
    return False, "unverified", claim.confidence, reason


def _normalize_for_relevance(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def _readme_normalized_text(clone_cache: Path) -> str:
    """The current repository's own README, normalized -- the real "does
    this section already say this" signal (section need / duplication /
    existing-README relevance). `clone_cache` already holds the live clone
    every other corroboration check in this module reads from; no new
    plumbing is required to reach it."""

    readme_path = clone_cache / "README.md"
    if not readme_path.is_file():
        return ""
    try:
        raw = readme_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    return _normalize_for_relevance(raw)


_CORROBORATION_RANK: dict[ClaimCorroboration, int] = {
    "corroborated": 2,
    "uncorroborated": 1,
    "conflict": 0,
}


def _relevance_sort_key(
    claim: ImportedKnowledgeClaimV1,
    *,
    corroboration: ClaimCorroboration,
    already_in_readme: bool,
    search_intent_match: bool,
) -> tuple[int, bool, bool, float, str, str]:
    """Genuine multi-signal relevance ranking -- not confidence+kind+id
    alone (the pseudo-relevance defect this function replaces). Real
    repository corroboration outranks everything; among equally-corroborated
    claims, information the current README does not already state outranks
    information it does (the highest-value gap to fill, not a restatement a
    visitor can already read); a claim naming one of this product's own
    relevance-filtered SEO keywords
    (`aspose_seo_keyword_facts.py`/`aspose_detectors.detect_relevant_seo_
    keywords`'s already-proven grounding logic, reused here rather than
    reinvented -- the "search intent" signal) outranks one that does not;
    confidence and a stable id break remaining ties, never decide alone."""

    return (
        -_CORROBORATION_RANK[corroboration],
        already_in_readme,
        not search_intent_match,
        -claim.confidence,
        claim.kind,
        claim.claim_id,
    )


def _knowledge_fact_record(
    field: str,
    qualifier: str,
    items: list[tuple[ImportedKnowledgeClaimV1, float]],
    *,
    verification_state: Literal["verified", "unverified"],
    family: str,
    platform: str,
    provenance: KnowledgeBundleProvenanceV1 | None,
    stable_retrieved_at: str,
    surfaces: list[str],
) -> FactRecordV2:
    return FactRecordV2(
        fact_id=descriptive_fact_id(field, qualifier),
        field=field,
        value=[
            {
                "claim_id": claim.global_claim_id,
                "kind": claim.kind,
                "text": claim.text,
                "confidence": confidence,
            }
            for claim, confidence in items
        ],
        source=FactSourceV2(
            source_type="approved_documentation",
            location=f"data/imported:{family}/{platform}",
            source_revision=provenance.repo_sha if provenance else None,
            retrieved_at=stable_retrieved_at,
        ),
        verification_state=verification_state,
        authoritative_owner="aspose.org",
        confidence=max(c for _, c in items),
        affected_surfaces=surfaces,
    )


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
    corpus + identical `source_revision` + identical current clone contents
    always produce identical dispositions and fact records (selection ranks
    by real corroboration/README-overlap/search-intent signals, breaking
    remaining ties by confidence then `claim_id` -- never by insertion order
    or randomness; see `_relevance_sort_key`)."""

    load_result = load_knowledge_claims_with_findings(family, platform, data_root=data_root)
    all_claims = load_result.claims
    provenance = load_bundle_provenance(family, platform, data_root=data_root)
    freshness = assess_bundle_freshness(provenance, current_repo_sha=source_revision)
    readme_normalized = _readme_normalized_text(clone_cache)
    seo_keywords = detect_relevant_seo_keywords(family, platform, data_root=data_root).keywords

    dispositions: list[KnowledgeClaimDispositionV1] = []
    fact_records: list[FactRecordV2] = []
    # Stable, content-derived provenance timestamp -- never wall-clock. Using
    # the bundle's own recorded promotion time (real, immutable imported
    # data) instead of "now" means two runs against the identical corpus and
    # repository revision always produce byte-identical FactRecordV2 values,
    # which ProductFactsV2.canonical_hash() depends on for no-op proof.
    stable_retrieved_at = (provenance.promoted_at if provenance else None) or "unknown"

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
                    corroboration="uncorroborated",
                    intended_section=None,
                    accepted=False,
                    rejection_reason=reason,
                )
            )

    # Group by target FIELD, not by raw `kind` -- `format`/`format_support`
    # deliberately share one field (`aspose.format_support_claims`); emitting
    # a fact record per kind instead of per field would produce two records
    # with the same descriptive fact_id, which ProductFactsV2 rejects as a
    # duplicate.
    fields_present = sorted(
        {mapping[0] for kind, mapping in _KIND_FIELD_MAP.items() if kind in present_kinds}
    )
    for field in fields_present:
        field_kinds = [k for k, m in _KIND_FIELD_MAP.items() if m[0] == field]
        _, section, surfaces = _KIND_FIELD_MAP[field_kinds[0]]
        field_claims: list[ImportedKnowledgeClaimV1] = []
        for kind in field_kinds:
            field_claims.extend(claims_by_kind(all_claims, kind))  # type: ignore[arg-type]

        # Corroboration and relevance signals are computed once per claim,
        # up front, so ranking itself can be genuinely multi-signal (Gate
        # R3: repository corroboration, existing-README overlap, and search
        # intent all inform ORDER, not just which claims later pass the
        # confidence/cap gates).
        signals: dict[str, tuple[ClaimCorroboration, bool, bool]] = {}
        for claim in field_claims:
            corroboration = _claim_corroboration(claim, clone_cache)
            claim_normalized = _normalize_for_relevance(claim.text)
            already_in_readme = bool(claim_normalized) and claim_normalized in readme_normalized
            search_intent_match = any(
                keyword.casefold() in claim.text.casefold() for keyword in seo_keywords
            )
            signals[claim.global_claim_id] = (corroboration, already_in_readme, search_intent_match)

        ranked = sorted(
            field_claims,
            key=lambda c: _relevance_sort_key(
                c,
                corroboration=signals[c.global_claim_id][0],
                already_in_readme=signals[c.global_claim_id][1],
                search_intent_match=signals[c.global_claim_id][2],
            ),
        )
        selected_for_field: list[
            tuple[ImportedKnowledgeClaimV1, float, Literal["verified", "unverified"]]
        ] = []
        seen_normalized_texts: set[str] = set()
        for claim in ranked:
            corroboration, already_in_readme, _search_intent_match = signals[claim.global_claim_id]
            eligible, state, confidence, ineligibility_reason = _claim_eligibility(
                claim, freshness=freshness, corroboration=corroboration
            )
            if not eligible:
                dispositions.append(
                    KnowledgeClaimDispositionV1(
                        global_claim_id=claim.global_claim_id,
                        family=family,
                        platform=platform,
                        kind=claim.kind,
                        source_revision=source_revision,
                        freshness=freshness,
                        corroboration=corroboration,
                        intended_section=section,
                        accepted=False,
                        rejection_reason=ineligibility_reason,
                        resulting_fact_field=field,
                        verification_state=state,
                        confidence=confidence,
                        already_in_readme=already_in_readme,
                    )
                )
                continue
            if confidence < _MIN_CONFIDENCE and corroboration != "corroborated":
                dispositions.append(
                    KnowledgeClaimDispositionV1(
                        global_claim_id=claim.global_claim_id,
                        family=family,
                        platform=platform,
                        kind=claim.kind,
                        source_revision=source_revision,
                        freshness=freshness,
                        corroboration=corroboration,
                        intended_section=section,
                        accepted=False,
                        rejection_reason="below_confidence_threshold",
                        resulting_fact_field=field,
                        verification_state=state,
                        confidence=confidence,
                        already_in_readme=already_in_readme,
                    )
                )
                continue
            normalized_text = _normalize_for_relevance(claim.text)
            if normalized_text and normalized_text in seen_normalized_texts:
                dispositions.append(
                    KnowledgeClaimDispositionV1(
                        global_claim_id=claim.global_claim_id,
                        family=family,
                        platform=platform,
                        kind=claim.kind,
                        source_revision=source_revision,
                        freshness=freshness,
                        corroboration=corroboration,
                        intended_section=section,
                        accepted=False,
                        rejection_reason="duplicate_of_higher_ranked_claim",
                        resulting_fact_field=field,
                        verification_state=state,
                        confidence=confidence,
                        already_in_readme=already_in_readme,
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
                        corroboration=corroboration,
                        intended_section=section,
                        accepted=False,
                        rejection_reason="exceeds_selection_cap",
                        resulting_fact_field=field,
                        verification_state=state,
                        confidence=confidence,
                        already_in_readme=already_in_readme,
                    )
                )
                continue
            if normalized_text:
                seen_normalized_texts.add(normalized_text)
            selected_for_field.append((claim, confidence, state))
            dispositions.append(
                KnowledgeClaimDispositionV1(
                    global_claim_id=claim.global_claim_id,
                    family=family,
                    platform=platform,
                    kind=claim.kind,
                    source_revision=source_revision,
                    freshness=freshness,
                    corroboration=corroboration,
                    intended_section=section,
                    accepted=True,
                    resulting_fact_field=field,
                    verification_state=state,
                    confidence=confidence,
                    already_in_readme=already_in_readme,
                )
            )

        if not selected_for_field:
            continue
        verified_items = [
            (claim, confidence)
            for claim, confidence, state in selected_for_field
            if state == "verified"
        ]
        unverified_items = [
            (claim, confidence)
            for claim, confidence, state in selected_for_field
            if state == "unverified"
        ]
        # One verified item must never promote its unverified siblings
        # (the `verified_any` laundering defect): when both are present,
        # emit two records -- the resolver's precedence rules
        # (`resolution.py::_VERIFICATION_PRECEDENCE`) always pick the
        # verified one as this field's authorizing fact, leaving the
        # unverified one visible as supporting context but never
        # composition- or claim-map-eligible. The primary record keeps the
        # original `aspose-knowledge` qualifier so a field that is (as
        # today) homogeneously one state or the other is fully unchanged.
        primary_state: Literal["verified", "unverified"]
        primary_items: list[tuple[ImportedKnowledgeClaimV1, float]]
        if verified_items:
            primary_state, primary_items = "verified", verified_items
        else:
            primary_state, primary_items = "unverified", unverified_items
        fact_records.append(
            _knowledge_fact_record(
                field,
                "aspose-knowledge",
                primary_items,
                verification_state=primary_state,
                family=family,
                platform=platform,
                provenance=provenance,
                stable_retrieved_at=stable_retrieved_at,
                surfaces=surfaces,
            )
        )
        if verified_items and unverified_items:
            fact_records.append(
                _knowledge_fact_record(
                    field,
                    "aspose-knowledge-supporting",
                    unverified_items,
                    verification_state="unverified",
                    family=family,
                    platform=platform,
                    provenance=provenance,
                    stable_retrieved_at=stable_retrieved_at,
                    surfaces=surfaces,
                )
            )

    return KnowledgeSelectionResultV1(
        family=family,
        platform=platform,
        source_revision=source_revision,
        bundle_repo_sha=provenance.repo_sha if provenance else None,
        freshness=freshness,
        load_findings=load_result.findings,
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
    "ClaimCorroboration",
    "KnowledgeClaimDispositionV1",
    "KnowledgeSelectionResultV1",
    "knowledge_claim_fact_records",
    "select_knowledge_claims",
]
