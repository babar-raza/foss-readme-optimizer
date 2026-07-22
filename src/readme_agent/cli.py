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
    p_inspect.add_argument(
        "--check-install",
        action="store_true",
        help="Live-resolve the install path against the package registry (opt-in, network)",
    )

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
    p_run.add_argument(
        "--durable-state",
        action="store_true",
        help=(
            "Check/record accepted state via this repo's own git-ref-backed "
            "state backend (opt-in, network write to this project's own "
            "remote -- never a default, matching --check-install)"
        ),
    )

    p_run_registry = sub.add_parser(
        "run-registry", help="Run every enabled entry in data/products.json"
    )
    p_run_registry.add_argument("--only", help="Comma-separated org/repo list to restrict to")
    p_run_registry.add_argument(
        "--durable-state", action="store_true", help="See `run --durable-state`"
    )

    p_profile_registry = sub.add_parser(
        "profile-registry",
        help=(
            "Read-only: profile every data/products.json entry regardless of mode "
            "(decision #40) -- with --durable-state, a repo whose upstream commit "
            "hasn't changed since the last run is a cache hit, not a re-clone"
        ),
    )
    p_profile_registry.add_argument("--only", help="Comma-separated org/repo list to restrict to")
    p_profile_registry.add_argument(
        "--durable-state", action="store_true", help="See `run --durable-state`"
    )

    p_supervise = sub.add_parser(
        "supervise",
        help=(
            "Wave 5: observe -> plan -> execute -> observe -> replan against the real "
            "capability registry, dynamic capability selection instead of a fixed pipeline"
        ),
    )
    p_supervise.add_argument("--repo", required=True)
    p_supervise.add_argument(
        "--durable-state",
        action="store_true",
        help="See `run --durable-state` -- same opt-in convention, same backend.",
    )
    p_supervise.add_argument(
        "--domain",
        default=None,
        help=(
            "Wave 7: run exactly one registered specialist domain (e.g. "
            "readme_reconciliation) instead of the full specialist-tier sweep and planner "
            "loop -- the concrete, usable-today version of 'trigger only the README agent' "
            "once every surface has an accepted baseline and only one changed. See "
            "specialists/registry.py::all_domains() for the registered set."
        ),
    )
    p_supervise.add_argument(
        "--no-registry-heal",
        action="store_true",
        help=(
            "Skip the supervise-time registry drift self-heal (CORE-034) -- used by "
            "portfolio fan-out jobs so 25 matrix runs don't each rescan every GitHub org; "
            "a dedicated once-per-pass job heals instead."
        ),
    )

    p_report = sub.add_parser(
        "report", help="Render a human-readable summary from a prior evidence dir"
    )
    p_report.add_argument("--run-id", required=True)

    p_model_route_enable = sub.add_parser(
        "model-route-enable",
        help=(
            "Wave 8.6 (OPS-011 extension): explicit, human-authored re-enable of an LLM job "
            "route a golden-set run previously disabled -- never automatic, never silent."
        ),
    )
    p_model_route_enable.add_argument("--job", required=True, help="e.g. supervisor_planning")
    p_model_route_enable.add_argument(
        "--reason", required=True, help="Why this route is being re-enabled"
    )

    p_scaffold_policy = sub.add_parser(
        "scaffold-policy",
        help=(
            "ONB-004: pre-fill config/policies/<profile>.yml for a registry entry -- "
            "live-verifies license + products.aspose.org/.com links (never guesses "
            "a URL by string-formatting, decision #4); leaves anything unverifiable "
            "as an explicit TODO. Does not itself touch data/products.json -- wiring "
            "ecosystem/policy_profile in stays a separate, deliberate human step "
            "(docs/policy-authoring.md)."
        ),
    )
    p_scaffold_policy.add_argument(
        "--repo", required=True, help="org/repo, must already be in data/products.json"
    )
    p_scaffold_policy.add_argument(
        "--force", action="store_true", help="Overwrite an existing profile file"
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    # README/evidence content this CLI prints is arbitrary upstream text (e.g.
    # emoji in a bot-authored README) that a native Windows console's default
    # cp1252 encoding can't represent -- reconfigure rather than crash.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

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
        "profile-registry": commands.cmd_profile_registry,
        "supervise": commands.cmd_supervise,
        "report": commands.cmd_report,
        "model-route-enable": commands.cmd_model_route_enable,
        "scaffold-policy": commands.cmd_scaffold_policy,
    }[args.command]

    try:
        return handler(args)
    except ReadmeAgentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
