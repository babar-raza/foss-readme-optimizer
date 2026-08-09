"""Select the one Python install target authorized by verified acquisition truth."""

from __future__ import annotations

import re
from dataclasses import dataclass

from readme_agent.facts.schema_v2 import FactRecordV2, ProductFactsV2

_EXTRAS_TARGET = r"(?P<target>\.|[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
_EXTRAS = r"(?P<extras>[A-Za-z0-9_.-]+(?:,[A-Za-z0-9_.-]+)*)"
_DIRECT_EXTRAS_INSTALL = re.compile(
    rf"\Apython\s+-m\s+pip\s+install\s+(?P<quote>['\"]?){_EXTRAS_TARGET}"
    rf"\[{_EXTRAS}\](?P=quote)\Z",
    re.IGNORECASE,
)
_FENCED_SHELL = re.compile(
    r"\A```(?:bash|sh|shell|console|powershell|ps1)?[^\S\r\n]*\r?\n"
    r"(?P<body>[^\r\n]+)\r?\n```\Z",
    re.IGNORECASE,
)
_LISTED_EXTRAS_INSTALL = re.compile(
    rf"\A[-+*]\s+`(?P<label>[A-Za-z0-9_.-]+)`\s*:\s*`"
    rf"python\s+-m\s+pip\s+install\s+(?P<quote>['\"]?){_EXTRAS_TARGET}"
    rf"\[{_EXTRAS}\](?P=quote)`\Z",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PythonInstallTargetV1:
    target: str
    acquisition_fact_id: str
    coordinates_fact_id: str


def _accepted(facts: ProductFactsV2, field: str) -> FactRecordV2 | None:
    fact_id = facts.selected_fact_ids.get(field)
    if fact_id is None:
        return None
    fact = facts.fact_by_id(fact_id)
    if fact.verification_state not in {"verified", "policy_approved"}:
        return None
    return None if fact.has_unresolved_conflict else fact


def normalized_python_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).casefold()


def parse_python_optional_extras_install(text: str) -> tuple[str, tuple[str, ...]] | None:
    """Parse one complete, bounded pip-extras command and reject trailing shell content."""

    candidate = text.strip()
    fenced = _FENCED_SHELL.fullmatch(candidate)
    if fenced is not None:
        candidate = fenced.group("body").strip()
    match = _DIRECT_EXTRAS_INSTALL.fullmatch(candidate) or _LISTED_EXTRAS_INSTALL.fullmatch(
        candidate
    )
    if match is None:
        return None
    extras = tuple(dict.fromkeys(item.casefold() for item in match.group("extras").split(",")))
    return (match.group("target"), extras) if extras else None


def selected_python_install_target(facts: ProductFactsV2) -> PythonInstallTargetV1 | None:
    """Return dot or one receipt-selected distribution, never a sibling coordinate."""

    identity = _accepted(facts, "product.identity")
    coordinates = _accepted(facts, "installation.coordinates")
    acquisition = _accepted(facts, "installation.verified_acquisition")
    if (
        identity is None
        or coordinates is None
        or acquisition is None
        or not isinstance(identity.value, dict)
        or not isinstance(acquisition.value, dict)
    ):
        return None
    ecosystem = str(identity.value.get("ecosystem") or identity.value.get("platform") or "")
    if ecosystem.casefold() != "python":
        return None
    value = acquisition.value
    if value.get("truth_eligible") is not True or value.get("ecosystem") not in {None, "python"}:
        return None
    if value.get("method") == "source_build":
        if value.get("outcome") != "SOURCE_BUILD_VERIFIED" or not isinstance(
            value.get("source_build_receipt"), dict
        ):
            return None
        return PythonInstallTargetV1(
            target=".",
            acquisition_fact_id=acquisition.fact_id,
            coordinates_fact_id=coordinates.fact_id,
        )
    if value.get("outcome") != "REGISTRY_VERIFIED":
        return None
    selected_coordinate = value.get("coordinate")
    receipt = value.get("registry_receipt")
    if (
        not isinstance(selected_coordinate, dict)
        or not isinstance(receipt, dict)
        or receipt.get("found") is not True
        or receipt.get("coordinate") != selected_coordinate
    ):
        return None
    selected_name = str(selected_coordinate.get("name") or "").strip()
    rows = coordinates.value if isinstance(coordinates.value, list) else [coordinates.value]
    matching = [
        row
        for row in rows
        if isinstance(row, dict)
        and str(row.get("ecosystem") or "").casefold() == "python"
        and normalized_python_distribution(str(row.get("name") or ""))
        == normalized_python_distribution(selected_name)
    ]
    if not selected_name or len(matching) != 1:
        return None
    return PythonInstallTargetV1(
        target=selected_name,
        acquisition_fact_id=acquisition.fact_id,
        coordinates_fact_id=coordinates.fact_id,
    )


__all__ = [
    "PythonInstallTargetV1",
    "normalized_python_distribution",
    "parse_python_optional_extras_install",
    "selected_python_install_target",
]
