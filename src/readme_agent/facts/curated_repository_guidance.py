"""Collect source-bound repository guidance, commands, constraints, and security routes."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

from readme_agent.facts.curated_constraint_evidence import source_limitations

_PRIVATE_REPORT_URL = re.compile(
    r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/security/advisories/new"
)
_CONSTRAINT = re.compile(
    r"\b(?:not certification-grade|not fully implemented|not implemented|"
    r"does not perform layout reflow|only\b.+\bimplemented|unsupported)\b",
    flags=re.IGNORECASE,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repository_development_commands(root: Path) -> tuple[object, list[str]] | None:
    """Return exact checked-in validation scripts and a source-derived MCP test command."""

    entries: list[dict[str, object]] = []
    locations: list[str] = []
    mcp_tests = sorted(path for path in (root / "tests/mcp").glob("test_*.py") if path.is_file())
    if mcp_tests:
        modules = [
            path.relative_to(root).with_suffix("").as_posix().replace("/", ".")
            for path in mcp_tests
        ]
        paths = [
            {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)}
            for path in mcp_tests
        ]
        entries.append(
            {
                "kind": "focused_test",
                "scope": "MCP",
                "command": "python -m unittest " + " ".join(modules),
                "sources": paths,
            }
        )
        locations.extend(str(item["path"]) for item in paths)
    scripts = root / "scripts"
    if scripts.is_dir():
        for path in sorted(scripts.glob("*.sh")):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            commands = [
                line.strip() for line in text.splitlines() if line.strip().startswith("python -m ")
            ]
            if not commands:
                continue
            relative = path.relative_to(root).as_posix()
            entries.append(
                {
                    "kind": "repository_script",
                    "command": relative,
                    "embedded_commands": commands,
                    "path": relative,
                    "source_sha256": _sha256(path),
                }
            )
            locations.append(relative)
    if not entries:
        return None
    return {"entries": entries}, sorted(set(locations))


def repository_documentation_assets(root: Path) -> tuple[object, list[str]] | None:
    """Return checksum-bound implementation and community documents."""

    names = (
        "supported-features.md",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
    )
    entries = [
        {"path": name, "sha256": _sha256(root / name)} for name in names if (root / name).is_file()
    ]
    if not entries:
        return None
    return {"entries": entries}, [str(item["path"]) for item in entries]


def repository_security_guidance(root: Path) -> tuple[object, list[str]] | None:
    """Return the repository security route and statically inspectable resource controls."""

    policy = root / "SECURITY.md"
    if not policy.is_file():
        return None
    try:
        policy_text = policy.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    private_url = _PRIVATE_REPORT_URL.search(policy_text)
    value: dict[str, object] = {
        "policy": {
            "path": "SECURITY.md",
            "sha256": _sha256(policy),
            "private_reporting_url": private_url.group(0) if private_url else None,
        }
    }
    locations = ["SECURITY.md"]
    limits_path = next(iter(sorted((root / "src").glob("**/load_limits.py"))), None)
    if limits_path is not None and limits_path.is_file():
        try:
            tree = ast.parse(limits_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            tree = None
        if tree is not None:
            limits_class = next(
                (
                    node
                    for node in tree.body
                    if isinstance(node, ast.ClassDef) and node.name == "PdfLoadLimits"
                ),
                None,
            )
            if limits_class is not None:
                fields = [
                    node.target.id
                    for node in limits_class.body
                    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                ]
                methods = [
                    node.name
                    for node in limits_class.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and not node.name.startswith("_")
                ]
                relative = limits_path.relative_to(root).as_posix()
                bounded_defaults = all(
                    not (isinstance(node.value, ast.Constant) and node.value.value is None)
                    for node in limits_class.body
                    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
                )
                value["resource_limits"] = {
                    "class": "PdfLoadLimits",
                    "fields": fields,
                    "methods": methods,
                    "bounded_defaults": bounded_defaults,
                    "path": relative,
                    "source_sha256": _sha256(limits_path),
                }
                locations.append(relative)
    document_path = next(iter(sorted((root / "src").glob("**/document.py"))), None)
    if document_path is not None and document_path.is_file():
        try:
            document_tree = ast.parse(document_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            document_tree = None
        if document_tree is not None:
            entry_points = sorted(
                node.name
                for node in ast.walk(document_tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in {"__init__", "load_from", "open_streaming"}
                and any(
                    argument.arg == "limits"
                    for argument in (*node.args.args, *node.args.kwonlyargs)
                )
            )
            if entry_points:
                relative = document_path.relative_to(root).as_posix()
                value["resource_limits"]["entry_points"] = entry_points  # type: ignore[index]
                locations.append(relative)
    features = root / "supported-features.md"
    if features.is_file() and "resource_limits" in value:
        try:
            features_text = " ".join(features.read_text(encoding="utf-8").split())
        except (OSError, UnicodeDecodeError):
            features_text = ""
        required = (
            "Lazy opening still defers page-content decoding",
            "`PdfLoadLimits.unlimited()` returns a policy with every field disabled",
            "they are not a proof",
            "Run highly hostile documents in an isolated worker",
        )
        if all(marker in features_text for marker in required):
            value["operational_guidance"] = {
                "lazy_work_uses_shared_limits": True,
                "unlimited_disables_safeguards": True,
                "limits_are_not_a_complete_dos_sandbox": True,
                "isolate_highly_hostile_documents": True,
                "path": "supported-features.md",
                "source_sha256": _sha256(features),
            }
            locations.append("supported-features.md")
    return value, locations


def repository_contribution_guidance(root: Path) -> tuple[object, list[str]] | None:
    """Return only contribution entry points that exist independently of README prose."""

    contribution = root / "CONTRIBUTING.md"
    if contribution.is_file():
        return (
            {"path": "CONTRIBUTING.md", "sha256": _sha256(contribution)},
            ["CONTRIBUTING.md"],
        )
    scripts = [
        path
        for path in (root / "scripts").glob("*.sh")
        if path.is_file() and path.name in {"check.sh", "build.sh"}
    ]
    if not scripts:
        return None
    rows = [
        {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)}
        for path in sorted(scripts)
    ]
    return {"validation_scripts": rows}, [str(row["path"]) for row in rows]


def _sentences(text: str) -> list[str]:
    normalized = " ".join(text.split())
    return [item.strip() for item in re.split(r"(?<=[.!?])\s+", normalized) if item.strip()]


def source_guidance_limitations(root: Path) -> tuple[object, list[str]] | None:
    """Return explicit source constraints, including docstrings and literal notices."""

    found: list[dict[str, object]] = []
    locations: list[str] = []
    executable = source_limitations(root)
    if executable is not None:
        rows, row_locations = executable
        if isinstance(rows, list):
            found.extend(item for item in rows if isinstance(item, dict))
        locations.extend(row_locations)
    source_root = root / "src"
    if not source_root.is_dir():
        return (found, sorted(set(locations))) if found else None
    for path in sorted(source_root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        relative = path.relative_to(root).as_posix()
        digest = _sha256(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            for sentence in _sentences(node.value):
                if _CONSTRAINT.search(sentence) is None:
                    continue
                record = {
                    "statement": sentence,
                    "path": relative,
                    "line": getattr(node, "lineno", 1),
                    "source_sha256": digest,
                }
                if any(item.get("statement") == sentence for item in found):
                    continue
                found.append(record)
                locations.append(relative)
    if not found:
        return None
    substantial = [
        item for item in found if len(re.findall(r"[A-Za-z0-9]+", str(item.get("statement")))) >= 5
    ]
    prioritized = sorted(
        substantial,
        key=lambda item: (
            0 if "certification-grade" in str(item.get("statement")).casefold() else 1,
            0 if "layout reflow" in str(item.get("statement")).casefold() else 1,
            0 if "not fully implemented" in str(item.get("statement")).casefold() else 1,
            0 if "not implemented" in str(item.get("statement")).casefold() else 1,
            str(item.get("path")),
            int(str(item.get("line") or 0)),
        ),
    )[:10]
    selected_locations = sorted({str(item["path"]) for item in prioritized})
    return prioritized, selected_locations
