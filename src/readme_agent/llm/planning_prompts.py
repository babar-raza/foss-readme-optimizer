"""Assemble every planning prompt from the governed prompt registry."""

from __future__ import annotations

import json
from string import Template

from readme_agent.llm import prompt_registry


def supervisor_turn_prompt() -> tuple[str, str]:
    """Return the system and turn-context templates for supervisor planning."""

    manifest = prompt_registry.get("supervisor_turn")
    assert manifest is not None, "prompts/planning/supervisor_turn.yaml missing"
    assert manifest.turn_context_template is not None
    return manifest.system.strip(), manifest.turn_context_template


def build_supervisor_turn_messages(turn_context: str) -> list[dict]:
    system, _ = supervisor_turn_prompt()
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": turn_context},
    ]


def build_supervisor_followup_message(template_id: str, **values: str) -> dict:
    """Build one governed correction turn after a rejected planner choice."""

    manifest = prompt_registry.get("supervisor_turn")
    assert manifest is not None, "prompts/planning/supervisor_turn.yaml missing"
    try:
        template = manifest.message_templates[template_id]
    except KeyError as exc:
        raise ValueError(f"unknown supervisor message template: {template_id}") from exc
    return {
        "role": "user",
        "content": Template(template).substitute(**values).strip(),
    }


def build_specialist_selection_messages(
    org_repo: str,
    eligible_domains: list[str],
) -> list[dict]:
    manifest = prompt_registry.get("specialist_selection_turn")
    assert manifest is not None, "prompts/planning/specialist_selection_turn.yaml missing"
    assert manifest.user_template is not None
    user = Template(manifest.user_template).substitute(
        org_repo=org_repo,
        eligible_domains=", ".join(eligible_domains),
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user.strip()},
    ]


def build_repair_capability_selection_messages(
    *,
    capability_id: str,
    arguments: dict,
    classification: str,
    reason: str,
) -> list[dict]:
    manifest = prompt_registry.get("repair_capability_selection")
    assert manifest is not None, "prompts/planning/repair_capability_selection.yaml missing"
    assert manifest.user_template is not None
    user = Template(manifest.user_template).substitute(
        capability_id=capability_id,
        arguments=json.dumps(arguments),
        classification=classification,
        reason=reason,
    )
    return [
        {"role": "system", "content": manifest.system.strip()},
        {"role": "user", "content": user.strip()},
    ]
