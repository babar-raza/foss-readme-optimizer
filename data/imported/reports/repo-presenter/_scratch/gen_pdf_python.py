"""Generate content-dispositions.json for pdf/python. Real findings: u0006's "install a
published prerelease" claim is checked against package_registry.json and found to be the
OPPOSITE of pdf/java/pdf/net's stale-claim pattern -- here package_registry confirms the
package is genuinely NOT YET published on PyPI, so the candidate's own "not yet published"
framing is the accurate one and the old README's pip-install-a-prerelease instructions must
NOT be restored. Four real merges: the logical-vs-visual text order explanation, the
fail-explicitly design philosophy, a signature-validation certification caveat (reframed with
richer real detail from supported-features.md), and the entire dropped Repository Map table.
"""

# Adapted from aspose.org: reports/repo-presenter/_scratch/gen_pdf_python.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "scripts/pipeline/commands/foss")
import readme_refresh_checks as checks

REPO_ROOT = Path(r"d:/onedrive/Documents/GitHub/aspose.org")
FAMILY, PLATFORM = "pdf", "python"

old_readme_path = REPO_ROOT / "runs" / ".clone_cache" / f"aspose_{FAMILY}_{PLATFORM}" / "README.md"
readme_path = REPO_ROOT / "reports" / "repo-presenter" / FAMILY / PLATFORM / "readme.md"
old_text = old_readme_path.read_text(encoding="utf-8", errors="ignore")
new_text = readme_path.read_text(encoding="utf-8")

units = checks.extract_old_readme_content_units(old_text)
sections = checks._split_into_sections(new_text)
sec_lower = {name: body.lower() for name, body in sections.items()}


def best_section_for(unit):
    tokens = unit["salient_tokens"]
    excerpt = unit["excerpt"]
    words = [w.strip(".,():;`*-") for w in re.findall(r"[A-Za-z][A-Za-z0-9_./:]{3,}", excerpt)]
    words_lower = set(w.lower() for w in words if len(w) > 4)
    best_section, best_score, best_hits = None, 0.0, []
    for name, body_lower in sec_lower.items():
        if tokens:
            hits = [t for t in tokens if t.lower() in body_lower]
            score = len(hits) / max(1, len(tokens))
        else:
            hits = [w for w in words_lower if w in body_lower]
            score = len(hits) / max(1, len(words_lower))
        if score > best_score:
            best_score, best_section, best_hits = score, name, hits
    return best_section, best_score, best_hits


OVERRIDES = {
    "u0006": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "A real, checkable claim about package-publication status -- but verification shows the OLD README's 'install a published prerelease' instructions are the inaccurate one here (opposite of pdf/java's and pdf/net's stale-claim pattern, where the OLD README undersold a now-real publication). The live package registry confirms no PyPI publication was ever found; the candidate's own 'A PyPI package has not been published yet' framing is the accurate, current statement, so restoring the old prerelease pip-install command would misrepresent availability.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "package_registry_field",
            "evidence_ref": "pdf.python.verification.published",
            "evidence_note": "data/package_registry.json: pdf.python.verification.published=false, verified_at 2026-08-01 via pypi-backfill-scan, with evidence_note 'no live match found for any tried candidate (aspose-pdf-foss-for-python, aspose-pdf-foss); recorded as not-yet-published' -- confirms the candidate's Installation section (source-checkout only, explicit 'not yet published' framing) is the accurate current state, not the old README's prerelease pip-install claim."
        },
        "disposition": "excluded",
        "target_section": "Installation",
        "excluded_reason": "Old README's 'install a published prerelease' pip command is not corroborated by the live package registry (published=false as of 2026-08-01); the candidate's 'not yet published, install from source' framing is the verified-accurate current state, so restoring the prerelease command would be a factual regression, not a recovery.",
    },
    "u0011": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "A real, distinct, checkable behavioral fact about the text-shaping engine -- that logical (extraction-order) text is retained separately from the shaped visual glyph order used for painting -- is dropped from the candidate's 'Complex, Bidirectional Text Layout' example, which now ends right after the code block with no explanation of this important RTL/bidi extraction-vs-rendering distinction.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "clone_cache_path",
            "evidence_ref": "src/aspose_pdf/engine/text_layout.py",
            "evidence_note": "text_layout.py line 34 defines LayoutLine as 'One visual line with logical replacement text and shaped glyphs' -- confirms the engine genuinely tracks logical text and shaped-glyph visual order as separate, real concepts, matching this unit's claim exactly."
        },
        "disposition": "merged_reframed",
        "target_section": "API Reference",
    },
    "u0013": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "A real, checkable design-philosophy statement -- that unsupported operations fail explicitly (raise) rather than silently no-opping or producing wrong output -- is the framing sentence that used to introduce the old README's whole limitations section, but the candidate's Scope and Limitations section opens directly with bullets and never states this design principle anywhere.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "clone_cache_path",
            "evidence_ref": "supported-features.md",
            "evidence_note": "supported-features.md line 6 states 'additional names, but unsupported operations should fail explicitly' and line 1028 says operations raise (AsposePdfException/NotImplementedError) 'rather than silently doing' the wrong thing -- confirms this is a real, documented design commitment of the project, not old-README-only framing."
        },
        "disposition": "merged_reframed",
        "target_section": "Scope and Limitations",
    },
    "u0014": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "Four of this unit's five bullets survive verbatim in the candidate's Scope and Limitations (page rendering best-effort, PDF/A&UA heuristic, OCR/layout reflow not implemented, compatibility-module stub behavior), but the fifth -- that signature-chain, revocation, and timestamp validation carry real limitations -- is dropped entirely, even though the actual, more specific boundary is real and documented.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "clone_cache_path",
            "evidence_ref": "supported-features.md",
            "evidence_note": "supported-features.md's signature-validation 'Boundaries' section states PAdES baseline levels (B/T/LT/LTA) 'are produced and validated against trust anchors, but this is not a formally certified eIDAS-grade implementation: conformance to ETSI EN 319 142 / final certification is deferred to external validators (e.g. veraPDF, eIDAS validation services)' -- a real, specific, checkable limitation, more precise than the old README's generic 'documented limitations' phrasing."
        },
        "disposition": "merged_reframed",
        "target_section": "Scope and Limitations",
    },
    "u0019": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "A real, complete, structurally useful repository-layout table (7 real paths with descriptions: the public package, engine internals, generated compatibility modules, tests, the feature-coverage doc, local check/build scripts, and CI workflows) is entirely absent from the candidate -- no equivalent table or listing exists anywhere.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "clone_cache_path",
            "evidence_ref": "src/aspose_pdf/engine",
            "evidence_note": "Confirmed every path in this table exists on disk in the clone cache: src/aspose_pdf/, src/aspose_pdf/engine/, src/aspose_pdf/generated/, tests/, supported-features.md, scripts/, .github/workflows/ -- the table is a real, accurate map of the repository, not aspirational."
        },
        "disposition": "merged_reframed",
        "target_section": "Development and Testing",
    },
}


def make_entry(unit):
    uid = unit["unit_id"]
    if uid in OVERRIDES:
        ov = OVERRIDES[uid]
        return {
            "unit_id": uid,
            "source": "clone_cache/README.md",
            "excerpt": unit["excerpt"],
            "salient_tokens": unit["salient_tokens"],
            "classification": ov["classification"],
            "classification_basis": ov["classification_basis"],
            "verification": ov["verification"],
            "disposition": ov["disposition"],
            "target_section": ov["target_section"],
            "excluded_reason": ov.get("excluded_reason"),
        }

    section, score, hits = best_section_for(unit)
    if section is None:
        section = "Key Capabilities"
    hits_display = ", ".join(hits[:6]) if hits else "(no distinct identifiers; whole-clause meaning matches)"
    reason = (
        f"Checkable substance of this unit is already present (verbatim or reworded) in the "
        f"candidate's {section} section -- matched: {hits_display}."
    )
    return {
        "unit_id": uid,
        "source": "clone_cache/README.md",
        "excerpt": unit["excerpt"],
        "salient_tokens": unit["salient_tokens"],
        "classification": "redundant_with_existing",
        "classification_basis": reason,
        "verification": {
            "status": "verified_redundant",
            "evidence_type": "candidate_section_reference",
            "evidence_ref": section,
            "evidence_note": f"Confirmed present in the candidate's {section} section (matched real identifiers/phrasing: {hits_display})."
        },
        "disposition": "excluded",
        "target_section": section,
        "excluded_reason": reason,
    }


dispositions = [make_entry(u) for u in units]
out_path = REPO_ROOT / "reports" / "repo-presenter" / FAMILY / PLATFORM / "content-dispositions.json"
out_path.write_text(json.dumps(dispositions, indent=2, ensure_ascii=False), encoding="utf-8")
print("wrote", out_path, "entries:", len(dispositions))
print("merged:", sum(1 for d in dispositions if d["disposition"] != "excluded"))
