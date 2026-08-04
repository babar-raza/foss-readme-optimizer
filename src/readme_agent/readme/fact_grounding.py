"""Locate exact fact phrases in generated or corrected README text."""

from __future__ import annotations

import re
from dataclasses import dataclass

from readme_agent.facts.render_views import visitor_fact_render_view
from readme_agent.facts.schema_v2 import ProductFactsV2


@dataclass(frozen=True)
class LiteralFactMatch:
    phrase: str
    character_start: int
    character_end: int
    line_start: int
    line_end: int


def fact_strings(value: object) -> list[str]:
    """Flatten nonempty fact strings without inventing display text."""

    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [text for item in value for text in fact_strings(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in fact_strings(item)]
    return []


def _typed_fact_strings(field: str, value: object) -> list[str]:
    """Expose only visitor-meaningful values from structured internal facts."""

    if isinstance(value, str):
        return fact_strings(value)
    if (
        field
        in {
            "product.capabilities",
            "product.formats",
            "product.limitations",
            "relationship.commercial_foss",
        }
        and isinstance(value, list)
        and all(isinstance(item, str) for item in value)
    ):
        return fact_strings(value)
    if not isinstance(value, dict):
        return []
    if field == "example.minimal":
        return fact_strings([value.get("code"), value.get("verified_public_symbols")])
    if field == "api.public_surface":
        modules = value.get("modules")
        if not isinstance(modules, list):
            return []
        exports: list[object] = []
        for module in modules:
            module_exports = module.get("exports") if isinstance(module, dict) else None
            if isinstance(module_exports, list):
                exports.extend(module_exports)
        classes = value.get("classes")
        member_surfaces: list[object] = []
        if isinstance(classes, list):
            for item in classes:
                members = item.get("members") if isinstance(item, dict) else None
                if not isinstance(members, list):
                    continue
                member_surfaces.extend(
                    member.get("surface") for member in members if isinstance(member, dict)
                )
        return fact_strings(
            [
                [module.get("module"), module.get("exports"), module.get("source_path")]
                for module in modules
                if isinstance(module, dict)
            ]
            + [f"{len(exports)} public exports", member_surfaces, value.get("mcp_server")]
        )
    if field == "repository.examples":
        files = value.get("files")
        return fact_strings(
            [
                [item.get("path") for item in files if isinstance(item, dict)]
                if isinstance(files, list)
                else [],
                value.get("inline_examples"),
                value.get("result_assets"),
            ]
        )
    if field == "development.assets":
        paths: list[str] = []
        labels = {"tests": "test files", "tools": "maintenance tools", "goldens": "golden assets"}
        for group, inventory in value.items():
            if not isinstance(inventory, dict):
                continue
            count = inventory.get("count")
            if isinstance(count, int) and group in labels:
                paths.append(f"{count} {labels[group]}")
            representatives = inventory.get("representative_paths")
            if not isinstance(representatives, list):
                continue
            paths.extend(
                str(item["path"])
                for item in representatives
                if isinstance(item, dict) and isinstance(item.get("path"), str)
            )
        commands = value.get("commands")
        if isinstance(commands, dict):
            paths.extend(fact_strings(commands.get("entries")))
        return paths
    if field == "repository.third_party_notices":
        return fact_strings(value.get("path"))
    if field == "installation.optional_extras":
        extras = value.get("extras")
        if not isinstance(extras, dict):
            return []
        return fact_strings([value.get("manifest_path"), list(extras), list(extras.values())])
    if field == "installation.capability_dependencies":
        entries = value.get("entries")
        if not isinstance(entries, list):
            return []
        return fact_strings(
            [
                [
                    item.get("distribution"),
                    item.get("purpose"),
                    item.get("install_command"),
                ]
                for item in entries
                if isinstance(item, dict)
            ]
        )
    if field == "python.distribution":
        marker = value.get("typed_marker")
        return fact_strings(
            [
                value.get("manifest_path"),
                value.get("requires_python"),
                value.get("runtime_dependencies"),
                value.get("development_status"),
                marker.get("path") if isinstance(marker, dict) else None,
            ]
        )
    if field == "development.commands":
        entries = value.get("entries")
        if not isinstance(entries, list):
            return []
        return fact_strings(
            [
                [
                    item.get("command"),
                    item.get("embedded_commands"),
                    [
                        source.get("path")
                        for source in item.get("sources", [])
                        if isinstance(source, dict)
                    ]
                    if isinstance(item.get("sources"), list)
                    else [],
                ]
                for item in entries
                if isinstance(item, dict)
            ]
        )
    if field == "repository.documentation_assets":
        entries = value.get("entries")
        if not isinstance(entries, list):
            return []
        return fact_strings([item.get("path") for item in entries if isinstance(item, dict)])
    if field == "repository.contribution_guidance":
        scripts = value.get("validation_scripts")
        return fact_strings(
            [
                value.get("path"),
                [item.get("path") for item in scripts if isinstance(item, dict)]
                if isinstance(scripts, list)
                else [],
            ]
        )
    if field == "repository.security_guidance":
        policy = value.get("policy")
        limits = value.get("resource_limits")
        limit_fields = limits.get("fields") if isinstance(limits, dict) else None
        limit_methods = limits.get("methods") if isinstance(limits, dict) else None
        entry_points = limits.get("entry_points") if isinstance(limits, dict) else None
        guidance = value.get("operational_guidance")
        operational: list[str] = []
        if isinstance(guidance, dict):
            if guidance.get("lazy_work_uses_shared_limits") is True:
                operational.append(
                    "Lazy decoding and streaming work continue to consume the document's shared "
                    "resource limits."
                )
            if guidance.get("unlimited_disables_safeguards") is True:
                operational.append(
                    "`PdfLoadLimits.unlimited()` disables every safeguard and is appropriate "
                    "only for trusted input with external resource controls."
                )
            if guidance.get("limits_are_not_a_complete_dos_sandbox") is True:
                statement = (
                    "These limits reduce known parser and allocation risks but are not a complete "
                    "denial-of-service sandbox."
                )
                if guidance.get("isolate_highly_hostile_documents") is True:
                    statement += " Isolate highly hostile PDF workloads at the process boundary."
                operational.append(statement)
        return fact_strings(
            [
                [policy.get("path"), policy.get("private_reporting_url")]
                if isinstance(policy, dict)
                else [],
                [
                    limits.get("class"),
                    limit_fields,
                    limit_methods,
                    entry_points,
                    f"{len(limit_fields)} source-defined limits"
                    if isinstance(limit_fields, list) and limit_fields
                    else None,
                ]
                if isinstance(limits, dict)
                else [],
                operational,
            ]
        )
    if field == "installation.verified_acquisition":
        coordinate = value.get("coordinate")
        return fact_strings(coordinate) if isinstance(coordinate, dict) else []
    if field == "product.limitations":
        return fact_strings(value.get("statement"))
    return []


def _structured_rows(field: str, value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    if field == "release.state":
        return fact_strings([row.get("version") for row in value if isinstance(row, dict)])
    return []


def _maven_dependency_matches(text: str, coordinate: dict) -> bool:
    stripped = text.strip()
    if not stripped.startswith("```") or not stripped.endswith("```"):
        return False
    expected = {
        "groupId": coordinate.get("group_id"),
        "artifactId": coordinate.get("artifact_id"),
        "version": coordinate.get("version"),
    }
    if not all(isinstance(value, str) and value.strip() for value in expected.values()):
        return False
    dependencies = re.findall(
        r"<dependency(?:\s[^>]*)?>(.*?)</dependency\s*>",
        stripped,
        flags=re.DOTALL | re.IGNORECASE,
    )
    for dependency in dependencies:
        actual = {}
        for tag in expected:
            match = re.search(
                rf"<{tag}\s*>\s*([^<]+?)\s*</{tag}\s*>",
                dependency,
                flags=re.IGNORECASE,
            )
            actual[tag] = match.group(1).strip() if match is not None else None
        if actual == expected:
            return True
    return False


def _exact_coordinate_match(text: str, value: object) -> bool:
    rows = value if isinstance(value, list) else [value]
    stripped = text.strip()
    if any(
        stripped == str(row.get("version") or "").strip()
        for row in rows
        if isinstance(row, dict) and str(row.get("version") or "").strip()
    ):
        return True
    return any(
        _maven_dependency_matches(text, row)
        for row in rows
        if isinstance(row, dict)
        and str(row.get("ecosystem") or "").strip().casefold() in {"java", "maven"}
    )


def find_literal_fact_match(text: str, value: object) -> LiteralFactMatch | None:
    """Find the earliest literal fact phrase and its containing line."""

    folded = text.casefold()
    matches: list[tuple[int, str]] = []
    for phrase in fact_strings(value):
        folded_phrase = phrase.casefold()
        if len(phrase) >= 4:
            start = folded.find(folded_phrase)
            if start >= 0:
                matches.append((start, phrase))
            continue
        if len(phrase) < 2:
            continue
        match = re.search(
            rf"(?<![A-Za-z0-9]){re.escape(phrase)}(?![A-Za-z0-9])",
            text,
            flags=re.IGNORECASE,
        )
        if match is not None:
            matches.append((match.start(), phrase))
    if not matches:
        return None
    start, phrase = min(matches, key=lambda item: (item[0], -len(item[1])))
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", start + len(phrase))
    if line_end < 0:
        line_end = len(text)
    return LiteralFactMatch(
        phrase=phrase,
        character_start=start,
        character_end=start + len(phrase),
        line_start=line_start,
        line_end=line_end,
    )


def literal_fact_ids(
    text: str,
    facts: ProductFactsV2,
    fact_ids: list[str],
) -> list[str]:
    """Keep only fact IDs whose selected value is literally present in text."""

    matched: set[str] = set()
    for fact_id in fact_ids:
        fact = facts.fact_by_id(fact_id)
        if fact.field == "installation.coordinates":
            if _exact_coordinate_match(text, fact.value):
                matched.add(fact_id)
            continue
        view = visitor_fact_render_view(facts, fact.field)
        value = (
            view.phrases
            if view is not None and view.fact_id == fact_id and view.phrases
            else [
                *_typed_fact_strings(fact.field, fact.value),
                *_structured_rows(fact.field, fact.value),
            ]
        )
        if find_literal_fact_match(text, value) is not None:
            matched.add(fact_id)
    return sorted(matched)
