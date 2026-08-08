"""Bind common inherited portfolio details to repository-verified fact families."""

from __future__ import annotations

import json
import re

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2
from readme_agent.readme.assessment_claims import ReadmeMaterialClaimAssessmentV1
from readme_agent.readme.source_claim_risk import classify_source_claim_risk

_FENCE = re.compile(r"^\s*```(?P<language>[A-Za-z0-9_+-]*)\s*\n(?P<body>.*)\n```\s*$", re.DOTALL)
_PATH = re.compile(r"`(?P<path>(?:\.?[A-Za-z0-9_.-]+/)+[A-Za-z0-9_./*-]*)`")
_PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*")
_EXTRA_INSTALL = re.compile(
    r"python\s+-m\s+pip\s+install\s+['\"]?(?P<target>[^'\"\s\[]+)"
    r"\[(?P<extras>[A-Za-z0-9_.,-]+)\]",
    re.IGNORECASE,
)


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
    coordinates = _accepted(facts, "installation.coordinates")
    acquisition = _accepted(facts, "installation.verified_acquisition")
    install = _EXTRA_INSTALL.search(text)
    if install is not None:
        if extras is None or not isinstance(extras.value, dict):
            return set()
        declared = extras.value.get("extras")
        if not isinstance(declared, dict):
            return set()
        requested = {item.casefold() for item in install.group("extras").split(",")}
        if not requested or not requested.issubset({str(item).casefold() for item in declared}):
            return set()
        target = install.group("target")
        coordinate_names = {
            str(item.get("name")).casefold()
            for item in (
                coordinates.value
                if coordinates is not None and isinstance(coordinates.value, list)
                else [coordinates.value]
                if coordinates is not None
                else []
            )
            if isinstance(item, dict) and item.get("name")
        }
        if target != "." and target.casefold() not in coordinate_names:
            return set()
        return {
            extras.fact_id,
            *([coordinates.fact_id] if coordinates is not None else []),
            *([acquisition.fact_id] if acquisition is not None else []),
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
    fence = _FENCE.fullmatch(text)
    if fence is None:
        return {guidance.fact_id}
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
    api = _accepted(facts, "api.public_surface")
    api_corpus = json.dumps(api.value, sort_keys=True).casefold() if api is not None else ""
    fence = _FENCE.fullmatch(text)
    if fence is not None:
        code = fence.group("body")
        required = {
            token for token in ("PdfLoadLimits", "PdfResourceLimitException") if token in code
        }
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
