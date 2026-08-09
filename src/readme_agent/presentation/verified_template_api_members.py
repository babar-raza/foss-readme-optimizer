"""Render exact Python API member signatures and visitor-facing descriptions."""

from __future__ import annotations

import re
from typing import Any

from readme_agent.presentation.verified_template_api_text import public_noun

_LOW_VALUE_MEMBERS = {
    "Count",
    "Current",
    "Document",
    "FirstChild",
    "GetEnumerator",
    "IsReadOnly",
    "LastChild",
    "ParentNode",
}
_EMPTY_ACTIONS = {"add", "all", "as", "ascend", "begin", "do", "from", "get", "set"}
_EMPTY_OBJECTS = {"all", "object", "objects", "value", "values"}
_TRAILING_PREPOSITIONS = {
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "to",
    "with",
}
_EXACT_METHOD_PHRASES = {
    "Accept": "traversing content with a visitor",
    "AppendChild": "appending child nodes",
    "AsBytes": "serializing content to bytes",
    "AutoTag": "tagging document content automatically",
    "Clear": "clearing content",
    "Clone": "cloning content",
    "CopyTo": "copying the current value to a destination",
    "Create": "creating document instances",
    "EncryptionPasswordAllowsAccess": "checking encryption-password access",
    "GetChildNodes": "retrieving child nodes",
    "IndexOf": "locating items",
    "IsByteArray": "checking for byte-array results",
    "IsString": "checking for string results",
    "Process": "processing documents",
    "Save": "saving document output",
    "SetLicense": "configuring package licensing",
    "SetMeteredKey": "configuring metered licensing keys",
    "ToDict": "serializing values to a dictionary",
    "ToPng": "encoding page content as PNG",
}


def _words(value: str) -> list[str]:
    expanded = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    expanded = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", expanded).replace("_", " ")
    return expanded.split()


def _gerund(verb: str) -> str:
    if verb.endswith("ie"):
        return verb[:-2] + "ying"
    if verb.endswith("e") and verb not in {"see"}:
        return verb[:-1] + "ing"
    return verb + "ing"


def _plural_object(value: str) -> str:
    words = value.split()
    if not words:
        return value
    exact = {"box": "boxes", "checkbox": "checkboxes", "child": "children"}
    tail = words[-1]
    if tail in exact:
        words[-1] = exact[tail]
    elif tail.endswith("y") and not tail.endswith(("ay", "ey", "iy", "oy", "uy")):
        words[-1] = tail[:-1] + "ies"
    elif not tail.endswith("s"):
        words[-1] = tail + "s"
    return " ".join(words)


def method_phrase(name: str) -> str | None:
    """Return a complete action phrase, or none when the identifier cannot support one."""

    compact = name.replace("_", "")
    for exact, phrase in _EXACT_METHOD_PHRASES.items():
        if compact.casefold() == exact.casefold():
            return phrase
    words = [word.casefold() for word in _words(name)]
    if not words:
        return None
    verb, remainder = words[0], public_noun(" ".join(words[1:]))
    if remainder.casefold() in _EMPTY_OBJECTS:
        return None
    if verb in _EMPTY_ACTIONS and not remainder:
        return None
    if remainder.split()[-1:] and remainder.split()[-1] in _TRAILING_PREPOSITIONS:
        return None
    if verb == "as":
        return f"serializing content as {remainder}"
    if verb == "from":
        return f"loading content from {remainder}"
    if verb == "is":
        return f"checking whether {remainder}"
    if verb == "to":
        return f"converting content to {remainder}"
    if verb == "add":
        return f"adding {_plural_object(remainder)}"
    if verb == "append":
        return f"appending {remainder or 'content'}"
    if verb == "build":
        return f"building {remainder or 'output'}"
    if verb == "clear":
        return f"clearing {remainder or 'content'}"
    if verb == "clone":
        return f"cloning {remainder or 'content'}"
    if verb == "create":
        return f"creating {remainder or 'instances'}"
    if verb == "default":
        return f"creating default {remainder or 'values'}"
    if verb == "detect":
        return f"detecting {remainder or 'changes'}"
    if verb == "get":
        return f"retrieving {remainder}"
    if verb == "has":
        return f"checking for {remainder or 'content'}"
    if verb == "insert":
        return f"inserting {remainder or 'content'}"
    if verb == "load":
        return f"loading {remainder or 'content'}"
    if verb == "open":
        return f"opening {remainder or 'content'}"
    if verb == "read":
        return f"reading {remainder or 'content'}"
    if verb == "remove":
        return f"removing {remainder or 'content'}"
    if verb == "replace":
        return f"replacing {remainder or 'content'}"
    if verb == "save":
        return f"saving {remainder or 'output'}"
    if verb == "set":
        return f"setting {remainder}"
    if verb == "visit":
        if remainder.endswith(" start"):
            return f"starting a visit to {remainder.removesuffix(' start')}"
        if remainder.endswith(" end"):
            return f"finishing a visit to {remainder.removesuffix(' end')}"
        return f"visiting {remainder or 'content'}"
    if verb == "write":
        return f"writing {remainder or 'output'}"
    return f"{_gerund(verb)} {remainder}" if remainder else None


def _member_rows(item: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    members = item.get("members")
    if not isinstance(members, list):
        return []
    rows: list[tuple[int, dict[str, Any]]] = []
    for member in members:
        if not isinstance(member, dict):
            continue
        name = str(member.get("name") or "").strip()
        if not name:
            continue
        score = 20 if member.get("inherited") is True else 0
        score += 10 if str(member.get("kind") or "") != "method" else 0
        score += 30 if name in _LOW_VALUE_MEMBERS else 0
        score += 5 if name.endswith("End") else 0
        rows.append((score, member))
    return sorted(rows, key=lambda row: (row[0], str(row[1]["name"]).casefold()))


def summarize_api_members(item: dict[str, Any], *, limit: int = 3) -> list[str]:
    """Return a bounded class overview; full details remain in member table rows."""

    actions: list[str] = []
    for _score, member in _member_rows(item):
        if str(member.get("kind") or "") != "method":
            continue
        phrase = method_phrase(str(member.get("name") or "").strip())
        if phrase and phrase not in actions:
            actions.append(phrase)
        if len(actions) == limit:
            break
    return actions


def _member_surface(member: dict[str, Any]) -> str:
    name = str(member.get("name") or "").strip()
    surface = " ".join(str(member.get("surface") or name).split())
    annotation = str(member.get("return_annotation") or "").strip()
    if annotation and str(member.get("kind") or "") == "method" and " -> " not in surface:
        surface += f" -> {annotation}"
    return surface


def member_api_identifier(owner: str, member: dict[str, Any]) -> str:
    """Return the exact class-qualified member signature for a README table."""

    surface = _member_surface(member)
    return f"{owner}.{surface}" if surface else owner


def describe_api_member(
    owner: str,
    member: dict[str, Any],
    *,
    case_variant_of: str | None = None,
) -> str:
    """Describe one public class member without turning its name into fragmentary prose."""

    name = str(member.get("name") or "").strip()
    kind = str(member.get("kind") or "").strip()
    declared_by = str(member.get("declared_by") or owner).strip()
    inherited = member.get("inherited") is True and declared_by != owner
    origin = f" Inherited from `{declared_by}`." if inherited else ""
    if case_variant_of is not None:
        return (
            f"Exposes the `{name}` entry point alongside `{case_variant_of}` on `{owner}`." + origin
        )
    if kind == "method":
        phrase = method_phrase(name)
        description = (
            f"Calls the `{name}` operation on `{owner}`."
            if phrase is None
            else f"Supports {phrase} through `{owner}`."
        )
        return description + origin
    if kind == "enum_member":
        return f"Selects the `{name}` value from the `{owner}` enumeration." + origin
    if kind == "property":
        access = "Gets or sets" if member.get("writable") is True else "Gets"
        return f"{access} the `{name}` property on `{owner}`." + origin
    if kind == "typed_field":
        return f"Stores the `{name}` field on `{owner}`." + origin
    return f"Exposes the `{name}` member on `{owner}`." + origin


__all__ = [
    "describe_api_member",
    "member_api_identifier",
    "method_phrase",
    "summarize_api_members",
]
