"""Render optional verified fact families into reusable README template sections."""

from __future__ import annotations

from readme_agent.facts.example_quality import strip_source_comments
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2

_ACCEPTED = {"verified", "policy_approved"}


def _accepted(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    try:
        fact = facts.selected_fact(field)
    except KeyError:
        return None
    if fact.verification_state not in _ACCEPTED or fact.has_unresolved_conflict:
        return None
    return fact


def _details(summary: str, body: list[str]) -> str:
    return "\n".join(["<details>", f"<summary>{summary}</summary>", "", *body, "", "</details>"])


def optional_extras_markdown(facts: ProductFactsV2) -> str | None:
    """Render exact package extras without assigning an inferred purpose to them."""

    extras_fact = _accepted(facts, "installation.optional_extras")
    coordinates = _accepted(facts, "installation.coordinates")
    if extras_fact is None or coordinates is None or not isinstance(extras_fact.value, dict):
        return None
    extras = extras_fact.value.get("extras")
    if not isinstance(extras, dict) or not extras:
        return None
    rows = coordinates.value if isinstance(coordinates.value, list) else [coordinates.value]
    package = next(
        (
            str(row.get("name"))
            for row in rows
            if isinstance(row, dict) and str(row.get("name") or "").strip()
        ),
        None,
    )
    if not package:
        return None
    acquisition = _accepted(facts, "installation.verified_acquisition")
    acquisition_value = acquisition.value if acquisition is not None else None
    install_target = (
        "."
        if isinstance(acquisition_value, dict) and acquisition_value.get("method") == "source_build"
        else package
    )
    manifest_path = str(extras_fact.value.get("manifest_path") or "pyproject.toml")
    lines = [f"Optional dependency groups declared in `{manifest_path}`:"]
    for name in sorted(str(item) for item in extras):
        lines.append(f'- `{name}`: `python -m pip install "{install_target}[{name}]"`')
    return "\n".join(lines)


def dependency_markdown(facts: ProductFactsV2) -> str | None:
    """Render only manifest or source-bound Python dependency coordinates."""

    sections: list[str] = []
    distribution = _accepted(facts, "python.distribution")
    if distribution is not None and isinstance(distribution.value, dict):
        dependencies = distribution.value.get("runtime_dependencies")
        if isinstance(dependencies, list) and dependencies:
            sections.append(
                "Required runtime dependencies declared in `pyproject.toml`: "
                + ", ".join(f"`{item}`" for item in dependencies if isinstance(item, str))
                + "."
            )
    capabilities = _accepted(facts, "installation.capability_dependencies")
    if capabilities is not None and isinstance(capabilities.value, dict):
        entries = capabilities.value.get("entries")
        if isinstance(entries, list) and entries:
            lines: list[str] = []
            for item in entries:
                if not isinstance(item, dict) or not item.get("install_command"):
                    continue
                purpose = str(item.get("purpose") or "Optional capability")
                lines.append(f"- {purpose}: `{item['install_command']}`")
            if lines:
                sections.append("\n".join(lines))
    return "\n\n".join(sections) or None


def package_status_markdown(facts: ProductFactsV2) -> str | None:
    """Render manifest-bound maturity and typing status."""

    fact = _accepted(facts, "python.distribution")
    if fact is None or not isinstance(fact.value, dict):
        return None
    statements: list[str] = []
    status = str(fact.value.get("development_status") or "").strip()
    if status:
        statements.append(f"The package manifest classifies this release as **{status}**.")
    typed = fact.value.get("typed_marker")
    if fact.value.get("typed_classifier") is True and isinstance(typed, dict):
        path = str(typed.get("path") or "").strip()
        if path:
            statements.append(f"The distribution includes the [`{path}`]({path}) type marker.")
    return " ".join(statements) or None


def repository_documents_markdown(facts: ProductFactsV2) -> str | None:
    """Render exact checksum-bound repository documentation links."""

    fact = _accepted(facts, "repository.documentation_assets")
    if fact is None or not isinstance(fact.value, dict):
        return None
    entries = fact.value.get("entries")
    if not isinstance(entries, list):
        return None
    paths = {
        str(item.get("path")) for item in entries if isinstance(item, dict) and item.get("path")
    }
    if "supported-features.md" not in paths:
        return None
    return (
        "Review [`supported-features.md`](supported-features.md) for the repository's detailed "
        "implementation boundaries."
    )


def additional_examples_markdown(facts: ProductFactsV2) -> str | None:
    """Render repository examples without overstating their execution assurance."""

    fact = _accepted(facts, "repository.examples")
    if fact is None or not isinstance(fact.value, dict):
        return None
    files = fact.value.get("files")
    files = files if isinstance(files, list) else []
    paths = [
        str(item.get("path"))
        for item in files
        if isinstance(item, dict)
        and str(item.get("path") or "").endswith(".py")
        and item.get("execution_verified") is False
    ]
    minimal = _accepted(facts, "example.minimal")
    minimal_value = minimal.value if minimal is not None and isinstance(minimal.value, dict) else {}
    minimal_code = str(minimal_value.get("code") or "").strip()
    inline = fact.value.get("inline_examples")
    inline = inline if isinstance(inline, list) else []
    verified_inline = [
        item
        for item in inline
        if isinstance(item, dict)
        and item.get("static_api_verified") is True
        and str(item.get("code") or "").strip()
        and str(item.get("code") or "").strip() != minimal_code
    ]
    assets = fact.value.get("result_assets")
    assets = assets if isinstance(assets, list) else []
    if not paths and not verified_inline and not assets:
        return None
    body: list[str] = []
    for item in verified_inline:
        title = str(item.get("title") or "Additional workflow").strip()
        language = str(item.get("language") or "text").strip()
        code = strip_source_comments(language, str(item["code"])).strip()
        if not code:
            continue
        body.extend([f"### {title}", "", f"```{language}", code, "```", ""])
    if paths:
        body.extend(
            [
                "### Repository example files",
                "",
                *(f"- [`{path.rsplit('/', 1)[-1]}`]({path})" for path in paths),
                "",
            ]
        )
    if assets:
        body.extend(["### Example results", ""])
        body.extend(
            f"![{str(item.get('alt') or 'Example result')}]({str(item.get('path'))})"
            for item in assets
            if isinstance(item, dict) and item.get("path")
        )
    return (
        "These additional workflows were syntax-checked and matched to the repository's static "
        "public API. They were not executed by the evidence collector.\n\n"
        + _details("View additional examples and results", body)
    )


def api_reference_markdown(facts: ProductFactsV2) -> str | None:
    """Render literal public exports discovered from static package declarations."""

    fact = _accepted(facts, "api.public_surface")
    if fact is None or not isinstance(fact.value, dict):
        return None
    modules = fact.value.get("modules")
    if not isinstance(modules, list):
        return None
    body: list[str] = []
    export_count = 0
    mcp = fact.value.get("mcp_server")
    if isinstance(mcp, dict):
        tools = mcp.get("tools")
        defaults = mcp.get("runner_defaults")
        module = str(mcp.get("module") or "").strip()
        if module and isinstance(tools, list) and tools:
            host = defaults.get("host") if isinstance(defaults, dict) else "127.0.0.1"
            port = defaults.get("port") if isinstance(defaults, dict) else 8000
            dependency = str(mcp.get("dependency_package") or "").strip()
            body.extend(
                [
                    "### MCP server",
                    "",
                    "The repository registers these MCP tools:",
                    "",
                    *(f"- `{tool}`" for tool in tools),
                    "",
                    "```python",
                    f"from {module} import create_server",
                    "",
                    "server = create_server()",
                    f'server.run(host="{host}", port={port})',
                    "```",
                ]
            )
            if dependency:
                body.extend(
                    [
                        "",
                        "The server imports FastMCP from the separately supplied "
                        f"`{dependency}` package.",
                        "",
                    ]
                )
    for module_index, module in enumerate(modules):
        if not isinstance(module, dict):
            continue
        name = str(module.get("module") or "").strip()
        exports = module.get("exports")
        if not name or not isinstance(exports, list):
            continue
        if module_index:
            body.append("")
        body.append(f"### `{name}`")
        body.append("")
        for export in exports:
            body.append(f"- `{export}`")
            export_count += 1
    classes = fact.value.get("classes")
    if isinstance(classes, list):
        for item in classes:
            if not isinstance(item, dict):
                continue
            class_name = str(item.get("name") or "").strip()
            members = item.get("members")
            if not class_name or not isinstance(members, list) or not members:
                continue
            body.append("")
            body.append(f"### `{class_name}` members")
            body.append("")
            body.extend(
                f"- `{str(member.get('surface'))}`"
                for member in members
                if isinstance(member, dict) and member.get("surface")
            )
    if not body:
        return None
    return (
        f"The package declares {export_count} public exports in its static `__all__` surface.\n\n"
        + _details("View MCP and public API details", body)
    )


def development_markdown(facts: ProductFactsV2) -> str | None:
    """Summarize repository development assets without claiming they executed."""

    fact = _accepted(facts, "development.assets")
    assets = fact.value if fact is not None and isinstance(fact.value, dict) else {}
    counts: list[str] = []
    body: list[str] = []
    labels = {"tests": "test files", "tools": "maintenance tools", "goldens": "golden assets"}
    singular = {"tests": "test file", "tools": "maintenance tool", "goldens": "golden asset"}
    for group in ("tests", "tools", "goldens"):
        inventory = assets.get(group)
        if not isinstance(inventory, dict):
            continue
        count = inventory.get("count")
        rows = inventory.get("representative_paths")
        if not isinstance(count, int) or count < 1 or not isinstance(rows, list):
            continue
        counts.append(f"{count} {singular[group] if count == 1 else labels[group]}")
        body.append(f"### {group.title()}")
        body.append("")
        body.extend(
            f"- [`{str(row.get('path'))}`]({str(row.get('path'))})"
            for row in rows
            if isinstance(row, dict)
            and row.get("path")
            and not str(row["path"]).rsplit("/", 1)[-1].startswith("_")
        )
        if count > len(rows):
            directory = "tests/goldens" if group == "goldens" else group
            body.append(f"- [Browse all {labels[group]}]({directory})")
        body.append("")
    commands = assets.get("commands")
    entries = commands.get("entries") if isinstance(commands, dict) else None
    if isinstance(entries, list) and entries:
        body.extend(["### Repository Make targets", ""])
        for item in entries:
            if not isinstance(item, dict) or not item.get("command"):
                continue
            body.extend(["```bash", str(item["command"]), "```", ""])
        counts.append(f"{len(entries)} declared Make targets")
    guidance = _accepted(facts, "development.commands")
    guidance_value = (
        guidance.value if guidance is not None and isinstance(guidance.value, dict) else {}
    )
    guidance_entries = guidance_value.get("entries")
    if isinstance(guidance_entries, list) and guidance_entries:
        body.extend(["### Focused commands and repository scripts", ""])
        rendered_count = 0
        for item in guidance_entries:
            if not isinstance(item, dict) or not item.get("command"):
                continue
            body.extend(["```bash", str(item["command"]), "```", ""])
            rendered_count += 1
        if rendered_count:
            label = "command" if rendered_count == 1 else "commands"
            counts.append(f"{rendered_count} source-bound validation {label}")
    if not counts:
        return None
    return (
        "The repository includes "
        + ", ".join(counts)
        + ".\n\n"
        + _details("View development and testing resources", body)
    )


def contributing_markdown(facts: ProductFactsV2) -> str | None:
    """Render repository-owned contribution entry points without inventing policy."""

    fact = _accepted(facts, "repository.contribution_guidance")
    if fact is None or not isinstance(fact.value, dict):
        return None
    path = str(fact.value.get("path") or "").strip()
    if path:
        return f"See [`{path}`]({path}) for the repository's contribution guidance."
    scripts = fact.value.get("validation_scripts")
    if not isinstance(scripts, list) or not scripts:
        return None
    paths = [
        str(item.get("path")) for item in scripts if isinstance(item, dict) and item.get("path")
    ]
    if not paths:
        return None
    return "Validate a proposed change with the checked-in repository scripts:\n\n" + "\n".join(
        f"- [`{path}`]({path})" for path in paths
    )


def security_markdown(facts: ProductFactsV2) -> str | None:
    """Render repository-owned security reporting and resource-limit evidence."""

    fact = _accepted(facts, "repository.security_guidance")
    if fact is None or not isinstance(fact.value, dict):
        return None
    paragraphs: list[str] = []
    policy = fact.value.get("policy")
    if isinstance(policy, dict):
        path = str(policy.get("path") or "").strip()
        private_url = str(policy.get("private_reporting_url") or "").strip()
        if path and private_url:
            paragraphs.append(
                f"Follow the [`{path}`]({path}) policy and use "
                f"[GitHub private vulnerability reporting]({private_url}) for security issues."
            )
        elif path:
            paragraphs.append(f"Follow the repository's [`{path}`]({path}) policy.")
    limits = fact.value.get("resource_limits")
    if isinstance(limits, dict):
        class_name = str(limits.get("class") or "").strip()
        fields = limits.get("fields")
        if class_name and isinstance(fields, list) and fields:
            paragraphs.append(
                f"`{class_name}` exposes {len(fields)} source-defined limits for bounding "
                "untrusted input and authored assets."
            )
            entry_points = limits.get("entry_points")
            if isinstance(entry_points, list) and entry_points:
                rendered = ", ".join(f"`{item}`" for item in entry_points)
                paragraphs.append(
                    f"Pass a `{class_name}` policy through the source-defined {rendered} "
                    "entry points when tighter limits are required."
                )
    guidance = fact.value.get("operational_guidance")
    if isinstance(guidance, dict):
        if guidance.get("lazy_work_uses_shared_limits") is True:
            paragraphs.append(
                "Lazy decoding and streaming work continue to consume the document's shared "
                "resource limits."
            )
        if guidance.get("unlimited_disables_safeguards") is True:
            paragraphs.append(
                "`PdfLoadLimits.unlimited()` disables every safeguard and is appropriate only "
                "for trusted input with external resource controls."
            )
        if guidance.get("limits_are_not_a_complete_dos_sandbox") is True:
            statement = (
                "These limits reduce known parser and allocation risks but are not a complete "
                "denial-of-service sandbox."
            )
            if guidance.get("isolate_highly_hostile_documents") is True:
                statement += " Isolate highly hostile PDF workloads at the process boundary."
            paragraphs.append(statement)
    return "\n\n".join(paragraphs) or None


def third_party_notices_markdown(facts: ProductFactsV2) -> str | None:
    """Render the exact repository-local notices path."""

    fact = _accepted(facts, "repository.third_party_notices")
    if fact is None or not isinstance(fact.value, dict):
        return None
    path = str(fact.value.get("path") or "").strip()
    if not path:
        return None
    return (
        "Third-party attribution and dependency license notices are recorded in "
        f"[`{path}`]({path})."
    )
