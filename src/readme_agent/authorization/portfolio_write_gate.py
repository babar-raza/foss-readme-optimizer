"""TW-01 (freshness-service plan): portfolio-wide remote-write gate.

This composes with, and never duplicates, the existing per-repo authorization
system (`registry.py::authorized_for`, `AuthorizationRecordV1`) and the existing,
already-proven git-push blocking (`gitsafety/neuter.py` + `hooks.py` + `verify.py`,
which this module does not touch). What is genuinely new here, per this plan's
binding amendment ("portfolio-wide local approval before ANY remote write"): a
remote write requires BOTH the per-repo `AuthorizationRecordV1` grant AND a
separate, portfolio-wide approval receipt covering the complete reviewed
portfolio -- one approved product must never be able to open a write path alone.

**Honest scope note**: the receipt format here is a minimal stub (inventory
revision + timestamp + note), not the full byte-exact candidate/source-hash
binding this plan's TW-05 card designs (immutable receipt, automatic
invalidation on drift). TW-05 was not built this session; this module defines
the narrowest real thing needed to make the portfolio-wide gate load-bearing
now, and is meant to be superseded by TW-05's richer schema, not duplicated by
it -- `PortfolioApprovalReceiptV1` should gain fields, not gain a sibling.

**Also honest about defense-in-depth scope**: this module governs SYSTEM-OWNED
execution (this runtime and its subprocesses). It cannot and does not claim to
stop an independent human or process holding separate credentials.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.authorization.registry import authorization_directory, authorized_for
from readme_agent.authorization.schema import EffectClass
from readme_agent.errors import GitSafetyError

DEFAULT_RECEIPT_PATH = Path("config/authorization/portfolio-approval-receipt.json")
DEFAULT_REJECTION_LOG = Path("runs/remote-write-guard/rejected-attempts.jsonl")


class PortfolioApprovalReceiptV1(BaseModel):
    """Minimal portfolio-wide approval marker. See module docstring: superseded
    by TW-05's richer, hash-bound schema when that card is built."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = 1
    portfolio_inventory_revision: str = Field(min_length=1)
    approved_at: str = Field(min_length=1)
    approval_note: str = Field(min_length=1)


class RemoteWriteBlockedError(GitSafetyError):
    """Raised when a remote-write attempt lacks the required dual authorization."""


def receipt_path() -> Path:
    return Path(os.environ.get("README_AGENT_PORTFOLIO_RECEIPT_PATH", str(DEFAULT_RECEIPT_PATH)))


def rejection_log_path() -> Path:
    return Path(os.environ.get("README_AGENT_REJECTION_LOG_PATH", str(DEFAULT_REJECTION_LOG)))


def load_portfolio_approval_receipt(
    *, path: Path | None = None
) -> PortfolioApprovalReceiptV1 | None:
    """`None` (never raises for absence) when no receipt exists -- the correct,
    fail-closed default. Malformed receipts are also treated as absent: a
    corrupt or partial receipt file must never be read as "somehow approved."
    """

    target = path or receipt_path()
    if not target.exists():
        return None
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
        return PortfolioApprovalReceiptV1.model_validate(raw)
    except (json.JSONDecodeError, ValueError):
        return None


def _record_rejection(reason: str, *, org_repo: str | None, effect_class: str) -> None:
    log_path = rejection_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "org_repo": org_repo,
        "effect_class": effect_class,
        "reason": reason,
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def assert_remote_write_authorized(
    org_repo: str,
    effect_class: EffectClass,
    *,
    receipt_dir: Path | None = None,
) -> None:
    """Fail closed unless BOTH the portfolio receipt exists AND this specific
    repo/effect has its own `AuthorizationRecordV1` grant. Every rejection is
    recorded before the exception propagates -- the caller cannot lose the
    record by catching and swallowing the error.
    """

    receipt = load_portfolio_approval_receipt(path=receipt_dir)
    if receipt is None:
        _record_rejection(
            "no portfolio-wide approval receipt", org_repo=org_repo, effect_class=effect_class
        )
        raise RemoteWriteBlockedError(
            "remote write blocked: no portfolio-wide approval receipt at "
            f"{(receipt_dir or receipt_path())} -- the complete portfolio must be locally "
            "reviewed and approved before any product becomes remote-eligible"
        )
    record = authorized_for(org_repo, effect_class, authorization_dir=authorization_directory())
    if record is None:
        _record_rejection(
            "no per-repo AuthorizationRecordV1 grant for this effect class",
            org_repo=org_repo,
            effect_class=effect_class,
        )
        raise RemoteWriteBlockedError(
            f"remote write blocked: {org_repo} has no AuthorizationRecordV1 grant covering "
            f"{effect_class!r} (a portfolio-wide receipt existing is necessary, not sufficient)"
        )


__all__ = [
    "DEFAULT_RECEIPT_PATH",
    "DEFAULT_REJECTION_LOG",
    "PortfolioApprovalReceiptV1",
    "RemoteWriteBlockedError",
    "assert_remote_write_authorized",
    "load_portfolio_approval_receipt",
    "receipt_path",
    "rejection_log_path",
]
