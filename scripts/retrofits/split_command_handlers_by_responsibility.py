"""Split the audited CLI handler monolith into responsibility modules."""

import ast
import hashlib
from pathlib import Path

SOURCE = Path("src/readme_agent/commands.py")
EXPECTED_SHA256 = "33559ba4f5cf9e78e98ba54857d756fc523e2c5cb7e6602c282b6eb0b3306d16"

GROUPS = {
    "commands_compatibility.py": {
        "cmd_preflight",
        "cmd_inspect",
        "cmd_generate",
        "cmd_validate",
        "cmd_run",
        "_durable_state_backend",
        "cmd_run_registry",
        "cmd_profile_registry",
        "cmd_report",
    },
    "commands_supervision.py": {
        "cmd_supervise",
        "_force_durable_state_backend",
        "_cmd_supervise_single_domain",
    },
    "commands_governance.py": {
        "cmd_authorization_validate",
        "cmd_golden_set_run",
        "cmd_model_route_enable",
        "_SCAFFOLD_SECONDARY_LINKS",
        "_SCAFFOLD_PROHIBITED_TERMS",
        "_SCAFFOLD_LINK_WHITELIST_DOMAINS",
        "_build_scaffold_profile",
        "cmd_scaffold_policy",
    },
}

HEADERS = {
    "commands_compatibility.py": (
        '"""Read-only compatibility and diagnostic CLI handlers."""\n\n'
        "import argparse\nimport sys\n"
    ),
    "commands_supervision.py": (
        '"""Canonical repository-supervision CLI handlers."""\n\nimport argparse\nimport sys\n'
    ),
    "commands_governance.py": (
        '"""Authorization, evaluation, and policy-governance CLI handlers."""\n\n'
        "import argparse\nimport sys\n"
    ),
}


def _node_name(node: ast.AST) -> str | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return node.name
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if len(targets) == 1 and isinstance(targets[0], ast.Name):
            return targets[0].id
    return None


def main() -> None:
    raw = SOURCE.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(
            f"refusing to split commands.py: expected {EXPECTED_SHA256}, observed {digest}"
        )
    text = raw.decode("utf-8")
    tree = ast.parse(text)
    segments: dict[str, str] = {}
    for node in tree.body:
        name = _node_name(node)
        if name is not None:
            segment = ast.get_source_segment(text, node)
            if segment is not None:
                segments[name] = segment

    for filename, names in GROUPS.items():
        missing = names - segments.keys()
        if missing:
            raise SystemExit(f"{filename}: missing source nodes {sorted(missing)}")
        ordered = [
            segments[name]
            for node in tree.body
            if (name := _node_name(node)) is not None and name in names
        ]
        output = HEADERS[filename] + "\n\n\n".join(ordered) + "\n"
        SOURCE.with_name(filename).write_text(output, encoding="utf-8", newline="\n")

    facade = '''"""Stable CLI handler façade over responsibility-sized modules."""

from readme_agent.commands_compatibility import (
    cmd_generate,
    cmd_inspect,
    cmd_preflight,
    cmd_profile_registry,
    cmd_report,
    cmd_run,
    cmd_run_registry,
    cmd_validate,
)
from readme_agent.commands_governance import (
    cmd_authorization_validate,
    cmd_golden_set_run,
    cmd_model_route_enable,
    cmd_scaffold_policy,
)
from readme_agent.commands_supervision import cmd_supervise

__all__ = [
    "cmd_authorization_validate",
    "cmd_generate",
    "cmd_golden_set_run",
    "cmd_inspect",
    "cmd_model_route_enable",
    "cmd_preflight",
    "cmd_profile_registry",
    "cmd_report",
    "cmd_run",
    "cmd_run_registry",
    "cmd_scaffold_policy",
    "cmd_supervise",
    "cmd_validate",
]
'''
    SOURCE.write_text(facade, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
