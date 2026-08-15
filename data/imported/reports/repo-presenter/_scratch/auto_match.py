"""Scratch helper: for each old-README content unit, find the best-matching section in the
candidate readme.md by salient-token overlap, to bucket units into high-confidence-redundant vs
needs-manual-review. This is a triage aid only -- every unit still gets read and a real
disposition written by hand; this just prioritizes attention.
"""

# Adapted from aspose.org: reports/repo-presenter/_scratch/auto_match.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "scripts/pipeline/commands/foss")
import readme_refresh_checks as checks

REPO_ROOT = Path(r"d:/onedrive/Documents/GitHub/aspose.org")


def analyze(family, platform):
    old_readme_path = REPO_ROOT / "runs" / ".clone_cache" / f"aspose_{family}_{platform}" / "README.md"
    readme_path = REPO_ROOT / "reports" / "repo-presenter" / family / platform / "readme.md"
    old_text = old_readme_path.read_text(encoding="utf-8", errors="ignore")
    new_text = readme_path.read_text(encoding="utf-8")

    units = checks.extract_old_readme_content_units(old_text)
    sections = checks._split_into_sections(new_text)

    sec_lower = {name: body.lower() for name, body in sections.items()}

    results = []
    for u in units:
        excerpt = u["excerpt"]
        tokens = u["salient_tokens"]
        excerpt_lower = excerpt.lower()
        words = [w.strip(".,():;`*-") for w in re.findall(r"[A-Za-z][A-Za-z0-9_./:]{3,}", excerpt)]
        words_lower = set(w.lower() for w in words if len(w) > 4)

        best_section = None
        best_score = 0.0
        best_hits = []
        for name, body_lower in sec_lower.items():
            if tokens:
                hits = [t for t in tokens if t.lower() in body_lower]
                score = len(hits) / max(1, len(tokens))
            else:
                hits = [w for w in words_lower if w in body_lower]
                score = len(hits) / max(1, len(words_lower))
            if score > best_score:
                best_score = score
                best_section = name
                best_hits = hits

        verbatim = None
        norm_excerpt = re.sub(r"\s+", " ", excerpt_lower)
        for name, body_lower in sec_lower.items():
            norm_body = re.sub(r"\s+", " ", body_lower)
            head = norm_excerpt[:50]
            if len(head) > 20 and head in norm_body:
                verbatim = name
                break

        results.append({
            "unit_id": u["unit_id"],
            "excerpt": excerpt,
            "salient_tokens": tokens,
            "prefilter_cat1": u["likely_category_1_prefilter"],
            "best_section": best_section,
            "best_score": round(best_score, 2),
            "verbatim_section": verbatim,
        })
    return results, len(units)


if __name__ == "__main__":
    products = sys.argv[1:]
    out = {}
    for p in products:
        fam, plat = p.split("/", 1)
        results, n = analyze(fam, plat)
        out[p] = results
        print(f"{p}: {n} units")
    outpath = Path(__file__).parent / "auto_match_out.json"
    json.dump(out, open(outpath, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("wrote", outpath)
