#!/usr/bin/env python3
"""Read-only metric collector for the bundled canonical Aspose README candidates."""

from __future__ import annotations

import hashlib
import json
import re
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/workspace/scratch/22cd18c3f75c")
BUNDLE = ROOT / "work/readme-refresh-complete-bundle-20260819-174412"
FILES = BUNDLE / "files"
TREE = FILES / "reports/repo-presenter-regen-full"
OUT = ROOT / "work/owner_audit/aspose_candidate_rubric/CANDIDATE_METRICS.json"
AUDIT = FILES / "reports/_scratch/mt056_audit_portfolio_FINAL.json"
AS_OF = datetime(2026, 8, 19, 23, 59, 59, tzinfo=UTC)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def section_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def markdown_metrics(path: Path) -> dict:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    headings = []
    in_fence = False
    fence_langs = []
    fence_count = 0
    code_lines = 0
    for line in lines:
        if re.match(r"^\s*```", line):
            if not in_fence:
                fence_count += 1
                m = re.match(r"^\s*```\s*([^\s`]*)", line)
                fence_langs.append((m.group(1).lower() if m else "") or "plain")
            in_fence = not in_fence
            continue
        if in_fence:
            code_lines += 1
        else:
            m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
            if m:
                headings.append({"level": len(m.group(1)), "title": m.group(2)})
    h2 = [h["title"] for h in headings if h["level"] == 2]
    h2keys = [section_key(x) for x in h2]
    preamble = text.split("\n## ", 1)[0]
    links = re.findall(r"(?<!!)\[[^\]]*\]\(([^)\s]+)", text)
    urls = re.findall(r"https?://[^\s)>\"]+", text)
    images = len(re.findall(r"!\[[^\]]*\]\([^)]+\)", text)) + len(re.findall(r"<img\b", text, re.I))
    tables = sum(1 for line in lines if re.match(r"^\s*\|.*\|\s*$", line))
    table_separators = sum(1 for line in lines if re.match(r"^\s*\|(?:\s*:?-+:?\s*\|)+\s*$", line))
    list_items = sum(1 for line in lines if re.match(r"^\s*(?:[-*+] |\d+\. )", line))
    return {
        "sha256": sha256(raw),
        "bytes": len(raw),
        "lines": len(lines),
        "words": len(re.findall(r"\b[\w.+#/-]+\b", text)),
        "heading_count": len(headings),
        "h2_count": len(h2),
        "h2_headings": h2,
        "fenced_code_blocks": fence_count,
        "executable_or_command_code_blocks": fence_count
        - sum(1 for x in fence_langs if x == "mermaid"),
        "fence_languages": dict(Counter(fence_langs)),
        "code_lines": code_lines,
        "mermaid_blocks": sum(1 for x in fence_langs if x == "mermaid"),
        "image_count": images,
        "preamble_badge_image_count": max(
            0,
            len(re.findall(r"!\[[^\]]*\]\([^)]+\)", preamble))
            - preamble.lower().count("banner-readme"),
        ),
        "markdown_link_count": len(links),
        "http_url_count": len(urls),
        "aspose_com_url_count": sum(1 for x in urls if "aspose.com" in x.lower()),
        "badge_like_count": len(
            re.findall(r"shields\.io|badge|actions/workflows|license-", text, re.I)
        ),
        "table_row_lines": tables,
        "table_count_estimate": table_separators,
        "list_item_count": list_items,
        "section_presence": {
            "navigation": any(x == "navigation" for x in h2keys),
            "at_a_glance": any(x == "at a glance" for x in h2keys),
            "key_capabilities": any("capabilit" in x or "feature" in x for x in h2keys),
            "dependencies": any("dependenc" in x or "requirement" in x for x in h2keys),
            "installation": any("install" in x or "getting started" in x for x in h2keys),
            "quick_start": any("quick start" in x or "usage" == x for x in h2keys),
            "additional_examples": any("example" in x or "workflow" in x for x in h2keys),
            "api_reference": any("api" in x for x in h2keys),
            "limitations": any("limitation" in x or "scope" in x or "status" in x for x in h2keys),
            "development_and_testing": any("development" in x or "testing" in x for x in h2keys),
            "license": any("license" in x for x in h2keys),
            "resources": any("resource" in x or "documentation" in x for x in h2keys),
        },
    }


def disposition_metrics(product_dir: Path) -> dict:
    out = {}
    for name in ("content", "structure", "code-example", "badge"):
        path = product_dir / f"{name}-dispositions.json"
        if not path.exists():
            out[name] = {"present": False, "entries": 0}
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        dispositions = Counter()
        verification = Counter()
        missing_target = 0
        missing_reason_for_exclusion = 0
        for item in data:
            disposition = item.get("disposition") or item.get("action") or "missing"
            dispositions[disposition] += 1
            verification[(item.get("verification") or {}).get("status", "missing")] += 1
            if disposition in {"merged_verbatim", "merged_reframed", "preserved", "replaced"}:
                if name != "badge" and not item.get("target_section"):
                    missing_target += 1
            if disposition in {"excluded", "removed"} and not item.get("excluded_reason"):
                missing_reason_for_exclusion += 1
        out[name] = {
            "present": True,
            "entries": len(data),
            "dispositions": dict(dispositions),
            "verification_statuses": dict(verification),
            "missing_target_for_kept": missing_target,
            "missing_reason_for_exclusion": missing_reason_for_exclusion,
        }
    return out


products = json.loads((FILES / "data/products.json").read_text(encoding="utf-8"))
exclusions = json.loads((FILES / "data/registry_exclusions.json").read_text(encoding="utf-8"))
pins = json.loads((FILES / "CLONE-CACHE-PINS.json").read_text(encoding="utf-8"))
audit = json.loads(AUDIT.read_text(encoding="utf-8"))
audit_by = {(x["family"], x["platform"]): x for x in audit["products"]}
pin_by = {(x["family"], x["platform"]): x for x in pins}


def exclusion_reason(product: dict) -> str | None:
    for ex in exclusions:
        if ex.get("match") == "family_platform" and (ex.get("family"), ex.get("platform")) == (
            product["family"],
            product["platform"],
        ):
            return ex["reason"]
        if ex.get("match") == "repo_name" and ex.get("value") == product.get("repo_name"):
            return ex["reason"]
    return None


records = []
for product in products:
    family, platform = product["family"], product["platform"]
    pdir = TREE / family / platform
    readme = pdir / "readme.md"
    if not readme.exists():
        continue
    metrics = markdown_metrics(readme)
    ex_reason = exclusion_reason(product)
    pin = pin_by.get((family, platform))
    published = None
    if pin:
        pub_path = FILES / "runs/.clone_cache" / pin["repo_dir"] / "README.md"
        if pub_path.exists():
            published = markdown_metrics(pub_path)
            published = {
                "sha256": published["sha256"],
                "bytes": published["bytes"],
                "words": published["words"],
                "same_bytes_as_candidate": published["sha256"] == metrics["sha256"],
                "pipeline_strip_equal_to_candidate": pub_path.read_text(encoding="utf-8").strip()
                == readme.read_text(encoding="utf-8").strip(),
                "pinned_repo_head": pin.get("pinned_head_sha"),
                "model_repo_sha": pin.get("model_yaml_repo_sha"),
                "repo_sha_match": pin.get("sha_match"),
            }
    last = pdir / "last-verified.json"
    verified = None
    if last.exists():
        v = json.loads(last.read_text(encoding="utf-8"))
        dt = datetime.fromisoformat(v["verified_at"].replace("Z", "+00:00"))
        verified = {
            **v,
            "marker_matches_candidate": v.get("readme_sha256") == metrics["sha256"],
            "age_hours_at_bundle_day_end": round((AS_OF - dt).total_seconds() / 3600, 2),
        }
    au = audit_by.get((family, platform))
    records.append(
        {
            "family": family,
            "platform": platform,
            "repo_name": product.get("repo_name"),
            "registry_active": bool(product.get("active")),
            "excluded": ex_reason is not None,
            "eligible_active": bool(product.get("active")) and ex_reason is None,
            "exclusion_reason": ex_reason,
            "candidate": metrics,
            "published_snapshot": published,
            "last_verified": verified,
            "disposition_ledgers": disposition_metrics(pdir),
            "portfolio_audit": (
                {
                    "clean": au["clean"],
                    "published": au["published"],
                    "hard_gate_findings": au["hard_gate_findings"],
                    "hard_gate_finding_count": sum(au["hard_gate_findings"].values()),
                }
                if au
                else None
            ),
        }
    )


def describe(values: list[int | float]) -> dict:
    s = sorted(values)
    if not s:
        return {}
    q = statistics.quantiles(s, n=4, method="inclusive") if len(s) > 1 else [s[0]] * 3
    return {
        "min": s[0],
        "p25": round(q[0], 2),
        "median": round(statistics.median(s), 2),
        "p75": round(q[2], 2),
        "max": s[-1],
        "mean": round(statistics.mean(s), 2),
    }


eligible = [r for r in records if r["eligible_active"]]
summary = {}
for field in (
    "bytes",
    "lines",
    "words",
    "h2_count",
    "fenced_code_blocks",
    "executable_or_command_code_blocks",
    "code_lines",
    "mermaid_blocks",
    "image_count",
    "preamble_badge_image_count",
    "markdown_link_count",
    "table_count_estimate",
    "table_row_lines",
    "list_item_count",
):
    summary[field] = describe([r["candidate"][field] for r in eligible])

section_frequency = {
    k: sum(1 for r in eligible if r["candidate"]["section_presence"][k])
    for k in next(iter(eligible))["candidate"]["section_presence"]
}
ledger_frequency = {
    k: sum(1 for r in eligible if r["disposition_ledgers"][k]["present"])
    for k in ("content", "structure", "code-example", "badge")
}

ledger_aggregate = {}
for kind in ("content", "structure", "code-example", "badge"):
    rows = [r["disposition_ledgers"][kind] for r in eligible]
    dispositions: Counter[str] = Counter()
    verification_statuses: Counter[str] = Counter()
    for row in rows:
        dispositions.update(row.get("dispositions", {}))
        verification_statuses.update(row.get("verification_statuses", {}))
    ledger_aggregate[kind] = {
        "present": sum(1 for row in rows if row["present"]),
        "entries": sum(row["entries"] for row in rows),
        "dispositions": dict(dispositions),
        "verification_statuses": dict(verification_statuses),
        "missing_target_for_kept": sum(row.get("missing_target_for_kept", 0) for row in rows),
        "missing_reason_for_exclusion": sum(
            row.get("missing_reason_for_exclusion", 0) for row in rows
        ),
    }

hard_finding_totals: Counter[str] = Counter()
for r in eligible:
    hard_finding_totals.update((r["portfolio_audit"] or {}).get("hard_gate_findings", {}))

grouped = defaultdict(list)
for r in eligible:
    grouped[r["platform"]].append(r)
by_platform = {}
for platform, rows in sorted(grouped.items()):
    by_platform[platform] = {
        "count": len(rows),
        "words": describe([x["candidate"]["words"] for x in rows]),
        "fenced_code_blocks": describe([x["candidate"]["fenced_code_blocks"] for x in rows]),
        "api_reference_present": sum(
            1 for x in rows if x["candidate"]["section_presence"]["api_reference"]
        ),
        "dependencies_present": sum(
            1 for x in rows if x["candidate"]["section_presence"]["dependencies"]
        ),
        "limitations_present": sum(
            1 for x in rows if x["candidate"]["section_presence"]["limitations"]
        ),
    }

grouped_family = defaultdict(list)
for r in eligible:
    grouped_family[r["family"]].append(r)
by_family = {}
for family, rows in sorted(grouped_family.items()):
    by_family[family] = {
        "count": len(rows),
        "words": describe([x["candidate"]["words"] for x in rows]),
        "executable_or_command_code_blocks": describe(
            [x["candidate"]["executable_or_command_code_blocks"] for x in rows]
        ),
        "audit_clean": sum(
            1 for x in rows if x["portfolio_audit"] and x["portfolio_audit"]["clean"]
        ),
        "audit_dirty": sum(
            1 for x in rows if x["portfolio_audit"] and not x["portfolio_audit"]["clean"]
        ),
    }

payload = {
    "schema_version": 1,
    "scope": {
        "source_bundle": "readme-refresh-complete-bundle-20260819-174412.zip",
        "source_bundle_sha256": "2d8eb6ae810d920b98136f3fa587b46d36b2e0c6b5250df109fa98c73e470465",
        "canonical_tree": "repo-presenter-regen-full",
        "canonical_candidate_count": len(records),
        "registry_active_true_count": sum(1 for r in records if r["registry_active"]),
        "eligible_active_count": len(eligible),
        "excluded_canonical_candidates": [
            f"{r['family']}/{r['platform']}" for r in records if r["excluded"]
        ],
        "portfolio_audit_artifact": str(AUDIT.relative_to(BUNDLE)),
        "portfolio_audit_clean": audit["clean_count"],
        "portfolio_audit_dirty": audit["dirty_count"],
        "portfolio_audit_total": audit["total"],
        "optimizer_tip_context_only": "56a5f09c80f57581d977d77142ed8809ed1ede9d",
        "as_of": "2026-08-19",
    },
    "eligible_portfolio_summary": {
        "metric_distributions": summary,
        "section_frequency_out_of_30": section_frequency,
        "ledger_presence_out_of_30": ledger_frequency,
        "ledger_aggregate": ledger_aggregate,
        "hard_gate_finding_totals": dict(hard_finding_totals.most_common()),
        "clean_candidates": sum(
            1 for r in eligible if r["portfolio_audit"] and r["portfolio_audit"]["clean"]
        ),
        "dirty_candidates": sum(
            1 for r in eligible if r["portfolio_audit"] and not r["portfolio_audit"]["clean"]
        ),
        "candidate_byte_matches_pinned_published_snapshot": sum(
            1
            for r in eligible
            if r["published_snapshot"] and r["published_snapshot"]["same_bytes_as_candidate"]
        ),
        "candidate_pipeline_strip_matches_pinned_published_snapshot": sum(
            1
            for r in eligible
            if r["published_snapshot"]
            and r["published_snapshot"]["pipeline_strip_equal_to_candidate"]
        ),
        "last_verified_marker_present": sum(1 for r in eligible if r["last_verified"]),
        "last_verified_marker_matches_candidate": sum(
            1
            for r in eligible
            if r["last_verified"] and r["last_verified"]["marker_matches_candidate"]
        ),
        "marker_mismatch_products": [
            f"{r['family']}/{r['platform']}"
            for r in eligible
            if r["last_verified"] and not r["last_verified"]["marker_matches_candidate"]
        ],
        "audit_clean_products": [
            f"{r['family']}/{r['platform']}"
            for r in eligible
            if r["portfolio_audit"] and r["portfolio_audit"]["clean"]
        ],
        "audit_dirty_products": [
            f"{r['family']}/{r['platform']}"
            for r in eligible
            if r["portfolio_audit"] and not r["portfolio_audit"]["clean"]
        ],
    },
    "by_platform": by_platform,
    "by_family": by_family,
    "candidates": records,
}

OUT.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
