"""ONB-004: report which data/products.json entries still lack a policy
profile (ecosystem/policy_profile both null), grouped by family/platform, so
the real remaining onboarding backlog is visible at a glance instead of
requiring a manual products.json read.

Usage:
    python scripts/data-refresh/policy_profile_coverage_report.py

Read-only. For each backlog entry, prints the `readme-agent scaffold-policy`
command that would start authoring it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTS_PATH = REPO_ROOT / "data" / "products.json"


def main() -> int:
    products = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    backlog = [e for e in products if e["ecosystem"] is None or e["policy_profile"] is None]
    covered_count = len(products) - len(backlog)

    print(f"Registry: {len(products)} entries, {covered_count} with a policy profile configured.\n")

    if not backlog:
        print("No backlog: every registry entry has ecosystem + policy_profile configured.")
        return 0

    print(f"Backlog ({len(backlog)} entries lacking a policy profile):\n")
    print(f"{'family':<12} {'platform':<12} {'mode':<10} org_repo")
    print("-" * 70)
    for e in sorted(backlog, key=lambda x: (x["family"], x["platform"])):
        org = e["repo_url"].split("/")[3]
        org_repo = f"{org}/{e['repo_name']}"
        print(f"{e['family']:<12} {e['platform']:<12} {e['mode']:<10} {org_repo}")

    print("\nTo start authoring one of these:")
    for e in sorted(backlog, key=lambda x: (x["family"], x["platform"])):
        org = e["repo_url"].split("/")[3]
        org_repo = f"{org}/{e['repo_name']}"
        print(f"  readme-agent scaffold-policy --repo {org_repo}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
