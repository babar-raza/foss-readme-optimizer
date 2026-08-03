"""Match constrained API claim shapes to exact public-surface fact coordinates."""

from __future__ import annotations

import hashlib
import json
import re

from readme_agent.readme.claim_accountability_api_index import api_coordinate_index
from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1

_CODE_SPAN = re.compile(r"`([^`]+)`")
_IDENTIFIER = r"(?<![A-Za-z0-9_]){}(?![A-Za-z0-9_])"
_API_SHELL = re.compile(
    r"(?is)^\s*[-+*]\s*(?:`[^`]+`(?:\s*[,;/]\s*`[^`]+`)*)\s*"
    r"(?:\(\s*has\s+a\s+`[^`]+`\s+field\s*\))?\s*$"
)
_MEMBER_SIGNATURE = re.compile(
    r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\((?P<parameters>[^)]*)\)"
    r"(?:\s*->\s*(?P<return>.+))?$"
)
_PROPERTY_SIGNATURE = re.compile(
    r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?:\s*(?::|->)\s*(?P<type>.+))?$"
)
_SYMBOL_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _coordinate(*, fact_id: str, path: str, value: object) -> StructuredFactCoordinateV1:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return StructuredFactCoordinateV1(
        fact_id=fact_id,
        field="api.public_surface",
        path=path,
        value_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    )


def _contains_identifier(text: str, identifier: str) -> bool:
    return re.search(_IDENTIFIER.format(re.escape(identifier)), text) is not None


def _parameter_names(value: str) -> list[tuple[str, bool]]:
    parameters = []
    for raw in value.split(",") if value.strip() else []:
        token = raw.strip()
        name = token.split("=", 1)[0].split(":", 1)[0].strip().lstrip("*")
        if name:
            parameters.append((name, "=" in token or token.startswith("*")))
    return parameters


def _compatible_member_reference(reference: str, surfaces: list[str]) -> bool:
    reference = reference.strip()
    call = _MEMBER_SIGNATURE.fullmatch(reference)
    if call is not None:
        for surface in surfaces:
            candidate = _MEMBER_SIGNATURE.fullmatch(surface)
            if candidate is None or candidate.group("name") != call.group("name"):
                continue
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
            claimed_return = (call.group("return") or "").strip()
            actual_return = (candidate.group("return") or "").strip()
            if not claimed_return or claimed_return == actual_return:
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


def _expanded_references(codes: list[str], member_names: set[str]) -> set[str]:
    references = {
        part.strip() for code in codes for part in re.split(r"\s*[,;]\s*", code) if part.strip()
    }
    expanded = set(references)
    for reference in references:
        if "/" not in reference:
            continue
        expanded.discard(reference)
        first, *raw_suffixes = reference.split("/")
        first_name = re.match(r"[A-Za-z_][A-Za-z0-9_]*", first)
        suffixes = {
            match.group(0)
            for raw in raw_suffixes
            if (match := re.match(r"[A-Za-z_][A-Za-z0-9_]*", raw.strip())) is not None
        }
        if first_name is None:
            continue
        expanded.add(first_name.group(0))
        for member_name in member_names:
            if member_name in suffixes:
                expanded.add(member_name)
                continue
            common_length = 0
            for left, right in zip(first_name.group(0), member_name, strict=False):
                if left != right:
                    break
                common_length += 1
            if common_length >= 2 and member_name[common_length:] in suffixes:
                expanded.add(member_name)
    return expanded


def api_structured_fact_coordinates(
    text: str,
    context: str,
    fact_id: str,
    value: object,
) -> list[StructuredFactCoordinateV1]:
    """Return coordinates only for a completely recognized API list-item shape."""

    if not isinstance(value, dict) or not _API_SHELL.fullmatch(text.strip()):
        return []
    index = api_coordinate_index(value)
    codes = _CODE_SPAN.findall(text)
    code = " ".join(codes)
    if not index.classes_by_name:
        return []
    references = _expanded_references(codes, set(index.all_member_names))
    symbol_tokens = set(_SYMBOL_TOKEN.findall(f"{context}\n{code}"))
    referenced_member_names = set(_SYMBOL_TOKEN.findall(" ".join(references)))
    member_coordinates: list[StructuredFactCoordinateV1] = []
    member_references: set[str] = set()
    fallback_coordinates: list[StructuredFactCoordinateV1] = []
    fallback_references: set[str] = set()
    for class_name in sorted(symbol_tokens & set(index.classes_by_name)):
        class_item = index.classes_by_name[class_name]
        members = class_item.get("members")
        member_groups: dict[str, list[dict]] = {}
        if isinstance(members, list):
            for member in members:
                if isinstance(member, dict) and isinstance(member.get("name"), str):
                    member_groups.setdefault(member["name"], []).append(member)
        matched_members = []
        for member_name in sorted(referenced_member_names & set(member_groups)):
            group = member_groups[member_name]
            surfaces = [
                member["surface"] for member in group if isinstance(member.get("surface"), str)
            ]
            matching_references = {
                reference
                for reference in references
                if _contains_identifier(reference, member_name)
                and _compatible_member_reference(reference, surfaces)
            }
            if matching_references:
                matched_members.append((member_name, group))
                member_references.update(matching_references)
        for member_name, group in matched_members:
            member_coordinates.append(
                _coordinate(
                    fact_id=fact_id,
                    path=f"/classes/{class_name}/members/{member_name}",
                    value={"class": class_name, "members": group},
                )
            )
        if matched_members:
            continue
        class_references = {
            reference
            for reference in references
            if reference == class_name or reference.endswith(f".{class_name}")
        }
        if class_references:
            fallback_coordinates.append(
                _coordinate(
                    fact_id=fact_id,
                    path=f"/classes/{class_name}",
                    value={
                        "name": class_name,
                        "source_path": class_item.get("source_path"),
                        "source_sha256": class_item.get("source_sha256"),
                    },
                )
            )
            fallback_references.update(class_references)
    if not member_coordinates:
        for export in sorted(symbol_tokens & set(index.modules_by_export)):
            if export in index.classes_by_name or not _contains_identifier(code, export):
                continue
            for module in index.modules_by_export[export]:
                module_name = str(module.get("module") or "")
                fallback_coordinates.append(
                    _coordinate(
                        fact_id=fact_id,
                        path=f"/modules/{module_name}/exports/{export}",
                        value={
                            "module": module_name,
                            "export": export,
                            "source_path": module.get("source_path"),
                        },
                    )
                )
                fallback_references.update(
                    reference for reference in references if _contains_identifier(reference, export)
                )
    if member_coordinates:
        return member_coordinates if references.issubset(member_references) else []
    return fallback_coordinates if references.issubset(fallback_references) else []
