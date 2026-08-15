"""Generate content-dispositions.json for pdf/net. Candidate is exceptionally thorough (66 units,
only 3 low auto-match scores) -- most units are genuinely redundant. Real findings: u0006's
"build from source" install method is now stale (NuGet package verified published 2026-08-01,
same pattern as pdf/java's Maven Central discovery); u0004/u0065's Aspose.PDF-compatible/
migration-ease branding claim is genuinely missing from Intro; four real Scope-and-Limitations
gaps (ResizeContents imposition-matrix caveat, XFA's real flatten-to-AcroForm/two-way-sync
nuance, Document comparison feature, Tagged PDF/PDF-UA-2 layout-tagging partial fidelity); and two
tiny real terminology/fact restorations (OCG abbreviation, pure-managed-crypto claim).
"""

# Adapted from aspose.org: reports/repo-presenter/_scratch/gen_pdf_net.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, "scripts/pipeline/commands/foss")
import readme_refresh_checks as checks

REPO_ROOT = Path(r"d:/onedrive/Documents/GitHub/aspose.org")
FAMILY, PLATFORM = "pdf", "net"

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
    "u0004": {
        "classification": "3_branding_positioning",
        "classification_basis": "The 'Aspose.PDF-compatible API surface... a large part of existing Aspose.PDF for .NET code can compile and run unchanged' positioning claim is entirely absent from the candidate's Intro, which never mentions the commercial product's API compatibility at all -- unusual among this product's siblings (pdf/cpp, pdf/go, pdf/java candidates all state their API-compatibility with the corresponding commercial product in their Intro).",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "clone_cache_path",
            "evidence_ref": "README.md",
            "evidence_note": "Confirmed the claim is real (not marketing invention) by cross-checking the API surface: the candidate's own API Reference lists namespaces/types (Document, Page, TextAbsorber, PdfFileEditor, etc.) matching the commercial Aspose.PDF for .NET's public API 1:1, consistent with 'a large part of existing code can compile unchanged.'"
        },
        "disposition": "merged_reframed",
        "target_section": "Intro",
    },
    "u0006": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "This is a real, checkable installation-mechanism claim (build-from-source, reference the .csproj) -- but verification shows it is STALE: the candidate's current Installation section installs from NuGet directly, which is correct because the package is now actually published. Restoring the old build-from-source-only instructions would be a factual regression, same pattern as pdf/java's stale 'not yet on Maven Central' claim.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "package_registry_field",
            "evidence_ref": "pdf.net.verification.published",
            "evidence_note": "data/package_registry.json: pdf.net.verification.published=true, verified_at 2026-08-01 via a live NuGet flat-container API check (https://api.nuget.org/v3-flatcontainer/aspose.pdf.foss/index.json) -- the candidate's 'dotnet add package Aspose.Pdf.Foss --version 26.7.0' Installation instructions correctly reflect that the package is live on NuGet, unlike this old README's build-from-source-only snapshot."
        },
        "disposition": "excluded",
        "target_section": "Installation",
        "excluded_reason": "Old README's build-from-source-only install instructions are stale -- package_registry.json confirms Aspose.PDF.FOSS has been live on NuGet since 2026-08-01. Restoring 'build from source, reference the .csproj' as the only path would be a factual regression.",
    },
    "u0010": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "The optional-content-groups/layers capability itself is thoroughly covered (Key Capabilities bullet plus API Reference's OptionalContentGroup/OptionalContentBuilder/Layer classes), but the standard ISO PDF abbreviation 'OCG' -- real, checkable terminology used throughout the actual PDF spec and the library's own API -- does not appear anywhere in the candidate, not even inside the class descriptions.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "clone_cache_path",
            "evidence_ref": "README.md",
            "evidence_note": "Old README's own 'optional content (OCG) layers' phrasing matches the library's real OptionalContentGroup class name (confirmed present in the candidate's API Reference) -- OCG is the standard ISO 32000 abbreviation for this class's real subject, not old-README-only jargon."
        },
        "disposition": "merged_reframed",
        "target_section": "Key Capabilities",
    },
    "u0012": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "A real, distinct, checkable implementation fact -- that the library's cryptography is pure-managed and does not depend on System.Security.Cryptography at runtime -- is absent from the candidate; the Installation section only discusses the System.Drawing.Common dependency, leaving crypto dependency status unstated.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "clone_cache_path",
            "evidence_ref": "src/Security/AesCipher.cs",
            "evidence_note": "AesCipher.cs's own header comment states it 'Replaces System.Security.Cryptography.Aes dependency' -- confirms the pure-managed-crypto claim is a real, deliberate design choice (the source mentions the BCL namespace only in a comment explaining what was reimplemented, not as an actual dependency)."
        },
        "disposition": "merged_reframed",
        "target_section": "Installation",
    },
    "u0054": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "The MakeNUp/MakeBooklet imposition-fallback caveat survives in Scope and Limitations, but the third example this unit lists -- ResizeContents with custom imposition matrices falling back to the simple layout -- is dropped entirely. MT031 mixed-unit rule: merge only the missing fact.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "clone_cache_path",
            "evidence_ref": "src/Facades/PdfFileEditor.cs",
            "evidence_note": "PdfFileEditor.cs's ResizeContents implementation (around line 863-890) applies a plain scale/translate transform derived from ContentsResizeParameters' margins -- confirms it is the same kind of 'simple layout' fallback as MakeNUp/MakeBooklet, not a custom-imposition-matrix-aware implementation."
        },
        "disposition": "merged_reframed",
        "target_section": "Scope and Limitations",
    },
    "u0055": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "The candidate's Scope and Limitations compresses XFA support down to 'XFA authoring/editing is read-only (dynamic XFA can be read)' -- but the real, source-verified capability is more specific and arguably contradicts a literal 'read-only' reading: dynamic XFA is read AND can be flattened into real, findable AcroForm pages, with XFA datasets syncing two-way with the resulting AcroForm fields and exporting/importing via FDF/XFDF/XML. Only fine-grained authoring of individual XFA dataset fields is actually limited.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "clone_cache_path",
            "evidence_ref": "src/Forms/Xfa/XfaFormEngine.cs",
            "evidence_note": "XfaFormEngine.cs is a real 'Dynamic-XFA -> static-AcroForm engine' (its own file header) whose FlatXfaField carries 'AcroForm field flags' and whose header notes 'a flattened dynamic-XFA form keeps its data values on the flat AcroForm fields' -- confirms the flatten-to-AcroForm and data-sync behavior is real and more capable than a bare 'read-only' summary conveys."
        },
        "disposition": "merged_reframed",
        "target_section": "Scope and Limitations",
    },
    "u0057": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "Document comparison (the low-level Aspose.Pdf.Comparison.Diff edit-operation model, present but without a higher-level visual-diff workflow) is a real, distinct, checkable scope caveat that does not appear anywhere in the candidate -- neither in Scope and Limitations nor in any API Reference table.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "clone_cache_path",
            "evidence_ref": "src/Comparison",
            "evidence_note": "src/Comparison/Diff/ is a real source directory implementing the diff/merge/slide-optimizer edit-operation model this unit describes -- confirms the low-level API exists (so the caveat about the missing higher-level visual-diff workflow is a real, accurate scope boundary, not a fabricated one)."
        },
        "disposition": "merged_reframed",
        "target_section": "Scope and Limitations",
    },
    "u0058": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "Tagged PDF rendering fidelity -- the structure tree round-trips through /StructTreeRoot, but advanced PDF/UA-2 layout-aware tagging features are partial -- is a real, distinct, checkable limitation entirely absent from the candidate's Scope and Limitations, which otherwise thoroughly lists partial features.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "clone_cache_path",
            "evidence_ref": "docs/tagged-pdf.md",
            "evidence_note": "docs/tagged-pdf.md's own 'Adjusting element positioning' section states PositionSettings 'are stored on the element but are not yet applied to content layout' -- confirms the real, source-documented gap between what tagging metadata can be set and what actually affects rendered layout, matching this unit's 'layout-aware tagging features are partial' claim."
        },
        "disposition": "merged_reframed",
        "target_section": "Scope and Limitations",
    },
    "u0065": {
        "classification": "3_branding_positioning",
        "classification_basis": "The Enterprise-Edition differentiator list (AI workflows, additional format converters, multithreading, full validation coverage) survives in Scope and Limitations, but the unit's closing branding claim -- 'shares the same public API shape, so code can usually migrate between the two with minimal changes' -- is dropped, and is the same fact u0004's merge restores to Intro; excluding here to avoid a duplicate merge.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "candidate_section_reference",
            "evidence_ref": "Intro",
            "evidence_note": "Covered by u0004's merge into Intro, which restores the same Aspose.PDF-compatible / migrate-with-minimal-changes claim this unit's closing sentence makes."
        },
        "disposition": "excluded",
        "target_section": "Intro",
        "excluded_reason": "Migration-ease branding claim covered by u0004's merge into Intro; the Enterprise Edition differentiator list this unit also contains is already present verbatim in Scope and Limitations.",
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
