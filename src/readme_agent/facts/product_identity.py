"""Canonicalize repository-bound product family identities."""

from __future__ import annotations

import re

_ASPOSE_FAMILY = re.compile(
    r"^Aspose(?P<separator>[.-])(?P<family>[A-Za-z0-9][A-Za-z0-9.-]*)$",
    flags=re.IGNORECASE,
)


def canonical_aspose_family_name(value: str) -> str | None:
    """Return canonical ``Aspose.{Family}`` spelling for an Aspose family token."""

    match = _ASPOSE_FAMILY.fullmatch(value.strip())
    if match is None:
        return None
    return f"Aspose.{match.group('family')}"
