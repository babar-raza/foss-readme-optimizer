"""Skip re-executing an already-triaged BLOCKED repository until something changes.

Why this exists (2026-08-18, Gate A recovery): the portfolio loop short-circuits
COMPLETE bundles through `local_poc_cache.py` with zero provider calls, but a
repository whose last canonical run ended BLOCKED was re-executed *in full* on
every subsequent pass -- re-cloning, re-extracting, and re-spending provider
calls (observed live: 4 calls/pass on Note, 7 on Slides) to re-derive a failure
that was already precisely triaged.  With ~8 known-blocked members ahead of them
in registry order, the remaining 22 registry entries never fit inside one slice
budget, and non-deterministic corroboration turned every needless retry into
classification noise ("claim counts fluctuated") that read as progress or
regression when it was neither.

Contract:

- A BLOCKED outcome is persisted together with the exact dependency
  fingerprints current at the moment it was produced
  (`local_poc_cache.current_blocked_decision_dependencies()` -- the same
  sources the completed-bundle cache binds to, so "what counts as a change"
  can never drift between the two caches).
- On a later pass the stored decision is reusable only while every fingerprint
  still matches.  Any mismatch, missing file, or malformed payload makes the
  decision non-reusable and the repository runs live again (fail-open toward
  re-execution -- this cache may only ever *save* work, never suppress a
  legitimately-due retry).
- A live run that ends anything other than BLOCKED clears the record.
- `--retry-blocked` bypasses the cache for one invocation without deleting
  the records (deleting is the live run's job when it succeeds).

This is deliberately NOT a backoff timer: a blocked repository is retried when
one of its semantic inputs changes (new upstream revision, prompt/template/
contract/control-plane change), not when a clock expires.  Re-rolling an
unchanged model decision is exactly the "portfolio loop as random search"
behavior this cache exists to stop.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

BLOCKED_DECISION_SCHEMA_VERSION = 1


class BlockedDecisionRecordV1(BaseModel):
    """One persisted, dependency-bound BLOCKED outcome for one repository."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = BLOCKED_DECISION_SCHEMA_VERSION
    org_repo: str
    status: str
    exit_code: int
    blocked_reason: str
    blocked_category: str | None = None
    dependencies: dict[str, Any]
    consecutive_count: int = 1
    recorded_run_id: str | None = None


class BlockedDecisionCacheDecisionV1(BaseModel):
    """Inspectable outcome of one reuse evaluation."""

    model_config = ConfigDict(extra="forbid")

    reusable: bool
    record: BlockedDecisionRecordV1 | None = None
    mismatch_reasons: list[str]


def load_blocked_decision(path: Path) -> BlockedDecisionRecordV1 | None:
    """The persisted record, or None for missing/unreadable/invalid content."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    try:
        record = BlockedDecisionRecordV1.model_validate(payload)
    except ValidationError:
        return None
    if record.schema_version != BLOCKED_DECISION_SCHEMA_VERSION:
        return None
    return record


def persist_blocked_decision(path: Path, record: BlockedDecisionRecordV1) -> None:
    """Write the record atomically (same replace idiom the summary writer uses)."""

    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_suffix(".json.tmp")
    staging.write_text(
        json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    staging.replace(path)


def clear_blocked_decision(path: Path) -> None:
    """Remove a superseded record; missing is fine (idempotent)."""

    try:
        path.unlink()
    except FileNotFoundError:
        pass


def record_blocked_outcome(
    path: Path,
    *,
    org_repo: str,
    status: str,
    exit_code: int,
    blocked_reason: str,
    blocked_category: str | None,
    dependencies: dict[str, Any],
    run_id: str | None = None,
) -> BlockedDecisionRecordV1:
    """Persist a live BLOCKED outcome, counting identical consecutive reasons.

    The count only ever reflects *live* re-derivations of the same reason --
    cache reuses deliberately do not inflate it, so it stays meaningful as
    the "how often did a real run reproduce this" escalation signal.
    """

    previous = load_blocked_decision(path)
    consecutive = (
        previous.consecutive_count + 1
        if previous is not None
        and previous.org_repo == org_repo
        and previous.blocked_reason == blocked_reason
        else 1
    )
    record = BlockedDecisionRecordV1(
        org_repo=org_repo,
        status=status,
        exit_code=exit_code,
        blocked_reason=blocked_reason,
        blocked_category=blocked_category,
        dependencies=dependencies,
        consecutive_count=consecutive,
        recorded_run_id=run_id,
    )
    persist_blocked_decision(path, record)
    return record


def evaluate_blocked_decision_cache(
    path: Path,
    *,
    org_repo: str,
    current_dependencies: dict[str, Any],
) -> BlockedDecisionCacheDecisionV1:
    """Reusable only while every stored dependency fingerprint still matches."""

    record = load_blocked_decision(path)
    if record is None:
        return BlockedDecisionCacheDecisionV1(
            reusable=False,
            record=None,
            mismatch_reasons=["blocked_decision_missing_or_invalid"],
        )
    reasons: list[str] = []
    if record.org_repo != org_repo:
        reasons.append("org_repo_mismatch")
    for key in sorted(set(record.dependencies) | set(current_dependencies)):
        if record.dependencies.get(key) != current_dependencies.get(key):
            reasons.append(f"{key}_changed")
    return BlockedDecisionCacheDecisionV1(
        reusable=not reasons,
        record=record,
        mismatch_reasons=reasons,
    )
