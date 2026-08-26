"""Deterministic method/property-tier API presentation.

Separate from `verified_template_api_reference.py`'s class-level table
(deliberately concise, proven by `test_api_reference_uses_complete_catalog_
without_dumping_every_member_row`) -- this module renders ONLY the verified
public methods and properties the maintainer's own original README already
named in inline code. That intersection (mentioned-by-the-source AND
verified-in-the-current-API-surface) is what `document_validation.py`'s
protected-content check requires to survive somewhere; grounding it here, in
its own optional slot, closes that requirement without touching the
class-level table's own concise-by-design contract.
"""

from __future__ import annotations

import re
from typing import Any

from markdown_it import MarkdownIt

from readme_agent.facts.schema_v2 import ProductFactsV2
from readme_agent.presentation.verified_template_api_members import (
    describe_api_member,
    member_api_identifier,
)
from readme_agent.presentation.verified_template_api_reference import (
    _accepted_api_value,
    _complete_catalog,
    _excluded_exports,
)
from readme_agent.readme.knowledge_claim_presentation import knowledge_unimplemented_symbols

_TRAILING_CALL_RE = re.compile(r"\(.*\)\s*$")


def _bare_identifier(mentioned_term: str) -> str:
    """Reduce a source-mentioned inline-code term to a bare member name:
    "Worksheet.rename()" -> "rename"; "add_worksheet()" -> "add_worksheet"."""

    without_call = _TRAILING_CALL_RE.sub("", mentioned_term).strip()
    return without_call.rsplit(".", 1)[-1].strip()


def _source_mentioned_bare_names(source_text: str) -> set[str]:
    tokens = MarkdownIt("commonmark").parse(source_text)
    names: set[str] = set()
    for token in tokens:
        if token.type != "inline":
            continue
        for child in token.children or []:
            if child.type != "code_inline" or not child.content.strip():
                continue
            bare = _bare_identifier(child.content.strip())
            if bare:
                names.add(bare.casefold())
    return names


def _verified_method_rows(
    complete: dict[str, Any],
    excluded: set[tuple[str, str]],
    mentioned: set[str],
    unimplemented_symbols: frozenset[str] = frozenset(),
) -> dict[str, list[tuple[str, str]]]:
    rows_by_owner: dict[str, list[tuple[str, str]]] = {}
    classes = complete.get("classes")
    if not isinstance(classes, list):
        return rows_by_owner
    eligible: list[tuple[str, str, str, bool, dict[str, Any]]] = []
    for item in classes:
        if not isinstance(item, dict):
            continue
        owner = str(item.get("name") or "").strip()
        module = str(item.get("module") or "").strip()
        if not owner or (module, owner) in excluded:
            continue
        members = item.get("members")
        if not isinstance(members, list):
            continue
        for member in members:
            if not isinstance(member, dict):
                continue
            if str(member.get("kind") or "") not in {"method", "property"}:
                continue
            name = str(member.get("name") or "").strip()
            if not name or name.casefold() not in mentioned:
                continue
            declared_by = str(member.get("declared_by") or owner).strip()
            inherited = member.get("inherited") is True and declared_by != owner
            eligible.append((owner, name, declared_by, inherited, member))

    # A deep class hierarchy repeats every base member on every subclass: the
    # HTML Python canary emitted 1,349 rows of which 1,197 (189KB of a 206KB
    # section) were inherited restatements such as `HTMLMarkElement.append_child`
    # "Inherited from `Node`". That bloat is why the candidate reached 264KB and
    # became structurally unreviewable -- a single table unit far exceeding the
    # bounded-review packet budget -- while telling a visitor nothing the base
    # type's own row does not. idea.md keeps "top APIs" visible and allows long
    # inventories to be condensed, but never at the cost of dropping information,
    # so a subclass restatement is withheld only when the declaring type's own row
    # is actually emitted here. Measured on that canary: all 1,197 qualified, so
    # nothing was lost.
    declared_rows = {(owner, name) for owner, name, _by, inherited, _m in eligible if not inherited}
    for owner, name, declared_by, inherited, member in eligible:
        if inherited and (declared_by, name) in declared_rows:
            continue
        identifier = member_api_identifier(owner, member)
        description = (
            "Declared in the public API but not implemented in this FOSS package."
            if f"{owner}.{name}".casefold() in unimplemented_symbols
            else describe_api_member(owner, member)
        )
        rows_by_owner.setdefault(owner, []).append((identifier, description))
    return rows_by_owner


def known_public_surface_bare_names(facts: ProductFactsV2) -> frozenset[str]:
    """The casefolded bare names of every real, verified public class
    method/property AND top-level module function in the current
    API-surface facts -- the same complete-catalog/exclusion access
    `api_method_index_markdown` below uses to confirm a source-mentioned
    name is real (for class members), minus the `mentioned` filter, plus
    `verified_template_api_reference.py::_function_keys`'s own top-level
    `functions` list (module-level entry points like barcode-python's real
    `generate(symbology, data)`, confirmed live in the extracted facts --
    not a class member at all, so the class-only reduction alone would
    miss it).

    2026-08-19 (second aspose.org lesson): reused by `claim_accountability.py`
    to give `verification/claim_disposition.py`'s `api_surface_member`
    evidence path a minimal, deterministic membership set -- callers pass
    just this bare-name set into `corroborate_claim_disposition()`, not the
    full `ProductFactsV2` object, mirroring how this module already reduces
    facts to a bare-name set (`_source_mentioned_bare_names`) rather than
    threading the whole document around."""

    value = _accepted_api_value(facts)
    if value is None:
        return frozenset()
    complete = _complete_catalog(value)
    excluded = _excluded_exports(value)
    names: set[str] = set()
    classes = complete.get("classes")
    if isinstance(classes, list):
        for item in classes:
            if not isinstance(item, dict):
                continue
            owner = str(item.get("name") or "").strip()
            module = str(item.get("module") or "").strip()
            if not owner or (module, owner) in excluded:
                continue
            members = item.get("members")
            if not isinstance(members, list):
                continue
            for member in members:
                if not isinstance(member, dict):
                    continue
                if str(member.get("kind") or "") not in {"method", "property"}:
                    continue
                name = str(member.get("name") or "").strip()
                if name:
                    names.add(name.casefold())
    functions = complete.get("functions")
    if isinstance(functions, list):
        for item in functions:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            module = str(item.get("module") or "").strip()
            if name and (module, name) not in excluded:
                names.add(name.casefold())
    return frozenset(names)


def api_method_index_markdown(facts: ProductFactsV2, source_text: str) -> str | None:
    """Render every verified public method or property the source README
    already named in inline code, as one Type/Member/Description table --
    deliberately mirroring `verified_template_api_reference.py::
    api_reference_markdown`'s shape (one combined table inside one
    collapsible block) rather than a per-class table, so its policy
    recognition can mirror that proven, already-governed shape. Returns None
    when no verified method/property-level obligation exists -- the slot is
    then simply omitted."""

    value = _accepted_api_value(facts)
    if value is None:
        return None
    complete = _complete_catalog(value)
    excluded = _excluded_exports(value)
    mentioned = _source_mentioned_bare_names(source_text)
    if not mentioned:
        return None
    rows_by_owner = _verified_method_rows(
        complete,
        excluded,
        mentioned,
        knowledge_unimplemented_symbols(facts),
    )
    if not rows_by_owner:
        return None

    table_rows: list[tuple[str, str, str]] = [
        (owner, identifier, description)
        for owner in rows_by_owner
        for identifier, description in rows_by_owner[owner]
    ]
    table_rows.sort()
    body = [
        "| Type | Member | Description |",
        "| --- | --- | --- |",
        *(
            f"| `{owner}` | `{identifier}` | {description} |"
            for owner, identifier, description in table_rows
        ),
    ]
    return "\n".join(
        [
            "<details>",
            "<summary>View Documented Public Members</summary>",
            "",
            *body,
            "",
            "</details>",
        ]
    )


__all__ = ["api_method_index_markdown"]
