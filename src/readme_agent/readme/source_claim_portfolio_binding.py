"""Bind common inherited portfolio details to repository-verified fact families."""

from __future__ import annotations

import json
import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.python_install_target import (
    normalized_python_distribution,
    parse_python_optional_extras_install,
    selected_python_install_target,
)
from readme_agent.readme.source_claim_risk import classify_source_claim_risk

_FENCE = re.compile(r"^\s*```(?P<language>[A-Za-z0-9_+-]*)\s*\n(?P<body>.*)\n```\s*$", re.DOTALL)
_PATH = re.compile(r"`(?P<path>(?:\.?[A-Za-z0-9_.-]+/)+[A-Za-z0-9_./*-]*)`")
_PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*")


def _accepted(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def _dependency_ids(text: str, facts: ProductFactsV2) -> set[str]:
    distribution = _accepted(facts, "python.distribution")
    extras = _accepted(facts, "installation.optional_extras")
    capability = _accepted(facts, "installation.capability_dependencies")
    install = parse_python_optional_extras_install(text)
    if install is not None:
        target_policy = selected_python_install_target(facts)
        if extras is None or not isinstance(extras.value, dict) or target_policy is None:
            return set()
        declared = extras.value.get("extras")
        if not isinstance(declared, dict):
            return set()
        target, parsed_extras = install
        requested = set(parsed_extras)
        if not requested or not requested.issubset({str(item).casefold() for item in declared}):
            return set()
        if normalized_python_distribution(target) != normalized_python_distribution(
            target_policy.target
        ):
            return set()
        return {
            extras.fact_id,
            target_policy.coordinates_fact_id,
            target_policy.acquisition_fact_id,
        }

    known: dict[str, str] = {}
    if distribution is not None and isinstance(distribution.value, dict):
        for item in distribution.value.get("runtime_dependencies", []):
            if not isinstance(item, str):
                continue
            name = re.split(r"[<>=!~\[]", item, maxsplit=1)[0].strip().casefold()
            if name:
                known[name] = distribution.fact_id
    if extras is not None and isinstance(extras.value, dict):
        declared = extras.value.get("extras")
        if isinstance(declared, dict):
            for name, values in declared.items():
                known[str(name).casefold()] = extras.fact_id
                for item in values if isinstance(values, list) else []:
                    package = re.split(r"[<>=!~\[]", str(item), maxsplit=1)[0].strip().casefold()
                    if package:
                        known[package] = extras.fact_id
    if capability is not None and isinstance(capability.value, dict):
        for item in capability.value.get("entries", []):
            if isinstance(item, dict) and item.get("distribution"):
                known[str(item["distribution"]).casefold()] = capability.fact_id
    aliases = {"harfbuzz": "uharfbuzz", "bidi": "python-bidi"}
    folded = text.casefold()
    mentioned = {
        fact_id
        for token, fact_id in known.items()
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", folded)
    }
    for alias, target in aliases.items():
        if re.search(rf"\b{alias}\b", folded) and target in known:
            mentioned.add(known[target])
    bare = re.fullmatch(r"\s*[-+*]\s+`(?P<name>[A-Za-z0-9_.-]+)`\s*", text)
    if bare is not None and bare.group("name").casefold() not in known:
        return set()
    return mentioned


def _repository_map_ids(text: str, facts: ProductFactsV2) -> set[str]:
    paths = [match.group("path").rstrip("*") for match in _PATH.finditer(text)]
    if not paths:
        return set()
    accepted = [
        fact
        for fact in facts.facts
        if facts.selected_fact_ids.get(fact.field) == fact.fact_id
        and fact.verification_state in {"verified", "policy_approved"}
        and not fact.has_unresolved_conflict
    ]
    matches: set[str] = set()
    for path in paths:
        owners = [
            fact
            for fact in accepted
            if path in fact.source.location
            or path.rstrip("/") in json.dumps(fact.value, sort_keys=True)
        ]
        if not owners:
            return set()
        matches.update(fact.fact_id for fact in owners)
    return matches


def _contribution_ids(text: str, facts: ProductFactsV2) -> set[str]:
    guidance = _accepted(facts, "repository.contribution_guidance")
    if guidance is None:
        return set()
    value = guidance.value if isinstance(guidance.value, dict) else {}
    readme_workflow = value.get("readme_standard_workflow")
    if isinstance(readme_workflow, dict):
        statements = {
            " ".join(str(item).split())
            for item in readme_workflow.get("validated_statements", [])
            if str(item).strip()
        }
        if " ".join(text.split()) in statements:
            return {guidance.fact_id}
    fence = _FENCE.fullmatch(text)
    if fence is None:
        return set()
    commands = _accepted(facts, "development.commands")
    if commands is None or not isinstance(commands.value, dict):
        return set()
    known = {
        str(item.get("command")).strip()
        for item in commands.value.get("entries", [])
        if isinstance(item, dict) and item.get("command")
    }
    body = fence.group("body").strip()
    return {guidance.fact_id, commands.fact_id} if body in known else set()


def _security_ids(text: str, facts: ProductFactsV2) -> set[str]:
    security = _accepted(facts, "repository.security_guidance")
    if security is None or not isinstance(security.value, dict):
        return set()
    corpus = json.dumps(security.value, sort_keys=True).casefold()
    fence = _FENCE.fullmatch(text)
    api = _accepted(facts, "api.public_surface") if fence is not None else None
    if fence is not None:
        code = fence.group("body")
        required = {
            token for token in ("PdfLoadLimits", "PdfResourceLimitException") if token in code
        }
        api_corpus = (
            json.dumps(api.value, sort_keys=True).casefold() if required and api is not None else ""
        )
        if not required or not all(
            token.casefold() in corpus or token.casefold() in api_corpus for token in required
        ):
            return set()
        fields = re.findall(r"\b(max_[a-z0-9_]+)\s*=", code)
        if any(field.casefold() not in corpus for field in fields):
            return set()
    return {security.fact_id, *([api.fact_id] if fence is not None and api is not None else [])}


def portfolio_source_claim_fact_ids(
    document: str,
    claim: ReadmeMaterialClaimAssessmentV1,
    text: str,
    facts: ProductFactsV2,
) -> set[str]:
    """Return accepted facts for common source-detail obligations across products."""

    if parse_python_optional_extras_install(text) is not None:
        return _dependency_ids(text, facts)
    obligation = classify_source_claim_risk(document, claim).obligation_id
    if obligation == "dependency_requirements":
        return _dependency_ids(text, facts)
    if obligation == "repository_map":
        return _repository_map_ids(text, facts)
    if obligation == "contribution_guidance":
        return _contribution_ids(text, facts)
    if obligation == "security_guidance":
        return _security_ids(text, facts)
    return set()


__all__ = ["portfolio_source_claim_fact_ids"]
