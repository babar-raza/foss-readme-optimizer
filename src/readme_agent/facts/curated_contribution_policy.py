"""Validate maintainer-authored contribution policy without promoting technical claims."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

_NUMBERED = re.compile(r"^\d+\.\s+")
_RUN_COMMANDS = re.compile(r"^\d+\. Run (?P<commands>.+)\.$")
_SAFE_STATEMENTS = (
    re.compile(r"(?i)^Contributions are welcome!? Please feel free to submit a Pull Request\.$"),
    re.compile(r"(?i)^Issues and pull requests are welcome\. Please:$"),
    re.compile(r"^\d+\. Fork the repository$"),
    re.compile(
        r"^\d+\. Create your feature branch "
        r"\(`git checkout -b feature/[a-z0-9._-]+`\)$"
    ),
    re.compile(r"^\d+\. Commit your changes \(`git commit -m '[^']+'`\)$"),
    re.compile(r"^\d+\. Push to the branch \(`git push origin feature/[a-z0-9._-]+`\)$"),
    re.compile(r"^\d+\. Open a Pull Request$"),
    re.compile(r"^\d+\. Keep changes focused\.$"),
    re.compile(r"^\d+\. Add tests for new behavior and bug fixes\.$"),
    re.compile(r"^\d+\. Write code comments and docstrings in English\.$"),
    re.compile(r"^\d+\. Document public API changes and important limitations\.$"),
    re.compile(
        r"^When reporting a [A-Za-z0-9 /_-]+ problem, include a minimal "
        r"[A-Z][A-Z0-9.+-]{1,9} that can be shared publicly whenever possible\.$"
    ),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _statements(body: str) -> list[str]:
    statements: list[str] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            statements.append(" ".join(paragraph))
            paragraph.clear()

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
        elif _NUMBERED.match(line):
            flush()
            statements.append(line)
        else:
            paragraph.append(line)
    flush()
    return statements


def _script_corpus(root: Path) -> str:
    text: list[str] = []
    for name in ("check.sh", "build.sh"):
        path = root / "scripts" / name
        if not path.is_file():
            continue
        try:
            text.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return "\n".join(text)


def _statement_is_supported(statement: str, scripts: str) -> bool:
    if any(pattern.fullmatch(statement) for pattern in _SAFE_STATEMENTS):
        return True
    run = _RUN_COMMANDS.fullmatch(statement)
    if run is None:
        return False
    commands = re.findall(r"`([^`]+)`", run.group("commands"))
    return bool(commands) and all(command in scripts for command in commands)


def validated_readme_contribution_policy(root: Path, readme: Path) -> dict[str, object] | None:
    """Return exact safe policy statements when every statement has a bounded owner."""

    try:
        readme_text = readme.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = re.search(
        r"(?ims)^##\s+Contributing\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        readme_text,
    )
    if match is None:
        return None
    statements = _statements(match.group("body"))
    scripts = _script_corpus(root)
    if not statements or not all(
        _statement_is_supported(statement, scripts) for statement in statements
    ):
        return None
    return {
        "source_path": "README.md",
        "source_sha256": _sha256(readme),
        "validated_statements": statements,
    }


__all__ = ["validated_readme_contribution_policy"]
