#!/usr/bin/env python3
"""Compatibility facade for the paired, domain-pure Aspose catalog generator."""

from __future__ import annotations

import sys
from pathlib import Path

DATA_REFRESH = Path(__file__).resolve().parent / "data-refresh"
sys.path.insert(0, str(DATA_REFRESH))

from build_aspose_link_catalogs import main as build_catalogs  # noqa: E402


def _translate_legacy_arguments(arguments: list[str]) -> list[str]:
    translated: list[str] = []
    iterator = iter(arguments)
    for argument in iterator:
        if argument == "--from-source":
            translated.extend(["--aspose-com-source", next(iterator)])
        elif argument == "--output":
            translated.extend(["--com-output", next(iterator)])
        elif argument in {"--skip-http-verify", "--families"}:
            raise ValueError(
                f"{argument} is not supported by the domain-pure paired generator; "
                "use registry scope and explicit --verify-*-pattern inputs"
            )
        else:
            translated.append(argument)
    return translated


def main(argv: list[str] | None = None) -> int:
    """Forward supported legacy arguments into the sole paired generator."""

    try:
        translated = _translate_legacy_arguments(list(argv if argv is not None else sys.argv[1:]))
    except (StopIteration, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return build_catalogs(translated)


if __name__ == "__main__":
    raise SystemExit(main())
