"""Freeze and settle one registry revision before portfolio fan-out."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from readme_agent import paths
from readme_agent.evidence.writer import write_redacted_json
from readme_agent.registry.loader import load_products
from readme_agent.registry.revision import (
    RegistryRevisionV1,
    with_pending_intake,
)
from readme_agent.registry.revision_gate import RegistryRevisionGateV1, evaluate_registry_revision
from readme_agent.registry.revision_store import write_registry_revision
from readme_agent.registry.self_heal import heal_registry_drift
from readme_agent.state.backend import StateBackend
from readme_agent.supervisor.registry_intake_queue import (
    RegistryIntakeQueueResultV1,
    settle_registry_intake_queue,
)


class RegistryRevisionPreflightV1(BaseModel):
    """Observable discovery, intake, and Gate-A preflight result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    heal_status: str
    revision: RegistryRevisionV1
    gate: RegistryRevisionGateV1
    intake_queue: RegistryIntakeQueueResultV1 | None = None


def prepare_registry_revision(
    products_path: Path,
    backend: StateBackend,
    *,
    heal_enabled: bool = True,
    force_refresh: bool = False,
) -> RegistryRevisionPreflightV1:
    """Run or reuse discovery, settle intake, and emit a fail-closed gate."""

    heal = heal_registry_drift(
        enabled=heal_enabled,
        products_path=products_path,
        min_interval_seconds=0 if force_refresh else 6 * 3600,
    )
    if heal.registry_revision is None and heal.status == "SKIPPED_RECENT":
        heal = heal_registry_drift(
            enabled=True,
            products_path=products_path,
            min_interval_seconds=0,
        )
    revision = heal.registry_revision
    if revision is None:
        raise RuntimeError(
            f"registry revision unavailable after discovery boundary ({heal.status}: {heal.detail})"
        )
    entries = list(load_products(products_path))
    queue = None
    if revision.pending_intake:
        queue = settle_registry_intake_queue(revision, entries, backend)
        revision = with_pending_intake(revision, queue.pending_intake)
        write_registry_revision(revision)
        write_redacted_json(paths.registry_revision_root() / "intake-queue.json", queue)
    products = json.loads(products_path.read_text(encoding="utf-8"))
    gate = evaluate_registry_revision(revision, products)
    write_redacted_json(paths.registry_revision_root() / "gate.json", gate)
    result = RegistryRevisionPreflightV1(
        heal_status=heal.status,
        revision=revision,
        gate=gate,
        intake_queue=queue,
    )
    write_redacted_json(paths.registry_revision_root() / "preflight.json", result)
    return result
