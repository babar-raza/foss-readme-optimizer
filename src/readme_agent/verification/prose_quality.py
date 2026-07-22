"""A narrow, corroborated LLM signal layered ADDITIVELY onto the existing
deterministic verification gate (Wave 8.6, `VER-006` reversal) -- never a
replacement of it, and never trusted at face value.

Resolves the "who verifies the verifier" regress the prior decision named,
by construction rather than assertion: the LLM is never granted the
"sole authority accepting" role `VER-001` reserves for the deterministic
gate (`verification/checks.py::independently_verify_readme_candidate()`,
untouched by this module). It only ever produces a narrow, falsifiable
claim (`flagged`, `quoted_span`, `reason`), which `corroborate_prose_
finding()` -- plain, deterministic code -- checks before it can affect
anything: does `quoted_span` appear verbatim in the one span the LLM was
actually shown? An uncorroborated (hallucinated or out-of-scope) claim is
discarded before it ever reaches a verdict.

Scope is deliberately narrow: this only ever judges `RDM-020`'s already-
named gap (generic/repetitive/mechanically-inserted prose) in the one
`resources` span an LLM call actually authored -- never facts the
deterministic checks already own (license, links, required elements stay
deterministic-only, forever, by design)."""

from readme_agent.llm.verification_prompts import (
    PROSE_QUALITY_TOOL_SCHEMA,
    build_prose_quality_messages,
)
from readme_agent.llm.verifier_client import ForcedToolClient
from readme_agent.readme.markers import find_span


def corroborate_prose_finding(span_text: str, llm_result: dict) -> dict:
    """Pure, deterministic. A flagged finding is only corroborated if its
    `quoted_span` appears verbatim in the exact text the LLM was shown --
    the structural answer to "who verifies the verifier": this check, not
    the LLM's own say-so, is what makes a finding actionable."""
    flagged = bool(llm_result.get("flagged"))
    reason = str(llm_result.get("reason") or "")
    if not flagged:
        return {"flagged": False, "corroborated": False, "quoted_span": "", "reason": reason}
    quoted_span = str(llm_result.get("quoted_span") or "")
    corroborated = bool(quoted_span) and quoted_span in span_text
    return {
        "flagged": True,
        "corroborated": corroborated,
        "quoted_span": quoted_span,
        "reason": reason,
    }


def check_prose_quality(final_text: str, client: ForcedToolClient | None) -> dict:
    """Extracts the one span an LLM call actually authored (`resources`)
    and asks one narrow, forced-tool-call question about it.

    `client=None` (no verifier configured for this run) degrades honestly:
    never flags, never crashes -- this check is additive, not required for
    the deterministic gate to function. A real `LLMError` from `client`
    (timeout, malformed response, HTTP failure) is deliberately NOT caught
    here -- it propagates to the caller, which must let it flow into the
    normal `execution_error`/repair machinery, never silently treated as
    accept or reject."""
    if client is None:
        return {
            "flagged": False,
            "corroborated": False,
            "quoted_span": "",
            "reason": "no verifier client configured",
        }

    span = find_span(final_text, "resources")
    if span is None:
        return {
            "flagged": False,
            "corroborated": False,
            "quoted_span": "",
            "reason": "no resources span present -- nothing LLM-authored to review",
        }

    messages = build_prose_quality_messages(span.content)
    result = client.call(
        messages, PROSE_QUALITY_TOOL_SCHEMA
    )  # LLMError propagates, deliberately uncaught
    return corroborate_prose_finding(span.content, result.arguments)
