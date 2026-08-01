"""Select a digest-pinned Python runtime compatible with package metadata."""

from __future__ import annotations

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

PYTHON_311_IMAGE = "python@sha256:13f0881a239ca0d27fb8b2539536ace85f7d680a707bfaa178571e1dbfe85a91"
PYTHON_312_IMAGE = "python@sha256:a9e4190f02729f01e5b3719bd8b3ea0f8d9350dc17d01a1ce1ca6e3fbfcf7a99"

_APPROVED_RUNTIMES = (
    (Version("3.11.15"), PYTHON_311_IMAGE),
    (Version("3.12.13"), PYTHON_312_IMAGE),
)


def select_python_image(requires_python: str | None) -> str:
    """Return the lowest approved runtime satisfying a PEP 440 requirement."""

    try:
        requirement = SpecifierSet(requires_python or "")
    except InvalidSpecifier as exc:
        raise ValueError(f"invalid requires-python specifier: {requires_python!r}") from exc
    for version, image in _APPROVED_RUNTIMES:
        if requirement.contains(version, prereleases=True):
            return image
    raise ValueError(
        "no approved immutable Python runtime satisfies "
        f"requires-python {requires_python!r}; approved versions are "
        + ", ".join(str(version) for version, _image in _APPROVED_RUNTIMES)
    )
