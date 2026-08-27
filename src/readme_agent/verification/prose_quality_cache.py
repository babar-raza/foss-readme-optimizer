"""Persist prose-quality verdicts for zero-call reuse (Decision #110/#113, requirement
LLM-023, 2026-08-27 production recovery sprint).

`verify_prose_quality`/`check_prose_quality()` was the one LLM-authored judgment surface
in this codebase with no cache at all -- every other surface (claim disposition, bounded
review, section authoring, trusted-fidelity review) already persists an accepted verdict
keyed by content hash plus a deliberately-bumped contract-version literal, so a rerun with
unchanged input reproduces the same verdict instead of re-rolling qwen3-next's proven-
nondeterministic tool-call arguments (Decision #105). This mirrors that same pattern,
scoped as simply as `readme/claim_accountability_llm_disposition.py`'s per-repo ratchet
(no revision-scoped directory needed -- the verdict depends only on `final_text` and the
contract version, not on which snapshot/revision produced that text).

Unlike the claim-disposition ratchet (which deliberately persists only *accepted*
verdicts, to let a rejected claim retry against later-changed candidate text), this cache
persists every verdict, flagged or not: for a fixed `final_text`, there is no candidate-
side change a retry could observe -- re-asking only re-rolls the same nondeterministic
dice, never converges the answer, and costs a call either way.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from readme_agent import paths

# Bump whenever the prose-quality prompt, tool schema, or corroboration logic changes --
# invalidates every cached entry at once, the same convention as
# section_authoring_cache.py::SECTION_AUTHORING_CONTRACT_VERSION and
# trusted_fidelity_cache.py::FIDELITY_BATCH_CONTRACT_VERSION.
PROSE_QUALITY_CONTRACT_VERSION = "prose-quality-v1-rdm020-baseline"

_SCHEMA_VERSION = 1


def prose_quality_cache_key(final_text: str, *, contract_version: str | None = None) -> str:
    """Bind the reviewed text and the check's own implementation/version hash into one
    cache identity -- deliberately NOT keyed on org_repo/source_revision: the verdict is a
    pure function of `final_text` (plus the contract version), so identical text from any
    repository or revision is safely interchangeable, exactly like the claim-disposition
    ratchet's `sha256(claim_text)`-only key."""

    payload = json.dumps(
        {
            "contract_version": contract_version or PROSE_QUALITY_CONTRACT_VERSION,
            "final_text_sha256": hashlib.sha256(final_text.encode("utf-8")).hexdigest(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def prose_quality_cache_path(org_repo: str) -> Path:
    """Repo-level cache store, sibling of `claim-disposition-ratchet.json`."""

    org, repo = org_repo.split("/", maxsplit=1)
    return paths.readme_poc_root() / f"{org}__{repo}" / "prose-quality-cache.json"


def load_cached_prose_quality(path: Path, cache_key: str) -> dict | None:
    """Load an exact-key cached verdict, or `None` on any miss/corruption (a corrupt or
    unreadable cache file is a cache miss, never a hard failure -- this check is additive
    and must degrade to a fresh call, exactly like `client=None`'s existing behavior)."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("schema_version") != _SCHEMA_VERSION:
        return None
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return None
    entry = entries.get(cache_key)
    return entry if isinstance(entry, dict) else None


def persist_prose_quality_verdict(path: Path, cache_key: str, verdict: dict) -> None:
    """Persist a verdict (flagged or not) through an atomic write, matching the
    write-then-replace pattern `_persist_ratchet_entry()` already uses."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        entries = payload.get("entries") if isinstance(payload, dict) else None
        if not isinstance(entries, dict) or payload.get("schema_version") != _SCHEMA_VERSION:
            entries = {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        entries = {}

    entries[cache_key] = verdict
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_suffix(".json.tmp")
    staging.write_text(
        json.dumps(
            {"schema_version": _SCHEMA_VERSION, "entries": entries}, indent=2, sort_keys=True
        )
        + "\n",
        encoding="utf-8",
    )
    staging.replace(path)
