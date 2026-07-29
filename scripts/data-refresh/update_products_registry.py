"""Refresh data/products.json by scanning the GitHub orgs listed in data/families.json.

Usage:
    python scripts/data-refresh/update_products_registry.py [--dry-run] [--token TOKEN]
    python scripts/data-refresh/update_products_registry.py --org aspose-3d-foss,aspose-pdf-foss

Thin CLI wrapper: source inventory lives in registry/discovery_inventory.py and
stable-identity reconciliation in registry/reconciliation.py, shared with the
supervise-time self-heal. This wrapper only parses arguments, prints, and decides
dry-run vs write.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILIES_PATH = REPO_ROOT / "data" / "families.json"
PRODUCTS_PATH = REPO_ROOT / "data" / "products.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", help="GitHub token (falls back to GH_TOKEN / GITHUB_PAT env)")
    parser.add_argument(
        "--org", help="Comma-separated GitHub orgs to scan (default: every org in families.json)"
    )
    parser.add_argument(
        "--families", type=Path, default=FAMILIES_PATH, help="Path to data/families.json"
    )
    parser.add_argument(
        "--products", type=Path, default=PRODUCTS_PATH, help="Path to data/products.json"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the diff; do not write data/products.json"
    )
    args = parser.parse_args(argv)

    try:
        from readme_agent.registry import discovery
    except ImportError as exc:  # pragma: no cover
        print(f"ERROR: readme_agent must be installed (pip install -e .): {exc}", file=sys.stderr)
        return 2

    token = args.token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_PAT")

    families = discovery.load_families(args.families)
    if args.org:
        wanted = {o.strip() for o in args.org.split(",") if o.strip()}
        families = [f for f in families if f["github_org"] in wanted]

    org_names = [f["github_org"] for f in families]
    print(f"Scanning {len(families)} org(s): {org_names}", file=sys.stderr)
    from readme_agent.registry.discovery_inventory import inventory_sources
    from readme_agent.registry.reconciliation import reconcile_registry

    inventory = inventory_sources(
        families,
        scan_organization=discovery.scan_org,
        classify_repository=discovery.classify_repo_name,
        token=token,
    )
    for failure in inventory.failures:
        print(
            f"WARN: could not scan {failure.source.organization}: {failure.error}",
            file=sys.stderr,
        )
    matched_msg = (
        f"  observed {len(inventory.observations)} repo(s); "
        f"matched {len(inventory.matched_observations)}"
    )
    print(matched_msg, file=sys.stderr)

    existing: list[dict] = []
    if args.products.is_file():
        existing = json.loads(args.products.read_text(encoding="utf-8"))

    reconciliation = reconcile_registry(existing, inventory)
    merged = reconciliation.entries
    new_count = len(merged) - len(existing)
    action_counts: dict[str, int] = {}
    for record in reconciliation.records:
        action_counts[record.action] = action_counts.get(record.action, 0) + 1
    print(
        f"  inventory_complete={inventory.complete} reconciliation={action_counts}",
        file=sys.stderr,
    )

    if args.dry_run:
        print(f"{'family':<12} {'platform':<12} {'repo_name':<40} {'mode':<10} {'active'}")
        print("-" * 90)
        for e in merged:
            print(
                f"{e['family']:<12} {e['platform']:<12} {e['repo_name']:<40} "
                f"{e['mode']:<10} {e.get('active', False)}"
            )
        print(f"\nTotal: {len(merged)}  new={new_count}")
        print("DRY-RUN: data/products.json was NOT modified.")
        return 0

    discovery.write_atomic(args.products, merged)
    print(f"OK  wrote {len(merged)} entries to {args.products} (new={new_count})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
