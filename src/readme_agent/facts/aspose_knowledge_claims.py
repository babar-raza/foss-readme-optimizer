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


KnowledgeLoadFindingType = Literal[
    "imported_corpus_root_missing",
    "product_platform_not_in_imported_corpus",
    "expected_bundle_missing",
    "claims_file_missing",
    "json_parse_error",
    "wrong_top_level_shape",
    "invalid_record",
    "empty_valid_collection",
]


class KnowledgeLoadFindingV1(BaseModel):
    """One accountable outcome from attempting to load one product's claims.
    Every raw record and every failure mode gets exactly one of these --
    there is no `continue` in this module that does not also produce a
    finding. `agent_fixable=True` marks a real corpus-integrity gap
    (expected data is missing/corrupt); `agent_fixable=False` marks a
    condition that is not a defect (e.g. a product genuinely outside the
    imported corpus's own scope, or a bundle whose claims.json is legitimately
    empty)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    finding_type: KnowledgeLoadFindingType
    family: str
    platform: str
    detail: str
    raw_index: int | None = None
    agent_fixable: bool


class KnowledgeLoadResultV1(BaseModel):
    """The complete, accountable outcome of loading one product's claims:
    every valid claim plus every finding for everything that was not a
    valid, selectable claim. `len(claims)` alone can never answer "was
    anything silently dropped" -- `findings` always can."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    family: str
    platform: str
    claims: tuple[ImportedKnowledgeClaimV1, ...]
    findings: tuple[KnowledgeLoadFindingV1, ...]


def _expected_family_platforms(data_root: Path) -> frozenset[tuple[str, str]] | None:
    """The imported corpus's own recorded scope at import time
    (`data/imported/data/products.json`, aspose.org's own product registry
    snapshot -- 31 entries, one per bundle, confirmed 1:1 with the actual
    31 `knowledge/` bundles present). `None` when this registry itself is
    unavailable (never fatal -- callers fall back to "cannot determine
    whether this was expected")."""

    registry_path = data_root / "data" / "products.json"
    if not registry_path.is_file():
        return None
    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, list):
        return None
    pairs: set[tuple[str, str]] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        family = entry.get("family")
        platform = entry.get("platform")
        if isinstance(family, str) and isinstance(platform, str):
            pairs.add((family, platform))
    return frozenset(pairs)


def load_knowledge_claims_with_findings(
    family: str, platform: str, *, data_root: Path
) -> KnowledgeLoadResultV1:
    """The authoritative, fail-closed loader: every raw claims.json entry and
    every failure mode along the way produces exactly one accountable
    outcome -- valid+considered, or a typed `KnowledgeLoadFindingV1` with a
    real reason. Nothing disappears silently."""

    def _result(
        claims: tuple[ImportedKnowledgeClaimV1, ...],
        findings: list[KnowledgeLoadFindingV1],
    ) -> KnowledgeLoadResultV1:
        return KnowledgeLoadResultV1(
            family=family, platform=platform, claims=claims, findings=tuple(findings)
        )

    def _finding(
        finding_type: KnowledgeLoadFindingType, detail: str, *, agent_fixable: bool
    ) -> KnowledgeLoadFindingV1:
        return KnowledgeLoadFindingV1(
            finding_type=finding_type,
            family=family,
            platform=platform,
            detail=detail,
            agent_fixable=agent_fixable,
        )

    if not data_root.is_dir():
        return _result(
            (),
            [
                _finding(
                    "imported_corpus_root_missing",
                    f"imported corpus root does not exist: {data_root}",
                    agent_fixable=True,
                )
            ],
        )

    expected = _expected_family_platforms(data_root)
    if expected is not None and (family, platform) not in expected:
        return _result(
            (),
            [
                _finding(
                    "product_platform_not_in_imported_corpus",
                    f"{family}/{platform} is not in the imported corpus's own recorded "
                    "scope (data/imported/data/products.json) -- never expected to have "
                    "knowledge, not a load failure",
                    agent_fixable=False,
                )
            ],
        )

    bundle_dir = knowledge_bundle_dir(family, platform, data_root=data_root)
    if not bundle_dir.is_dir():
        return _result(
            (),
            [
                _finding(
                    "expected_bundle_missing",
                    f"expected bundle directory missing: {bundle_dir}",
                    agent_fixable=True,
                )
            ],
        )

    claims_path = bundle_dir / "claims.json"
    if not claims_path.is_file():
        return _result(
            (),
            [
                _finding(
                    "claims_file_missing",
                    f"expected claims.json missing: {claims_path}",
                    agent_fixable=True,
                )
            ],
        )

    try:
        raw = json.loads(claims_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return _result(
            (),
            [
                _finding(
                    "json_parse_error",
                    f"{claims_path}: {type(exc).__name__}: {exc}",
                    agent_fixable=True,
                )
            ],
        )

    if not isinstance(raw, list):
        return _result(
            (),
            [
                _finding(
                    "wrong_top_level_shape",
                    f"{claims_path}: expected a JSON list, got {type(raw).__name__}",
                    agent_fixable=True,
                )
            ],
        )

    claims: list[ImportedKnowledgeClaimV1] = []
    findings: list[KnowledgeLoadFindingV1] = []
    for index, entry in enumerate(raw):
        if not isinstance(entry, dict):
            findings.append(
                KnowledgeLoadFindingV1(
                    finding_type="invalid_record",
                    family=family,
                    platform=platform,
                    detail=f"record is not a JSON object, got {type(entry).__name__}",
                    raw_index=index,
                    agent_fixable=True,
                )
            )
            continue
        claim_id = entry.get("claim_id")
        kind = entry.get("kind")
        text = entry.get("text")
        if not claim_id or kind not in _KNOWN_KINDS or not text:
            reason = []
            if not claim_id:
                reason.append("missing claim_id")
            if kind not in _KNOWN_KINDS:
                reason.append(f"unrecognized kind {kind!r}")
            if not text:
                reason.append("missing text")
            findings.append(
                KnowledgeLoadFindingV1(
                    finding_type="invalid_record",
                    family=family,
                    platform=platform,
                    detail="; ".join(reason),
                    raw_index=index,
                    agent_fixable=True,
                )
            )
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

    if not raw:
        findings.append(
            _finding(
                "empty_valid_collection",
                f"{claims_path} parsed successfully but contains zero records",
                agent_fixable=False,
            )
        )

    return _result(tuple(claims), findings)


def load_knowledge_claims(
    family: str, platform: str, *, data_root: Path
) -> tuple[ImportedKnowledgeClaimV1, ...]:
    """Compatibility wrapper over `load_knowledge_claims_with_findings()` for
    callers that only need the valid claims, not the accountability ledger.
    Prefer the richer function directly wherever findings matter (selection,
    evidence)."""

    return load_knowledge_claims_with_findings(family, platform, data_root=data_root).claims


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
    "KnowledgeLoadFindingType",
    "KnowledgeLoadFindingV1",
    "KnowledgeLoadResultV1",
    "assess_bundle_freshness",
    "claims_by_kind",
    "knowledge_bundle_dir",
    "load_bundle_provenance",
    "load_knowledge_claims",
    "load_knowledge_claims_with_findings",
]
