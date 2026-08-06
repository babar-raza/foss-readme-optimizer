"""Match package acquisition claims to exact verified method and outcome evidence."""

from __future__ import annotations

import re

_SHELL_FENCE = re.compile(
    r"\A```(?:bash|sh|shell|console|powershell|ps1)?[^\S\r\n]*\r?\n"
    r"(?P<body>.*?)\r?\n```\Z",
    re.DOTALL | re.IGNORECASE,
)
_PYTHON_INSTALL_COMMAND = re.compile(
    r"\A(?:python(?:3(?:\.\d+)?)?\s+-m\s+)?pip\s+install\s+"
    r"(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\Z",
    re.IGNORECASE,
)


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


def exact_coordinate_match(text: str, value: object) -> bool:
    """Match only an exact package command, version, or fenced Maven coordinate."""

    rows = value if isinstance(value, list) else [value]
    stripped = text.strip()
    python_name = _exact_python_install_name(text)
    if python_name is not None and any(
        str(row.get("ecosystem") or "").strip().casefold() == "python"
        and python_name == _normalized_python_distribution(str(row.get("name") or "").strip())
        for row in rows
        if isinstance(row, dict) and str(row.get("name") or "").strip()
    ):
        return True
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


def _normalized_python_distribution(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).casefold()


def _exact_python_install_name(text: str) -> str | None:
    claim = text.strip()
    if claim.startswith("```"):
        fence = _SHELL_FENCE.fullmatch(claim)
        if fence is None:
            return None
        claim = fence.group("body").strip()
    elif "```" in claim:
        return None
    match = _PYTHON_INSTALL_COMMAND.fullmatch(claim)
    if match is None:
        return None
    return _normalized_python_distribution(match.group("name"))


def verified_acquisition_matches(text: str, value: object) -> bool:
    """Match pip only to a truth-eligible found registry receipt for the exact package."""

    if not isinstance(value, dict) or value.get("truth_eligible") is not True:
        return False
    install_name = _exact_python_install_name(text)
    if install_name is None or value.get("outcome") != "REGISTRY_VERIFIED":
        return False
    receipt = value.get("registry_receipt")
    coordinate = value.get("coordinate")
    if (
        not isinstance(receipt, dict)
        or receipt.get("found") is not True
        or not isinstance(coordinate, dict)
        or receipt.get("coordinate") != coordinate
    ):
        return False
    expected = _normalized_python_distribution(str(coordinate.get("name") or "").strip())
    return bool(expected and expected == install_name)
