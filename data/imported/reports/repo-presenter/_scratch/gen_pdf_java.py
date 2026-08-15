"""Generate content-dispositions.json for pdf/java. This product's old README (194 lines) is
far terser than its very thorough candidate (989 lines) -- nearly everything is genuinely
redundant. The two interesting findings are u0024/u0025: the old README's "not yet on Maven
Central" claim is now STALE (package_registry.json shows it went live 2026-07-16), so those units
are excluded as stale rather than merged -- restoring them would be a factual regression.
"""

# Adapted from aspose.org: reports/repo-presenter/_scratch/gen_pdf_java.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md
import json
import sys
from pathlib import Path

sys.path.insert(0, "scripts/pipeline/commands/foss")
import readme_refresh_checks as checks

REPO_ROOT = Path(r"d:/onedrive/Documents/GitHub/aspose.org")
FAMILY, PLATFORM = "pdf", "java"

old_readme_path = REPO_ROOT / "runs" / ".clone_cache" / f"aspose_{FAMILY}_{PLATFORM}" / "README.md"
readme_path = REPO_ROOT / "reports" / "repo-presenter" / FAMILY / PLATFORM / "readme.md"
old_text = old_readme_path.read_text(encoding="utf-8", errors="ignore")
units = checks.extract_old_readme_content_units(old_text)
units_by_id = {u["unit_id"]: u for u in units}


def R(section, note, reason=None):
    """Build a standard redundant_with_existing entry payload."""
    return {
        "classification": "redundant_with_existing",
        "verification": {
            "status": "verified_redundant",
            "evidence_type": "candidate_section_reference",
            "evidence_ref": section,
        "evidence_note": note,
        },
        "disposition": "excluded",
        "target_section": section,
        "excluded_reason": reason or note,
    }


OVERRIDES = {
    "u0001": R("Intro", "Tagline ('pure Java PDF library, zero third-party dependencies') restated in the Intro paragraph's second sentence."),
    "u0002": R("Intro", "Present near-verbatim: API-compatible with Aspose.PDF for Java, ISO 32000-1:2008 compliance, standard-Java-platform-only dependency claim all in the Intro paragraph."),
    "u0003": R("Intro", "The 'functional for many common workflows, but breaking changes may still happen between releases' sentence is present verbatim in the Intro; the specific version number (26.7 vs. candidate's 26.6.0) is ordinary version drift tracked by Installation, not lost content, and the '#status--roadmap' anchor pointed at a coverage-matrix section whose substance is now in Scope and Limitations (see u0029)."),
    "u0004": R("Key Capabilities", "Text extraction/search with TextFragmentAbsorber/TextAbsorber including RTL/Arabic shaping present verbatim in a Key Capabilities bullet."),
    "u0005": R("Key Capabilities", "Document generation (pages, paragraphs, tables Table/Row/Cell, floating boxes, headers/footers, stamps) present verbatim in a Key Capabilities bullet."),
    "u0006": R("Key Capabilities", "Drawing API shapes (Line/Rectangle/Circle/Arc/Curve/Ellipse) and gradient shadings present verbatim in a Key Capabilities bullet."),
    "u0007": R("Key Capabilities", "Image extraction and rasterization to PNG/JPEG/GIF/BMP/TIFF including multi-frame TIFF import present in a Key Capabilities bullet."),
    "u0008": R("Key Capabilities", "AcroForm field types (text, checkbox, radio, combo, list, signature) present via Form/Field in a Key Capabilities bullet."),
    "u0009": R("Key Capabilities", "XFA forms (fill, JavaScript/FormCalc scripting, conversion to AcroForm, flattening) present verbatim in a Key Capabilities bullet."),
    "u0010": R("Key Capabilities", "Annotation types present via AnnotationCollection bullet (text markup, free text, ink, stamps, file attachments, links, redaction); the specific highlight/underline/strikeout/squiggly text-markup subtypes are individually listed in the API Reference Annotations class table."),
    "u0011": R("Key Capabilities", "Bookmark/outline-tree read/modify/create present via OutlineCollection in a Key Capabilities bullet."),
    "u0012": R("Key Capabilities", "PKCS#7 signing (RSA/DSA/ECDSA) and verification present via PdfSigner in a Key Capabilities bullet."),
    "u0013": R("Key Capabilities", "AES-128/256 and RC4 encryption with password protection present in a Key Capabilities bullet; the RC4-40-vs-128 bit-length distinction is enum-level detail not called out separately anywhere in the candidate, matching how other minor algorithm-variant enumerations were handled."),
    "u0014": R("Key Capabilities", "Document.optimizeResources() mechanism (unused-object removal, duplicate-stream linking, recompression, image downsampling, font subsetting) present near-verbatim in a Key Capabilities bullet."),
    "u0015": R("Key Capabilities", "PDF/A-1 through PDF/A-4 validation and conversion present verbatim in a Key Capabilities bullet."),
    "u0016": R("Key Capabilities", "HTML-to-PDF import (HtmlLoadOptions) and PDF-to-HTML/XML save present verbatim in a Key Capabilities bullet."),
    "u0017": R("Key Capabilities", "XMP metadata read/write present via XmpMetadata in a Key Capabilities bullet."),
    "u0018": R("Key Capabilities", "Split/merge/extract/resize/reorder page operations present via the PdfFileEditor facade bullet."),
    "u0019": R("Key Capabilities", "Optional content group (layer) read/write present via Layer in a Key Capabilities bullet."),
    "u0020": R("Key Capabilities", "Embedded-files collection, preserved across merges, present verbatim via EmbeddedFileCollection in a Key Capabilities bullet."),
    "u0021": R("API Reference", "Tagged PDF / logical structure capability is covered by the large Logicalstructure API Reference class table (StructTreeRoot, StructureElement, etc.) and by the Scope and Limitations note that this support is partial."),
    "u0022": R("API Reference", "Facades (PdfFileEditor, PdfContentEditor, PdfBookmarkEditor, PdfExtractor, PdfConverter, PdfFileSignature) present via the Key Capabilities page-editing bullet and the full API Reference Facades class table."),
    "u0023": R("Installation", "Zero-third-party-dependency claim (java.*, javax.crypto, javax.imageio, javax.xml.*) present verbatim in Installation."),
    "u0024": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "This is a real, checkable claim (Maven Central publication status) -- but verification shows it is now STALE, not missing. The old README's clone-cache snapshot says the artifact is 'not yet available' on Central; the live package registry shows it went live weeks before this old-README snapshot's own capture. Restoring 'not yet available, build from source' would introduce a factual regression, not recover lost truth.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "package_registry_field",
            "evidence_ref": "pdf.java.verification.published",
            "evidence_note": "data/package_registry.json: pdf.java.verification.published=true, verified_at 2026-07-24 via a live curl of repo1.maven.org/maven2/org/aspose/aspose-pdf-foss/maven-metadata.xml returning HTTP 200 with lastUpdated 20260716135116 -- the artifact was live on Maven Central as of 2026-07-16, before this old README's own information was captured. The candidate's Installation section (real groupId org.aspose, artifactId aspose-pdf-foss, version 26.6.0, both Maven and Gradle snippets) correctly reflects the current, live state."
        },
        "disposition": "excluded",
        "target_section": "Installation",
        "excluded_reason": "Old README's 'not yet available on Maven Central, build from source' claim is stale -- package_registry.json confirms the artifact has been live on Maven Central since 2026-07-16. Restoring it would be a factual regression, not a recovery.",
    },
    "u0025": {
        "classification": "2_mechanism_explanation",
        "classification_basis": "Same stale-claim situation as u0024: this sentence's 'Once on Maven Central' conditional framing is now moot -- the pom.xml dependency snippet it introduces is already present in the candidate's Installation section, unconditionally, because the library is in fact published.",
        "verification": {
            "status": "verified_against_source",
            "evidence_type": "package_registry_field",
            "evidence_ref": "pdf.java.verification.published",
            "evidence_note": "Same package_registry.json evidence as u0024 -- pdf.java.verification.published=true since 2026-07-16. The candidate's Installation pom.xml/Gradle snippets already exist unconditionally; restoring the old 'once available' framing would misrepresent current availability as hypothetical."
        },
        "disposition": "excluded",
        "target_section": "Installation",
        "excluded_reason": "Stale 'once on Maven Central' conditional framing -- the dependency snippet is already present in Installation unconditionally because the artifact is live now.",
    },
    "u0026": R("Development and Testing", "The still-true, checkable mechanism this unit introduces -- generating JavaDoc locally with 'mvn javadoc:javadoc' -- is present verbatim in Development and Testing; the 'will be published once a stable release is tagged' hedge is superseded by the candidate's own live 'Full API reference' link to reference.aspose.org/pdf/java/ in Documentation & Resources, so restoring the hedge would be stale."),
    "u0027": R("Development and Testing", "'The generated HTML lives in target/site/apidocs/' present verbatim in Development and Testing."),
    "u0028": R("Scope and Limitations", "The coverage-matrix concept this sentence introduces is distilled into the Scope and Limitations note (Tagged PDF/logical structure partial, everything else implemented); the 'early-stage' self-description is soft narrative framing around real, already-captured status information."),
    "u0029": R("Scope and Limitations", "The single non-'Implemented' row of this table (Tagged PDF / logical structure: Partial) is exactly what Scope and Limitations states, and it also explicitly names the same implemented-area list (document generation, text/image extraction, forms, XFA, annotations, digital signatures, encryption, PDF/A, editing facades) that makes up the rest of the table."),
    "u0030": R("Documentation & Resources", "GitHub Issues link for bug reports/feature requests present verbatim in Documentation & Resources."),
    "u0031": R("Contributing", "'Pull requests are welcome. Before opening one' present near-verbatim as the opening of Contributing."),
    "u0032": R("Contributing", "All 5 checklist points (open an issue first, mvn test passes, existing code style, keep changes focused, no third-party runtime dependencies) are condensed but all present in the Contributing paragraph."),
    "u0033": R("Contributing", "AGENTS.md pointer, with the same 'particularly if you're using an AI coding assistant' framing, present verbatim in Contributing (and again in Documentation & Resources)."),
    "u0034": R("License", "MIT License statement with LICENSE link present verbatim in License."),
    "u0035": R("Scope and Limitations", "API-compatibility/migration-ease claim present in the Intro ('API-compatible with Aspose.PDF for Java'); the OCR and broader-non-PDF-format-conversion differentiators present verbatim in the Scope and Limitations Enterprise Edition paragraph."),
}

dispositions = []
for u in units:
    uid = u["unit_id"]
    ov = OVERRIDES[uid]
    entry = {
        "unit_id": uid,
        "source": "clone_cache/README.md",
        "excerpt": u["excerpt"],
        "salient_tokens": u["salient_tokens"],
        "classification": ov["classification"],
        "classification_basis": ov.get("classification_basis") or ov["verification"]["evidence_note"],
        "verification": ov["verification"],
        "disposition": ov["disposition"],
        "target_section": ov["target_section"],
        "excluded_reason": ov.get("excluded_reason"),
    }
    dispositions.append(entry)

out_path = REPO_ROOT / "reports" / "repo-presenter" / FAMILY / PLATFORM / "content-dispositions.json"
out_path.write_text(json.dumps(dispositions, indent=2, ensure_ascii=False), encoding="utf-8")
print("wrote", out_path, "entries:", len(dispositions))
print("merged:", sum(1 for d in dispositions if d["disposition"] != "excluded"))
