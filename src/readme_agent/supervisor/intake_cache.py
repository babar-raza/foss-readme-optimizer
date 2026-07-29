"""Validate one reusable source-bound intake receipt without mutating durable state."""

from __future__ import annotations

import json
from pathlib import Path

from readme_agent.registry.intake import ReadOnlyIntakePreflightV1, intake_contract_hash
from readme_agent.registry.models import ProductEntry
from readme_agent.state.lifecycle_schema import (
    IntakePreflightBindingV1,
    ReadmePocLifecycleStateV2,
)
from readme_agent.state.readme_poc_intake import intake_preflight_dedup_key
from readme_agent.state.schema import RunStateV2

_READY_OUTCOMES = {"READY_FAST_PATH", "READY_FULL_PIPELINE"}


def completed_intake_binding(
    state: RunStateV2 | None,
    entry: ProductEntry,
    *,
    current_source_revision: str | None,
) -> IntakePreflightBindingV1 | None:
    """Return a current, evidence-backed ready receipt or fail closed."""

    identity = entry.provider_identity
    lifecycle = state.readme_poc_lifecycle if state is not None else None
    if (
        identity is None
        or current_source_revision is None
        or not isinstance(lifecycle, ReadmePocLifecycleStateV2)
        or lifecycle.intake_preflight_pending is not None
    ):
        return None
    contract_hash = intake_contract_hash(entry)
    dedup_key = intake_preflight_dedup_key(
        entry.org_repo,
        identity.repository_id,
        current_source_revision,
        contract_hash,
    )
    binding = next(
        (
            item
            for item in reversed(lifecycle.intake_preflight_history)
            if item.dedup_key == dedup_key
        ),
        None,
    )
    if (
        binding is None
        or binding.outcome not in _READY_OUTCOMES
        or binding.source_revision != current_source_revision
        or not binding.source_revision_resolved
        or not binding.evidence_refs
    ):
        return None
    receipt_path = Path(binding.evidence_refs[0])
    try:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        result = ReadOnlyIntakePreflightV1.model_validate(payload["result"])
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        return None
    if (
        payload.get("dedup_key") != binding.dedup_key
        or payload.get("attempt") != binding.attempt
        or result.org_repo != entry.org_repo
        or result.source_revision != current_source_revision
        or result.contract_hash != contract_hash
        or result.outcome != binding.outcome
        or result.canonical_hash() != binding.result_hash
        or result.target_remote_effects_allowed
        or result.target_local_effects_allowed
    ):
        return None
    return binding
