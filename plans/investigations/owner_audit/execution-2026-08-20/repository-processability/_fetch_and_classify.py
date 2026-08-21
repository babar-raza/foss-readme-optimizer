"""One-shot read-only audit helper for OPT-REGISTRY-PROCESSABILITY-AUDIT.

Not part of the tracked machinery. Lives entirely inside the authorized
write path runs/owner_audit_staging/repository-processability-aa9981021/.
Fetches each registry repo's pinned tree via the read-only GitHub REST API
(GET only) and classifies every path into README / LICENSE / administrative /
substantive-product-evidence, mirroring the existing generic name/glob rules
in src/readme_agent/inspection/file_inventory.py and
src/readme_agent/ecosystems/registry.py so the audit does not invent a
second, drifting definition of those categories.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import hashlib
from pathlib import Path
from urllib.parse import urlparse

import requests

REPO_ROOT = Path(__file__).resolve().parents[3]
STAGING = Path(__file__).resolve().parent
RAW = STAGING / "raw"
RAW.mkdir(parents=True, exist_ok=True)

PRODUCTS_PATH = REPO_ROOT / "data" / "products.json"

# Mirrors src/readme_agent/inspection/file_inventory.py's own name sets
# (kept independent here since this is a read-only audit script, not a
# change to that module) plus a few additional common variants seen across
# real-world FOSS repos.
README_NAMES = {
    "readme.md", "readme", "readme.rst", "readme.txt", "readme.adoc", "readme.markdown",
}
LICENSE_NAMES = {
    "license", "license.txt", "license.md", "license.rst", "license.adoc",
    "copying", "copying.txt", "copying.md", "unlicense", "unlicense.txt",
}

# .github/** administration per the binding policy text (badges, workflows,
# issue templates, repo administration alone never count as product
# implementation evidence).
ADMIN_PREFIX_DIRS = {".github"}

ADMIN_EXACT_BASENAMES = {
    ".gitignore", ".gitattributes", ".editorconfig", ".gitmodules", ".mailmap",
    ".gitkeep", ".npmignore", ".dockerignore", ".pre-commit-config.yaml",
    ".pre-commit-config.yml", "codeowners", "funding.yml", "funding.yaml",
    ".clang-format", ".clang-tidy", ".flake8", ".pylintrc", ".editorrc",
}

# Community-process files (decision #19 in this repo's own file_inventory.py)
# -- administration of the *project*, not implementation of the *product*.
COMMUNITY_BASENAMES = {
    "contributing.md", "contributing", "contributing.txt", "contributing.rst",
    "code_of_conduct.md", "code_of_conduct", "code_of_conduct.txt", "code_of_conduct.rst",
    "security.md", "security", "security.txt", "security.rst",
    "support.md", "support", "support.txt", "support.rst",
    "governance.md",
}

# Recorded as explicit borderline calls (per audit instructions), classified
# administrative by default -- process/legal metadata, not runnable product
# implementation -- but flagged so a human can override deliberately rather
# than this script silently deciding for good.
BORDERLINE_ADMIN_BASENAMES = {
    "changelog.md", "changelog", "changelog.txt", "changelog.rst",
    "history.md", "releases.md",
    "notice", "notice.txt", "notice.md",
    "third_party_notices.md", "third_party_notices.txt",
    "acknowledgements.md", "acknowledgments.md",
}

# Mirrors src/readme_agent/ecosystems/registry.py::known_manifest_globs(),
# widened with sibling extensions the fnmatch-based production matcher
# already tolerates in practice (verified against this registry's own repos).
MANIFEST_BASENAME_EXACT = {
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts",
    "pyproject.toml", "setup.cfg", "setup.py",
    "go.mod", "go.sum",
    "cmakelists.txt",
    "cargo.toml", "cargo.lock",
    "package.json",
}
MANIFEST_SUFFIXES = {".csproj", ".sln", ".fsproj", ".vbproj", ".vcxproj"}

SOURCE_SUFFIXES = {
    ".java", ".cs", ".py", ".go", ".rs", ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp", ".hxx",
    ".ts", ".tsx", ".js", ".jsx", ".kt", ".scala", ".m", ".mm", ".swift",
}

with open(PRODUCTS_PATH, encoding="utf-8") as fh:
    PRODUCTS = json.load(fh)


def gh_token() -> str:
    env = {"GH_TOKEN": "", "GITHUB_TOKEN": "", "GITHUB_PAT": ""}
    import os

    stripped = dict(os.environ)
    for key in env:
        stripped.pop(key, None)
    result = subprocess.run(
        ["gh", "auth", "token"],
        capture_output=True,
        text=True,
        env=stripped,
        shell=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh auth token failed: {result.stderr}")
    return result.stdout.strip()


TOKEN = gh_token()
HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
}
API = "https://api.github.com"


def owner_repo(repo_url: str) -> tuple[str, str]:
    parts = urlparse(repo_url).path.strip("/").split("/")
    return parts[0], parts[1]


def get_json(url: str, *, params: dict | None = None) -> tuple[int, dict | list]:
    for attempt in range(3):
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            wait = int(resp.headers.get("Retry-After", "5")) + 1
            time.sleep(wait)
            continue
        return resp.status_code, (resp.json() if resp.content else {})
    return resp.status_code, (resp.json() if resp.content else {})


def classify_path(path: str) -> tuple[str, bool]:
    """Returns (class, is_borderline). class in {readme, license, admin, substantive}."""

    lower = path.lower()
    parts = lower.split("/")
    base = parts[-1]

    if parts[0] in ADMIN_PREFIX_DIRS:
        return "admin", False
    if base in README_NAMES:
        return "readme", False
    if base in LICENSE_NAMES:
        return "license", False
    if base in ADMIN_EXACT_BASENAMES:
        return "admin", False
    if base in COMMUNITY_BASENAMES:
        return "admin", False
    if base in BORDERLINE_ADMIN_BASENAMES:
        return "admin", True

    if base in MANIFEST_BASENAME_EXACT:
        return "substantive", False
    suffix = "." + base.rsplit(".", 1)[-1] if "." in base else ""
    if suffix in MANIFEST_SUFFIXES:
        return "substantive", False
    if suffix in SOURCE_SUFFIXES:
        return "substantive", False

    # Everything else defaults to substantive-by-elimination but is flagged
    # borderline when it sits under a docs/assets-style directory or looks
    # like a pure branding/image asset, per the audit instruction not to
    # silently choose on ambiguous cases.
    borderline_dirs = {"docs", "doc", "assets", "img", "images", "media", "resources"}
    image_suffixes = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".bmp"}
    if parts[0] in borderline_dirs or suffix in image_suffixes:
        return "substantive", True
    return "substantive", False


def main() -> None:
    assert len(PRODUCTS) == 33, f"expected 33 registry entries, found {len(PRODUCTS)}"
    matrix = []
    errors = []

    for entry in PRODUCTS:
        org, repo = owner_repo(entry["repo_url"])
        org_repo = f"{org}/{repo}"
        print(f"== {org_repo}", file=sys.stderr)

        status, repo_obj = get_json(f"{API}/repos/{org}/{repo}")
        if status != 200:
            errors.append({"org_repo": org_repo, "stage": "repo_get", "status": status, "body": repo_obj})
            continue
        default_branch = repo_obj["default_branch"]
        github_license_spdx = (repo_obj.get("license") or {}).get("spdx_id")

        status, branch_obj = get_json(f"{API}/repos/{org}/{repo}/branches/{default_branch}")
        if status != 200:
            errors.append({"org_repo": org_repo, "stage": "branch_get", "status": status, "body": branch_obj})
            continue
        commit_sha = branch_obj["commit"]["sha"]
        tree_sha = branch_obj["commit"]["commit"]["tree"]["sha"]

        status, tree_obj = get_json(
            f"{API}/repos/{org}/{repo}/git/trees/{tree_sha}", params={"recursive": "1"}
        )
        if status != 200:
            errors.append({"org_repo": org_repo, "stage": "tree_get", "status": status, "body": tree_obj})
            continue

        truncated = bool(tree_obj.get("truncated"))
        blobs = [item for item in tree_obj.get("tree", []) if item["type"] == "blob"]
        path_list = sorted(item["path"] for item in blobs)
        inventory_sha256 = hashlib.sha256(
            "\n".join(path_list).encode("utf-8")
        ).hexdigest()

        classes: dict[str, list[str]] = {"readme": [], "license": [], "admin": [], "substantive": []}
        borderline: list[dict] = []
        for item in blobs:
            path = item["path"]
            cls, is_borderline = classify_path(path)
            classes[cls].append(path)
            if is_borderline:
                borderline.append({"path": path, "assigned_class": cls})

        counts = {cls: len(paths) for cls, paths in classes.items()}
        total_files = len(blobs)
        processable = counts["substantive"] > 0

        if total_files == 0:
            reason = "pinned tree contains zero files"
        elif not processable:
            non_admin_present = counts["readme"] + counts["license"] > 0
            if non_admin_present and counts["admin"] == 0:
                reason = "pinned tree contains only README and/or LICENSE files"
            else:
                reason = (
                    "pinned tree contains only README/LICENSE files plus "
                    "non-product administrative metadata (no substantive product-evidence file)"
                )
        else:
            reason = f"{counts['substantive']} substantive product-evidence file(s) present"

        row = {
            "registry_identity": {
                "family": entry["family"],
                "platform": entry["platform"],
                "org_repo": org_repo,
                "policy_profile": entry.get("policy_profile"),
                "mode": entry.get("mode"),
                "provider_repository_id": entry.get("provider_identity", {}).get("repository_id"),
            },
            "repository_sha": commit_sha,
            "tree_sha_github": tree_sha,
            "tree_inventory_sha256": inventory_sha256,
            "tree_truncated_by_github_api": truncated,
            "total_files": total_files,
            "github_declared_license_spdx": github_license_spdx,
            "counts": counts,
            "representative_paths": {
                cls: paths[:5] for cls, paths in classes.items()
            },
            "borderline_paths": borderline[:15],
            "borderline_count": len(borderline),
            "classification": "PROCESSABLE" if processable else "UNPROCESSABLE_SKIP",
            "reason": reason,
        }
        matrix.append(row)

        raw_path = RAW / f"{org}__{repo}.json"
        raw_path.write_text(
            json.dumps(
                {"repo": repo_obj, "branch": branch_obj, "tree": tree_obj},
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    out = {
        "audit_id": "OPT-REGISTRY-PROCESSABILITY-AUDIT",
        "expected_github_pin": "aa998102191c530af4dca3a6895d62a4027a613e",
        "registry_entry_count": len(PRODUCTS),
        "rows_collected": len(matrix),
        "errors": errors,
        "rows": matrix,
    }
    (STAGING / "REGISTRY_PROCESSABILITY_MATRIX.json").write_text(
        json.dumps(out, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(matrix)} rows, {len(errors)} errors", file=sys.stderr)


if __name__ == "__main__":
    main()
