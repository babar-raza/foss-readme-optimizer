"""PRODSYS-P2-T1 (production-system-redesign.md, DD-VERIFIER-ENFORCEMENT-PARITY): a cheap,
warn-only static check against VERIFIER-BUILT-NOT-WIRED recurring -- a public `verify_*`
function defined in `src/readme_agent/` with zero call sites anywhere else in `src/readme_agent/`
is reachable only by hand (a test, a standalone script under `plans/investigations/tools/`), which
is exactly the failure mode this project already hit once (`verify_readme_proposal_bundle()`,
built in commit `ff77c5f`, unwired until `de7ff3d`).

The default remains diagnostic for development, but `--check` is the release gate: a verifier that
has no production call site is a closure failure, not advisory evidence.

Usage: `.venv/Scripts/python.exe scripts/governance/check_verifiers_are_wired.py`
Usage: `.venv/Scripts/python.exe scripts/governance/check_verifiers_are_wired.py --check`
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "readme_agent"

_DEF_RE = re.compile(r"^(?:async )?def (verify_[a-z0-9_]+)\(", re.MULTILINE)


def _find_verifier_definitions(src_root: Path) -> dict[str, Path]:
    """Every top-level `def verify_*(` under `src_root`, keyed by name.
    Module-level only (not `def verify_*` nested inside a class or another
    function) -- matches this project's own convention of exposing verifiers
    as plain functions, not methods (see every existing example)."""
    definitions: dict[str, Path] = {}
    for path in sorted(src_root.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in _DEF_RE.finditer(text):
            definitions[match.group(1)] = path
    return definitions


def _has_call_site(name: str, src_root: Path) -> bool:
    """A call site is `name(` appearing anywhere under `src_root` outside the
    function's own definition line -- a real invocation, an import-and-alias
    doesn't count on its own (the alias would still need to be called
    somewhere, and this deliberately does not chase re-export indirection;
    false negatives here are a missed catch, not a false alarm, and the
    warn-only severity means a human still reviews each flag)."""
    call_re = re.compile(rf"\b{re.escape(name)}\(")
    def_line = f"def {name}("
    for path in src_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if def_line in line:
                continue
            if call_re.search(line):
                return True
    return False


def find_unwired_verifiers(src_root: Path | None = None) -> list[tuple[str, Path]]:
    """Return verifier definitions lacking a production call site.

    Resolve the default at call time so tests and future configured invocations
    can supply an isolated source tree without mutating import-time defaults.
    """
    resolved_src_root = src_root or SRC_ROOT
    definitions = _find_verifier_definitions(resolved_src_root)
    return sorted(
        (name, path)
        for name, path in definitions.items()
        if not _has_call_site(name, resolved_src_root)
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero when a verifier has no production call site",
    )
    args = parser.parse_args(argv)
    unwired = find_unwired_verifiers()
    if not unwired:
        print("check_verifiers_are_wired: every verify_* function has a call site in src/")
        return 0
    print(
        "check_verifiers_are_wired: WARNING -- verifier(s) with no call site in src/readme_agent/:"
    )
    for name, path in unwired:
        try:
            rel = path.relative_to(REPO_ROOT)
        except ValueError:
            rel = path
        print(f"  {name} ({rel}) -- reachable only from a test or a standalone script, if at all")
    if args.check:
        return 1
    print("Diagnostic mode: use --check to make an unwired verifier a build failure.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
