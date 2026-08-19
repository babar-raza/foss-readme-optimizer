"""Typed loading, provenance, and freshness assessment for the imported
aspose.org product-knowledge corpus (`data/imported/knowledge/{family}/
{platform}/merged/`).

This is the loading layer only: it reads `claims.json` (97k+ records across
31 family/platform bundles, covering the 12 `kind` values documented below)
and each bundle's `model.yaml` provenance header, and projects both into
typed, frozen Pydantic records. It performs no selection, corroboration, or
fact-graph projection -- see `aspose_knowledge_selection.py` for that.

Every claim keeps its upstream `claim_id` plus a corpus-wide
`global_claim_id` (`{family}/{platform}/{claim_id}`), since `claim_id` alone
is only unique within one family (the vendored extractor derives it from a
hash of family + content, not family + platform).

Freshness is judged against the *current* repository revision this run
actually observed (`source_revision`, threaded in from the live clone), not
wall-clock time: an imported bundle is `current` only when its recorded
`repo_sha` matches that revision exactly. This repo's own product/platform
truth already treats README prose as untrusted-until-verified evidence
(`schema_v2.py`); imported third-party knowledge gets the same discipline,
not a free pass -- see the module docstring on `aspose_knowledge_selection.py`
for how freshness turns into a verification decision.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict

KnowledgeClaimKind = Literal[
    "feature",
    "format_support",
    "format",
    "install",
    "license",
    "api",
    "api_class",
    "api_method",
    "api_field",
    "dependency",
    "limitation",
    "troubleshoot",
]

_KNOWN_KINDS: frozenset[str] = frozenset(
    (
        "feature",
        "format_support",
        "format",
        "install",
        "license",
        "api",
        "api_class",
        "api_method",
        "api_field",
        "dependency",
        "limitation",
        "troubleshoot",
    )
)


class ImportedKnowledgeClaimV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    global_claim_id: str
    claim_id: str
    family: str
    platform: str
    kind: KnowledgeClaimKind
    text: str
    confidence: float
    claim_source: str
    provenance: str
    page_role: str | None = None
    evidence: tuple[dict, ...] = ()


class KnowledgeBundleProvenanceV1(BaseModel):
    """One bundle's `model.yaml` header -- the only universal per-product
    provenance record in the corpus (18 of 31 bundles lack the redundant
    per-file `bundle_manifest.json`; every one of the 31 has `model.yaml`,
    confirmed by direct inspection of the imported tree)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    family: str
    platform: str
    product_name: str | None
    repo_sha: str | None
    repo_url: str | None
    version: str | None
    schema_version: int | None
    promoted_at: str | None
    generator_semver: str | None


def knowledge_bundle_dir(family: str, platform: str, *, data_root: Path) -> Path:
    """The one canonical bundle directory for one product -- `merged/` is the
    post-reconciliation output the rest of this repo's aspose.org adaptation
    already treats as authoritative (see `aspose_detectors.py`)."""

    return data_root / "knowledge" / family / platform / "merged"


def load_bundle_provenance(
    family: str, platform: str, *, data_root: Path
) -> KnowledgeBundleProvenanceV1 | None:
    """Read one bundle's `model.yaml`. `None` when absent, unreadable, or
    malformed -- never fatal, matching every other imported-corpus reader in
    this repo (`aspose_detectors.py`'s graceful-degradation convention)."""

    model_path = knowledge_bundle_dir(family, platform, data_root=data_root) / "model.yaml"
    if not model_path.is_file():
        return None
    try:
        raw = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(raw, dict):
        return None
    return KnowledgeBundleProvenanceV1(
        family=str(raw.get("family") or family),
        platform=str(raw.get("platform") or platform),
        product_name=raw.get("product_name"),
        repo_sha=raw.get("repo_sha") or None,
        repo_url=raw.get("repo_url") or None,
        version=raw.get("version") or None,
        schema_version=raw.get("schema_version"),
        promoted_at=raw.get("promoted_at") or None,
        generator_semver=raw.get("generator_semver") or None,
    )


def load_knowledge_claims(
    family: str, platform: str, *, data_root: Path
) -> tuple[ImportedKnowledgeClaimV1, ...]:
    """Load every well-formed claim for one product from `claims.json`.
    Malformed individual records (missing `claim_id`/`kind`/`text`, or an
    unrecognized `kind`) are skipped rather than failing the whole load --
    they are recorded as evidence of corpus drift by the caller
    (`aspose_knowledge_selection.py`'s disposition ledger), never silently
    merged into the accepted set. An absent or unparseable `claims.json`
    returns an empty tuple, not an error -- the same graceful-degradation
    contract every other imported-corpus reader in this repo uses."""

    claims_path = knowledge_bundle_dir(family, platform, data_root=data_root) / "claims.json"
    if not claims_path.is_file():
        return ()
    try:
        raw = json.loads(claims_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return ()
    if not isinstance(raw, list):
        return ()
    claims: list[ImportedKnowledgeClaimV1] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        claim_id = entry.get("claim_id")
        kind = entry.get("kind")
        text = entry.get("text")
        if not claim_id or kind not in _KNOWN_KINDS or not text:
            continue
        evidence_raw = entry.get("evidence") or []
        claims.append(
            ImportedKnowledgeClaimV1(
                global_claim_id=f"{family}/{platform}/{claim_id}",
                claim_id=str(claim_id),
                family=family,
                platform=platform,
                kind=kind,
                text=str(text),
                confidence=float(entry.get("confidence") or 0.0),
                claim_source=str(entry.get("claim_source") or "unknown"),
                provenance=str(entry.get("provenance") or "unknown"),
                page_role=entry.get("page_role"),
                evidence=tuple(item for item in evidence_raw if isinstance(item, dict)),
            )
        )
    return tuple(claims)


def claims_by_kind(
    claims: tuple[ImportedKnowledgeClaimV1, ...], kind: KnowledgeClaimKind
) -> tuple[ImportedKnowledgeClaimV1, ...]:
    return tuple(claim for claim in claims if claim.kind == kind)


BundleFreshness = Literal["current", "stale_revision", "unknown_revision"]


def assess_bundle_freshness(
    provenance: KnowledgeBundleProvenanceV1 | None, *, current_repo_sha: str | None
) -> BundleFreshness:
    """Compare the bundle's recorded upstream `repo_sha` (the commit
    aspose.org's own scout pipeline observed when this bundle was built)
    against the revision *this run* actually cloned. A mismatch means the
    imported claims may describe a product state that has since changed --
    they are never trusted merely because they exist (product/platform
    authority: current repository evidence always wins over imported
    knowledge on conflict; see `aspose_knowledge_selection.py`).

    `unknown_revision` (no provenance, no recorded repo_sha, or no current
    revision to compare against) is deliberately distinct from
    `stale_revision`: the selection layer treats both as "requires
    corroboration to reach verified," but disposition reasoning should be
    able to tell "we know this is stale" apart from "we can't tell."
    """

    if provenance is None or provenance.repo_sha is None or current_repo_sha is None:
        return "unknown_revision"
    if provenance.repo_sha == current_repo_sha:
        return "current"
    return "stale_revision"


__all__ = [
    "BundleFreshness",
    "ImportedKnowledgeClaimV1",
    "KnowledgeBundleProvenanceV1",
    "KnowledgeClaimKind",
    "assess_bundle_freshness",
    "claims_by_kind",
    "knowledge_bundle_dir",
    "load_bundle_provenance",
    "load_knowledge_claims",
]
