# Adapted from aspose.org: reports/repo-presenter/_scratch/append_note_python_dispositions.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

import json
from pathlib import Path

TARGET = Path(r"D:\onedrive\Documents\GitHub\aspose.org\reports\repo-presenter\note\python\content-dispositions.json")

API_BASIS = (
    "Public API member/class/enum/exception detail from the old README public-API section "
    "(recovered by the MT031 4+-letter-word noise-filter fix); the same member is already "
    "reproduced (verbatim or with additional detail) in the candidate collapsed View the "
    "Supported Public API Surface block."
)

def api_entry(unit_id, excerpt, tokens, evidence_ref, evidence_note, basis=None):
    return {
        "unit_id": unit_id,
        "source": "clone_cache/README.md",
        "excerpt": excerpt,
        "salient_tokens": tokens,
        "classification": "redundant_with_existing",
        "classification_basis": basis or API_BASIS,
        "verification": {
            "status": "verified_redundant",
            "evidence_type": "candidate_section_reference",
            "evidence_ref": evidence_ref,
            "evidence_note": evidence_note,
        },
        "disposition": "excluded",
        "target_section": None,
        "excluded_reason": "redundant_with_existing_content: this API member already appears in the candidate API Reference section",
    }

new_entries = []

# u0007 - Content extraction category header (old README Features list, "- ✅ Content extraction")
new_entries.append({
    "unit_id": "u0007",
    "source": "clone_cache/README.md",
    "excerpt": "- \u2705 Content extraction",
    "salient_tokens": [],
    "classification": "redundant_with_existing",
    "classification_basis": "Old-README Features parent-category bullet (recovered by the MT031 4+-letter-word noise-filter fix) grouping the Rich text/Images/Attached files/Tables/OneNote tags/Numbered lists sub-bullets; the same capability grouping is already reframed into the candidate Key Capabilities section.",
    "verification": {
        "status": "verified_redundant",
        "evidence_type": "candidate_section_reference",
        "evidence_ref": "Key Capabilities",
        "evidence_note": "Candidate Key Capabilities already states: 'Extract rich text, formatting runs, hyperlinks, images, attached files, and document metadata.' and 'Inspect tables, OneNote tags, numbered lists, and nested outline elements.' -- covers every child bullet the old README nested under this Content extraction header.",
    },
    "disposition": "excluded",
    "target_section": None,
    "excluded_reason": "redundant_with_existing_content: this capability grouping is already listed in the candidate Key Capabilities section",
})

# u0015 - "From PyPI:" install label
new_entries.append({
    "unit_id": "u0015",
    "source": "clone_cache/README.md",
    "excerpt": "From PyPI:",
    "salient_tokens": ["PyPI"],
    "classification": "redundant_with_existing",
    "classification_basis": "Transitional label introducing the base-package PyPI install command; the equivalent transitional sentence and identical command already exist in the candidate Installation section.",
    "verification": {
        "status": "verified_redundant",
        "evidence_type": "candidate_section_reference",
        "evidence_ref": "Installation",
        "evidence_note": "Candidate Installation section already states 'Install the library from PyPI:' immediately followed by the identical `python -m pip install aspose-note` command.",
    },
    "disposition": "excluded",
    "target_section": None,
    "excluded_reason": "redundant_with_existing_content: an equivalent transitional sentence and identical command already exist in Installation",
})

# u0016 - "With PDF export support:" install label
new_entries.append({
    "unit_id": "u0016",
    "source": "clone_cache/README.md",
    "excerpt": "With PDF export support:",
    "salient_tokens": ["PDF"],
    "classification": "redundant_with_existing",
    "classification_basis": "Transitional label introducing the PDF-extra install command; the equivalent transitional sentence and identical command already exist in the candidate Installation section.",
    "verification": {
        "status": "verified_redundant",
        "evidence_type": "candidate_section_reference",
        "evidence_ref": "Installation",
        "evidence_note": "Candidate Installation section already states 'Install PDF export support:' immediately followed by the identical `python -m pip install \"aspose-note[pdf]\"` command.",
    },
    "disposition": "excluded",
    "target_section": None,
    "excluded_reason": "redundant_with_existing_content: an equivalent transitional sentence and identical command already exist in Installation",
})

# u0017 - "From a local checkout:" install label
new_entries.append({
    "unit_id": "u0017",
    "source": "clone_cache/README.md",
    "excerpt": "From a local checkout:",
    "salient_tokens": [],
    "classification": "redundant_with_existing",
    "classification_basis": "Transitional label introducing the base-package editable-install command; the equivalent transitional sentence and identical command already exist in the candidate Development and Testing section (relocated there rather than Installation).",
    "verification": {
        "status": "verified_redundant",
        "evidence_type": "candidate_section_reference",
        "evidence_ref": "Development and Testing",
        "evidence_note": "Candidate Development and Testing section already states 'Install the base package from a local checkout:' immediately followed by the identical `python -m pip install -e .` command.",
    },
    "disposition": "excluded",
    "target_section": None,
    "excluded_reason": "redundant_with_existing_content: an equivalent transitional sentence and identical command already exist in Development and Testing",
})

# API member/class entries -----------------------------------------------

new_entries.append(api_entry(
    "u0037", "- `PageHistory`", ["PageHistory"],
    "API Reference",
    "Confirmed real class `PageHistory` at runs/.clone_cache/aspose_note_python/src/aspose/note/model.py:1186; already reproduced verbatim (with Count/IsReadOnly typed) in the candidate's Detailed Member Reference under 'PageHistory'.",
))
new_entries.append(api_entry(
    "u0038", "- `Current: Page`", ["Current: Page", "Current"],
    "API Reference",
    "Confirmed real property `PageHistory.Current -> Page` at model.py:1197-1199 (`@property def Current(self) -> Page`); already reproduced verbatim in the candidate's Detailed Member Reference under 'PageHistory'.",
))
new_entries.append(api_entry(
    "u0042", "- `Node`", ["Node"],
    "API Reference",
    "Confirmed real base class `Node` at model.py:134; already reproduced (with ParentNode/Document/Accept(visitor)) in the candidate's Detailed Member Reference under 'Node'.",
))
new_entries.append(api_entry(
    "u0043", "- `ParentNode`", ["ParentNode"],
    "API Reference",
    "Confirmed real property `Node.ParentNode -> Node | None` at model.py:145-147; already reproduced verbatim in the candidate's Detailed Member Reference under 'Node'.",
))
new_entries.append(api_entry(
    "u0045", "- `Accept(visitor)`", ["Accept(visitor)", "Accept"],
    "API Reference",
    "Confirmed real method `Node.Accept(visitor)` at model.py:161-162; already reproduced verbatim in the candidate's Detailed Member Reference under 'Node'.",
))
new_entries.append(api_entry(
    "u0051", "- `Page`", ["Page"],
    "API Reference",
    "Confirmed real class `Page` at model.py:1156 (`@dataclass class Page(CompositeNode)`); already reproduced (with Title/Author/CreationTime/LastModifiedTime/Level/Clone) in the candidate's Detailed Member Reference under 'Document Structure -> Page'.",
))
new_entries.append(api_entry(
    "u0052", "- `Title: Title | None`", ["Title: Title | None", "Title"],
    "API Reference",
    "Confirmed real field `Page.Title: Title | None = None` at model.py:1157; already reproduced verbatim in the candidate's Detailed Member Reference under 'Page'.",
))
new_entries.append(api_entry(
    "u0053", "- `Author: str | None`", ["Author: str | None", "Author"],
    "API Reference",
    "Confirmed real field `Page.Author: str | None = None` at model.py:1158; already reproduced verbatim in the candidate's Detailed Member Reference under 'Page'.",
))
new_entries.append(api_entry(
    "u0055", "- `Level: int | None`", ["Level: int | None", "Level"],
    "API Reference",
    "Confirmed real field `Page.Level: int | None = None` at model.py:1161; already reproduced verbatim in the candidate's Detailed Member Reference under 'Page'.",
))
new_entries.append(api_entry(
    "u0057", "- `Title`", ["Title"],
    "API Reference",
    "Confirmed real class `Title(Node)` at model.py:836; already reproduced (with TitleText/TitleDate/TitleTime) in the candidate's Detailed Member Reference under 'Title'.",
))
new_entries.append(api_entry(
    "u0061", "- `Outline`", ["Outline"],
    "API Reference",
    "Confirmed real class `Outline(CompositeNode)` at model.py:944; already reproduced (with HorizontalOffset/VerticalOffset/MaxWidth/etc.) in the candidate's Detailed Member Reference under 'Outline'.",
))
new_entries.append(api_entry(
    "u0065", "- `OutlineElement`", ["OutlineElement"],
    "API Reference",
    "Confirmed real class `OutlineElement(CompositeNode)` at model.py:933; already reproduced (with NumberList) in the candidate's Detailed Member Reference under 'OutlineElement'.",
))
new_entries.append(api_entry(
    "u0067", "- `RichText(Node)`", ["RichText(Node)", "RichText"],
    "API Reference",
    "Confirmed real class `RichText(Node)` at model.py:627; already reproduced (with Text/TextRuns/ParagraphStyle/Length/Alignment/Tags/etc.) in the candidate's Detailed Member Reference under 'RichText(Node)'.",
))
new_entries.append(api_entry(
    "u0068", "- `Text: str`", ["Text: str", "Text"],
    "API Reference",
    "Confirmed real property `RichText.Text -> str` at model.py:676-680; already reproduced verbatim in the candidate's Detailed Member Reference under 'RichText(Node)'.",
))
new_entries.append(api_entry(
    "u0071", "- `Length: int`", ["Length: int", "Length"],
    "API Reference",
    "Confirmed real property `RichText.Length -> int` (`return len(self.Text)`) at model.py:709-711; already reproduced verbatim in the candidate's Detailed Member Reference under 'RichText(Node)'.",
))
new_entries.append(api_entry(
    "u0073", "- `Tags: list[NoteTag]`", ["Tags: list[NoteTag]", "NoteTag"],
    "API Reference",
    "Confirmed real property `RichText.Tags -> list[NoteTag]` at model.py:648, 705-707; already reproduced verbatim in the candidate's Detailed Member Reference under 'RichText(Node)'.",
))
new_entries.append(api_entry(
    "u0076", "- `IndexOf(...) -> int`", ["IndexOf(...) -> int", "IndexOf"],
    "API Reference",
    "Confirmed real method `RichText.IndexOf(value, startIndex=0, count=None, comparison=None) -> int` at model.py:756-763; already reproduced verbatim in the candidate's Detailed Member Reference under 'RichText(Node)'.",
))
new_entries.append(api_entry(
    "u0077", "- `TextRun`", ["TextRun"],
    "API Reference",
    "Confirmed real class `TextRun` at model.py:622-624 (`Text: str`, `Style: TextStyle`); already reproduced verbatim in the candidate's Detailed Member Reference under 'TextRun'.",
))
new_entries.append(api_entry(
    "u0078", "- `Text: str`", ["Text: str", "Text"],
    "API Reference",
    "Confirmed real field `TextRun.Text: str = \"\"` at model.py:623; already reproduced verbatim in the candidate's Detailed Member Reference under 'TextRun'.",
))
new_entries.append(api_entry(
    "u0079", "- `Style: TextStyle`", ["Style: TextStyle", "TextStyle"],
    "API Reference",
    "Confirmed real field `TextRun.Style: TextStyle` at model.py:624; already reproduced verbatim in the candidate's Detailed Member Reference under 'TextRun'.",
))
new_entries.append(api_entry(
    "u0080", "- `ParagraphStyle`", ["ParagraphStyle"],
    "API Reference",
    "Confirmed real class `ParagraphStyle` at model.py:340; already reproduced (as default paragraph-level formatting for RichText.ParagraphStyle) in the candidate's Detailed Member Reference under 'ParagraphStyle'.",
))
new_entries.append(api_entry(
    "u0082", "- `TextStyle`", ["TextStyle"],
    "API Reference",
    "Confirmed real class `TextStyle` at model.py:397; already reproduced (with IsBold/IsItalic/FontName/FontSize/Language/FontStyle/IsHyperlink/etc.) in the candidate's Detailed Member Reference under 'TextStyle'.",
))
new_entries.append(api_entry(
    "u0087", "- `Language: int | None`", ["Language: int | None", "Language"],
    "API Reference",
    "Confirmed real property `TextStyle.Language -> int | None` at model.py:425, 500-504; the property name (without an explicit inline type annotation) already appears in the candidate's Detailed Member Reference 'TextStyle' bullet: 'FontName, FontSize, FontColor, Highlight, Language, FontStyle'.",
))
new_entries.append(api_entry(
    "u0088", "- `FontStyle: int`", ["FontStyle: int", "FontStyle"],
    "API Reference",
    "Confirmed real property `TextStyle.FontStyle -> int` at model.py:572; the property name (without an explicit inline type annotation) already appears in the candidate's Detailed Member Reference 'TextStyle' bullet: 'FontName, FontSize, FontColor, Highlight, Language, FontStyle'.",
))
new_entries.append(api_entry(
    "u0090", "- `Image`", ["Image"],
    "API Reference",
    "Confirmed real class `Image(CompositeNode)` at model.py:962; already reproduced (with FileName/Bytes/Width/Height/AlternativeTextTitle/HyperlinkUrl/Tags/Replace) in the candidate's Detailed Member Reference under 'Image'.",
))
new_entries.append(api_entry(
    "u0095", "- `Tags: list[NoteTag]`", ["Tags: list[NoteTag]", "NoteTag"],
    "API Reference",
    "Confirmed real property `Image.Tags -> list[NoteTag]` at model.py:1002, 1047-1049; the property name already appears in the candidate's Detailed Member Reference 'Image' bullet: 'HyperlinkUrl, Tags, LastModifiedTime'.",
))
new_entries.append(api_entry(
    "u0097", "- `AttachedFile(Node)`", ["AttachedFile(Node)", "AttachedFile"],
    "API Reference",
    "Confirmed real class `AttachedFile(Node)` at model.py:1085; already reproduced (with FileName/Bytes/Tags) in the candidate's Detailed Member Reference under 'AttachedFile(Node)'.",
))
new_entries.append(api_entry(
    "u0099", "- `Tags: list[NoteTag]`", ["Tags: list[NoteTag]", "NoteTag"],
    "API Reference",
    "Confirmed real property `AttachedFile.Tags -> list[NoteTag]` at model.py:1093, 1108-1110; already reproduced verbatim in the candidate's Detailed Member Reference 'AttachedFile(Node)' bullet: 'FileName, Bytes, Tags'.",
))
new_entries.append(api_entry(
    "u0100", "- `Table`", ["Table"],
    "API Reference",
    "Confirmed real class `Table(CompositeNode)` at model.py:1129; already reproduced (with Columns/IsBordersVisible/Tags/LastModifiedTime) in the candidate's Detailed Member Reference under 'Table'.",
))
new_entries.append(api_entry(
    "u0103", "- `Tags: list[NoteTag]`", ["Tags: list[NoteTag]", "NoteTag"],
    "API Reference",
    "Confirmed real property `Table.Tags -> list[NoteTag]` at model.py:1135, 1146-1148; already reproduced verbatim in the candidate's Detailed Member Reference under 'Table'.",
))
new_entries.append(api_entry(
    "u0104", "- `TableColumn`", ["TableColumn"],
    "API Reference",
    "Confirmed real class `TableColumn` at model.py:1123-1126 (`@dataclass` with Width/LockedWidth); already reproduced verbatim in the candidate's Detailed Member Reference under 'TableColumn'.",
))
new_entries.append(api_entry(
    "u0105", "- `Width: float | None`", ["Width: float | None", "Width"],
    "API Reference",
    "Confirmed real field `TableColumn.Width: float | None = None` at model.py:1125; already reproduced verbatim in the candidate's Detailed Member Reference under 'TableColumn'.",
))
new_entries.append(api_entry(
    "u0106", "- `LockedWidth: bool`", ["LockedWidth: bool", "LockedWidth"],
    "API Reference",
    "Confirmed real field `TableColumn.LockedWidth: bool = False` at model.py:1126; already reproduced verbatim in the candidate's Detailed Member Reference under 'TableColumn'.",
))
new_entries.append(api_entry(
    "u0108", "- `NoteTag`", ["NoteTag"],
    "API Reference",
    "Confirmed real class `NoteTag` at model.py:220; already reproduced (with Label/Icon/Status/Highlight/CreationTime/CompletedTime/FontColor and CreateYellowStar()/CreateQuestionMark()/CreateMusicalNote() factories) in the candidate's Detailed Member Reference under 'NoteTag'.",
))
new_entries.append(api_entry(
    "u0111", "- `NumberList`", ["NumberList"],
    "API Reference",
    "Confirmed real class `NumberList` at model.py:912-922 (`@dataclass` with Format/NumberFormat/Font/FontSize/FontColor/IsBold/IsItalic/LastModifiedTime/Restart and GetNumberedListHeader()); already reproduced verbatim in the candidate's Detailed Member Reference under 'NumberList'.",
))
new_entries.append(api_entry(
    "u0116", "- `LoadOptions`", ["LoadOptions"],
    "API Reference",
    "Confirmed real class `LoadOptions` at model.py:127-130 (`@dataclass` with DocumentPassword/LoadHistory); already reproduced verbatim in the candidate's Detailed Member Reference under 'LoadOptions'.",
))
new_entries.append(api_entry(
    "u0118", "- `LoadHistory: bool`", ["LoadHistory: bool", "LoadHistory"],
    "API Reference",
    "Confirmed real field `LoadOptions.LoadHistory: bool = False` at model.py:130; already reproduced verbatim in the candidate's Detailed Member Reference under 'LoadOptions'.",
))
new_entries.append(api_entry(
    "u0126", "- `SaveFormat`: `Pdf`", ["SaveFormat", "Pdf"],
    "API Reference",
    "Confirmed real enum member `SaveFormat.Pdf = \"pdf\"` at runs/.clone_cache/aspose_note_python/src/aspose/note/enums.py:6-7; already reproduced verbatim in the candidate's Detailed Member Reference under 'Enums: SaveFormat: Pdf'.",
))

# u0140 / u0143 - Other platforms section headers
new_entries.append({
    "unit_id": "u0140",
    "source": "clone_cache/README.md",
    "excerpt": "- Aspose.Note for .NET",
    "salient_tokens": ["NET"],
    "classification": "redundant_with_existing",
    "classification_basis": "Old-README '## Other platforms (official Aspose.Note)' sub-heading naming the .NET full-featured product; the same pointer is already merged into the candidate Documentation & Resources section (see u0097 in the existing 102 dispositions, which merged the parent Other platforms paragraph).",
    "verification": {
        "status": "verified_redundant",
        "evidence_type": "candidate_section_reference",
        "evidence_ref": "Documentation & Resources",
        "evidence_note": "Candidate Documentation & Resources already states: 'If you need the full-featured Aspose product ... see the official Aspose.Note for .NET -- Enterprise Edition (products.aspose.com/note/net/) (docs) or Aspose.Note for Java -- Enterprise Edition ...' -- names Aspose.Note for .NET with working product+docs links.",
    },
    "disposition": "excluded",
    "target_section": None,
    "excluded_reason": "redundant_with_existing_content: the Aspose.Note for .NET cross-platform pointer already appears in Documentation & Resources",
})
new_entries.append({
    "unit_id": "u0143",
    "source": "clone_cache/README.md",
    "excerpt": "- Aspose.Note for Java",
    "salient_tokens": [],
    "classification": "redundant_with_existing",
    "classification_basis": "Old-README '## Other platforms (official Aspose.Note)' sub-heading naming the Java full-featured product; the same pointer is already merged into the candidate Documentation & Resources section (see u0097 in the existing 102 dispositions, which merged the parent Other platforms paragraph).",
    "verification": {
        "status": "verified_redundant",
        "evidence_type": "candidate_section_reference",
        "evidence_ref": "Documentation & Resources",
        "evidence_note": "Candidate Documentation & Resources already states: '... or Aspose.Note for Java -- Enterprise Edition (products.aspose.com/note/java/) (docs).' -- names Aspose.Note for Java with working product+docs links.",
    },
    "disposition": "excluded",
    "target_section": None,
    "excluded_reason": "redundant_with_existing_content: the Aspose.Note for Java cross-platform pointer already appears in Documentation & Resources",
})

# u0146 - "Run tests:" label under old README "## Development" -- flags a real false claim (pytest)
new_entries.append({
    "unit_id": "u0146",
    "source": "clone_cache/README.md",
    "excerpt": "Run tests:",
    "salient_tokens": [],
    "classification": "redundant_with_existing",
    "classification_basis": (
        "Transitional label from the old README's '## Development' section, introducing "
        "`python -m pip install -e \".[pdf]\" && python -m pytest -q`. VERIFIED FALSE CLAIM: the "
        "real repository has zero pytest usage anywhere -- pytest is not declared in pyproject.toml "
        "(no [tool.pytest] section, not in dependencies/optional-dependencies/dev extras), no source "
        "or config file references pytest except README.md itself, .gitignore's boilerplate "
        "'.pytest_cache/' entry, and .vscode/settings.json explicitly sets "
        "\"python.testing.pytestEnabled\": false. The real, authoritative test entry point is Python's "
        "built-in unittest module: .github/workflows/ci.yml's 'Run unit test suite' step invokes "
        "`python -m unittest tests.<module> -v` for 8 named test modules plus a separate PDF-goldens "
        "step. The candidate's Development and Testing section already introduces test-running with "
        "the CORRECT command (`python -m unittest discover -q`) rather than propagating the old "
        "README's incorrect pytest instruction, so the real underlying mechanism this label announces "
        "is already present -- correctly, not verbatim."
    ),
    "verification": {
        "status": "verified_redundant",
        "evidence_type": "candidate_section_reference",
        "evidence_ref": "Development and Testing",
        "evidence_note": (
            "Checked runs/.clone_cache/aspose_note_python/pyproject.toml (no pytest anywhere), "
            "grepped the entire clone cache for 'pytest' (only hits: README.md's own false claim, "
            ".gitignore boilerplate, and .vscode/settings.json's pytestEnabled:false), and "
            ".github/workflows/ci.yml (test step runs exclusively `python -m unittest ...`). Candidate "
            "Development and Testing already states 'Install the repository with PDF support and run "
            "the test suite:' followed by `python -m pip install -e \".[pdf]\"` and "
            "`python -m unittest discover -q` -- the real command, not the old README's pytest one."
        ),
    },
    "disposition": "excluded",
    "target_section": None,
    "excluded_reason": (
        "redundant_with_existing_content: the real install+test-run mechanism already appears in "
        "Development and Testing, using the verified-correct unittest command rather than the old "
        "README's factually incorrect pytest reference (repo has no pytest dependency and CI never "
        "invokes pytest)"
    ),
})

assert len(new_entries) == 45, f"expected 45 new entries, got {len(new_entries)}"

expected_ids = [
    "u0007","u0015","u0016","u0017","u0037","u0038","u0042","u0043","u0045","u0051",
    "u0052","u0053","u0055","u0057","u0061","u0065","u0067","u0068","u0071","u0073",
    "u0076","u0077","u0078","u0079","u0080","u0082","u0087","u0088","u0090","u0095",
    "u0097","u0099","u0100","u0103","u0104","u0105","u0106","u0108","u0111","u0116",
    "u0118","u0126","u0140","u0143","u0146",
]
actual_ids = [e["unit_id"] for e in new_entries]
assert actual_ids == expected_ids, f"unit_id mismatch/order: {actual_ids}"

existing = json.loads(TARGET.read_text(encoding="utf-8"))
assert len(existing) == 102, f"expected 102 existing entries, got {len(existing)}"

combined = existing + new_entries
TARGET.write_text(json.dumps(combined, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"Wrote {len(combined)} total entries ({len(existing)} existing + {len(new_entries)} new)")
