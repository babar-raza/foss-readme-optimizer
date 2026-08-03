"""Rank verified README examples by complete public-workflow value."""

from __future__ import annotations

import ast
import hashlib
from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from readme_agent.facts.example_quality import generated_example_quality_failures

_MAX_CODE_BYTES = 800
_MAX_NONEMPTY_LINES = 12
_ACCEPTED_VERIFICATION_STATES = {"verified", "policy_approved"}
_INPUT_OPERATIONS = {
    "from_bytes",
    "from_file",
    "from_stream",
    "load",
    "open",
    "parse",
    "read",
    "read_bytes",
    "read_text",
}
_MEANINGFUL_PREFIXES = (
    "add",
    "apply",
    "convert",
    "create",
    "delete",
    "extract",
    "merge",
    "redact",
    "remove",
    "render",
    "replace",
    "run",
    "save",
    "split",
    "to_",
    "transform",
    "write",
)
_OBSERVABLE_PREFIXES = ("export", "run", "save", "write")

ExampleClassification = Literal[
    "complete_workflow",
    "operation_without_observable_result",
    "setup_only",
    "invalid",
]
VerificationState = Literal["verified", "policy_approved", "unverified", "blocked"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExampleValueSignalsV1(_StrictModel):
    """Language-owned signals consumed by the ecosystem-neutral ranker."""

    has_input: bool = False
    has_meaningful_operation: bool = False
    has_observable_result: bool = False


class MinimalExampleValueV1(_StrictModel):
    """Deterministic value assessment for one exact snippet."""

    schema_version: Literal[1] = 1
    language: str
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    classification: ExampleClassification
    score: int = Field(ge=0, le=100)
    approval_eligible: bool
    signals: ExampleValueSignalsV1
    failures: list[str] = Field(default_factory=list)


class VerifiedExampleCandidateV1(_StrictModel):
    """One evidence-gated candidate offered to deterministic ranking."""

    candidate_id: str = Field(min_length=1)
    language: str = Field(min_length=1)
    code: str = Field(min_length=1)
    verification_state: VerificationState


class RankedExampleCandidateV1(_StrictModel):
    """One stable ranking row with an explicit rejection reason."""

    candidate_id: str
    rank: int = Field(ge=1)
    selectable: bool
    rejection_reason: str | None = None
    value: MinimalExampleValueV1


class MinimalExampleSelectionV1(_StrictModel):
    """Selection result that never promotes setup-only code over a complete workflow."""

    schema_version: Literal[1] = 1
    selected_candidate_id: str | None
    approval_eligible: bool
    ranked: list[RankedExampleCandidateV1]


ExampleValueEvaluator = Callable[[str], ExampleValueSignalsV1]


def _call_name(call: ast.Call) -> str:
    function = call.func
    if isinstance(function, ast.Name):
        return function.id.casefold()
    if isinstance(function, ast.Attribute):
        return function.attr.casefold()
    return ""


def _is_meaningful_operation(name: str) -> bool:
    return name not in _INPUT_OPERATIONS and name.startswith(_MEANINGFUL_PREFIXES)


def _python_value_signals(source: str) -> ExampleValueSignalsV1:
    """Inspect Python syntax without importing or executing repository code."""

    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    names = [_call_name(call) for call in calls]
    has_input = any(name in _INPUT_OPERATIONS for name in names)
    has_operation = any(_is_meaningful_operation(name) for name in names)
    observable_calls = [
        call
        for call in calls
        if _call_name(call).startswith(_OBSERVABLE_PREFIXES) or _call_name(call) == "print"
    ]
    has_observable = bool(observable_calls) or any(
        isinstance(node, ast.Return) and node.value is not None for node in ast.walk(tree)
    )
    return ExampleValueSignalsV1(
        has_input=has_input,
        has_meaningful_operation=has_operation,
        has_observable_result=has_observable,
    )


DEFAULT_EXAMPLE_VALUE_EVALUATORS: Mapping[str, ExampleValueEvaluator] = MappingProxyType(
    {"python": _python_value_signals}
)


def assess_minimal_example_value(
    language: str,
    source: str,
    *,
    evaluators: Mapping[str, ExampleValueEvaluator] = DEFAULT_EXAMPLE_VALUE_EVALUATORS,
) -> MinimalExampleValueV1:
    """Assess one snippet through shared bounds and one registered language evaluator."""

    normalized_language = language.strip().casefold()
    failures = generated_example_quality_failures(normalized_language, source)
    encoded = source.encode("utf-8")
    nonempty_lines = sum(bool(line.strip()) for line in source.splitlines())
    if len(encoded) > _MAX_CODE_BYTES:
        failures.append(
            f"minimal README example has {len(encoded)} bytes; maximum is {_MAX_CODE_BYTES}"
        )
    if nonempty_lines > _MAX_NONEMPTY_LINES:
        failures.append(
            "minimal README example has "
            f"{nonempty_lines} nonempty lines; maximum is {_MAX_NONEMPTY_LINES}"
        )
    evaluator = evaluators.get(normalized_language)
    if evaluator is None:
        failures.append(f"no example-value evaluator is registered for {normalized_language!r}")
        signals = ExampleValueSignalsV1()
    elif failures:
        signals = ExampleValueSignalsV1()
    else:
        try:
            signals = evaluator(source)
        except SyntaxError as exc:
            failures.append(f"minimal example value analysis failed: {exc.msg}")
            signals = ExampleValueSignalsV1()
    if failures:
        classification: ExampleClassification = "invalid"
        score = 0
    elif signals.has_meaningful_operation and signals.has_observable_result:
        classification = "complete_workflow"
        score = 80 + (10 if signals.has_input else 0) + 10
    elif signals.has_meaningful_operation:
        classification = "operation_without_observable_result"
        score = 55 + (10 if signals.has_input else 0)
    else:
        classification = "setup_only"
        score = 20 + (10 if signals.has_input else 0) + (5 if signals.has_observable_result else 0)
    return MinimalExampleValueV1(
        language=normalized_language,
        source_sha256=hashlib.sha256(encoded).hexdigest(),
        classification=classification,
        score=score,
        approval_eligible=classification == "complete_workflow",
        signals=signals,
        failures=failures,
    )


def rank_verified_minimal_examples(
    candidates: list[VerifiedExampleCandidateV1],
    *,
    evaluators: Mapping[str, ExampleValueEvaluator] = DEFAULT_EXAMPLE_VALUE_EVALUATORS,
) -> MinimalExampleSelectionV1:
    """Prefer the smallest highest-value verified workflow with stable tie breaking."""

    assessed = [
        (
            candidate,
            assess_minimal_example_value(
                candidate.language,
                candidate.code,
                evaluators=evaluators,
            ),
        )
        for candidate in candidates
    ]
    assessed.sort(
        key=lambda item: (
            item[0].verification_state not in _ACCEPTED_VERIFICATION_STATES,
            item[1].classification != "complete_workflow",
            -item[1].score,
            len(item[0].code.encode("utf-8")),
            item[0].candidate_id,
        )
    )
    complete_exists = any(
        candidate.verification_state in _ACCEPTED_VERIFICATION_STATES
        and value.classification == "complete_workflow"
        for candidate, value in assessed
    )
    rows: list[RankedExampleCandidateV1] = []
    for rank, (candidate, value) in enumerate(assessed, start=1):
        accepted = candidate.verification_state in _ACCEPTED_VERIFICATION_STATES
        selectable = accepted and value.classification != "invalid"
        reason = None
        if not accepted:
            selectable = False
            reason = "candidate is not verified or policy-approved"
        elif value.classification == "invalid":
            selectable = False
            reason = "candidate violates syntax, public-API, comment, or minimality constraints"
        elif complete_exists and value.classification != "complete_workflow":
            selectable = False
            reason = "stronger verified complete workflow is available"
        rows.append(
            RankedExampleCandidateV1(
                candidate_id=candidate.candidate_id,
                rank=rank,
                selectable=selectable,
                rejection_reason=reason,
                value=value,
            )
        )
    selected = next((row for row in rows if row.selectable), None)
    return MinimalExampleSelectionV1(
        selected_candidate_id=selected.candidate_id if selected else None,
        approval_eligible=bool(selected and selected.value.approval_eligible),
        ranked=rows,
    )
