"""Verify the real, checkable business facts a policy profile asserts:
GitHub's own detected license, and whether products.aspose.org/products.aspose.com
URLs for a family/platform actually resolve.

Thin CLI wrapper -- the actual verification logic lives once in
src/readme_agent/registry/policy_facts.py, shared with `readme-agent
scaffold-policy` (ONB-004).

Usage:
    python scripts/data-refresh/verify_policy_profile_facts.py --org-repo org/repo ...
    python scripts/data-refresh/verify_policy_profile_facts.py --all-non-disabled

Read-only: one GitHub API GET per repo (license), plus one HTTP GET per
org/com URL at family and platform depth. Prints a table; does not write
anything (a human/agent applies the results to the actual policy YAML and
to data/aspose_com_links.json).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTS_PATH = REPO_ROOT / "data" / "products.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--org-repo", action="append", default=None)
    parser.add_argument("--all-non-disabled", action="store_true")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        from readme_agent import env
        from readme_agent.registry import policy_facts
    except ImportError as exc:  # pragma: no cover
        print(f"ERROR: readme_agent must be installed (pip install -e .): {exc}", file=sys.stderr)
        return 2

    products = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    if args.all_non_disabled:
        entries = [e for e in products if e["mode"] != "disabled"]
    elif args.org_repo:
        wanted = set(args.org_repo)
        entries = [
            e for e in products if f"{e['repo_url'].split('/')[3]}/{e['repo_name']}" in wanted
        ]
    else:
        parser.error("pass --org-repo (repeatable) or --all-non-disabled")
        return 2

    token = env.gh_token()
    results = []
    for entry in entries:
        org_repo = f"{entry['repo_url'].split('/')[3]}/{entry['repo_name']}"
        print(f"Verifying {entry['family']}/{entry['platform']}...", file=sys.stderr)
        results.append(
            policy_facts.verify_repo_facts(org_repo, entry["family"], entry["platform"], token)
        )

    header = (
        f"{'family/platform':<22} {'license':<10} {'org(family)':<12} {'org(platform)':<14} "
        f"{'com(family)':<12} {'com(platform)':<14}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['family'] + '/' + r['platform']:<22} {str(r['license']):<10} "
            f"{str(r['org_family_status']):<12} {str(r['org_platform_status']):<14} "
            f"{str(r['com_family_status']):<12} {str(r['com_platform_status']):<14}"
        )

    if args.json_out:
        args.json_out.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.json_out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
