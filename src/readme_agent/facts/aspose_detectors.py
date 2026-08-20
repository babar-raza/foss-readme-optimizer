"""T4 -- adapted detector logic from the vendored aspose.org factpack builder.

Per this plan's own capability-reuse table (Annex A / §3): the run/state-
machine orchestration in `readme_refresh_run.py` (locking, session identity,
atomic writes) is explicitly **not ported** -- this repo owns its own
equivalent state machinery. Only the individual, mostly-pure `_detect_*`
helper functions are reused, and only by extracting their logic into
standalone functions that take an explicit `data_root: Path` rather than
depending on that module's global, test-injection-only `_repo_root` state
(discovered while probing T4: importing the whole orchestration module pulls
in `session_identity`/`advisory_lock`/`core.fs`, none of which belong here).

**Honest scope**: this covers 9 of the vendored module's 11 `_detect_*`
functions -- the ones verified self-contained or tractably adaptable (pure
path/JSON/YAML logic plus, for the enterprise-link detector, the already-
vendored `backlink_targets.py`). `detect_homepage_link` always returns
`verified=False` in this repo, honestly: it checks for a real file under
`content/products.aspose.org/`, the Hugo website-content tree, which was
never in TD-01's authorized lean-import scope (a large, separate tree, out
of proportion to a "check-battery corpus" import) -- the vendored logic's
own graceful-degradation contract ("never invent a URL not backed by
verified data") makes this the correct, safe behavior, not a bug.
The remaining 2 (`_detect_available_badges` -- has its own language-
version-template table and per-ecosystem branching; `_detect_archetype_
entry_raw` -- a near-duplicate of the already-adapted `detect_archetype`
returning the full raw row instead of a filtered view) were not extracted
this session.

A 12th piece, `detect_api_public_surface`, was added in a later session:
not one of `readme_refresh_run.py`'s `_detect_*` functions, but the ground
truth behind them -- `knowledge/{family}/{platform}/merged/api_surface.json`,
the real, per-language, source-level static-analysis output of aspose.org's
own `scripts/pipeline/extraction/scout.py`. This data was already imported
into `data/imported/knowledge/` by an earlier T1B import but never wired to
a fact detector; `api.public_surface` was populated for Python only until
now (this repo's own separate AST extractor). See its own docstring for the
full trace.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

# aspose_detectors.py lives at src/readme_agent/facts/ -- parents[2] is src/.
_VENDORED_PIPELINE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "readme_agent"
    / "vendored_asposeorg"
    / "scripts"
    / "pipeline"
)
_VENDORED_LIB_ROOT = _VENDORED_PIPELINE_ROOT / "lib"
_VENDORED_FOSS_ROOT = _VENDORED_PIPELINE_ROOT / "commands" / "foss"


def _ensure_vendored_on_path() -> None:
    # `_VENDORED_PIPELINE_ROOT` (the parent of `lib/`) must be on sys.path,
    # not `lib/` itself -- readme_refresh_checks.py does `from lib.
    # api_table_dupes import ...`, resolving `lib` as an (implicit
    # namespace) package relative to its parent directory.
    for path in (str(_VENDORED_PIPELINE_ROOT), str(_VENDORED_LIB_ROOT), str(_VENDORED_FOSS_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)


def _load_backlink_targets_module() -> Any:
    _ensure_vendored_on_path()
    import backlink_targets  # noqa: PLC0415 -- deliberately lazy; see module docstring

    return backlink_targets


def _load_readme_refresh_checks_module() -> Any:
    _ensure_vendored_on_path()
    import readme_refresh_checks  # noqa: PLC0415 -- deliberately lazy; see module docstring

    return readme_refresh_checks


class ArchetypeDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    archetype: str
    archetype_basis: str


def detect_archetype(family: str, platform: str, *, data_root: Path) -> ArchetypeDetectionV1:
    """Adapted from `_detect_archetype` (readme_refresh_run.py)."""

    path = data_root / "data" / "diagram_archetypes.json"
    if not path.is_file():
        return ArchetypeDetectionV1(
            archetype="transform", archetype_basis="default (no override entry)"
        )
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        if row.get("family") == family and row.get("platform") == platform:
            return ArchetypeDetectionV1(
                archetype=row["archetype"], archetype_basis=row.get("evidence", "")
            )
    return ArchetypeDetectionV1(
        archetype="transform", archetype_basis="default (no override entry)"
    )


class SeoKeywordsDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    keywords: tuple[str, ...]
    source_path: str | None
    entry_found: bool


def detect_seo_keywords(family: str, platform: str, *, data_root: Path) -> SeoKeywordsDetectionV1:
    """Adapted from `_detect_seo_keywords` (readme_refresh_run.py)."""

    path = data_root / "keywords" / f"{family}.json"
    if not path.is_file():
        return SeoKeywordsDetectionV1(keywords=(), source_path=None, entry_found=False)
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return SeoKeywordsDetectionV1(keywords=(), source_path=None, entry_found=False)
    platform_source = f"content/products.aspose.org/en/{family}/{platform}/_index.md"
    family_source = f"content/products.aspose.org/en/{family}/_index.md"
    platform_entry = None
    family_entry = None
    for entry in entries:
        source_path = entry.get("sourcePath")
        if source_path == platform_source:
            platform_entry = entry
        elif source_path == family_source:
            family_entry = entry
    chosen = platform_entry or family_entry
    if chosen is None:
        return SeoKeywordsDetectionV1(keywords=(), source_path=None, entry_found=False)
    return SeoKeywordsDetectionV1(
        keywords=tuple(chosen.get("keywords", [])),
        source_path=chosen.get("sourcePath"),
        entry_found=True,
    )


class RelevantSeoKeywordsDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    keywords: tuple[str, ...]
    source_path: str | None
    entry_found: bool
    dropped_wrong_platform: tuple[str, ...]
    dropped_ungrounded: tuple[str, ...]
    dropped_cap_exceeded: tuple[str, ...]


def detect_relevant_seo_keywords(
    family: str,
    platform: str,
    *,
    data_root: Path,
    known_format_names: frozenset[str] | None = None,
) -> RelevantSeoKeywordsDetectionV1:
    """Filter `detect_seo_keywords()`'s raw list through the vendored,
    incident-hardened relevance logic (TC-HARDEN-39, MT037,
    `filter_relevant_seo_keywords`): drops any phrase naming a
    platform/language other than this product's own, keeps only phrases
    grounded in the family name, a known real format name, or an
    established capability-verb/framing term, and caps the result at 6 --
    "do not over-stuff, only use related keywords" as real code, not
    composition-time restraint alone.

    Every dropped keyword is recorded with its real reason -- never
    silently discarded -- by replicating the vendored function's own
    stop-early-at-6 iteration order instead of reverse-deriving reasons
    from a before/after set difference, which would mislabel a genuinely
    grounded, right-platform keyword that only missed the cap because
    earlier keywords already filled it (the vendored function evaluates
    keywords strictly in file order and stops calling either check the
    moment 6 are kept; a set-difference reconstruction would wrongly call
    such a keyword "ungrounded")."""

    raw = detect_seo_keywords(family, platform, data_root=data_root)
    if not raw.entry_found or not raw.keywords:
        return RelevantSeoKeywordsDetectionV1(
            keywords=(),
            source_path=raw.source_path,
            entry_found=raw.entry_found,
            dropped_wrong_platform=(),
            dropped_ungrounded=(),
            dropped_cap_exceeded=(),
        )
    checks = _load_readme_refresh_checks_module()
    known_formats = known_format_names or frozenset()
    kept: list[str] = []
    wrong_platform: list[str] = []
    ungrounded: list[str] = []
    cap_exceeded: list[str] = []
    for keyword in raw.keywords:
        if len(kept) >= 6:
            cap_exceeded.append(keyword)
            continue
        if checks._seo_keyword_wrong_platform(keyword, platform):
            wrong_platform.append(keyword)
            continue
        lowered = keyword.lower()
        grounded = (
            family.lower() in lowered
            or any(term in lowered for term in checks._SEO_KEYWORD_RELEVANCE_TERMS)
            or any(fmt.lower() in lowered for fmt in known_formats)
        )
        if grounded:
            kept.append(keyword)
        else:
            ungrounded.append(keyword)
    return RelevantSeoKeywordsDetectionV1(
        keywords=tuple(kept),
        source_path=raw.source_path,
        entry_found=True,
        dropped_wrong_platform=tuple(wrong_platform),
        dropped_ungrounded=tuple(ungrounded),
        dropped_cap_exceeded=tuple(cap_exceeded),
    )


class InstallInfoDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str
    registry_type: str | None = None
    # The real data (verified against data/imported/data/package_registry.json,
    # not assumed from the vendored code's untyped dict) is itself a structured
    # object (group_id/artifact_id/version/repo_sha for Maven, etc.), not a
    # scalar -- kept as dict[str, Any] rather than over-fitting one registry
    # type's shape.
    candidate: dict | None = None
    published: bool = False
    fallback_text_required: bool = False


def detect_install_info(family: str, platform: str, *, data_root: Path) -> InstallInfoDetectionV1:
    """Adapted from `_detect_install_info` (readme_refresh_run.py)."""

    path = data_root / "data" / "package_registry.json"
    if not path.is_file():
        return InstallInfoDetectionV1(source="package_registry_missing")
    registry = json.loads(path.read_text(encoding="utf-8"))
    family_entry = registry.get(family, {})
    platform_entry = family_entry.get(platform) if isinstance(family_entry, dict) else None
    if not platform_entry:
        return InstallInfoDetectionV1(
            source="no_package_registry_entry", fallback_text_required=True
        )
    verification = platform_entry.get("verification", {})
    published = bool(verification.get("published", False))
    return InstallInfoDetectionV1(
        source="package_registry.json",
        registry_type=platform_entry.get("registry_type"),
        candidate=platform_entry.get("candidate"),
        published=published,
        fallback_text_required=not published,
    )


class LicenseFileDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str


def detect_license_file(clone_cache: Path) -> LicenseFileDetectionV1 | None:
    """Adapted from `_detect_license_file` (readme_refresh_run.py). Widened
    match (200-char case-insensitive substring, not a 20-char exact prefix)
    is preserved verbatim from the vendored logic -- it fixed a real
    confirmed defect (TC-HARDEN-20) and this adaptation must not regress it.
    """

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
                head = candidate.read_text(encoding="utf-8", errors="ignore")[:200]
            except OSError:
                continue
            if "mit license" in head.lower():
                return LicenseFileDetectionV1(
                    relative_path=str(candidate.relative_to(clone_cache)).replace("\\", "/")
                )
    return None


class EnterpriseLinkDetectionV1(BaseModel):
    """Adapted from `_detect_enterprise_link` + `_classify_enterprise_relationship`
    (readme_refresh_run.py). `relationship`/`public_platform` implement the
    MT044 rule this repo's own TW-... T10 anchor-destination check enforces
    from the opposite direction (T10 catches a wrong anchor after the fact;
    this detector computes the correct relationship up front so a correct
    anchor can be composed in the first place) -- `public_platform` is always
    the normalized, implementation-neutral platform name; the bridge/suffix
    information is discarded entirely and never surfaced, matching MT044's
    permanent rule."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str | None
    link_type: str | None
    fallback_reason: str | None
    # Verified against the real backlink_targets.target_map_age_days() output:
    # a fractional number of days (elapsed time), not a whole-day count.
    target_map_age_days: float | None
    target_map_stale: bool | None
    relationship: str | None
    public_platform: str | None


def _load_canonical_overrides(data_root: Path) -> dict | None:
    """Adapted from `_load_canonical_overrides` (readme_refresh_run.py)."""

    path = data_root / "data" / "backlinks" / "platform_canonical_overrides.yaml"
    if not path.is_file():
        return None
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _classify_enterprise_relationship(
    source_platform: str, url: str | None, *, backlink_targets: Any, checks: Any
) -> tuple[str | None, str | None]:
    """Adapted verbatim (logic unchanged) from `_classify_enterprise_relationship`
    (readme_refresh_run.py) -- see that function's docstring in the vendored
    source for the full, incident-backed derivation of this classification
    rule. Returns (relationship, public_platform) instead of a dict."""

    if not url:
        return None, None
    path = url.split("products.aspose.com/", 1)[-1].strip("/")
    parts = path.split("/", 1)
    if len(parts) < 2 or not parts[1]:
        return "family", None
    segment = parts[1].split("/", 1)[0]

    if "-" in segment:
        normalized = backlink_targets.PLATFORM_ALIASES.get(segment)
        public_platform = checks._PLATFORM_DISPLAY_NAMES.get(normalized) if normalized else None
        if not public_platform:
            return "unresolved", None
        return "platform", public_platform

    normalized_dest = backlink_targets.PLATFORM_ALIASES.get(segment, segment)
    normalized_source = backlink_targets.PLATFORM_ALIASES.get(source_platform, source_platform)
    if normalized_dest != normalized_source:
        return "unresolved", None
    return "platform", checks._PLATFORM_DISPLAY_NAMES.get(normalized_dest)


def detect_enterprise_link(
    family: str, platform: str, *, data_root: Path
) -> EnterpriseLinkDetectionV1:
    """Adapted from `_detect_enterprise_link` (readme_refresh_run.py). Reuses
    the already-vendored `backlink_targets.py` (T1B) for URL/target
    resolution; deliberately does NOT reuse its
    `build_enterprise_anchor_suffix()` (a different, rejected anchor-text
    convention for this project -- "Enterprise Edition" portfolio-wide is
    this repo's own binding rule)."""

    backlink_targets = _load_backlink_targets_module()
    checks = _load_readme_refresh_checks_module()
    try:
        target_map = backlink_targets.load_target_map(data_root)
    except (FileNotFoundError, ValueError) as exc:
        return EnterpriseLinkDetectionV1(
            url=None,
            link_type=None,
            fallback_reason=f"target_map_unavailable: {exc}",
            target_map_age_days=None,
            target_map_stale=None,
            relationship=None,
            public_platform=None,
        )
    canonical_overrides = _load_canonical_overrides(data_root)
    url, target_type, _subdomain, fallback_reason = backlink_targets.resolve_backlink(
        family,
        platform,
        source_subdomain="readme-refresh",
        target_map=target_map,
        canonical_overrides=canonical_overrides,
    )
    age_days = backlink_targets.target_map_age_days(target_map)
    relationship, public_platform = _classify_enterprise_relationship(
        platform, url, backlink_targets=backlink_targets, checks=checks
    )
    return EnterpriseLinkDetectionV1(
        url=url,
        link_type=target_type,
        fallback_reason=fallback_reason,
        target_map_age_days=age_days,
        target_map_stale=bool(age_days is not None and age_days > backlink_targets.STALE_WARN_DAYS),
        relationship=relationship,
        public_platform=public_platform,
    )


class DevTestArtifactV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    relative_path: str
    kind: str
    section: str


def detect_dev_test_artifacts(clone_cache: Path) -> tuple[DevTestArtifactV1, ...]:
    """Adapted verbatim from `_detect_dev_test_artifacts` (readme_refresh_run.py) --
    a deliberately narrow, real-audit-confirmed allowlist (never guessed at),
    plus the case-insensitive AGENTS.md discovery fix and the pytest-cache
    exclusion, both preserved exactly."""

    if not clone_cache.is_dir():
        return ()
    found: list[DevTestArtifactV1] = []
    seen_real_paths: set[str] = set()

    def _add(path: Path, kind: str, section: str) -> None:
        if not path.is_file():
            return
        try:
            real_name = next(p.name for p in path.parent.iterdir() if p.name == path.name)
        except StopIteration:
            return
        if real_name != path.name:
            return
        relative_path = str(path.relative_to(clone_cache)).replace("\\", "/")
        if relative_path in seen_real_paths:
            return
        seen_real_paths.add(relative_path)
        found.append(DevTestArtifactV1(relative_path=relative_path, kind=kind, section=section))

    try:
        agents_entries = list(clone_cache.iterdir())
    except OSError:
        agents_entries = []
    for entry in agents_entries:
        if entry.is_file() and entry.name.lower() == "agents.md":
            _add(entry, "agents_guide", "Documentation & Resources")
            break
    for name in ("CONTRIBUTING.md", "CONTRIBUTING.rst"):
        _add(clone_cache / name, "contributing_guide", "Documentation & Resources")
    _add(clone_cache / "PUBLIC_API.md", "public_api_doc", "Documentation & Resources")
    _add(clone_cache / "CHANGELOG.md", "changelog", "Documentation & Resources")
    _add(clone_cache / "PUBLISHING.md", "publishing_guide", "Documentation & Resources")

    docs_dir = clone_cache / "docs"
    if docs_dir.is_dir():
        for md in sorted(docs_dir.glob("*.md")):
            _add(md, "docs_guide", "Documentation & Resources")

    workflows_dir = clone_cache / ".github" / "workflows"
    if workflows_dir.is_dir():
        for wf in sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml")):
            _add(wf, "ci_workflow", "Development and Testing")

    _add(clone_cache / "examples" / "README.md", "examples_readme", "Development and Testing")

    for child in sorted(clone_cache.iterdir()):
        if child.is_dir() and "test" in child.name.lower() and not child.name.startswith("."):
            _add(child / "README.md", "test_dir_readme", "Development and Testing")

    return tuple(found)


def detect_capability_dependencies(
    family: str, platform: str, *, data_root: Path
) -> tuple[list[str], ...] | None:
    """Adapted from `_detect_capability_dependencies` (readme_refresh_run.py).
    `None` means "never traced" -- distinct from an empty tuple ("confirmed
    independent, no pipeline edges"), preserved as the vendored logic's own
    documented distinction, not collapsed."""

    path = data_root / "data" / "diagram_capability_dependencies.json"
    if not path.is_file():
        return None
    rows = json.loads(path.read_text(encoding="utf-8"))
    for row in rows:
        if row.get("family") == family and row.get("platform") == platform:
            return tuple(row.get("pipeline_edges", []))
    return None


class HomepageLinkDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str
    verified: bool


def detect_homepage_link(family: str, platform: str, *, data_root: Path) -> HomepageLinkDetectionV1:
    """Adapted from `_detect_homepage_link` (readme_refresh_run.py). Honest
    scope note (module docstring): `content/products.aspose.org/` was never
    imported (TD-01's lean-import scope excluded the website-content tree),
    so `verified` is always False in this repo today -- the vendored
    logic's own "never invent a URL not backed by verified data" contract
    makes that the correct, safe behavior when the evidence isn't present,
    not a defect in this adaptation."""

    url = f"https://products.aspose.org/{family}/{platform}/"
    index_path = (
        data_root / "content" / "products.aspose.org" / "en" / family / platform / "_index.md"
    )
    return HomepageLinkDetectionV1(url=url, verified=index_path.is_file())


_MODEL_YAML_REPO_SHA_RE = re.compile(r"^repo_sha:\s*(\S+)\s*$", re.MULTILINE)


class DependencyClaimsDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    claims: tuple[dict, ...]
    repo_sha: str | None


def detect_dependency_claims(
    family: str, platform: str, *, data_root: Path
) -> DependencyClaimsDetectionV1:
    """Adapted from `_detect_dependency_claims` (readme_refresh_run.py).
    Reads the already-imported `knowledge/{family}/{platform}/merged/` tree
    (T1B); never fatal on absence, matching every other detector's
    graceful-degradation posture."""

    merged_dir = data_root / "knowledge" / family / platform / "merged"
    claims: list[dict] = []
    claims_path = merged_dir / "claims.json"
    if claims_path.is_file():
        try:
            raw = json.loads(claims_path.read_text(encoding="utf-8"))
            all_claims = raw if isinstance(raw, list) else raw.get("claims", [])
            claims = [c for c in all_claims if c.get("kind") == "dependency"]
        except (json.JSONDecodeError, OSError):
            claims = []
    repo_sha = None
    model_path = merged_dir / "model.yaml"
    if model_path.is_file():
        try:
            match = _MODEL_YAML_REPO_SHA_RE.search(model_path.read_text(encoding="utf-8"))
            repo_sha = match.group(1) if match else None
        except OSError:
            repo_sha = None
    return DependencyClaimsDetectionV1(claims=tuple(claims), repo_sha=repo_sha)


class ApiSurfaceMemberV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    doc: str
    signature: str


class ApiSurfaceClassV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str
    kind: str
    methods: tuple[ApiSurfaceMemberV1, ...]
    properties: tuple[ApiSurfaceMemberV1, ...]


class ApiSurfaceModuleV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    module: str
    classes: tuple[ApiSurfaceClassV1, ...]


class ApiPublicSurfaceDetectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    modules: tuple[ApiSurfaceModuleV1, ...]
    model_sha: str | None


_KIND_TO_MODULE = {
    "class_declaration": "Core API",
    "class_definition": "Core API",
    "struct_declaration": "Core API",
    "interface_declaration": "Interfaces",
    "enum_declaration": "Enumerations",
    "enum_definition": "Enumerations",
    "function": "Core API",
}

# The corpus's own visibility vocabulary varies by extraction pass -- "public"/
# "conventional" (3D), "exported"/"conventional" (Note), "public"-or-absent
# (Barcode) -- confirmed by direct inspection of all three real bundles.
_PUBLIC_VISIBILITY_LABELS = frozenset({"public", "exported"})
_PRIVATE_VISIBILITY_LABELS = frozenset({"conventional", "internal", "private"})


def _entry_is_publicly_reachable(entry: dict) -> bool:
    """Resolve public reachability from the corpus's own visibility label,
    never from the separate `reachable` field: direct inspection of the
    real 3D, Note, and Barcode bundles shows `reachable` is either uniformly
    `False` (3D, all 327 entries) or entirely absent (Note, Barcode) --
    never a discriminating signal, so requiring it true unconditionally
    rejects the entire bundle regardless of real visibility. A missing
    visibility label falls back to the symbol's own name not being
    conventionally private (leading underscore) -- a generic Python/most
    C-family convention, not a per-family or per-repository special case."""

    visibility = entry.get("visibility")
    if isinstance(visibility, str):
        normalized = visibility.strip().casefold()
        if normalized in _PUBLIC_VISIBILITY_LABELS:
            return True
        if normalized in _PRIVATE_VISIBILITY_LABELS:
            return False
    name = entry.get("name")
    return isinstance(name, str) and bool(name) and not name.startswith("_")


def _member_signature(entry: dict) -> str:
    params = entry.get("params") or []
    param_text = ", ".join(
        f"{param.get('name', '')}: {param['type']}" if param.get("type") else param.get("name", "")
        for param in params
    )
    return_type = entry.get("return_type") or ""
    suffix = f" -> {return_type}" if return_type else ""
    return f"{entry.get('name', '')}({param_text}){suffix}"


def detect_api_public_surface(
    family: str, platform: str, *, data_root: Path
) -> ApiPublicSurfaceDetectionV1 | None:
    """Adapted from `knowledge/{family}/{platform}/merged/api_surface.json` -- not one of
    readme_refresh_run.py's original 11 `_detect_*` functions this module's docstring tracks, but
    the ground-truth output of aspose.org's own `scripts/pipeline/extraction/scout.py`: a real,
    per-language, source-level static-analysis extractor (confirmed live: entries cite the exact
    `.cs`/`.java`/etc. source file and line number for every class, method, and property). This
    is a 12th piece of reused Aspose.org logic, and the most direct one -- `api_surface.json` was
    already imported into this repo's own `data/imported/knowledge/` tree by an earlier T1B
    import (commit 3e3fd55fb6) but never wired to a fact detector; `api.public_surface` was
    populated for Python only until now, via this repo's own separate AST-based extractor
    (`curated_python_public_surface.py`). No new data import was needed to close this gap for the
    other 6 platforms -- the real, verified per-class data was already committed here, unused.

    Deliberately reads `merged/api_surface.json`, not the `scout/` stage sibling some products
    also carry -- `merged/` is the post-reconciliation output the rest of aspose.org's own
    pipeline treats as authoritative (`readme_refresh_run.py`'s own `_detect_dependency_claims`
    reads the same `merged/` directory for the same reason).

    `None` when no `api_surface.json` exists for this family/platform, it fails to parse, or it
    contains zero publicly reachable entries."""

    surface_path = data_root / "knowledge" / family / platform / "merged" / "api_surface.json"
    if not surface_path.is_file():
        return None
    try:
        entries = json.loads(surface_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(entries, list):
        return None
    by_module: dict[str, list[ApiSurfaceClassV1]] = {}
    model_sha: str | None = None
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("name"):
            continue
        if not _entry_is_publicly_reachable(entry):
            continue
        module = _KIND_TO_MODULE.get(entry.get("kind", ""), "Core API")
        # A bare top-level function entry carries its own params/return_type
        # directly (never nested under "methods"); without this, a function
        # entry silently projects to an empty, useless zero-member class row.
        methods_raw = entry.get("methods") or ([entry] if entry.get("kind") == "function" else [])
        methods = tuple(
            ApiSurfaceMemberV1(
                name=method.get("name", ""),
                doc=method.get("doc", ""),
                signature=_member_signature(method),
            )
            for method in methods_raw
            if method.get("name")
        )
        properties = tuple(
            ApiSurfaceMemberV1(
                name=prop.get("name", ""),
                doc=prop.get("doc", ""),
                signature=f"{prop.get('name', '')}: {prop.get('type', '')}",
            )
            for prop in entry.get("properties") or []
            if prop.get("name")
        )
        by_module.setdefault(module, []).append(
            ApiSurfaceClassV1(
                name=entry["name"],
                description=entry.get("doc", ""),
                kind=entry.get("kind", ""),
                methods=methods,
                properties=properties,
            )
        )
        file_sha_source = entry.get("model_sha") or entry.get("repo_sha")
        if file_sha_source:
            model_sha = file_sha_source
    if not by_module:
        return None
    if model_sha is None:
        model_path = data_root / "knowledge" / family / platform / "merged" / "model.yaml"
        if model_path.is_file():
            match = _MODEL_YAML_REPO_SHA_RE.search(model_path.read_text(encoding="utf-8"))
            model_sha = match.group(1) if match else None
    modules = tuple(
        ApiSurfaceModuleV1(module=module_name, classes=tuple(classes))
        for module_name, classes in by_module.items()
    )
    return ApiPublicSurfaceDetectionV1(modules=modules, model_sha=model_sha)


__all__ = [
    "ApiPublicSurfaceDetectionV1",
    "ApiSurfaceClassV1",
    "ApiSurfaceModuleV1",
    "ArchetypeDetectionV1",
    "DependencyClaimsDetectionV1",
    "DevTestArtifactV1",
    "EnterpriseLinkDetectionV1",
    "HomepageLinkDetectionV1",
    "InstallInfoDetectionV1",
    "LicenseFileDetectionV1",
    "RelevantSeoKeywordsDetectionV1",
    "SeoKeywordsDetectionV1",
    "detect_api_public_surface",
    "detect_archetype",
    "detect_capability_dependencies",
    "detect_dependency_claims",
    "detect_dev_test_artifacts",
    "detect_enterprise_link",
    "detect_homepage_link",
    "detect_install_info",
    "detect_license_file",
    "detect_relevant_seo_keywords",
    "detect_seo_keywords",
]
