"""Supervise-time self-heal for registry drift (CORE-034, decision #47).

An upstream FOSS repo that GitHub added since the last weekly scan is invisible
to `data/products.json` until the cron runs -- this module closes that window:
`cmd_supervise()` calls `heal_registry_drift()` once, before preflight and the
allow-list gates, so a freshly published repo is merged (additively, always
`mode: "disabled"`) in-process and `require_listed()` sees it immediately.

Posture, deliberately different from every capability:
    - NOT a capability and NOT effect-ledger-gated: `data/products.json` is this
      project's own config-as-data, not a target-repo surface; the write is the
      same one scripts/data-refresh/update_products_registry.py performs. The
      safety envelope is `discovery.merge()`'s invariants (new entries land
      disabled, owned fields never written, additive-only) + `write_atomic()` +
      the evidence artifact written here.
    - Failure-isolated: supervision of already-admitted repositories continues,
      but a source failure produces `INCOMPLETE`/`HEALED_INCOMPLETE`, never
      `NO_DRIFT`. Unexpected outer failures degrade to `SKIPPED_ERROR`. The one
      place that needs active enforcement is GitHub's 403 rate-limit wait,
      capped at `_MAX_RATE_LIMIT_WAIT_SECONDS` via `RegistryScanRateLimited` --
      without the cap, failure isolation would silently sleep out a rate-limit
      reset inside supervise.
    - Fail-closed on the write itself: every merged entry is re-validated
      against `ProductEntry` before the file is replaced, so the heal can never
      write a registry the loader would refuse to load.
    - Throttled: a TTL marker (`paths.registry_heal_marker_path()`) makes a
      sequential portfolio pass scan GitHub once, not once per repository.
      `HEAL_MIN_INTERVAL_SECONDS` has no operational history yet -- tunable,
      same posture as the supervisor's `ESCALATION_ALERT_THRESHOLD`.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from readme_agent import env, paths
from readme_agent.evidence.writer import generate_run_id
from readme_agent.registry import discovery
from readme_agent.registry.discovery_inventory import inventory_sources
from readme_agent.registry.models import ProductEntry

HEAL_MIN_INTERVAL_SECONDS = 6 * 3600
_MAX_RATE_LIMIT_WAIT_SECONDS = 60.0


@dataclass
class RegistryHealResult:
    status: str  # HEALED | HEALED_INCOMPLETE | NO_DRIFT | INCOMPLETE |
    #             SKIPPED_DISABLED | SKIPPED_RECENT | SKIPPED_NO_TOKEN | SKIPPED_ERROR
    detail: str = ""
    new_entries: list[dict] = field(default_factory=list)
    refreshed_count: int = 0
    org_failures: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    observations: list[dict] = field(default_factory=list)
    inventory_complete: bool | None = None
    run_id: str | None = None

    def summary_line(self) -> str:
        if self.status in {"HEALED", "HEALED_INCOMPLETE"}:
            added = ", ".join(
                f"{e['repo_url'].split('/')[3]}/{e['repo_name']}" for e in self.new_entries
            )
            detail = f"+{len(self.new_entries)}" + (f" {added}" if added else "")
            if self.org_failures:
                detail += f"; {len(self.org_failures)} org scan(s) failed"
            return f"registry-heal: HEALED ({detail})"
        return f"registry-heal: {self.status}" + (f" ({self.detail})" if self.detail else "")


def heal_registry_drift(
    *,
    enabled: bool = True,
    products_path: Path = discovery.PRODUCTS_PATH,
    families_path: Path = discovery.FAMILIES_PATH,
    min_interval_seconds: float = HEAL_MIN_INTERVAL_SECONDS,
) -> RegistryHealResult:
    """Detect and additively merge registry drift. Never raises."""
    try:
        return _heal(
            enabled=enabled,
            products_path=products_path,
            families_path=families_path,
            min_interval_seconds=min_interval_seconds,
        )
    except Exception as exc:  # noqa: BLE001 -- fail-open is this module's contract
        result = RegistryHealResult(status="SKIPPED_ERROR", detail=str(exc))
        # A failed scan still stamps the TTL marker: a sequential 25-repo pass
        # with GitHub down must degrade to one failed attempt per interval,
        # not 25 slow ones.
        _try_write_marker(result)
        _try_write_evidence(result)
        return result


def _heal(
    *,
    enabled: bool,
    products_path: Path,
    families_path: Path,
    min_interval_seconds: float,
) -> RegistryHealResult:
    if not enabled:
        return RegistryHealResult(status="SKIPPED_DISABLED", detail="--no-registry-heal")

    marker_age = _marker_age_seconds()
    if marker_age is not None and marker_age < min_interval_seconds:
        return RegistryHealResult(
            status="SKIPPED_RECENT",
            detail=(
                f"last heal attempt {int(marker_age)}s ago, interval {int(min_interval_seconds)}s"
            ),
        )

    token = env.gh_token()
    if token is None:
        # An unauthenticated 26-org scan burns most of GitHub's 60/hour
        # anonymous quota and invites long 403 waits -- and a run without
        # GH_TOKEN is about to fail preflight's own GitHub check anyway.
        return RegistryHealResult(
            status="SKIPPED_NO_TOKEN", detail="set GH_TOKEN / GITHUB_PAT to enable"
        )

    if not products_path.is_file():
        # Never bootstrap a fresh allow-list: an absent products.json means a
        # wrong cwd, not an empty registry (loader.py fails closed on it too).
        return RegistryHealResult(
            status="SKIPPED_ERROR", detail=f"{products_path} not found (run from the repo root?)"
        )

    existing = json.loads(products_path.read_text(encoding="utf-8"))
    families = discovery.load_families(families_path)
    inventory = inventory_sources(
        families,
        scan_organization=discovery.scan_org,
        classify_repository=discovery.classify_repo_name,
        token=token,
        max_rate_limit_wait_seconds=_MAX_RATE_LIMIT_WAIT_SECONDS,
    )
    discovered = [observation.to_registry_entry() for observation in inventory.matched_observations]
    org_failures = [
        {"org": failure.source.organization, "error": failure.error}
        for failure in inventory.failures
    ]
    sources = [source.model_dump(mode="json") for source in inventory.sources]
    observations = [observation.model_dump(mode="json") for observation in inventory.observations]
    merged = discovery.merge(existing, discovered)

    existing_keys = {(e["family"], e["platform"]) for e in existing}
    new_entries = [e for e in merged if (e["family"], e["platform"]) not in existing_keys]
    refreshed_count = len(discovered) - len(new_entries)

    if merged == existing:
        result = RegistryHealResult(
            status="NO_DRIFT" if inventory.complete else "INCOMPLETE",
            refreshed_count=refreshed_count,
            org_failures=org_failures,
            sources=sources,
            observations=observations,
            inventory_complete=inventory.complete,
        )
    else:
        # Fail-closed write guard: the heal must never produce a file the
        # loader would reject (ValidationError propagates to the fail-open
        # wrapper as SKIPPED_ERROR, leaving the file untouched).
        for entry in merged:
            ProductEntry.model_validate(entry)
        discovery.write_atomic(products_path, merged)
        result = RegistryHealResult(
            status="HEALED" if inventory.complete else "HEALED_INCOMPLETE",
            new_entries=new_entries,
            refreshed_count=refreshed_count,
            org_failures=org_failures,
            sources=sources,
            observations=observations,
            inventory_complete=inventory.complete,
        )

    _try_write_marker(result)
    _try_write_evidence(result, orgs_scanned=[f["github_org"] for f in families])
    return result


def _try_write_marker(result: RegistryHealResult) -> None:
    """Best-effort: a marker-write failure (permissions, disk) must not undo
    fail-open -- it only costs extra scans on later invocations."""
    try:
        _write_marker(result)
    except Exception:  # noqa: BLE001 -- see docstring
        pass


def _marker_age_seconds() -> float | None:
    marker_path = paths.registry_heal_marker_path()
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        return time.time() - float(marker["last_heal_epoch"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _write_marker(result: RegistryHealResult) -> None:
    marker_path = paths.registry_heal_marker_path()
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = marker_path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            {
                "last_heal_epoch": time.time(),
                "last_status": result.status,
                "timestamp": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(tmp, marker_path)


def _try_write_evidence(result: RegistryHealResult, orgs_scanned: list[str] | None = None) -> None:
    """Evidence for every real heal attempt (scans and hard failures) -- the
    cheap SKIPPED_DISABLED/SKIPPED_RECENT/SKIPPED_NO_TOKEN short-circuits are
    recorded only in the printed status line, not as evidence dirs (a 25-repo
    sequential pass would otherwise mint 24 empty evidence dirs per interval).
    Best-effort by design: an evidence-write failure must not undo fail-open."""
    try:
        run_id = generate_run_id()
        result.run_id = run_id
        evidence_dir = paths.evidence_dir(run_id)
        evidence_dir.mkdir(parents=True, exist_ok=True)

        def _write(name: str, data) -> None:
            tmp = evidence_dir / f"{name}.tmp"
            tmp.write_text(
                json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8", newline="\n"
            )
            os.replace(tmp, evidence_dir / name)

        _write(
            "registry_heal.json",
            {
                "status": result.status,
                "detail": result.detail,
                "orgs_scanned": orgs_scanned or [],
                "org_failures": result.org_failures,
                "sources": result.sources,
                "observations": result.observations,
                "inventory_complete": result.inventory_complete,
                "new_entries": result.new_entries,
                "refreshed_count": result.refreshed_count,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        _write(
            "manifest.json",
            {
                "run_id": run_id,
                "kind": "registry_heal",
                "status": result.status,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    except Exception:  # noqa: BLE001 -- see docstring
        result.run_id = None
