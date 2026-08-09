"""Bind golden-workflow claims to exact typed fact coordinates."""

from __future__ import annotations

import hashlib
import json
import re

from readme_agent.readme.claim_accountability_models import StructuredFactCoordinateV1

_FENCE = re.compile(r"(?s)^\s*```(?:bash|console|shell|sh)?\s*\n(?P<body>.*?)\n```\s*$", re.I)
_MARKDOWN = re.compile(r"[`*~]")


def _hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _coordinate(fact_id: str, path: str, value: object) -> StructuredFactCoordinateV1:
    return StructuredFactCoordinateV1(
        fact_id=fact_id,
        field="development.golden_workflow",
        path=path,
        value_sha256=_hash(value),
    )


def _plain(text: str) -> str:
    return " ".join(_MARKDOWN.sub("", text).casefold().split())


def _command_coordinates(
    text: str,
    fact_id: str,
    commands: list,
) -> list[StructuredFactCoordinateV1]:
    fence = _FENCE.fullmatch(text)
    command_text = " ".join((fence.group("body") if fence else text).split())
    folded = command_text.casefold()
    coordinates: list[StructuredFactCoordinateV1] = []
    grouped: dict[str, list[dict]] = {}
    for item in commands:
        if not isinstance(item, dict) or not item.get("kind") or not item.get("command"):
            continue
        grouped.setdefault(str(item["kind"]), []).append(item)
        exact = " ".join(str(item["command"]).split())
        case_id = str(item.get("case_id") or "")
        if exact == command_text or (
            item.get("kind") == "regenerate_selected"
            and case_id
            and f"--case {case_id}" in command_text
        ):
            suffix = f"/{case_id}" if case_id else ""
            coordinates.append(_coordinate(fact_id, f"/commands/{item['kind']}{suffix}", item))
    if fence is None:
        intent = None
        if folded.startswith(("regenerate selected", "to rebuild only selected")):
            intent = "regenerate_selected"
        elif folded.startswith(("regenerate", "regenerate the baselines")):
            intent = "regenerate_all"
        elif folded.startswith(("run the verification", "run the golden verification")):
            intent = "verify"
        elif folded.startswith("install the workflow"):
            intent = "install_requirements"
        if intent in grouped:
            coordinates.append(_coordinate(fact_id, f"/command_kinds/{intent}", grouped[intent]))
    return coordinates


def golden_workflow_fact_coordinates(
    text: str,
    fact_id: str,
    value: object,
) -> list[StructuredFactCoordinateV1]:
    """Return exact coordinates visibly supported by one workflow claim."""

    if not isinstance(value, dict):
        return []
    folded = _plain(text)
    coordinates = _command_coordinates(text, fact_id, value.get("commands", []))

    inventory = value.get("artifact_inventory")
    if isinstance(inventory, dict):
        root = str(inventory.get("root") or "")
        count = inventory.get("count")
        if root and root.casefold() in folded:
            coordinates.append(_coordinate(fact_id, "/artifact_inventory/root", root))
        if isinstance(count, int) and re.search(rf"\b{count}\s+golden\b", folded):
            coordinates.append(_coordinate(fact_id, "/artifact_inventory/count", count))

    comparison = str(value.get("comparison_mode") or "")
    if comparison and "semantic" in folded and "manifest" in folded:
        coordinates.append(_coordinate(fact_id, "/comparison_mode", comparison))

    failure_path = str(value.get("failure_output_path") or "")
    if failure_path and failure_path.casefold() in folded:
        coordinates.append(_coordinate(fact_id, "/failure_output_path", failure_path))

    for item in value.get("renderer_fallbacks", []):
        if isinstance(item, dict) and str(item.get("name") or "").casefold() in folded:
            coordinates.append(_coordinate(fact_id, f"/renderer_fallbacks/{item['name']}", item))
    visual = value.get("visual_diff_policy")
    if isinstance(visual, dict) and "visual" in folded:
        packages = [str(item) for item in visual.get("required_python_packages", [])]
        if all(item.casefold() in folded for item in packages):
            coordinates.append(_coordinate(fact_id, "/visual_diff_policy", visual))

    for item in value.get("environment_controls", []):
        if isinstance(item, dict) and str(item.get("name") or "").casefold() in folded:
            coordinates.append(_coordinate(fact_id, f"/environment_controls/{item['name']}", item))
    font = value.get("font_policy")
    if isinstance(font, dict):
        environment = str(font.get("environment_name") or "")
        default_visible = "built-in" in folded or "base-14" in folded
        unicode_visible = "unicode" in folded
        enabled_visible = environment.casefold() in folded and "system font" in folded
        if default_visible and (unicode_visible or enabled_visible):
            coordinates.append(_coordinate(fact_id, "/font_policy", font))

    if "pip install" in folded or "workflow dependencies" in folded:
        for item in value.get("dependency_groups", []):
            if not isinstance(item, dict) or not item.get("name"):
                continue
            name = str(item["name"])
            if re.search(rf"(?<![a-z0-9-]){re.escape(name.casefold())}(?![a-z0-9-])", folded):
                coordinates.append(_coordinate(fact_id, f"/dependency_groups/{name}", item))
    return sorted(set(coordinates), key=lambda item: (item.path, item.value_sha256))


__all__ = ["golden_workflow_fact_coordinates"]
