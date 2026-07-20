# governed_by: plans/master.md + plans/requirements.md + plans/GOVERNANCE.md (governed)
# artifact_role: analysis_or_evidence_only
"""Survey all 25 repositories in data/products.json on real GitHub — not just the
3 enabled pilots. GET-only (repo core, community profile, languages, releases,
README) via `gh api`; then run the SHIPPED gap_detector + ecosystem dispatch
against each real README to see what the tool would actually find across the
whole portfolio the registry targets. No mutation, no clone, no write.

Evidence: plans/investigations/evidence/full-registry-github-survey/
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))
from readme_agent.readme.gap_detector import detect as detect_gaps  # noqa: E402

REGISTRY = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
OUT = REPO_ROOT / "plans" / "investigations" / "evidence" / "full-registry-github-survey"
OUT.mkdir(parents=True, exist_ok=True)

ECOSYSTEM_BY_PLATFORM = {
    "java": "maven",
    "net": "nuget",
    "python": "pypi",
    "typescript": "npm",
    "cpp": "conan",
    "go": "gomod",
}
MANIFEST_FILE_BY_PLATFORM = {
    "java": "pom.xml",
    "net": "*.csproj/*.nuspec",
    "python": "setup.py/pyproject.toml",
    "typescript": "package.json",
    "cpp": "conanfile.py/CMakeLists.txt",
    "go": "go.mod",
}


def org_repo(entry: dict) -> tuple[str, str]:
    path = entry["repo_url"].split("github.com/", 1)[1]
    org, repo = path.split("/", 1)
    return org, repo


def gh_api(path: str) -> tuple[int, dict | list | None, str]:
    r = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if r.returncode != 0:
        return 1, None, (r.stderr or "").strip()[:200]
    if not r.stdout:
        return 1, None, "empty response"
    try:
        return 0, json.loads(r.stdout), ""
    except json.JSONDecodeError as e:
        return 1, None, f"bad json: {e}"


def visitor_experience(readme: str, platform: str) -> dict:
    """What a human repo visitor actually needs, answered from the README text
    itself (deterministic heuristics, not the 4-element promo-gap check):
      1. Understand what the product does and who it's for -- in the FIRST screen.
      2. Trust it's real and maintained.
      3. Know how to install/get it for THEIR platform.
      4. See it work (a runnable example).
      5. Find what to do next (docs/support/contributing) without hunting.
    This is the BIZ-002/RDM-005..010 lens: product-first, not gap-first.
    """
    lower = readme.lower()
    lines = readme.split("\n")
    first_screen = "\n".join(lines[:25])  # ~ what's visible without scrolling
    first_screen_lower = first_screen.lower()

    # 1. First-screen product explanation: a sentence describing what it DOES,
    # not just its name (name-only H1 + one-liner is a common bot-template smell).
    non_heading_non_badge_lines = [
        ln
        for ln in lines[:15]
        if ln.strip()
        and not ln.strip().startswith("#")
        and not (ln.strip().startswith("[![") or ln.strip().startswith("!["))
    ]
    first_prose = " ".join(non_heading_non_badge_lines[:3])
    explains_what_it_does = len(first_prose.split()) >= 8 and any(
        w in first_prose.lower()
        for w in (
            "library",
            "tool",
            "convert",
            "read",
            "write",
            "generate",
            "parse",
            "create",
            "process",
            "render",
            "export",
            "import",
            "api",
            "sdk",
        )
    )

    # 2. Trust signals: license visible, badges (build/version) present, install
    # path doesn't look broken on its face (heuristic only -- real check needs
    # package-registry cross-check, done separately per-platform below).
    has_license_signal = "license" in lower
    has_build_or_version_badge = "shields.io" in lower or "badge" in lower

    # 3. Install/getting-started path present and platform-appropriate.
    install_keywords = {
        "java": ("maven", "gradle", "pom.xml", "<dependency>"),
        "net": ("nuget", "dotnet add", "packagereference", ".csproj"),
        "python": ("pip install", "pip3 install", "requirements.txt"),
        "typescript": ("npm install", "yarn add", "package.json"),
        "cpp": ("cmake", "conan", "vcpkg", "#include"),
        "go": ("go get", "go install", "go.mod"),
    }
    kws = install_keywords.get(platform, ())
    has_platform_install = any(k in lower for k in kws)
    has_any_install_section = bool(
        re.search(r"#+\s*(install|getting started|setup|quick ?start)", lower)
    )

    # 4. A runnable example (fenced code block beyond the install snippet).
    code_fence_count = readme.count("```")
    has_example_beyond_install = code_fence_count >= 4  # >=2 fenced blocks

    # 5. Next-step navigation: links to docs/support/contributing/issues.
    has_docs_link = "docs." in lower or "/docs" in lower or "documentation" in lower
    has_support_path = any(w in lower for w in ("support", "contact", "help", "issues"))

    # First-screen promotional dominance (RDM-002/BIZ-001): a commercial link
    # appearing before ANY product explanation.
    first_commercial_idx = None
    for kw in (
        "products.aspose.com",
        "products.aspose.org",
        "buy now",
        "purchase",
        "commercial license",
        "get a license",
    ):
        idx = first_screen_lower.find(kw)
        if idx != -1 and (first_commercial_idx is None or idx < first_commercial_idx):
            first_commercial_idx = idx
    promo_before_explanation = first_commercial_idx is not None and not explains_what_it_does

    checklist = {
        "explains_what_it_does_in_first_screen": explains_what_it_does,
        "has_license_signal": has_license_signal,
        "has_build_or_version_badge": has_build_or_version_badge,
        "has_platform_appropriate_install": has_platform_install,
        "has_any_install_section": has_any_install_section,
        "has_runnable_example": has_example_beyond_install,
        "has_docs_link": has_docs_link,
        "has_support_or_contribution_path": has_support_path,
        "promo_before_product_explanation": promo_before_explanation,
    }
    score = sum(1 for k, v in checklist.items() if v and k != "promo_before_product_explanation")
    if checklist["promo_before_product_explanation"]:
        score -= 2  # this is the one BIZ-001 forbids outright, not just a missing point
    checklist["visitor_experience_score_of_8"] = max(0, score)
    return checklist


def fetch_readme(org: str, repo: str) -> str | None:
    code, data, _ = gh_api(f"repos/{org}/{repo}/readme")
    if code != 0 or not isinstance(data, dict) or "content" not in data:
        return None
    try:
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        return None


def survey_one(entry: dict) -> dict:
    org, repo = org_repo(entry)
    key = f"{org}__{repo}"
    result: dict = {
        "family": entry["family"],
        "platform": entry["platform"],
        "registry_mode": entry["mode"],
        "org_repo": f"{org}/{repo}",
        "errors": [],
    }

    code, core, err = gh_api(f"repos/{org}/{repo}")
    if code != 0:
        result["errors"].append(f"repo: {err}")
        (OUT / f"{key}--repo.json").write_text(json.dumps({"error": err}), encoding="utf-8")
        return result
    (OUT / f"{key}--repo.json").write_text(json.dumps(core, indent=2), encoding="utf-8")
    result["description"] = core.get("description")
    result["homepage"] = core.get("homepage")
    result["topics"] = core.get("topics", [])
    result["default_branch"] = core.get("default_branch")
    result["pushed_at"] = core.get("pushed_at")
    result["stars"] = core.get("stargazers_count")
    result["license_api"] = (core.get("license") or {}).get("spdx_id")
    result["archived"] = core.get("archived")
    result["disabled_on_github"] = core.get("disabled")

    code, prof, err = gh_api(f"repos/{org}/{repo}/community/profile")
    if code == 0 and isinstance(prof, dict):
        (OUT / f"{key}--community_profile.json").write_text(
            json.dumps(prof, indent=2), encoding="utf-8"
        )
        files = prof.get("files", {})
        result["health_percentage"] = prof.get("health_percentage")
        result["license_recognized"] = bool(files.get("license"))
        result["has_contributing"] = bool(files.get("contributing"))
        result["has_code_of_conduct"] = bool(files.get("code_of_conduct"))
    else:
        result["errors"].append(f"community_profile: {err}")

    code, langs, err = gh_api(f"repos/{org}/{repo}/languages")
    if code == 0:
        (OUT / f"{key}--languages.json").write_text(json.dumps(langs, indent=2), encoding="utf-8")
        result["languages"] = langs
    else:
        result["errors"].append(f"languages: {err}")

    code, rels, err = gh_api(f"repos/{org}/{repo}/releases?per_page=5")
    if code == 0 and isinstance(rels, list):
        (OUT / f"{key}--releases.json").write_text(json.dumps(rels, indent=2), encoding="utf-8")
        result["release_count_sampled"] = len(rels)
        result["latest_release_tag"] = rels[0]["tag_name"] if rels else None
    else:
        result["errors"].append(f"releases: {err}")

    readme = fetch_readme(org, repo)
    if readme is None:
        result["errors"].append("readme: not fetched")
        result["has_readme"] = False
    else:
        (OUT / f"{key}--README.md").write_text(readme, encoding="utf-8")
        result["has_readme"] = True
        result["readme_length_chars"] = len(readme)
        gaps = detect_gaps(readme, detected_license=result.get("license_api"))
        result["gap_report"] = {
            "license_mentioned": gaps.license_mentioned,
            "products_org_link": gaps.products_org_link,
            "products_com_link": gaps.products_com_link,
            "relationship_explained": gaps.relationship_explained,
            "fully_compliant": gaps.fully_compliant,
            "gaps": gaps.gaps,
        }
        result["has_images"] = "![" in readme or "<img" in readme
        result["visitor_experience"] = visitor_experience(readme, entry["platform"])

    plat = entry["platform"]
    result["ecosystem_needed"] = ECOSYSTEM_BY_PLATFORM.get(plat, "unknown")
    result["ecosystem_parser_exists"] = entry.get("ecosystem") == "maven"  # only maven shipped
    result["manifest_file_expected"] = MANIFEST_FILE_BY_PLATFORM.get(plat, "?")

    return result


def main() -> int:
    results = []
    for entry in REGISTRY:
        r = survey_one(entry)
        results.append(r)
        gaps = r.get("gap_report", {}).get("gaps") if r.get("has_readme") else "NO_README"
        vscore = r.get("visitor_experience", {}).get("visitor_experience_score_of_8")
        promo_first = r.get("visitor_experience", {}).get("promo_before_product_explanation")
        print(
            f"{r['org_repo']:55s} plat={r['platform']:11s} mode={r['registry_mode']:9s} "
            f"visitor_score={vscore}/8 promo_before_explain={promo_first!s:5s} "
            f"promo_gaps={gaps} errors={r['errors'] or 'none'}"
        )

    (OUT / "portfolio-survey-summary.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(f"\nsurveyed {len(results)} repos -> {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
