"""Deterministic method-tier API presentation.

Separate from `verified_template_api_reference.py`'s class-level table
(deliberately concise, proven by `test_api_reference_uses_complete_catalog_
without_dumping_every_member_row`) -- this module renders ONLY the verified
public methods the maintainer's own original README already named in inline
code. That intersection (mentioned-by-the-source AND verified-in-the-current-
API-surface) is what `document_validation.py`'s protected-content check
requires to survive somewhere; grounding it here, in its own optional slot,
closes that requirement without touching the class-level table's own
concise-by-design contract.
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
    complete: dict[str, Any], excluded: set[tuple[str, str]], mentioned: set[str]
) -> dict[str, list[tuple[str, str]]]:
    rows_by_owner: dict[str, list[tuple[str, str]]] = {}
    classes = complete.get("classes")
    if not isinstance(classes, list):
        return rows_by_owner
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
            if str(member.get("kind") or "") != "method":
                continue
            name = str(member.get("name") or "").strip()
            if not name or name.casefold() not in mentioned:
                continue
            identifier = member_api_identifier(owner, member)
            description = describe_api_member(owner, member)
            rows_by_owner.setdefault(owner, []).append((identifier, description))
    return rows_by_owner


def api_method_index_markdown(facts: ProductFactsV2, source_text: str) -> str | None:
    """Render every verified public method the source README already named
    in inline code, as one Type/Member/Description table -- deliberately
    mirroring `verified_template_api_reference.py::api_reference_markdown`'s
    shape (one combined table inside one collapsible block) rather than a
    per-class table, so its policy recognition can mirror that proven,
    already-governed shape. Returns None when no verified method-level
    obligation exists -- the slot is then simply omitted."""

    value = _accepted_api_value(facts)
    if value is None:
        return None
    complete = _complete_catalog(value)
    excluded = _excluded_exports(value)
    mentioned = _source_mentioned_bare_names(source_text)
    if not mentioned:
        return None
    rows_by_owner = _verified_method_rows(complete, excluded, mentioned)
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
            "<summary>View documented public methods</summary>",
            "",
            *body,
            "",
            "</details>",
        ]
    )


__all__ = ["api_method_index_markdown"]
