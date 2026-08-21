"""Deterministic defense-in-depth: reject claim-map bindings that carry
capability wording for an `api.public_surface` member proven to be a stub.

This is independent of whichever renderer produced the candidate text
(`presentation/verified_template_api_members.py` is the current, primary
defense) -- a validator, not a generator, and it catches a regression in
any future generation path, not only the one this repo currently ships.
Symbol presence in the catalog is never itself capability authorization;
only a resolved `implemented is False` on the named member makes a
violation, matching `curated_python_api_ast.py::member_is_implemented`'s
own "absence of evidence is never a negative signal" contract -- an
unresolved/`None` member is never flagged here either.
"""

from __future__ import annotations

import re

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.readme.claim_map import ReadmeClaimMapV1

_CAPABILITY_VERB_RE = re.compile(
    r"\b(?:supports?|converts?|renders?|encodes?|decodes?|parses?|generates?|"
    r"serializes?|exports?|imports?)\b",
    re.IGNORECASE,
)


def _stub_members(facts: ProductFactsV2, fact_id: str) -> dict[str, set[str]]:
    try:
        fact = facts.fact_by_id(fact_id)
    except KeyError:
        return {}
    if not isinstance(fact.value, dict):
        return {}
    members: dict[str, set[str]] = {}
    for row in fact.value.get("classes") or []:
        if not isinstance(row, dict):
            continue
        for member in row.get("members") or []:
            if (
                isinstance(member, dict)
                and member.get("implemented") is False
                and isinstance(member.get("name"), str)
                and member["name"]
            ):
                name = member["name"].casefold()
                members.setdefault(name, set()).add(str(member.get("kind") or "member"))
    return members


def _mentions_stub_member(text: str, name: str, kinds: set[str]) -> bool:
    """Require an API-shaped code reference, not a coincidental prose/namespace token."""

    code_tokens = re.findall(r"`([^`\n]+)`", text)
    for token in code_tokens:
        if "method" in kinds and re.search(rf"(?i)(?:^|\.){re.escape(name)}\s*\(", token):
            return True
        if "method" not in kinds and re.search(rf"(?i)(?:^|\.){re.escape(name)}$", token.strip()):
            return True
    return False


def api_capability_claims_without_implementation_evidence(
    claim_map: ReadmeClaimMapV1,
    facts: ProductFactsV2,
    candidate_text: str,
) -> list[str]:
    """Return one violation description per claim-map binding whose bound
    text uses capability wording ("supports"/"converts"/"renders"/...) and
    names an `api.public_surface` member this run's own facts prove is an
    unimplemented stub. Scoped to `candidate_utf8`-space bindings -- newly
    rendered text, where a capability-authorization defect would actually
    originate; preserved source spans are a separate accountability
    concern this validator does not duplicate."""

    candidate_bytes = candidate_text.encode("utf-8")
    violations: list[str] = []
    for claim in claim_map.claims:
        if claim.field != "api.public_surface" or claim.coordinate_space != "candidate_utf8":
            continue
        stub_members = _stub_members(facts, claim.fact_id)
        if not stub_members:
            continue
        text = candidate_bytes[claim.byte_start : claim.byte_end].decode("utf-8", errors="ignore")
        if not _CAPABILITY_VERB_RE.search(text):
            continue
        for name, kinds in sorted(stub_members.items()):
            if _mentions_stub_member(text, name, kinds):
                violations.append(
                    f"{claim.claim_id}: capability wording for unimplemented member {name!r}"
                )
    return violations


__all__ = ["api_capability_claims_without_implementation_evidence"]
