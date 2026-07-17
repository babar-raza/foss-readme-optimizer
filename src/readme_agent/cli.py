"""readme-agent CLI — argparse subparsers, mirrors aspose.org's own convention."""

import argparse
import sys

from readme_agent.__about__ import __version__
from readme_agent.errors import ReadmeAgentError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="readme-agent")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("preflight", help="GitHub auth + LLM /models check, fail-closed")

    p_inspect = sub.add_parser("inspect", help="Clone baseline and extract facts (no LLM)")
    p_inspect.add_argument("--repo", required=True, help="org/repo, must be in data/products.json")

    p_generate = sub.add_parser(
        "generate", help="Detect gaps and render a fix (LLM only if needed)"
    )
    p_generate.add_argument("--repo", required=True)
    p_generate.add_argument("--force-regenerate", action="store_true")

    p_validate = sub.add_parser("validate", help="Re-run the validator registry offline")
    p_validate.add_argument("--repo", required=True)
    p_validate.add_argument("--check-links", action="store_true")

    p_run = sub.add_parser(
        "run", help="Full pipeline: preflight -> gitsafety -> inspect -> generate -> validate"
    )
    p_run.add_argument("--repo", required=True)
    p_run.add_argument("--mode", choices=["full", "dry_run"], default="dry_run")
    p_run.add_argument("--force-regenerate", action="store_true")

    p_run_registry = sub.add_parser(
        "run-registry", help="Run every enabled entry in data/products.json"
    )
    p_run_registry.add_argument("--only", help="Comma-separated org/repo list to restrict to")

    p_report = sub.add_parser(
        "report", help="Render a human-readable summary from a prior evidence dir"
    )
    p_report.add_argument("--run-id", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    from readme_agent import commands

    handler = {
        "preflight": commands.cmd_preflight,
        "inspect": commands.cmd_inspect,
        "generate": commands.cmd_generate,
        "validate": commands.cmd_validate,
        "run": commands.cmd_run,
        "run-registry": commands.cmd_run_registry,
        "report": commands.cmd_report,
    }[args.command]

    try:
        return handler(args)
    except ReadmeAgentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
