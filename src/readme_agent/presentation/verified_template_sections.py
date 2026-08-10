"""Render optional verified fact families into reusable README template sections."""

from __future__ import annotations

import re

from readme_agent.facts.example_quality import strip_source_comments
from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.presentation.template_schema import load_repository_presentation_template
from readme_agent.presentation.verified_template_example_presentation import (
    public_example_title,
    public_examples_introduction,
)
from readme_agent.presentation.verified_template_golden_workflow import (
    golden_workflow_development,
)
from readme_agent.readme.code_fence_presentation import normalize_code_snippet
from readme_agent.readme.document_structure import heading_identity
from readme_agent.readme.presentation_lint_text import strip_emoji_decorations
from readme_agent.readme.python_install_target import selected_python_install_target

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
    trimmed = list(body)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    return "\n".join(["<details>", f"<summary>{summary}</summary>", "", *trimmed, "", "</details>"])


def optional_extras_markdown(facts: ProductFactsV2) -> str | None:
    """Render exact package extras without assigning an inferred purpose to them."""

    extras_fact = _accepted(facts, "installation.optional_extras")
    target_policy = selected_python_install_target(facts)
    if extras_fact is None or target_policy is None or not isinstance(extras_fact.value, dict):
        return None
    extras = extras_fact.value.get("extras")
    if not isinstance(extras, dict) or not extras:
        return None
    install_target = target_policy.target
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
    return "\n\n".join(sections) or None


_EXTRA_PURPOSES = {
    "test": "Running the test suite",
    "tests": "Running the test suite",
    "docs": "Building the documentation",
}


def _purpose_api_annotation(facts: ProductFactsV2, purpose: str) -> str | None:
    """Name the concrete public entry points a dependency scenario serves."""

    if "image conversion" not in purpose.casefold():
        return None
    api = _accepted(facts, "api.public_surface")
    if api is None or not isinstance(api.value, dict):
        return None
    catalog = api.value.get("coordinate_catalog")
    module_lists = [
        api.value.get("modules"),
        catalog.get("modules") if isinstance(catalog, dict) else None,
    ]
    exports = sorted(
        {
            str(export)
            for modules in module_lists
            if isinstance(modules, list)
            for module in modules
            if isinstance(module, dict)
            for export in module.get("exports", [])
            if isinstance(export, str) and export.endswith("_to_image")
        }
    )
    if not exports:
        return None
    return ", ".join(f"`{name}`" for name in exports)


def scenario_dependency_markdown(
    facts: ProductFactsV2,
    *,
    source_text: str | None = None,
) -> str | None:
    """Merge capability dependencies and package extras into one scenario list.

    Verify-then-merge (Tweak 4): same-purpose install commands are combined and
    the source README's ordering of the merged distributions is preserved.
    """

    lines: list[str] = []
    capabilities = _accepted(facts, "installation.capability_dependencies")
    if capabilities is not None and isinstance(capabilities.value, dict):
        entries = capabilities.value.get("entries")
        purposes: list[str] = []
        distributions: dict[str, list[str]] = {}
        for item in entries if isinstance(entries, list) else []:
            if not isinstance(item, dict):
                continue
            purpose = str(item.get("purpose") or "").strip()
            distribution = str(item.get("distribution") or "").strip()
            if not purpose or not distribution:
                continue
            if purpose not in distributions:
                purposes.append(purpose)
                distributions[purpose] = []
            if distribution not in distributions[purpose]:
                distributions[purpose].append(distribution)
        for purpose in purposes:
            ordered = distributions[purpose]
            if source_text:
                mentioned = [name for name in ordered if name in source_text]
                ordered = [
                    *sorted(mentioned, key=source_text.find),
                    *(name for name in ordered if name not in mentioned),
                ]
            label = purpose if purpose[:1].isupper() else purpose[:1].upper() + purpose[1:]
            annotation = _purpose_api_annotation(facts, purpose)
            if annotation:
                label = f"{label} ({annotation})"
            lines.append(f"- {label}: `python -m pip install {' '.join(ordered)}`")
    extras_fact = _accepted(facts, "installation.optional_extras")
    target_policy = selected_python_install_target(facts)
    if (
        extras_fact is not None
        and target_policy is not None
        and isinstance(extras_fact.value, dict)
        and isinstance(extras_fact.value.get("extras"), dict)
    ):
        for name in sorted(str(item) for item in extras_fact.value["extras"]):
            label = _EXTRA_PURPOSES.get(name.casefold(), f"Installing the `{name}` extra")
            lines.append(f'- {label}: `python -m pip install "{target_policy.target}[{name}]"`')
    if not lines:
        return None
    return "Install optional dependencies by scenario:\n\n" + "\n".join(lines)


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


_RESULT_CAPTION_CONVERSION = re.compile(
    r"^(?P<subject>.+?)\s*\((?:that\s+is\s+)?converted\s+(?:than|then)?\s*to\s+"
    r"(?P<rendered>[A-Za-z0-9/]+)\)$",
    re.IGNORECASE,
)
_AN_SOUND_INITIALS = frozenset("AEFHILMNORSX")


def _caption_article(subject: str) -> str:
    first_word = subject.split()[0] if subject.split() else ""
    if first_word.isupper() and len(first_word) > 1:
        return "An" if first_word[0] in _AN_SOUND_INITIALS else "A"
    return "An" if first_word[:1].casefold() in "aeiou" else "A"


def _result_asset_caption(source_text: str | None, asset_path: str) -> str | None:
    """Rewrite the source's own caption heading for a result image as prose."""

    if not source_text:
        return None
    image_offset = source_text.find(f"]({asset_path})")
    if image_offset < 0:
        return None
    preceding = [
        line.strip().lstrip("#").strip()
        for line in source_text[:image_offset].splitlines()
        if line.strip().startswith("###")
    ]
    if not preceding:
        return None
    heading = strip_emoji_decorations(preceding[-1]).strip()
    if not heading:
        return None
    conversion = _RESULT_CAPTION_CONVERSION.fullmatch(heading)
    if conversion is not None:
        subject = " ".join(conversion.group("subject").split())
        rendered = conversion.group("rendered").upper()
        return f"{_caption_article(subject)} {subject}, rendered here as {rendered}:"
    return f"{_caption_article(heading)} {heading.rstrip(':.')}:"


def _mcp_workflow_section(
    facts: ProductFactsV2,
    source_text: str | None,
) -> tuple[str, list[str], str] | None:
    """Merge the source's verified MCP hosting example into a canonical workflow."""

    if not source_text:
        return None
    api = _accepted(facts, "api.public_surface")
    if api is None or not isinstance(api.value, dict):
        return None
    mcp = api.value.get("mcp_server")
    if not isinstance(mcp, dict):
        return None
    factory = str(mcp.get("factory") or "").strip()
    runner = str(mcp.get("runner") or "").strip()
    tools = [str(tool) for tool in mcp.get("tools") or [] if str(tool).strip()]
    if not factory or not runner or not tools:
        return None
    code = next(
        (
            normalize_code_snippet(block)
            for block in re.findall(r"```python\n(.*?)```", source_text, re.DOTALL)
            if f"{factory}(" in block and f".{runner}(" in block
        ),
        None,
    )
    if code is None:
        return None
    mentioned = [tool for tool in tools if tool in source_text]
    tools = [
        *sorted(mentioned, key=source_text.find),
        *(tool for tool in tools if tool not in mentioned),
    ]
    rendered_tools = ", ".join(f"`{tool}`" for tool in tools[:-1]) + f", and `{tools[-1]}`"
    workflow = (
        "conversion workflows" if any("_to_" in tool for tool in tools) else "product workflows"
    )
    sentence = f"The MCP server exposes the {rendered_tools} tools for integrating {workflow}."
    title = "Host the MCP Server"
    return title, [f"### {title}", "", sentence, "", "```python", code, "```", ""], code


def additional_examples_markdown(
    facts: ProductFactsV2,
    *,
    reserved_heading_titles: tuple[str, ...] = (),
    source_text: str | None = None,
) -> str | None:
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
    mcp_section = _mcp_workflow_section(facts, source_text)
    mcp_code = mcp_section[2] if mcp_section is not None else None
    verified_inline = [
        item
        for item in inline
        if isinstance(item, dict)
        and item.get("static_api_verified") is True
        and str(item.get("code") or "").strip()
        and str(item.get("code") or "").strip() != minimal_code
        and normalize_code_snippet(str(item.get("code") or "")) != mcp_code
    ]
    assets = fact.value.get("result_assets")
    assets = assets if isinstance(assets, list) else []
    if not paths and not verified_inline and not assets and mcp_section is None:
        return None
    body: list[str] = []
    rendered_titles: list[str] = []
    contract = load_repository_presentation_template()
    used_headings = {
        heading_identity(title) for title in (*contract.headings.values(), *reserved_heading_titles)
    }
    if paths:
        used_headings.add(heading_identity("Repository example files"))
    if assets:
        used_headings.add(heading_identity("Example results"))
    for item in verified_inline:
        base_title = strip_emoji_decorations(
            str(item.get("title") or "Additional workflow")
        ).strip()
        if not base_title:
            base_title = "Additional workflow"
        language = str(item.get("language") or "text").strip()
        title = public_example_title(
            base_title,
            str(item["code"]),
            language,
            used_headings,
        )
        used_headings.add(heading_identity(title))
        rendered_titles.append(title)
        code = normalize_code_snippet(strip_source_comments(language, str(item["code"])))
        if not code:
            continue
        body.extend([f"### {title}", "", f"```{language}", code, "```", ""])
    if mcp_section is not None:
        mcp_title, mcp_lines, _mcp_code = mcp_section
        if heading_identity(mcp_title) not in used_headings:
            used_headings.add(heading_identity(mcp_title))
            rendered_titles.append(mcp_title)
            body.extend(mcp_lines)
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
        for item in assets:
            if not isinstance(item, dict) or not item.get("path"):
                continue
            caption = _result_asset_caption(source_text, str(item.get("path")))
            if caption:
                body.extend([caption, ""])
            body.extend(
                [
                    f"![{str(item.get('alt') or 'Example result')}]({str(item.get('path'))})",
                    "",
                ]
            )
    introduction = public_examples_introduction(
        rendered_titles,
        has_repository_files=bool(paths),
        has_result_assets=bool(assets),
    )
    return "\n\n".join([introduction, _details("View additional examples and results", body)])


def development_markdown(facts: ProductFactsV2) -> str | None:
    """Summarize repository development assets without claiming they executed."""

    fact = _accepted(facts, "development.assets")
    assets = fact.value if fact is not None and isinstance(fact.value, dict) else {}
    counts: list[str] = []
    body: list[str] = []
    golden_workflow = golden_workflow_development(facts)
    labels = {"tests": "test files", "tools": "maintenance tools", "goldens": "golden assets"}
    singular = {"tests": "test file", "tools": "maintenance tool", "goldens": "golden asset"}
    for group in ("tests", "tools", "goldens"):
        if group == "goldens" and golden_workflow is not None:
            continue
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
            body.extend(["```bash", normalize_code_snippet(str(item["command"])), "```", ""])
        counts.append(f"{len(entries)} declared Make targets")
    guidance = _accepted(facts, "development.commands")
    guidance_value = (
        guidance.value if guidance is not None and isinstance(guidance.value, dict) else {}
    )
    guidance_entries = guidance_value.get("entries")
    if isinstance(guidance_entries, list) and guidance_entries:
        body.extend(["### Focused Commands and Repository Scripts", ""])
        for item in guidance_entries:
            if not isinstance(item, dict) or not item.get("command"):
                continue
            body.extend(["```bash", normalize_code_snippet(str(item["command"])), "```", ""])
    if golden_workflow is not None:
        label, lines = golden_workflow
        counts.append(label)
        body.extend(lines)
    if not body:
        return None
    visible_body = "\n".join(body).strip()
    if not counts:
        return visible_body
    return "The repository includes " + ", ".join(counts) + ".\n\n" + visible_body


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
                f"`{class_name}` exposes {len(fields)} configurable limits for bounding "
                "untrusted input and authored assets."
            )
            entry_points = limits.get("entry_points")
            if isinstance(entry_points, list) and entry_points:
                rendered = ", ".join(f"`{item}`" for item in entry_points)
                paragraphs.append(
                    f"Pass a `{class_name}` policy through the {rendered} "
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
        f"Third-party attribution and dependency license notices are recorded in [{path}]({path})."
    )
