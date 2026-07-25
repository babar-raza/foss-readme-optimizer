"""Resolve acquisition coordinates and isolate contradicted package claims."""

from __future__ import annotations

import re

_MAVEN_DEPENDENCY = re.compile(r"<dependency\b[^>]*>.*?</dependency>", re.DOTALL)
_GRADLE_DEPENDENCY_LINE = re.compile(
    r"(?m)^[^\S\r\n]*implementation\s+[\"']org\.[^\r\n]+(?:\r?\n)?"
)
_FENCED_BLOCK = re.compile(r"(?ms)^```[^\r\n]*\r?\n(?P<body>.*?)^```[^\S\r\n]*(?:\r?\n)?")


def coordinate_rows(value: object) -> list[dict]:
    """Normalize the manifest-coordinate fact without inventing a fallback row."""

    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


def matching_coordinate_row(value: object, coordinate: dict) -> dict:
    """Return the exact coordinate row, case-insensitively for package names."""

    rows = coordinate_rows(value)
    coordinate_name = str(coordinate.get("name") or "").casefold()
    coordinate_group = str(coordinate.get("group_id") or "").casefold()
    coordinate_artifact = str(coordinate.get("artifact_id") or "").casefold()
    for row in rows:
        row_name = str(row.get("name") or "").casefold()
        if coordinate_name and row_name == coordinate_name:
            return row
        row_group = str(row.get("group_id") or "").casefold()
        row_artifact = str(row.get("artifact_id") or "").casefold()
        if (
            coordinate_group
            and coordinate_artifact
            and row_group == coordinate_group
            and row_artifact == coordinate_artifact
        ):
            return row
    return {}


def contradicted_package_claim_spans(text: str) -> list[tuple[int, int]]:
    """Return only the Maven/Gradle claim spans contradicted by source-build truth."""

    spans: list[tuple[int, int]] = []
    covered: list[tuple[int, int]] = []
    for fence in _FENCED_BLOCK.finditer(text):
        body = fence.group("body")
        without_maven = _MAVEN_DEPENDENCY.sub("", body)
        without_package_claims = _GRADLE_DEPENDENCY_LINE.sub("", without_maven)
        if without_package_claims.strip() or without_package_claims == body:
            continue
        spans.append(fence.span())
        covered.append(fence.span())

    def outside_dedicated_fence(span: tuple[int, int]) -> bool:
        return not any(start <= span[0] and span[1] <= end for start, end in covered)

    spans.extend(
        match.span()
        for match in _MAVEN_DEPENDENCY.finditer(text)
        if outside_dedicated_fence(match.span())
    )
    spans.extend(
        match.span()
        for match in _GRADLE_DEPENDENCY_LINE.finditer(text)
        if outside_dedicated_fence(match.span())
    )
    return sorted(spans)
