#!/usr/bin/env python3
"""Build/refresh ``data/aspose_com_links.json`` — the aspose.com link database.

Adapted from aspose.org's ``scripts/pipeline/commands/ops/fetch_aspose_com_targets.py``
(recorded in plans/master.md, "Patterns adapted from aspose.org"). Trimmed to the only
two URL depths this project links to:

- family:   https://products.aspose.com/words/
- platform: https://products.aspose.com/words/python-net/

for the four content surfaces (products, docs, reference, kb), plus blog.aspose.com
category roots (https://blog.aspose.com/words/) extracted from blog post URL paths,
since the blog has no family/platform landing pages.

Two population modes:

    # Bootstrap/refresh offline from an aspose.org checkout's full 20 MB target map
    python scripts/fetch_aspose_com_links.py --from-source <path>/data/aspose_com_targets.json

    # Refresh live from aspose.com sitemaps + HTTP verification (no aspose.org needed)
    python scripts/fetch_aspose_com_links.py

Governance guard kept from the source script: with --skip-http-verify, unverified URLs
are stored with http_status -1 (never 200), so consumers that require 200 reject them.

Exit codes: 0 success; 1 fatal (no data produced); 2 partial (written with warnings).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import threading
import urllib.parse
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree

try:
    import requests
    from requests.exceptions import RequestException
except ImportError:
    print("ERROR: 'requests' package required (it is a project dependency).", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "data" / "aspose_com_links.json"

SCRIPT_VERSION = "1.0.0"
GENERATOR_NAME = "fetch_aspose_com_links.py"
USER_AGENT = "foss-readme-optimizer-linkdb/1.0"

# The four two-level content surfaces. docs.aspose.com has no useful product-level
# sitemap (same finding as the source script), so it is covered by grid synthesis only.
SURFACE_SITEMAPS: dict[str, str | None] = {
    "products.aspose.com": "https://products.aspose.com/sitemap.xml",
    "docs.aspose.com": None,
    "reference.aspose.com": "https://reference.aspose.com/sitemap.xml",
    "kb.aspose.com": "https://kb.aspose.com/sitemap.xml",
}
BLOG_SUBDOMAIN = "blog.aspose.com"
BLOG_SITEMAP = "https://blog.aspose.com/sitemap.xml"

KNOWN_FAMILIES = {
    "3d",
    "barcode",
    "cad",
    "cells",
    "diagram",
    "drawing",
    "email",
    "finance",
    "font",
    "gis",
    "html",
    "imaging",
    "medical",
    "note",
    "ocr",
    "omr",
    "page",
    "pdf",
    "psd",
    "pub",
    "slides",
    "svg",
    "tasks",
    "tex",
    "words",
    "zip",
}

# Blog categories are family slugs plus "total" (Aspose.Total has posts but no library).
BLOG_EXTRA_CATEGORIES = {"total"}

# Second path segments accepted as a platform step when classifying sitemap URLs.
# Variant segments (python-net, go-cpp, ...) are kept as-is: the key must mirror the
# real URL path, not a canonicalized token.
RECOGNIZED_PLATFORM_SEGMENTS = {
    "net",
    "dotnet",
    "csharp",
    "net60",
    "net48",
    "net40",
    "python",
    "python-net",
    "python-java",
    "java",
    "java-android",
    "cpp",
    "c-plus-plus",
    "cplusplus",
    "nodejs",
    "node-js",
    "javascript",
    "typescript",
    "android",
    "cloud",
    "ruby",
    "ruby-net",
    "go",
    "golang",
    "go-cpp",
}

# Segments used to synthesize candidate URLs for surfaces without a usable sitemap.
# Only segments observed live on aspose.com surfaces — keeps the verify pass small.
SYNTH_PLATFORM_SEGMENTS = (
    "net",
    "java",
    "python",
    "python-net",
    "cpp",
    "go",
    "go-cpp",
    "nodejs",
    "typescript",
    "android",
    "cloud",
)

SKIP_PATTERNS = re.compile(
    r"/(?:search|feed|rss|sitemap|tag|category|author|page/\d+|wp-|admin|login)",
    re.IGNORECASE,
)

NON_EN_LOCALE_RE = re.compile(
    r"/(?:ar|bg|ca|cs|da|de|el|es|fa|fi|fr|he|hi|hr|hu|id|it|ja|ko|lt|lv|ms|nl|no"
    r"|pl|pt|ro|ru|sk|sr|sv|th|tr|uk|vi|zh(?:-hant)?)/"
)

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

UNVERIFIED = -1  # governance guard: never store 200 without live verification


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def path_segments(url: str) -> list[str]:
    return [p for p in urllib.parse.urlparse(url).path.strip("/").split("/") if p]


def normalize_url(url: str) -> str | None:
    """Normalize a sitemap URL; None means skip (non-https, localized, query, junk)."""
    url = url.strip().lower()
    if url.startswith("http://"):
        url = "https://" + url[7:]
    if not url.startswith("https://"):
        return None
    url = re.sub(r"(/en)/", "/", url)
    parsed = urllib.parse.urlparse(url)
    if parsed.query or parsed.fragment:
        return None
    if SKIP_PATTERNS.search(parsed.path):
        return None
    if parsed.path and not parsed.path.endswith("/"):
        url += "/"
    return url


def classify_two_level(url: str) -> tuple[str, str | None, str | None]:
    """Classify a normalized URL as ("family"|"platform"|"other", family, key).

    key is "<family>" or "<family>/<segment>" taken from the *actual* URL path —
    variant segments like python-net are preserved, never canonicalized.
    """
    parts = path_segments(url)
    if len(parts) == 1 and parts[0] in KNOWN_FAMILIES:
        return "family", parts[0], parts[0]
    if len(parts) == 2 and parts[0] in KNOWN_FAMILIES and parts[1] in RECOGNIZED_PLATFORM_SEGMENTS:
        return "platform", parts[0], f"{parts[0]}/{parts[1]}"
    return "other", None, None


# ── HTTP verification (HEAD → GET fallback, kept from the source script) ─────

_thread_local = threading.local()


def _session() -> requests.Session:
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = requests.Session()
        sess.headers.update({"User-Agent": USER_AGENT})
        _thread_local.session = sess
    return sess


def verify_url(url: str) -> int:
    """Return the final HTTP status for url (0 on network failure)."""
    sess = _session()
    try:
        resp = sess.head(url, allow_redirects=True, timeout=15)
        if resp.status_code not in (403, 405):
            return resp.status_code
    except RequestException:
        pass
    try:
        resp = sess.get(url, allow_redirects=True, timeout=20, stream=True)
        resp.close()
        return resp.status_code
    except RequestException:
        return 0


def verify_many(urls: list[str], skip: bool, max_workers: int = 8) -> dict[str, int]:
    if skip:
        return dict.fromkeys(urls, UNVERIFIED)
    results: dict[str, int] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        for url, status in zip(urls, pool.map(verify_url, urls), strict=True):
            results[url] = status
    return results


# ── Sitemap fetching (recursive, English locale only) ────────────────────────


def fetch_sitemap_urls(sitemap_url: str, depth: int = 0) -> tuple[list[str], int]:
    """Return (urls, http_status). Handles <sitemapindex> and <urlset>."""
    if depth > 2:
        return [], 0
    try:
        resp = _session().get(sitemap_url, timeout=30)
        if resp.status_code != 200:
            return [], resp.status_code
        raw_xml = resp.text
    except RequestException as exc:
        print(f"  WARN: could not fetch {sitemap_url}: {exc}", file=sys.stderr)
        return [], 0

    try:
        root = ElementTree.fromstring(raw_xml)
    except ElementTree.ParseError as exc:
        print(f"  WARN: XML parse error for {sitemap_url}: {exc}", file=sys.stderr)
        return [], 200

    def findall(parent: ElementTree.Element, tag: str) -> list[ElementTree.Element]:
        return parent.findall("sm:" + tag, SITEMAP_NS) or parent.findall(tag)

    def loc_text(elem: ElementTree.Element) -> str | None:
        child = elem.find("sm:loc", SITEMAP_NS)
        if child is None:
            child = elem.find("loc")
        return child.text.strip() if child is not None and child.text else None

    if root.tag.endswith("sitemapindex"):
        urls: list[str] = []
        for sm_elem in findall(root, "sitemap"):
            child_url = loc_text(sm_elem)
            if child_url and not NON_EN_LOCALE_RE.search(child_url):
                child_urls, _ = fetch_sitemap_urls(child_url, depth + 1)
                urls.extend(child_urls)
        return urls, 200

    return [loc for elem in findall(root, "url") if (loc := loc_text(elem))], 200


# ── Blog category extraction ─────────────────────────────────────────────────


def extract_blog_categories(blog_urls: list[str]) -> dict[str, int]:
    """Map category slug -> post count from blog post URLs (/<category>/<slug>/)."""
    allowed = KNOWN_FAMILIES | BLOG_EXTRA_CATEGORIES
    counts: dict[str, int] = {}
    for url in blog_urls:
        parts = path_segments(url)
        if len(parts) >= 2 and parts[0] in allowed:
            counts[parts[0]] = counts.get(parts[0], 0) + 1
    return counts


def build_blog_section(category_counts: dict[str, int], skip_verify: bool) -> dict:
    # Post URLs live at /<category>/<slug>/, but /<category>/ is only a redirect
    # alias that exists for some categories. The canonical category page (verified
    # live for all categories, and matching aspose.org's blog taxonomy scheme in
    # data/blog_family_routes.yaml) is /categories/aspose.<category>-product-family/.
    urls = {
        cat: f"https://{BLOG_SUBDOMAIN}/categories/aspose.{cat}-product-family/"
        for cat in sorted(category_counts)
    }
    statuses = verify_many(list(urls.values()), skip=skip_verify)
    categories = {}
    for cat, url in urls.items():
        status = statuses[url]
        if status in (404, 0):
            continue
        categories[cat] = {
            "url": url,
            "http_status": status,
            "post_count": category_counts[cat],
        }
    return {"subdomain": BLOG_SUBDOMAIN, "categories": categories}


# ── Mode: --from-source (offline trim of aspose.org's full target map) ───────


def build_from_source(source_path: Path, skip_verify: bool) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    with source_path.open(encoding="utf-8") as fh:
        source = json.load(fh)

    surfaces: dict[str, dict] = {}
    for subdomain in SURFACE_SITEMAPS:
        src = source.get("targets", {}).get(subdomain, {})
        families: dict[str, dict] = {}
        platforms: dict[str, dict] = {}
        for bucket, out in (("families", families), ("platforms", platforms)):
            for entry in src.get(bucket, {}).values():
                if entry.get("http_status") != 200:
                    continue
                # Re-key from the real URL path: the source canonicalizes keys
                # (words/python for a .../words/python-net/ URL); we keep real paths.
                kind, _, key = classify_two_level(entry["url"])
                expected = "family" if bucket == "families" else "platform"
                if kind != expected or key is None:
                    warnings.append(f"skipped unclassifiable {subdomain} entry: {entry['url']}")
                    continue
                out[key] = {"url": entry["url"], "http_status": 200}
        surfaces[subdomain] = {
            "families": dict(sorted(families.items())),
            "platforms": dict(sorted(platforms.items())),
        }

    blog_urls = [
        url
        for url, info in source.get("all_urls", {}).items()
        if BLOG_SUBDOMAIN in url and info.get("http_status") == 200
    ]
    blog = build_blog_section(extract_blog_categories(blog_urls), skip_verify)

    src_prov = source.get("provenance", {})
    provenance = {
        "mode": "from-source",
        "sources": [
            {
                "type": "source-db",
                "path": str(source_path),
                "source_generated_at": src_prov.get("generated_at"),
                "source_output_hash": src_prov.get("output_hash"),
                "source_patched_at": src_prov.get("patched_at"),
            }
        ],
    }
    return assemble_output(surfaces, blog, provenance), warnings


# ── Mode: live (sitemaps + grid synthesis + HTTP verification) ───────────────


def build_live(skip_verify: bool, families_filter: set[str] | None) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    sources: list[dict] = []
    surfaces: dict[str, dict] = {}

    fam_list = sorted(families_filter or KNOWN_FAMILIES)

    for subdomain, sitemap_url in SURFACE_SITEMAPS.items():
        candidates: dict[str, tuple[str, str]] = {}  # url -> (kind, key)

        if sitemap_url is not None:
            print(f"Fetching {sitemap_url} ...", file=sys.stderr)
            raw_urls, status = fetch_sitemap_urls(sitemap_url)
            sources.append(
                {
                    "type": "sitemap",
                    "sitemap_url": sitemap_url,
                    "fetched_at": utc_now_iso(),
                    "http_status": status,
                    "entry_count": len(raw_urls),
                }
            )
            if status != 200:
                warnings.append(f"sitemap unavailable ({status}): {sitemap_url}")
            for raw in raw_urls:
                norm = normalize_url(raw)
                if norm is None or subdomain not in norm:
                    continue
                kind, family, key = classify_two_level(norm)
                if kind == "other" or (families_filter and family not in families_filter):
                    continue
                assert key is not None
                candidates[norm] = (kind, key)

        # Grid synthesis: covers docs (no sitemap) and variant platform URLs the
        # sitemaps omit (the source repo patched words/python-net etc. in by hand).
        for family in fam_list:
            candidates.setdefault(f"https://{subdomain}/{family}/", ("family", family))
            for seg in SYNTH_PLATFORM_SEGMENTS:
                url = f"https://{subdomain}/{family}/{seg}/"
                candidates.setdefault(url, ("platform", f"{family}/{seg}"))

        print(f"{subdomain}: verifying {len(candidates)} candidate URLs ...", file=sys.stderr)
        statuses = verify_many(list(candidates), skip=skip_verify)

        families: dict[str, dict] = {}
        platforms: dict[str, dict] = {}
        for url, (kind, key) in candidates.items():
            status = statuses[url]
            if status in (404, 0):
                continue
            bucket = families if kind == "family" else platforms
            bucket[key] = {"url": url, "http_status": status}
        surfaces[subdomain] = {
            "families": dict(sorted(families.items())),
            "platforms": dict(sorted(platforms.items())),
        }

    print(f"Fetching {BLOG_SITEMAP} ...", file=sys.stderr)
    blog_raw, blog_status = fetch_sitemap_urls(BLOG_SITEMAP)
    sources.append(
        {
            "type": "sitemap",
            "sitemap_url": BLOG_SITEMAP,
            "fetched_at": utc_now_iso(),
            "http_status": blog_status,
            "entry_count": len(blog_raw),
        }
    )
    if blog_status != 200:
        warnings.append(f"sitemap unavailable ({blog_status}): {BLOG_SITEMAP}")
    blog_norm = [n for n in (normalize_url(u) for u in blog_raw) if n]
    blog = build_blog_section(extract_blog_categories(blog_norm), skip_verify)

    provenance = {"mode": "live", "sources": sources}
    return assemble_output(surfaces, blog, provenance), warnings


# ── Output assembly / writing ────────────────────────────────────────────────


def assemble_output(surfaces: dict, blog: dict, provenance: dict) -> dict:
    total = sum(len(s["families"]) + len(s["platforms"]) for s in surfaces.values()) + len(
        blog["categories"]
    )
    output = {
        "schema_version": "1.0",
        "provenance": {
            "generated_at": utc_now_iso(),
            "generator": GENERATOR_NAME,
            "generator_version": SCRIPT_VERSION,
            **provenance,
            "total_links": total,
            "output_hash": "",
        },
        "surfaces": surfaces,
        "blog": blog,
    }
    output["provenance"]["output_hash"] = (
        f"sha256:{sha256_of(json.dumps(output, sort_keys=True, ensure_ascii=False))}"
    )
    return output


def write_output(output: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--from-source",
        type=Path,
        metavar="PATH",
        help="Trim an aspose.org data/aspose_com_targets.json instead of fetching live.",
    )
    parser.add_argument(
        "--skip-http-verify",
        action="store_true",
        help=f"Skip HTTP verification; unverified URLs get http_status {UNVERIFIED}, never 200.",
    )
    parser.add_argument(
        "--families",
        nargs="*",
        metavar="FAMILY",
        help="Live mode only: restrict to specific families (e.g. words cells).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build but do not write the output file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="Override the output path.",
    )
    args = parser.parse_args(argv)

    if args.from_source:
        if not args.from_source.is_file():
            print(f"ERROR: source not found: {args.from_source}", file=sys.stderr)
            return 1
        output, warnings = build_from_source(args.from_source, args.skip_http_verify)
    else:
        families_filter = set(args.families) if args.families else None
        output, warnings = build_live(args.skip_http_verify, families_filter)

    for subdomain, data in output["surfaces"].items():
        print(
            f"  {subdomain}: families={len(data['families'])} platforms={len(data['platforms'])}",
            file=sys.stderr,
        )
    print(f"  blog categories: {len(output['blog']['categories'])}", file=sys.stderr)
    for warning in warnings:
        print(f"  ! {warning}", file=sys.stderr)

    if output["provenance"]["total_links"] == 0:
        print("ERROR: no links collected — nothing written.", file=sys.stderr)
        return 1

    if args.dry_run:
        print("DRY RUN — no file written.", file=sys.stderr)
        return 0 if not warnings else 2

    write_output(output, args.output)
    print(f"Written: {args.output}", file=sys.stderr)
    return 0 if not warnings else 2


if __name__ == "__main__":
    sys.exit(main())
