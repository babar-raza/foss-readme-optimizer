"""Validate repository-example assurance wording against exact fact evidence."""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.assessment_claims import assess_material_claims
from readme_agent.readme.document_plan import CandidateContentProvenanceV1

_EXAMPLE_CONTEXT = re.compile(r"\b(?:example|workflow)s?\b", re.IGNORECASE)
_SYNTAX_CHECKED = re.compile(r"\bsyntax[- ]checked\b", re.IGNORECASE)
_API_MATCHED = re.compile(
    r"(?:\bmatched\s+to\b.{0,80}\bapi\b|\bstatic\s+public\s+api\s+checked\b)",
    re.IGNORECASE,
)
_EXECUTED = re.compile(r"\bexecuted\b", re.IGNORECASE)
_COMPILED = re.compile(r"\bcompiled\b", re.IGNORECASE)
_TESTED = re.compile(r"\b(?:runtime[- ]checked|tested)\b", re.IGNORECASE)
_NEGATED_ASSURANCE = re.compile(
    r"\b(?:not|never)\s+(?:executed|compiled|tested|runtime[- ]checked|syntax[- ]checked)"
    r"(?:\s+or\s+(?:executed|compiled|tested|runtime[- ]checked|syntax[- ]checked))*\b",
    re.IGNORECASE,
)
_ACCEPTED_STATES = {"verified", "policy_approved"}


def additional_examples_disclosure_fact_ids(
    claim_text: str,
    facts: ProductFactsV2,
) -> list[str]:
    """Bind generated disclosure wording only when the examples fact proves it."""

    try:
        fact = facts.selected_fact("repository.examples")
    except KeyError:
        return []
    if (
        fact.verification_state not in _ACCEPTED_STATES
        or fact.has_unresolved_conflict
        or not isinstance(fact.value, dict)
    ):
        return []
    folded = " ".join(claim_text.split()).casefold()
    inline = fact.value.get("inline_examples")
    files = fact.value.get("files")
    assets = fact.value.get("result_assets")
    if folded.startswith("| example source | verification |"):
        checks: list[bool] = []
        if "| inline workflows |" in folded:
            checks.append(
                isinstance(inline, list)
                and any(
                    isinstance(item, dict)
                    and item.get("static_api_verified") is True
                    and bool(str(item.get("code") or "").strip())
                    for item in inline
                )
            )
        if "| repository example files |" in folded:
            checks.append(
                isinstance(files, list)
                and any(
                    isinstance(item, dict) and bool(str(item.get("path") or "").strip())
                    for item in files
                )
            )
        if "| example result assets |" in folded:
            checks.append(
                isinstance(assets, list)
                and any(
                    isinstance(item, dict) and bool(str(item.get("path") or "").strip())
                    for item in assets
                )
            )
        supported = bool(checks) and all(checks)
    elif folded.startswith("the inline workflows below were syntax-checked"):
        supported = isinstance(inline, list) and any(
            isinstance(item, dict)
            and item.get("static_api_verified") is True
            and bool(str(item.get("code") or "").strip())
            for item in inline
        )
    elif folded.startswith("the repository example files below were inventoried"):
        supported = isinstance(files, list) and any(
            isinstance(item, dict) and bool(str(item.get("path") or "").strip()) for item in files
        )
    elif folded.startswith("the example result assets below were inventoried"):
        supported = isinstance(assets, list) and any(
            isinstance(item, dict) and bool(str(item.get("path") or "").strip()) for item in assets
        )
    else:
        supported = False
    return [fact.fact_id] if supported else []


def _selected_accepted_facts(
    facts: ProductFactsV2,
    fact_ids: set[str],
) -> list[FactRecordV2]:
    accepted: list[FactRecordV2] = []
    for fact_id in fact_ids:
        try:
            fact = facts.fact_by_id(fact_id)
        except KeyError:
            continue
        if (
            facts.selected_fact_ids.get(fact.field) == fact.fact_id
            and fact.verification_state in _ACCEPTED_STATES
            and not fact.has_unresolved_conflict
        ):
            accepted.append(fact)
    return accepted


def _example_rows(fact: FactRecordV2, keys: tuple[str, ...]) -> list[dict]:
    if fact.field != "repository.examples" or not isinstance(fact.value, dict):
        return []
    rows: list[dict] = []
    for key in keys:
        value = fact.value.get(key)
        if isinstance(value, list):
            rows.extend(item for item in value if isinstance(item, dict))
    return rows


def _positive_assurances(claim_text: str) -> set[str]:
    without_negations = _NEGATED_ASSURANCE.sub("", claim_text)
    assurances: set[str] = set()
    if _SYNTAX_CHECKED.search(without_negations):
        assurances.add("syntax")
    if _API_MATCHED.search(without_negations):
        assurances.add("api")
    if _EXECUTED.search(without_negations):
        assurances.add("execution")
    if _COMPILED.search(without_negations):
        assurances.add("compilation")
    if _TESTED.search(without_negations):
        assurances.add("testing")
    return assurances


def _assurance_scope_keys(claim_text: str) -> tuple[str, ...]:
    folded = " ".join(claim_text.split()).casefold()
    if "inline" in folded:
        return ("inline_examples",)
    if "repository example file" in folded:
        return ("files",)
    return ("inline_examples", "files")


def _facts_support_assurances(
    facts: list[FactRecordV2], assurances: set[str], claim_text: str
) -> bool:
    keys = _assurance_scope_keys(claim_text)
    rows = [row for fact in facts for row in _example_rows(fact, keys)]
    if not rows:
        return False
    predicates = {
        "syntax": lambda row: (
            row.get("syntax_verified") is True or row.get("static_api_verified") is True
        ),
        "api": lambda row: row.get("static_api_verified") is True,
        "execution": lambda row: row.get("execution_verified") is True,
        "compilation": lambda row: row.get("compilation_verified") is True,
        "testing": lambda row: (
            row.get("test_verified") is True or row.get("runtime_verified") is True
        ),
    }
    return all(all(predicates[assurance](row) for row in rows) for assurance in assurances)


def unsupported_example_assurance_claims(
    candidate_text: str,
    facts: ProductFactsV2,
    provenance: list[CandidateContentProvenanceV1],
) -> list[str]:
    """Return example claims whose verification wording lacks exact bound evidence."""

    candidate_bytes = candidate_text.encode("utf-8")
    unsupported: list[str] = []
    for claim in assess_material_claims(candidate_text):
        claim_text = candidate_bytes[claim.source_byte_start : claim.source_byte_end].decode(
            "utf-8"
        )
        if not _EXAMPLE_CONTEXT.search(claim_text):
            continue
        assurances = _positive_assurances(claim_text)
        if not assurances:
            continue
        fact_ids = {
            fact_id
            for binding in provenance
            if binding.candidate_byte_start < claim.source_byte_end
            and claim.source_byte_start < binding.candidate_byte_end
            for fact_id in binding.fact_ids
        }
        accepted = _selected_accepted_facts(facts, fact_ids)
        if not _facts_support_assurances(accepted, assurances, claim_text):
            unsupported.append(claim.claim_id)
    return sorted(unsupported)
