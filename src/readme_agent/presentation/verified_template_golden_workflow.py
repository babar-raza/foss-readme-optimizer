"""Render repository-native golden workflows from typed source evidence."""

from __future__ import annotations

from readme_agent.facts.schema_v2 import ProductFactsV2


def _accepted_value(facts: ProductFactsV2) -> dict | None:
    fact_id = facts.selected_fact_ids.get("development.golden_workflow")
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if (
        fact.verification_state not in {"verified", "policy_approved"}
        or fact.has_unresolved_conflict
        or not isinstance(fact.value, dict)
    ):
        return None
    return fact.value


def _selected_command(command: str, case_ids: list[str]) -> str:
    prefix = command.split(" --case ", 1)[0]
    return prefix + " " + " ".join(f"--case {case_id}" for case_id in case_ids)


def golden_workflow_development(
    facts: ProductFactsV2,
) -> tuple[str, list[str]] | None:
    """Return one summary label and public contributor detail for a typed workflow."""

    value = _accepted_value(facts)
    if value is None:
        return None
    inventory = value.get("artifact_inventory")
    commands = value.get("commands")
    case_ids = value.get("case_ids")
    if (
        not isinstance(inventory, dict)
        or not isinstance(commands, list)
        or not isinstance(case_ids, list)
    ):
        return None
    root = str(inventory.get("root") or "").strip()
    count = inventory.get("count")
    if not root or not isinstance(count, int) or count < 1:
        return None

    body = ["### Golden Workflow", ""]
    comparison = str(value.get("comparison_mode") or "").replace("_", " ")
    body.append(
        f"The repository maintains {count} golden artifacts under "
        f"[`{root}`]({root}). Comparisons use {comparison} data rather than raw file bytes."
    )
    body.append("")
    representative_cases = [str(case) for case in value.get("representative_case_ids", [])]
    selected_rendered = False
    for item in commands:
        if not isinstance(item, dict):
            continue
        command = str(item.get("command") or "").strip()
        kind = str(item.get("kind") or "").strip()
        if not command:
            continue
        if kind == "regenerate_selected":
            if selected_rendered:
                continue
            selected_rendered = True
            selected_cases = representative_cases or [str(item.get("case_id") or "")]
            command = _selected_command(command, [case for case in selected_cases if case])
        labels = {
            "regenerate_all": "Regenerate all golden artifacts:",
            "regenerate_selected": "Regenerate selected cases:",
            "verify": "Run the golden verification suite:",
            "install_requirements": "Install the workflow dependencies:",
        }
        body.extend(
            [
                labels.get(kind, "Run the repository command:"),
                "",
                "```bash",
                command,
                "```",
                "",
            ]
        )

    failure_path = str(value.get("failure_output_path") or "").strip()
    if failure_path:
        body.extend(
            [
                "Failed comparisons write diagnostic artifacts to "
                f"[`{failure_path}`]({failure_path}).",
                "",
            ]
        )
    renderers = value.get("renderer_fallbacks")
    visual = value.get("visual_diff_policy")
    if isinstance(renderers, list) and renderers:
        names = [
            str(item.get("name"))
            for item in renderers
            if isinstance(item, dict) and item.get("name")
        ]
        if names:
            prerequisites = (
                [str(item) for item in visual.get("required_python_packages", [])]
                if isinstance(visual, dict)
                else []
            )
            prefix = (
                "Optional visual comparisons require " + " and ".join(prerequisites) + " and use "
                if prerequisites
                else "Optional visual comparisons use "
            )
            body.extend(
                [
                    prefix + " with fallback to ".join(names) + ".",
                    "",
                ]
            )
    font = value.get("font_policy")
    if isinstance(font, dict) and font.get("environment_name"):
        body.extend(
            [
                "Built-in fonts are used by default unless text requires Unicode coverage. "
                f"Set `{font['environment_name']}=1` to search system font directories.",
                "",
            ]
        )
    return "1 repository-native golden workflow", body


__all__ = ["golden_workflow_development"]
