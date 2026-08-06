"""Parse constrained API-list grammar without granting factual authority."""

from __future__ import annotations

import re

_CODE_SPAN = re.compile(r"`([^`]+)`")
_ALLOWED_QUALIFIER = re.compile(r"(?is)\(\s*(?:save|load)\s+only\s*\)")
_ALLOWED_LINK_NOTE = re.compile(r"(?is)\(\s*see\s+\[[^]]+\]\([^)]+\)\s*\)")
_KEYFRAME_MEMBER_GROUP = re.compile(r"(?is)\btangent\s*/\s*weight\s+fields\b")
_CONTEXT_CLASS = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\([^)]*\))?$")
_PRIMITIVE_TO_MESH = re.compile(
    r"(?is)^each\s+exposes\s+`to_mesh\(\)\s*->\s*['\"]Mesh['\"]`\s+"
    r"to\s+convert\s+the\s+parameterized\s+primitive\s+into\s+a\s+concrete\s+mesh$"
)
_MEMBER_SIGNATURE = re.compile(
    r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\((?P<parameters>[^)]*)\)"
    r"(?:\s*->\s*(?P<return>.+))?$"
)
_PROPERTY_SIGNATURE = re.compile(
    r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\s*(?::|->)\s*(?P<type>.+))?$"
)
_CLASS_WITH_BASE = re.compile(
    r"^\s*`(?P<class>[A-Za-z_][A-Za-z0-9_]*)\((?P<base>[A-Za-z_][A-Za-z0-9_]*)\)`\s*$"
)
_CLASS_ROLE = re.compile(r"^\s*`(?P<class>[A-Za-z_][A-Za-z0-9_]*)`\s*\(base\)\s*$")
_CLASS_EXTENDS = re.compile(
    r"^\s*`(?P<class>[A-Za-z_][A-Za-z0-9_]*)`\s*"
    r"\(extends\s+`(?P<base>[A-Za-z_][A-Za-z0-9_]*)`\)\s*$"
)


def _parameter_names(value: str) -> list[tuple[str, bool]]:
    parameters = []
    for raw in value.split(",") if value.strip() else []:
        token = raw.strip()
        name = token.split("=", 1)[0].split(":", 1)[0].strip().lstrip("*")
        if name:
            parameters.append((name, "=" in token or token.startswith("*")))
    return parameters


def compatible_member_reference(reference: str, surfaces: list[str]) -> bool:
    """Require exact member ownership while treating empty calls as API-list shorthand."""

    reference = reference.strip()
    call = _MEMBER_SIGNATURE.fullmatch(reference)
    if call is not None:
        for surface in surfaces:
            candidate = _MEMBER_SIGNATURE.fullmatch(surface)
            if candidate is None or candidate.group("name") != call.group("name"):
                continue
            claimed_return = (call.group("return") or "").strip()
            actual_return = (candidate.group("return") or "").strip()
            if claimed_return and claimed_return != actual_return:
                continue
            if not call.group("parameters").strip() and not claimed_return:
                return True
            actual_parameters = _parameter_names(candidate.group("parameters"))
            claimed_parameters = _parameter_names(call.group("parameters"))
            if call.group("parameters").strip() == "...":
                claimed_parameters = []
            if [name for name, _ in claimed_parameters] != [
                name for name, _ in actual_parameters[: len(claimed_parameters)]
            ]:
                continue
            if any(not optional for _, optional in actual_parameters[len(claimed_parameters) :]):
                continue
            return True
        return False
    claimed = _PROPERTY_SIGNATURE.fullmatch(reference)
    if claimed is None:
        return False
    for surface in surfaces:
        candidate = _PROPERTY_SIGNATURE.fullmatch(surface)
        if candidate is None or candidate.group("name") != claimed.group("name"):
            continue
        claimed_type = (claimed.group("type") or "").strip()
        actual_type = (candidate.group("type") or "").strip()
        if not claimed_type or claimed_type == actual_type:
            return True
    return False


def member_surfaces(group: list[dict]) -> list[str]:
    """Return exact member surfaces, retaining separately collected return annotations."""

    surfaces: list[str] = []
    for member in group:
        surface = member.get("surface")
        if not isinstance(surface, str):
            continue
        annotation = member.get("return_annotation")
        surfaces.append(
            f"{surface} -> {annotation}"
            if isinstance(annotation, str) and annotation and "->" not in surface
            else surface
        )
    return surfaces


def class_headers(value: str) -> list[tuple[str, str | None, bool]] | None:
    """Parse only exact class-list, role, and explicit-inheritance header shapes."""

    for pattern in (_CLASS_WITH_BASE, _CLASS_EXTENDS):
        if match := pattern.fullmatch(value):
            return [(match.group("class"), match.group("base"), False)]
    if match := _CLASS_ROLE.fullmatch(value):
        return [(match.group("class"), None, True)]
    if not has_only_api_punctuation(value):
        return None
    headers: list[tuple[str, str | None, bool]] = []
    for reference, _ in coded_references(value):
        match = _CONTEXT_CLASS.fullmatch(reference)
        if match is None:
            return None
        headers.append((match.group("name"), None, False))
    return headers or None


def _split_references(code: str) -> list[str]:
    references: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(code):
        if character in "([":
            depth += 1
        elif character in ")]" and depth:
            depth -= 1
        elif character in ",;/" and depth == 0:
            if reference := code[start:index].strip():
                references.append(reference)
            start = index + 1
    if reference := code[start:].strip():
        references.append(reference)
    return references


def coded_references(value: str) -> list[tuple[str, str]]:
    """Return top-level code references paired with their following qualifier text."""

    matches = list(_CODE_SPAN.finditer(value))
    references: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        tail_end = matches[index + 1].start() if index + 1 < len(matches) else len(value)
        references.extend(
            (reference, value[match.end() : tail_end])
            for reference in _split_references(match.group(1))
        )
    return references


def has_only_api_punctuation(value: str, *, allow_qualifiers: bool = False) -> bool:
    """Reject prose that structured public-surface facts cannot prove."""

    residual = _CODE_SPAN.sub("", value)
    if allow_qualifiers:
        residual = _ALLOWED_QUALIFIER.sub("", residual)
        residual = _ALLOWED_LINK_NOTE.sub("", residual)
    return re.sub(r"[\s,;/()]+", "", residual) == ""


def context_classes(context: str, classes_by_name: dict[str, dict]) -> list[str]:
    """Resolve an exact parent class list without approving constructor syntax."""

    parent = next((line for line in reversed(context.splitlines()) if line.strip()), "")
    references = [reference for reference, _ in coded_references(parent)]
    names = []
    for reference in references:
        match = _CONTEXT_CLASS.fullmatch(reference)
        if match is None or match.group("name") not in classes_by_name:
            return []
        names.append(match.group("name"))
    return names


def is_matching_load_save_pair(class_names: list[str]) -> bool:
    """Allow unique ownership only for one same-family load/save options pair."""

    if len(class_names) != 2:
        return False
    load = next((name for name in class_names if name.endswith("LoadOptions")), None)
    save = next((name for name in class_names if name.endswith("SaveOptions")), None)
    return (
        load is not None
        and save is not None
        and load[: -len("LoadOptions")] == save[: -len("SaveOptions")]
    )


def is_primitive_to_mesh_claim(body: str) -> bool:
    """Recognize the one authorized primitive-group conversion claim."""

    return _PRIMITIVE_TO_MESH.fullmatch(body) is not None


def right_side_is_constrained(right: str, class_names: list[str]) -> bool:
    """Allow only structural punctuation plus the exact KeyFrame grouping label."""

    right = re.sub(r"(?is)^\s*adds\s+", "", right)
    if has_only_api_punctuation(right, allow_qualifiers=True):
        return True
    if class_names != ["KeyFrame"]:
        return False
    return has_only_api_punctuation(
        _KEYFRAME_MEMBER_GROUP.sub("", right),
        allow_qualifiers=True,
    )


__all__ = [
    "coded_references",
    "class_headers",
    "compatible_member_reference",
    "context_classes",
    "has_only_api_punctuation",
    "is_matching_load_save_pair",
    "is_primitive_to_mesh_claim",
    "member_surfaces",
    "right_side_is_constrained",
]
