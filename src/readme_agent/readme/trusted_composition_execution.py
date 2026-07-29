"""Execute and validate one bounded trusted README authoring batch."""

from __future__ import annotations

import hashlib
import json

from pydantic import ValidationError

from readme_agent import env
from readme_agent.errors import LLMError
from readme_agent.llm.generation_prompts import (
    build_trusted_readme_section_messages,
    build_trusted_readme_section_tool_schema,
)
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.llm.verifier_client import ForcedToolClient
from readme_agent.readme.trusted_composition_batching import TrustedCompositionBatch
from readme_agent.readme.trusted_composition_models import (
    TrustedCompositionEnvelopeV1,
    TrustedReadmeSectionDraftV1,
    TrustedReadmeSectionToolDraftV1,
)
from readme_agent.readme.trusted_composition_normalization import (
    normalize_configured_header,
    normalize_tool_arguments,
    preserve_omitted_source_facts,
)
from readme_agent.readme.trusted_composition_validation import (
    validate_trusted_section_tool_draft,
)

TRUSTED_COMPOSITION_JOB = "trusted_readme_section_transform"
_MAX_ATTEMPTS = 3


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _batch_payload(batch: TrustedCompositionBatch) -> dict:
    return {
        "batch_id": batch.batch_id,
        "source_items": [item.model_dump(mode="json") for item in batch.source_items],
        "configured_standards": [
            standard.model_dump(mode="json") for standard in batch.configured_standards
        ],
        "global_structures_allowed": batch.global_structures_allowed,
    }


def trusted_batch_tool_schema_hash(batch: TrustedCompositionBatch) -> str:
    """Hash the exact forced-tool schema offered for one batch."""

    return _canonical_hash(
        build_trusted_readme_section_tool_schema(
            fact_ids=[item.fact_id for item in batch.source_items],
            configured_standard_ids=[item.standard_id for item in batch.configured_standards],
        )
    )


def compose_trusted_batch(
    org_repo: str,
    batch: TrustedCompositionBatch,
    envelope: TrustedCompositionEnvelopeV1,
    client: ForcedToolClient,
    *,
    initial_repair_hint: str = "",
) -> tuple[TrustedReadmeSectionToolDraftV1, TrustedReadmeSectionDraftV1]:
    """Compose or repair one bounded batch through the same typed contract."""

    payload = _batch_payload(batch)
    tool_schema = build_trusted_readme_section_tool_schema(
        fact_ids=[item.fact_id for item in batch.source_items],
        configured_standard_ids=[item.standard_id for item in batch.configured_standards],
    )
    schema_hash = _canonical_hash(tool_schema)
    repair_hint = initial_repair_hint
    last_error: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        call_input = {
            "org_repo": org_repo,
            "batch": payload,
            "envelope": envelope.model_dump(mode="json"),
            "repair_hint": repair_hint,
        }
        messages = build_trusted_readme_section_messages(
            org_repo=org_repo,
            batch_json=json.dumps(payload, sort_keys=True, ensure_ascii=False),
            envelope_json=json.dumps(envelope.model_dump(mode="json"), sort_keys=True),
            repair_hint=repair_hint,
        )
        result = client.call(messages, tool_schema)
        try:
            arguments = normalize_tool_arguments(result.arguments, batch)
            draft = TrustedReadmeSectionToolDraftV1.model_validate(arguments)
            draft = preserve_omitted_source_facts(draft, batch)
            draft = normalize_configured_header(draft, batch)
            validate_trusted_section_tool_draft(draft, batch, envelope)
        except (LLMError, ValidationError) as exc:
            last_error = exc
            if attempt == _MAX_ATTEMPTS:
                raise LLMError(
                    f"trusted composition batch {batch.batch_id} failed after "
                    f"{_MAX_ATTEMPTS} attempts: {exc}"
                ) from exc
            repair_hint = (
                f"Your prior output was rejected: {exc}. Return all enumerated source facts and "
                "configured standards exactly once. Preserve context-truncated facts exactly."
            )
            continue
        bound = TrustedReadmeSectionDraftV1(
            batch_id=batch.batch_id,
            editorial_summary=draft.editorial_summary,
            source_inventory=draft.source_inventory,
            segments=draft.segments,
            prompt_sha256=prompt_hash(TRUSTED_COMPOSITION_JOB),
            tool_schema_sha256=schema_hash,
            input_sha256=_canonical_hash(call_input),
            model=result.meta.model or env.llm_model_for_job(TRUSTED_COMPOSITION_JOB),
            attempt_count=attempt,
        )
        return draft, bound
    assert last_error is not None
    raise LLMError(str(last_error))
