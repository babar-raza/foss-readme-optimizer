"""Onboard a registry entry: author its `config/policies/<profile>.yml` and
set its `ecosystem`/`policy_profile` fields in `data/products.json` (both
"agent-owned" fields per `data/README.md` -- never touched by the automated
discovery/self-heal scanners, only by this explicit, human-invoked tool).

Usage:
    python scripts/registry/generate_policy_profile.py \
        --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp
    python scripts/registry/generate_policy_profile.py --all-not-onboarded [--dry-run]

Thin CLI wrapper: the mechanical policy-content derivation lives in
`src/readme_agent/registry/policy_generator.py` (unit-tested there against
golden fixtures reproducing the 3 real, already-onboarded profiles). This
wrapper only resolves the one genuinely per-repo fact -- the detected
license, via a live GitHub repo-metadata lookup (the same signal
`preflight/github_check.py::check_repo()` already uses) -- and writes files.

Per `docs/policy-authoring.md`'s own documented onboarding order: run
`readme-agent inspect --repo <x>` against the result before ever running
`generate`/`supervise`, and never flip `mode` to `"full"` without a prior
`dry_run` pass.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

PRODUCTS_PATH = REPO_ROOT / "data" / "products.json"
FAMILIES_PATH = REPO_ROOT / "data" / "families.json"
POLICIES_DIR = REPO_ROOT / "config" / "policies"


def _org_repo(entry: dict) -> str:
    return f"{entry['repo_url'].split('/')[3]}/{entry['repo_name']}"


def _profile_name(entry: dict) -> str:
    org = entry["repo_url"].split("/")[3]
    return f"{org}-{entry['platform']}"


def _fallback_license_from_nested_license_dir(org_repo: str, token: str) -> str | None:
    """GitHub's own license classifier returns `null` for several real repos
    in this org (confirmed live, 2026-07-22) because their LICENSE file
    lives nested inside a nonstandard `License/` or `license/` directory
    rather than at repo root -- exactly the same edge case
    `config/policies/aspose-cells-foss.yml`'s own comment already documents
    for the one previously-onboarded pilot. Verified by direct content
    inspection for all 6 repos this hits in this registry: every one is a
    real MIT license, just not where GitHub's classifier looks. This checks
    the real file content (ground truth), never guesses."""
    import base64

    import requests

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    for dirname in ("License", "license"):
        resp = requests.get(
            f"https://api.github.com/repos/{org_repo}/contents/{dirname}",
            headers=headers,
            timeout=15,
        )
        if resp.status_code != 200 or not isinstance(resp.json(), list):
            continue
        for item in resp.json():
            if "license" not in item["name"].lower():
                continue
            file_resp = requests.get(item["url"], headers=headers, timeout=15)
            if file_resp.status_code != 200:
                continue
            content = base64.b64decode(file_resp.json()["content"]).decode(
                "utf-8", errors="replace"
            )
            if "mit license" in content.lower():
                return "MIT"
    return None


def _fallback_license_from_package_json(org_repo: str, token: str) -> str | None:
    """A second real gap in the same class: a repo with no LICENSE file
    anywhere in the tree at all, but a standard `license` field in
    `package.json` (npm's own convention) -- confirmed live, 2026-07-22,
    for `aspose-3d-foss/Aspose.3D-FOSS-for-TypeScript`. Ground truth from a
    real, standard project-metadata file, never a guess."""
    import base64

    import requests

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = requests.get(
        f"https://api.github.com/repos/{org_repo}/contents/package.json",
        headers=headers,
        timeout=15,
    )
    if resp.status_code != 200:
        return None
    try:
        content = base64.b64decode(resp.json()["content"]).decode("utf-8", errors="replace")
        license_value = json.loads(content).get("license")
    except (KeyError, ValueError):
        return None
    return license_value if isinstance(license_value, str) else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", help="org/repo to onboard (e.g. aspose-cells-foss/Aspose.Cells-FOSS-for-Cpp)"
    )
    parser.add_argument(
        "--all-not-onboarded",
        action="store_true",
        help="Onboard every dry_run/full entry currently missing ecosystem/policy_profile",
    )
    parser.add_argument("--token", help="GitHub token (falls back to GH_TOKEN / GITHUB_PAT env)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would be generated; write nothing"
    )
    args = parser.parse_args(argv)

    if not args.repo and not args.all_not_onboarded:
        parser.error("one of --repo or --all-not-onboarded is required")

    from readme_agent import env
    from readme_agent.preflight.github_check import check_repo
    from readme_agent.registry import discovery
    from readme_agent.registry.policy_generator import generate_policy_profile

    token = args.token or env.gh_token()
    if not token:
        print(
            "ERROR: no GH_TOKEN/GITHUB_PAT set -- a live license lookup needs one", file=sys.stderr
        )
        return 2

    products = json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))
    families = {
        f["family"]: f["name"] for f in json.loads(FAMILIES_PATH.read_text(encoding="utf-8"))
    }

    if args.repo:
        targets = [e for e in products if _org_repo(e) == args.repo]
        if not targets:
            print(f"ERROR: {args.repo!r} not found in {PRODUCTS_PATH}", file=sys.stderr)
            return 2
    else:
        targets = [
            e
            for e in products
            if e.get("mode") != "disabled"
            and (e.get("ecosystem") is None or e.get("policy_profile") is None)
        ]

    print(f"Onboarding {len(targets)} entr{'y' if len(targets) == 1 else 'ies'}", file=sys.stderr)

    for entry in targets:
        org_repo = _org_repo(entry)
        family_name = families.get(entry["family"])
        if family_name is None:
            print(
                f"SKIP {org_repo}: family {entry['family']!r} not found in {FAMILIES_PATH}",
                file=sys.stderr,
            )
            continue

        check = check_repo(org_repo, token)
        if not check.ok:
            print(f"SKIP {org_repo}: live repo check failed ({check.error})", file=sys.stderr)
            continue
        detected_license = check.license
        if detected_license is None:
            detected_license = _fallback_license_from_nested_license_dir(org_repo, token)
        if detected_license is None:
            detected_license = _fallback_license_from_package_json(org_repo, token)
        if detected_license is None:
            print(
                f"SKIP {org_repo}: no license detected (classifier and nested-directory "
                "fallback both came up empty) -- verify manually, never guess",
                file=sys.stderr,
            )
            continue

        profile_name = _profile_name(entry)
        policy = generate_policy_profile(
            profile_name=profile_name,
            family=entry["family"],
            family_name=family_name,
            platform=entry["platform"],
            repo_name=entry["repo_name"],
            detected_license=detected_license,
        )

        if args.dry_run:
            print(
                f"WOULD WRITE config/policies/{profile_name}.yml + "
                f"set ecosystem/policy_profile for {org_repo}"
            )
            continue

        policy_path = POLICIES_DIR / f"{profile_name}.yml"
        policy_path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
        entry["ecosystem"] = entry["platform"]
        entry["policy_profile"] = profile_name
        print(f"OK   {org_repo} -> {policy_path.relative_to(REPO_ROOT)}", file=sys.stderr)

    if not args.dry_run:
        discovery.write_atomic(PRODUCTS_PATH, products)
        print(f"OK   updated {PRODUCTS_PATH}", file=sys.stderr)
    else:
        print("DRY-RUN: nothing was written.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
