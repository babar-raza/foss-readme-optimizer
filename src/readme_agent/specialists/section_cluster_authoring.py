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
import re
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from readme_agent import env
from readme_agent.errors import LLMError, LLMTruncatedResponseError
from readme_agent.llm.analysis_client import AnalysisResult
from readme_agent.llm.call_ledger import record_non_provider_call
from readme_agent.llm.prompt_registry import prompt_hash
from readme_agent.llm.schema import Usage
from readme_agent.llm.section_authoring_prompts import (
    build_section_cluster_authoring_messages,
    build_section_cluster_authoring_tool_schema,
)
from readme_agent.readme.capability_semantics import is_action_led_capability_title
from readme_agent.readme.presentation_lint_public_contract import lint_public_contract
from readme_agent.readme.presentation_similarity import semantically_equivalent
from readme_agent.specialists.section_authoring_cache import (
    load_section_authoring_cache,
    section_authoring_cache_key,
    write_section_authoring_cache,
)
from readme_agent.specialists.section_authoring_contracts import (
    SectionAuthoringFactV1,
    SectionAuthoringOutcomeV1,
    SectionAuthoringPacketV1,
    SectionAuthoringReceiptV1,
    SectionClusterAuthoringResultV1,
)
from readme_agent.specialists.section_authoring_fact_validation import (
    enrich_directional_format_fact_ids,
    remove_reserved_directional_units,
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
    packet: SectionAuthoringPacketV1,
    result: SectionClusterAuthoringResultV1,
    *,
    enforce_sibling_separation: bool = True,
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
        fact_errors = section_authoring_fact_errors(
            packet,
            unit,
            enforce_sibling_separation=enforce_sibling_separation,
        )
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
            if semantically_equivalent(
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


def _reconcile_duplicate_fact_dispositions(
    result: SectionClusterAuthoringResultV1,
) -> SectionClusterAuthoringResultV1:
    """Discard redundant omissions for facts already used by an authored unit."""

    cited = {fact_id for unit in result.units for fact_id in unit.fact_ids}
    if not cited:
        return result
    reconciled_omissions = tuple(item for item in result.omitted if item.fact_id not in cited)
    if len(reconciled_omissions) == len(result.omitted):
        return result
    return result.model_copy(update={"omitted": reconciled_omissions})


_REMOVABLE_UNSUPPORTED_SUPERLATIVE = re.compile(
    r"\b(?:smallest|simplest)\s+possible\s+", re.IGNORECASE
)


def _remove_unsupported_superlatives(
    result: SectionClusterAuthoringResultV1,
) -> SectionClusterAuthoringResultV1:
    """Delete two closed-list modifiers that add no factual content.

    Qwen has repeatedly returned these exact prohibited phrases after receiving the targeted
    correction prompt. Removing only the modifiers leaves the fact-bearing noun phrase intact;
    the resulting unit still passes every normal structured-fact and public-contract check below.
    Broader guarantees remain fail-closed and continue through semantic repair.
    """

    units = tuple(
        unit.model_copy(update={"text": _REMOVABLE_UNSUPPORTED_SUPERLATIVE.sub("", unit.text)})
        for unit in result.units
    )
    return result.model_copy(update={"units": units})


def _itemized_capability_prompt_facts(
    packet: SectionAuthoringPacketV1,
) -> tuple[tuple[SectionAuthoringFactV1, str], ...]:
    """Expose list-valued capabilities as separate opaque aliases on recovery.

    The durable provenance ID remains the parent ProductFactsV2 fact. The aliases are
    provider-local coordinates only, allowing one bounded Qwen call to distinguish sibling
    entries without inventing a second fact graph or weakening post-call validation.
    """

    if packet.task_family != "capability_entry_cluster":
        return ()
    prompt_facts: list[SectionAuthoringFactV1] = []
    expanded = False
    for fact in packet.accepted_facts:
        items = (
            [item.strip() for item in fact.value if isinstance(item, str) and item.strip()]
            if isinstance(fact.value, list)
            else []
        )
        if len(items) < 2:
            prompt_facts.append(fact)
            continue
        expanded = True
        prompt_facts.extend(fact.model_copy(update={"value": item}) for item in items)
    if not expanded:
        return ()
    return tuple((fact, f"F{index}") for index, fact in enumerate(prompt_facts, start=1))


def _reconcile_itemized_alias_coverage(
    result: SectionClusterAuthoringResultV1,
    allowed_aliases: set[str],
) -> SectionClusterAuthoringResultV1:
    """Require an explicit item disposition before aliases collapse to parent facts."""

    cited = {fact_id for unit in result.units for fact_id in unit.fact_ids}
    omitted = {item.fact_id for item in result.omitted}
    unknown = (cited | omitted) - allowed_aliases
    if unknown:
        raise SectionAuthoringAcceptanceError(
            f"itemized capability recovery cited unsupported alias(es): {sorted(unknown)}"
        )
    fused_units = [
        unit.heading for unit in result.units if len(set(unit.fact_ids) & allowed_aliases) > 1
    ]
    if fused_units:
        raise SectionAuthoringAcceptanceError(
            "itemized capability recovery combined multiple sibling aliases in unit(s): "
            f"{fused_units}"
        )
    missing = allowed_aliases - cited - omitted
    if missing:
        raise SectionAuthoringAcceptanceError(
            f"itemized capability recovery left sibling alias(es) undisposed: {sorted(missing)}"
        )
    # Item aliases are provider-local recovery coordinates, not durable ProductFactsV2 IDs.
    # A cited sibling keeps the parent fact accountable; mapping an omitted sibling to that
    # same parent would falsely mark the complete parent fact both cited and omitted. The raw
    # response hash still binds the exact provider disposition.
    return result.model_copy(update={"omitted": ()})


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
    standard_prompt_facts = tuple(
        (fact, accepted_aliases[fact.fact_id]) for fact in packet.accepted_facts
    )
    itemized_prompt_facts = _itemized_capability_prompt_facts(packet)
    itemized_alias_to_fact_id = {alias: fact.fact_id for fact, alias in itemized_prompt_facts}
    schema = build_section_cluster_authoring_tool_schema(list(accepted_aliases.values()))
    schema_sha256 = (
        _canonical_hash(
            {
                "standard": schema,
                "itemized_capability_recovery": build_section_cluster_authoring_tool_schema(
                    [alias for _fact, alias in itemized_prompt_facts]
                ),
            }
        )
        if itemized_prompt_facts
        else _canonical_hash(schema)
    )
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
            record_non_provider_call(
                job=_PROMPT_ID,
                prompt_id=_PROMPT_ID,
                prompt_sha256=prompt_sha256,
                model=model,
                disposition="cache_reuse",
                request={
                    "cache_key": cache_key,
                    "packet_hash": packet_hash,
                    "target_section_id": packet.target_section_id,
                },
            )
            return cached.outcome.model_copy(update={"reused_from_cache": True})

    def build_messages(
        *,
        repair_hint: str = "",
        prompt_facts: tuple[tuple[SectionAuthoringFactV1, str], ...] = standard_prompt_facts,
    ) -> list[dict]:
        has_directional_formats = any(
            fact.field == "product.formats"
            for fact in (*packet.accepted_facts, *packet.do_not_claim)
        )
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
                        fact_id_alias=alias,
                        suppress_directionless_formats=has_directional_formats,
                    )
                    for fact, alias in prompt_facts
                ]
            ),
            do_not_claim_json=_canonical_json(
                [
                    authoring_fact_prompt_payload(
                        fact,
                        fact_id_alias=do_not_claim_aliases[fact.fact_id],
                        suppress_directionless_formats=has_directional_formats,
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
    accepted_rejected_unit_hashes: tuple[str, ...] = ()
    accepted_omitted_fact_ids: tuple[str, ...] = ()
    active_prompt_facts = standard_prompt_facts
    active_alias_to_fact_id = alias_to_fact_id
    itemized_recovery_active = False

    for attempt in range(1, _MAX_LOGICAL_ATTEMPTS + 1):
        active_aliases = [alias for _fact, alias in active_prompt_facts]
        try:
            analysis = client.analyze_section_cluster(messages, active_aliases)
        except LLMTruncatedResponseError as exc:
            last_error = exc
            if attempt == _MAX_LOGICAL_ATTEMPTS:
                break
            semantic_retry_used = True
            # A truncated response is a same-cluster conciseness-correction case, not a
            # transport failure -- reuses this loop's own retry/repair-hint machinery
            # rather than a client-level retry, matching how a schema/acceptance
            # failure is already handled below.
            #
            # fleet fan-out (2026-08-31): a conciseness instruction alone was not enough
            # for a large enough section (aspose-slides-foss/Aspose.Slides-FOSS-for-Java
            # truncated at ~10,770 characters against this client's 2048-token baseline --
            # the same "brevity reduces prompt bulk, not the true minimum output size"
            # gap already found and fixed for the whole-document composition call in
            # agentic_composition.py). Give the retry real headroom too, matching the
            # same 18000-token ceiling already proven for that call and for factual/
            # trusted review (reviewer_client.py) -- one consistent, already-validated
            # large-content ceiling project-wide, not a new arbitrary number. Guarded by
            # `hasattr` because `client` may be a test double that only implements the
            # `SectionClusterAuthorClientLike` Protocol's `analyze_section_cluster()`.
            if hasattr(client, "max_tokens"):
                client.max_tokens = max(client.max_tokens, 18000)
            messages = build_messages(
                repair_hint=(
                    f"Your previous submission (attempt {attempt}) was cut off before it "
                    "finished writing -- the response ran out of space and could not be "
                    "used. Cover the same facts and keep every disposition, but write "
                    "noticeably more concisely: shorter sentences, fewer or shorter units, "
                    "no unnecessary elaboration."
                ),
                prompt_facts=active_prompt_facts,
            )
            continue
        if analysis.meta.usage is not None:
            token_usage.append(analysis.meta.usage)
        if analysis.meta.latency_ms is not None:
            latency_ms.append(analysis.meta.latency_ms)
        try:
            provider_result = SectionClusterAuthoringResultV1.model_validate(analysis.parsed)
            if itemized_recovery_active:
                provider_result = _reconcile_itemized_alias_coverage(
                    provider_result, set(active_aliases)
                )
            parsed = enrich_directional_format_fact_ids(
                packet,
                _restore_fact_ids(provider_result, active_alias_to_fact_id),
            )
            parsed = _remove_unsupported_superlatives(parsed)
            parsed, rejected_unit_hashes, omitted_fact_ids = remove_reserved_directional_units(
                packet, parsed
            )
            # A fact that survives all structured unit checks is used. Qwen occasionally also
            # emits a stale omission for that same fact; keeping the validated use and dropping
            # only the redundant omission avoids an identical semantic retry without weakening
            # unknown-ID, unsupported-claim, or complete-disposition enforcement.
            parsed = _reconcile_duplicate_fact_dispositions(parsed)
            _validate_acceptance(
                packet,
                parsed,
                enforce_sibling_separation=not itemized_recovery_active,
            )
        except (ValidationError, SectionAuthoringAcceptanceError) as exc:
            last_error = exc
            if attempt == _MAX_LOGICAL_ATTEMPTS:
                break
            semantic_retry_used = True
            sibling_conflation = "combines" in str(exc) and "independent sibling items" in str(exc)
            if sibling_conflation and itemized_prompt_facts and not itemized_recovery_active:
                active_prompt_facts = itemized_prompt_facts
                active_alias_to_fact_id = itemized_alias_to_fact_id
                itemized_recovery_active = True
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
                    + (
                        "Each accepted capability item now has its own opaque alias. Cite each "
                        "alias in a separate unit and do not omit any alias. "
                        if itemized_recovery_active
                        else ""
                    )
                    + "Keep every unaffected unit and disposition unchanged."
                ),
                prompt_facts=active_prompt_facts,
            )
            continue
        result = parsed
        accepted_rejected_unit_hashes = rejected_unit_hashes
        accepted_omitted_fact_ids = omitted_fact_ids
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
        deterministically_rejected_unit_sha256=accepted_rejected_unit_hashes,
        deterministically_omitted_fact_ids=accepted_omitted_fact_ids,
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
    if "UTF-8 mojibake" in message:
        return (
            "Replace the corrupted characters with ordinary UTF-8 punctuation and preserve "
            "the supported meaning of the sentence."
        )
    if "unsupported quality, completeness, guarantee" in message:
        return (
            "Delete the unsupported adjective, guarantee, or inferred result clause. End each "
            "sentence immediately after the behavior stated in the accepted fact; do not add "
            "guarantees, absolutes, downstream outcomes, or dependency claims."
        )
    if "product identity must preserve exact public name" in message:
        return "Replace the product spelling with the exact public name given in the accepted fact."
    if "directional format prose must cite" in message:
        return (
            "Add the accepted product.formats fact alias to the fact_ids of every unit that "
            "states an input or output direction. Remove that alias from any unit that does not "
            "state its directional values."
        )
    if "directional format prose is reserved for deterministic rendering" in message:
        return (
            "Delete the entire format-direction unit and every format name from this cluster. "
            "Deterministic rendering owns that content; keep only the other accepted facts."
        )
    if "does not have cited direction support" in message:
        return (
            "Rewrite the format unit as separate input and output statements. List a format "
            "under input only when the accepted fact says 'Input format', and under output "
            "only when it says 'Output format'; never describe all formats as bidirectional."
        )
    if "combines" in message and "independent sibling items" in message:
        return (
            "Split the conflicting capability into separate units. Each unit must describe "
            "exactly one sibling item from the accepted list; do not join two sibling items "
            "with 'and', 'or', a slash, or an inferred relationship. The separate units may "
            "cite the same list fact alias."
        )
    if "structured fact coordinates" in message:
        return "Rewrite only the conflicting unit to agree literally with the structured values."
    return "Fix only the named acceptance failure."


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
