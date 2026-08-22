"""Execute one bounded section-cluster authoring call and deterministically accept its result.

Two independent, orthogonal retry bounds compose for one cluster's worst-case cost:

- **Logical** (this module): at most 3 attempts -- 1 normal + at most 2 same-cluster semantic-
  correction retries, triggered only by a schema-invalid or acceptance-rejected response. Never
  triggered by a transient gateway/transport failure -- that is the client's job, below.
- **Physical/transport** (`llm/section_author_client.py::TRANSPORT_MAX_ATTEMPTS`): at most 2
  physical HTTP attempts per logical call, with identical request bytes, for a transient
  gateway/transport failure only (HTTP 500/502/503/504, connection error) -- never for a
  schema/factual failure.

Worst case per cluster: 3 logical attempts x 2 physical transport attempts each = **at most 6
physical provider calls**. Best case (clean first response): 1 physical call. A cache hit
(`section_authoring_cache.py`) reuses an already-accepted section with **zero** calls. Exhausting
the logical retry fails only this section, never a broader README rebuild -- the document-level
entry point (`section_authoring_document.py`) returns every section already produced before it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from readme_agent import env
from readme_agent.errors import LLMError
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.llm.schema import Usage
from readme_agent.llm.section_authoring_prompts import (
    build_section_cluster_authoring_messages,
    build_section_cluster_authoring_tool_schema,
)
from readme_agent.readme.capability_semantics import is_action_led_capability_title
from readme_agent.readme.presentation_lint_public_contract import lint_public_contract
from readme_agent.readme.presentation_similarity import semantically_repeats
from readme_agent.specialists.section_authoring_cache import (
    load_section_authoring_cache,
    section_authoring_cache_key,
    write_section_authoring_cache,
)
from readme_agent.specialists.section_authoring_contracts import (
    SectionAuthoringOutcomeV1,
    SectionAuthoringPacketV1,
    SectionAuthoringReceiptV1,
    SectionClusterAuthoringResultV1,
)
from readme_agent.specialists.section_authoring_fact_validation import (
    section_authoring_fact_errors,
)
from readme_agent.specialists.section_authoring_prompt_projection import (
    authoring_fact_prompt_payload,
)

_ACTOR_ID = "llm-route:section-cluster-authoring"
_PROMPT_ID = "section_cluster_authoring"
_MAX_LOGICAL_ATTEMPTS = 3  # 1 normal + at most 2 same-cluster semantic-correction retries

_COMMAND_LIKE_PREFIXES = (
    "$",
    ">",
    "pip ",
    "python -m pip",
    "npm ",
    "npx ",
    "yarn ",
    "pnpm ",
    "dotnet ",
    "mvn ",
    "gradle ",
    "go ",
    "cargo ",
    "cmake ",
    "make ",
    "git ",
)
_PUBLIC_TASK_FAMILY = {
    "verified_example_framing": "example_framing",
}


class SectionAuthoringAcceptanceError(LLMError):
    """A section-cluster authoring response failed a deterministic acceptance gate."""


class SectionClusterAuthorClientLike(Protocol):
    def analyze_section_cluster(
        self, messages: list[dict], accepted_fact_ids: list[str]
    ) -> AnalysisResult: ...


def _introduces_protected_content(text: str) -> bool:
    """Authored prose must frame, never spell out, commands/code -- deterministic code owns
    those. A conservative structural screen, not a keyword/claim screen: this only ever flags
    the model's OWN output shape (fences, indentation, command-like line starts), never scans
    for closed-list boundary language the way a forbidden-claim keyword screen would (the
    probe's own evaluators.py found that class of screen produces false positives -- see
    runs/owner_audit_staging/qwen3-next-editorial-probe-aa9981021/REPORT.md)."""

    if "```" in text:
        return True
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if line.startswith("    ") or any(
            stripped.casefold().startswith(prefix) for prefix in _COMMAND_LIKE_PREFIXES
        ):
            return True
    return False


def _validate_acceptance(
    packet: SectionAuthoringPacketV1, result: SectionClusterAuthoringResultV1
) -> None:
    allowed = set(packet.allowed_fact_ids)
    do_not_claim_ids = {fact.fact_id for fact in packet.do_not_claim}
    cited: set[str] = set()
    for unit in result.units:
        # Checked before the general unknown-fact_id gate below: do_not_claim ids are always a
        # subset of "not in allowed" by the packet validator's disjointness invariant, so this
        # gives the specific, actionable "you cited a forbidden fact" message instead of a
        # generic "unsupported fact_id" one whenever both would otherwise fire.
        forbidden = set(unit.fact_ids) & do_not_claim_ids
        if forbidden:
            raise SectionAuthoringAcceptanceError(
                "section cluster cited do_not_claim fact_id(s) as authorization: "
                f"{sorted(forbidden)}"
            )
        unknown = set(unit.fact_ids) - allowed
        if unknown:
            raise SectionAuthoringAcceptanceError(
                f"section cluster cited unsupported fact_id(s): {sorted(unknown)}"
            )
        if _introduces_protected_content(unit.text):
            raise SectionAuthoringAcceptanceError(
                f"section cluster unit {unit.heading!r} introduced a code block or command; "
                "deterministic code owns commands, code blocks, and package identifiers"
            )
        if any(
            finding.rule_id == "internal_assurance_commentary"
            for finding in lint_public_contract(unit.text)
        ):
            raise SectionAuthoringAcceptanceError(
                f"section cluster unit {unit.heading!r} introduced internal verification "
                "narration that is forbidden in a public README"
            )
        fact_errors = section_authoring_fact_errors(packet, unit)
        if fact_errors:
            raise SectionAuthoringAcceptanceError(
                f"section cluster unit {unit.heading!r} contradicts its structured fact "
                f"coordinates: {'; '.join(fact_errors)}"
            )
        cited.update(unit.fact_ids)
    omitted_ids = {item.fact_id for item in result.omitted}
    unknown_omitted = omitted_ids - allowed
    if unknown_omitted:
        raise SectionAuthoringAcceptanceError(
            f"section cluster omitted an unsupported fact_id: {sorted(unknown_omitted)}"
        )
    double_disposed = cited & omitted_ids
    if double_disposed:
        raise SectionAuthoringAcceptanceError(
            f"fact_id(s) both cited and omitted: {sorted(double_disposed)}"
        )
    undisposed = allowed - cited - omitted_ids
    if undisposed:
        raise SectionAuthoringAcceptanceError(
            f"accepted fact_id(s) neither used nor omitted-with-reason: {sorted(undisposed)}"
        )
    if packet.task_family == "capability_entry_cluster":
        invalid_headings = [
            unit.heading
            for unit in result.units
            if not is_action_led_capability_title(unit.heading)
        ]
        if invalid_headings:
            raise SectionAuthoringAcceptanceError(
                "section cluster capability headings are not action-led visitor search "
                f"phrases: {invalid_headings}"
            )
        repeated_headings = [
            unit.heading
            for unit in result.units
            if semantically_repeats(
                unit.heading.rstrip("."),
                unit.text.split(". ", 1)[0].rstrip("."),
                threshold=0.9,
            )
        ]
        if repeated_headings:
            raise SectionAuthoringAcceptanceError(
                "section cluster capability descriptions repeat their headings instead of "
                f"adding visitor detail: {repeated_headings}"
            )


def execute_section_cluster_authoring(
    *,
    packet: SectionAuthoringPacketV1,
    client: SectionClusterAuthorClientLike,
    cache_dir: Path | None = None,
) -> SectionAuthoringOutcomeV1:
    """Run (or reuse) one bounded section-cluster authoring call."""

    packet_hash = packet.canonical_hash()
    accepted_aliases = {
        fact.fact_id: f"F{index}" for index, fact in enumerate(packet.accepted_facts, start=1)
    }
    do_not_claim_aliases = {
        fact.fact_id: f"N{index}" for index, fact in enumerate(packet.do_not_claim, start=1)
    }
    all_aliases = {**accepted_aliases, **do_not_claim_aliases}
    alias_to_fact_id = {alias: fact_id for fact_id, alias in all_aliases.items()}
    schema = build_section_cluster_authoring_tool_schema(list(accepted_aliases.values()))
    schema_sha256 = _canonical_hash(schema)
    prompt_sha256 = prompt_hash(_PROMPT_ID)
    model = env.llm_model_for_job(_PROMPT_ID)
    cache_key = section_authoring_cache_key(
        org_repo=packet.org_repo,
        source_revision=packet.source_revision,
        packet_hash=packet_hash,
        target_section_id=packet.target_section_id,
        prompt_sha256=prompt_sha256,
        schema_sha256=schema_sha256,
        model=model,
        sampling_parameters={"temperature": 0.0},
        protected_literal_hash=packet.protected_literal_hash,
    )
    if cache_dir is not None:
        cached = load_section_authoring_cache(cache_dir, packet.target_section_id, cache_key)
        if cached is not None:
            return cached.outcome.model_copy(update={"reused_from_cache": True})

    def build_messages(*, repair_hint: str = "") -> list[dict]:
        return build_section_cluster_authoring_messages(
            org_repo=packet.org_repo,
            public_product_name=packet.public_product_name,
            target_section_id=packet.target_section_id,
            task_family=_PUBLIC_TASK_FAMILY.get(packet.task_family, packet.task_family),
            section_objective=packet.section_objective,
            accepted_facts_json=_canonical_json(
                [
                    authoring_fact_prompt_payload(
                        fact,
                        fact_id_alias=accepted_aliases[fact.fact_id],
                    )
                    for fact in packet.accepted_facts
                ]
            ),
            do_not_claim_json=_canonical_json(
                [
                    authoring_fact_prompt_payload(
                        fact,
                        fact_id_alias=do_not_claim_aliases[fact.fact_id],
                    )
                    for fact in packet.do_not_claim
                ]
            ),
            seo_vocabulary_json=_canonical_json(list(packet.seo_vocabulary)),
            current_source_text=packet.current_source_text or "",
            repair_hint=repair_hint,
        )

    messages = build_messages()

    token_usage: list[Usage] = []
    latency_ms: list[float] = []
    semantic_retry_used = False
    last_error: Exception | None = None
    result: SectionClusterAuthoringResultV1 | None = None
    analysis: AnalysisResult | None = None

    for attempt in range(1, _MAX_LOGICAL_ATTEMPTS + 1):
        analysis = client.analyze_section_cluster(messages, list(accepted_aliases.values()))
        if analysis.meta.usage is not None:
            token_usage.append(analysis.meta.usage)
        if analysis.meta.latency_ms is not None:
            latency_ms.append(analysis.meta.latency_ms)
        try:
            provider_result = SectionClusterAuthoringResultV1.model_validate(analysis.parsed)
            parsed = _restore_fact_ids(provider_result, alias_to_fact_id)
            _validate_acceptance(packet, parsed)
        except (ValidationError, SectionAuthoringAcceptanceError) as exc:
            last_error = exc
            if attempt == _MAX_LOGICAL_ATTEMPTS:
                break
            semantic_retry_used = True
            # Rebuilds the FULL packet context (accepted facts, do_not_claim, source text,
            # SEO vocabulary) plus the correction instruction -- never a bare error message
            # with the original facts dropped, which would leave the model unable to fix
            # anything it can no longer see (mirrors agentic_composition.py::_repair_hints'
            # own "restate what's needed" shape, not a lossy compact-context retry).
            messages = build_messages(
                repair_hint=(
                    f"Your previous submission (attempt {attempt}) failed a deterministic "
                    "acceptance check and was rejected before reaching any reader: "
                    f"{_provider_safe_error(exc, all_aliases)}. "
                    f"{_targeted_repair_action(exc)} "
                    "Keep every unaffected unit and disposition unchanged."
                )
            )
            continue
        result = parsed
        break

    if result is None or analysis is None:
        raise SectionAuthoringAcceptanceError(
            f"section cluster {packet.target_section_id!r} failed acceptance after "
            f"{_MAX_LOGICAL_ATTEMPTS} attempt(s): {last_error}"
        ) from last_error

    receipt = SectionAuthoringReceiptV1(
        actor_id=_ACTOR_ID,
        prompt_id=_PROMPT_ID,
        prompt_sha256=prompt_sha256,
        packet_hash=packet_hash,
        raw_output_sha256=_canonical_hash(analysis.parsed),
        provider_request_id=analysis.meta.request_id,
        provider_model=analysis.meta.model,
        semantic_retry_used=semantic_retry_used,
        logical_call_count=attempt,
        token_usage=token_usage,
        latency_ms=latency_ms,
    )
    outcome = SectionAuthoringOutcomeV1(
        target_section_id=packet.target_section_id,
        packet_hash=packet_hash,
        result=result,
        receipt=receipt,
        reused_from_cache=False,
    )
    if cache_dir is not None:
        write_section_authoring_cache(
            cache_dir,
            cache_key=cache_key,
            org_repo=packet.org_repo,
            source_revision=packet.source_revision,
            outcome=outcome,
        )
    return outcome


def _restore_fact_ids(
    result: SectionClusterAuthoringResultV1,
    alias_to_fact_id: dict[str, str],
) -> SectionClusterAuthoringResultV1:
    """Translate provider-local opaque IDs back to durable provenance IDs."""

    return result.model_copy(
        update={
            "units": tuple(
                unit.model_copy(
                    update={
                        "fact_ids": tuple(
                            alias_to_fact_id.get(fact_id, fact_id) for fact_id in unit.fact_ids
                        )
                    }
                )
                for unit in result.units
            ),
            "omitted": tuple(
                item.model_copy(
                    update={"fact_id": alias_to_fact_id.get(item.fact_id, item.fact_id)}
                )
                for item in result.omitted
            ),
        }
    )


def _provider_safe_error(exc: Exception, fact_id_to_alias: dict[str, str]) -> str:
    """Keep internal fact-ID wording out of correction prompts."""

    message = str(exc)
    for fact_id, alias in sorted(
        fact_id_to_alias.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        message = message.replace(fact_id, alias)
    return message


def _targeted_repair_action(exc: Exception) -> str:
    """Turn a deterministic failure class into one unambiguous correction action."""

    message = str(exc)
    if "both cited and omitted" in message:
        return "Keep the cited units, and delete every omitted entry for a fact cited by any unit."
    if "neither used nor omitted-with-reason" in message:
        return (
            "For every missing fact alias, either cite it in exactly one supported unit or add "
            "one omitted entry with a concrete reason. Do not leave any missing alias "
            "undisposed."
        )
    if "repeat their headings" in message:
        return "Keep the headings and rewrite only the descriptions so they add new detail."
    if "internal verification narration" in message:
        return "Remove the verification method and state only reader-facing product behavior."
    if "unsupported quality, completeness, guarantee" in message:
        return (
            "Delete the unsupported adjective, guarantee, or inferred result clause. End each "
            "sentence immediately after the behavior stated in the accepted fact; do not add "
            "guarantees, absolutes, downstream outcomes, or dependency claims."
        )
    if "product identity must preserve exact public name" in message:
        return "Replace the product spelling with the exact public name given in the accepted fact."
    if "structured fact coordinates" in message:
        return "Rewrite only the conflicting unit to agree literally with the structured values."
    return "Fix only the named acceptance failure."


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
