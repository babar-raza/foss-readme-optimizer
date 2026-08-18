"""Three-way README parity comparison: original vs aspose.org candidate vs ours.

Phase-5/6 machinery of the 2026-08-18 mission recovery: a deterministic,
read-only oracle that compares, for one repository, the three documents the
quality bar is defined by:

1. the ORIGINAL target-repository README (`runs/baseline/<org>__<repo>/README.md`),
2. the aspose.org reference candidate
   (`<aspose-root>/reports/repo-presenter-regen-full/<family>/<platform>/readme.md`),
3. OUR candidate (newest `runs/readme-poc/<org>__<repo>/<rev>/candidate/README.md`,
   falling back to `diagnostics/blocked-candidate.md` for blocked members).

It measures structure and preservation, not prose taste: H2 section
inventories, code-fence and inline-code coverage, Mermaid presence, link
counts by domain, word counts, Key-Capabilities bullet counts — and the
cross checks that keep recurring in Decision #104 reviews: original
inline-code terminology missing from each candidate, and aspose.org H2
sections absent from ours. Judgment stays with the reviewing human/agent;
this makes the inputs to that judgment cheap, uniform, and diffable.

Usage:
    .venv/Scripts/python plans/investigations/tools/compare_candidate_parity.py \
        --repo aspose-cells-foss/Aspose.Cells-FOSS-for-Python \
        [--aspose-root D:/onedrive/Documents/GitHub/aspose.org] [--json-out PATH]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
_FENCE_RE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$", re.M)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_LINK_RE = re.compile(r"\]\((https?://[^)\s]+)\)")


def _registry_entry(org_repo: str) -> dict:
    registry = json.loads((REPO_ROOT / "data" / "products.json").read_text(encoding="utf-8"))
    rows = (
        registry["products"] if isinstance(registry, dict) and "products" in registry else registry
    )
    org = org_repo.split("/", maxsplit=1)[0]
    repo_name = org_repo.split("/", maxsplit=1)[1]
    for row in rows:
        if row.get("org_repo") == org_repo or (
            row.get("repo_name") == repo_name and org in str(row.get("repo_url", ""))
        ):
            return row
    raise SystemExit(f"error: {org_repo!r} not found in data/products.json")


def _our_candidate_path(org_repo: str) -> Path | None:
    org, repo = org_repo.split("/", maxsplit=1)
    root = REPO_ROOT / "runs" / "readme-poc" / f"{org}__{repo}"
    candidates = sorted(
        root.glob("*/candidate/README.md"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if candidates:
        return candidates[0]
    blocked = root / "diagnostics" / "blocked-candidate.md"
    return blocked if blocked.is_file() else None


def _document_profile(text: str) -> dict:
    sections = _H2_RE.findall(text)
    fences = _FENCE_RE.findall(text)
    inline = {span.strip() for span in _INLINE_CODE_RE.findall(text) if span.strip()}
    links = _LINK_RE.findall(text)
    domains: dict[str, int] = {}
    for url in links:
        domain = url.split("//", 1)[1].split("/", 1)[0]
        domains[domain] = domains.get(domain, 0) + 1
    capability_bullets = 0
    in_capabilities = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_capabilities = "capabilit" in line.lower()
        elif in_capabilities and line.lstrip().startswith(("- ", "* ")):
            capability_bullets += 1
    return {
        "words": len(text.split()),
        "h2_sections": sections,
        "code_fences": len([f for f in fences]),
        "fence_languages": sorted({f for f in fences if f}),
        "has_mermaid": "```mermaid" in text,
        "inline_code_spans": sorted(inline),
        "inline_code_count": len(inline),
        "link_count": len(links),
        "links_by_domain": dict(sorted(domains.items())),
        "key_capability_bullets": capability_bullets,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="org/repo from data/products.json")
    parser.add_argument("--aspose-root", default="D:/onedrive/Documents/GitHub/aspose.org")
    parser.add_argument("--json-out", default=None)
    args = parser.parse_args()

    entry = _registry_entry(args.repo)
    family = entry.get("family")
    platform = entry.get("platform")
    org, repo = args.repo.split("/", maxsplit=1)

    original_path = REPO_ROOT / "runs" / "baseline" / f"{org}__{repo}" / "README.md"
    aspose_path = (
        Path(args.aspose_root)
        / "reports"
        / "repo-presenter-regen-full"
        / str(family)
        / str(platform)
        / "readme.md"
    )
    ours_path = _our_candidate_path(args.repo)

    documents = {}
    for label, path in (
        ("original", original_path),
        ("aspose_org", aspose_path),
        ("ours", ours_path),
    ):
        if path is None or not path.is_file():
            documents[label] = {"path": str(path), "missing": True}
            continue
        profile = _document_profile(path.read_text(encoding="utf-8", errors="replace"))
        profile["path"] = str(path)
        documents[label] = profile

    report: dict = {
        "repo": args.repo,
        "family": family,
        "platform": platform,
        "documents": documents,
    }

    if not documents["original"].get("missing"):
        original_spans = set(documents["original"]["inline_code_spans"])
        for label in ("aspose_org", "ours"):
            if documents[label].get("missing"):
                continue
            kept = original_spans & set(documents[label]["inline_code_spans"])
            report[f"original_terminology_missing_from_{label}"] = sorted(
                original_spans - set(documents[label]["inline_code_spans"])
            )
            report[f"original_terminology_kept_in_{label}"] = f"{len(kept)}/{len(original_spans)}"
    if not documents["aspose_org"].get("missing") and not documents["ours"].get("missing"):
        report["aspose_sections_absent_from_ours"] = [
            section
            for section in documents["aspose_org"]["h2_sections"]
            if section not in documents["ours"]["h2_sections"]
        ]
        report["our_sections_absent_from_aspose"] = [
            section
            for section in documents["ours"]["h2_sections"]
            if section not in documents["aspose_org"]["h2_sections"]
        ]

    compact = {
        label: {
            key: value
            for key, value in profile.items()
            if key not in {"inline_code_spans", "h2_sections"}
        }
        for label, profile in documents.items()
    }
    print(json.dumps({**report, "documents": compact}, indent=1)[:4000])
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8", newline="\n")
        print(f"full report -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
