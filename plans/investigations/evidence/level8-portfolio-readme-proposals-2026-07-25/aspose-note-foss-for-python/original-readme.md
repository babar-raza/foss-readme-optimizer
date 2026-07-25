# 🗒️ Aspose.Note FOSS for Python

[![CI](https://github.com/aspose-note/aspose-note-python/actions/workflows/ci.yml/badge.svg)](https://github.com/aspose-note/aspose-note-python/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/aspose-note.svg)](https://pypi.org/project/aspose-note/)
[![Python Versions](https://img.shields.io/pypi/pyversions/aspose-note.svg)](https://pypi.org/project/aspose-note/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Quick links: [📚 Examples](examples/) • [📦 PyPI](https://pypi.org/project/aspose-note/)

✅ **Official Aspose project** — **100% free & open-source**. Provides an Aspose.Note-compatible Python API for working with OneNote `.one` files.

This repository provides a Python library with a **subset-compatible Aspose.Note for .NET-shaped public API** for reading Microsoft OneNote files (`.one`).

The goal is to offer a familiar surface (`aspose.note.*`) inspired by [Aspose.Note for .NET](https://products.aspose.com/note/net/), backed by this repository’s built-in MS-ONE/OneStore parser.

## ✨ Features

- ✅ Read `.one` from a file path or a binary stream
- ✅ Aspose-like DOM (Document/Page/Outline/…): traversal + type-based search
- ✅ Content extraction
  - ✅ Rich text with formatting runs (TextRun/TextStyle) and hyperlinks
  - ✅ Images (bytes, file name, dimensions)
  - ✅ Attached files (bytes, file name)
  - ✅ Tables (rows/cells + cell content)
  - ✅ OneNote tags (NoteTag) on text/images/tables and tagged list content
  - ✅ Numbered lists (NumberList) and nested outline elements
- ✅ PDF export via `Document.Save(..., SaveFormat.Pdf)` (uses ReportLab)

## 🚀 Quick start

```python
from aspose.note import Document

doc = Document("testfiles/SimpleTable.one")
print(doc.DisplayName)
pages = list(doc)
print(len(pages))

# pages are direct children of Document
for page in pages:
    print(page.Title.TitleText.Text)
```

### 📄 Export to PDF

```python
from aspose.note import Document, SaveFormat

doc = Document("testfiles/FormattedRichText.one")
doc.Save("out.pdf", SaveFormat.Pdf)
```

## 📦 Installation

From PyPI:

```bash
python -m pip install aspose-note
```

With PDF export support:

```bash
python -m pip install "aspose-note[pdf]"
```

From a local checkout:

```bash
python -m pip install -e .
```

PDF export requires ReportLab:

```bash
python -m pip install -e ".[pdf]"
```

Semantic PDF golden tests require `pypdf` in addition to ReportLab:

```bash
python -m pip install -e ".[pdf,test-pdf]"
```

## PDF golden workflow

Golden PDFs are stored under `tests/goldens/pdf/` together with JSON manifests extracted from the generated PDF.
The test suite compares manifests, not raw PDF bytes, so it stays stable across platforms and ReportLab internals.
The PDF writer now uses deterministic Base-14 fonts by default. If you explicitly want to try Windows system fonts for local inspection, set `ASPOSE_NOTE_PDF_USE_SYSTEM_FONTS=1` before export.

Regenerate the baselines with:

```bash
python tools/regenerate_pdf_goldens.py
```

To rebuild only selected cases:

```bash
python tools/regenerate_pdf_goldens.py --case formatted_richtext --case simple_table
```

Run the verification suite with:

```bash
python -m unittest tests.test_aspose_note_pdf_goldens -v
```

On mismatch, generated PDFs and manifests are written to `tests/out/pdf_golden_failures/` for inspection.
If `PyMuPDF` is installed, the failing test also renders baseline/generated pages to PNG and writes visual diff artifacts into the same output tree.
If `PyMuPDF` is unavailable but `pdftoppm` is available on `PATH`, the tests use `pdftoppm` as a fallback renderer.

PyPI release page (maintainers): https://pypi.org/manage/project/aspose-note/releases/

## 🧩 Public API (what is considered supported)

The supported public entry points are `aspose.note` and `aspose.note.saving`.
Everything under `aspose.note._internal` is internal implementation detail and may change.

Below is the supported public surface across those entry points.

### 🧭 Document and traversal

- `Document(source=None, load_options=None)`
  - `DisplayName: str | None`
  - `CreationTime: datetime | None`
  - iteration: `for page in doc: ...`
  - `FileFormat -> FileFormat` (best-effort)
  - `GetPageHistory(page) -> PageHistory`
  - `DetectLayoutChanges()` (compatibility stub)
  - `Save(target, format_or_options=None)`
    - supported: `SaveFormat.Pdf` only

- `PageHistory`
  - `Current: Page`
  - `Count: int`, `IsReadOnly: bool`
  - iteration/indexing over historical revisions only

- `DocumentVisitor` — base visitor for traversal:
  - `VisitDocumentStart/End`, `VisitPageStart/End`, `VisitTitleStart/End`, `VisitOutlineStart/End`,
    `VisitOutlineElementStart/End`, `VisitRichTextStart/End`, `VisitImageStart/End`

- `Node`
  - `ParentNode`
  - `Document` (property) — walk up to the root `Document`
  - `Accept(visitor)`

- Container nodes (`Document`, `Page`, `Title`, `Outline`, `OutlineElement`, `Image`, `Table`, `TableRow`, `TableCell`)
  - `FirstChild`, `LastChild`
  - `AppendChildLast(node)`, `AppendChildFirst(node)`, `InsertChild(index, node)`, `RemoveChild(node)`
  - `GetEnumerator()` / iteration `for child in node: ...`
  - `GetChildNodes(Type) -> list[Type]` — recursive search by type

### 🏗️ Document structure

- `Page`
  - `Title: Title | None`
  - `Author: str | None`
  - `CreationTime: datetime | None`, `LastModifiedTime: datetime | None`
  - `Level: int | None`
  - `Clone(deep=False) -> Page` (minimal clone)

- `Title`
  - `TitleText: RichText | None`
  - `TitleDate: RichText | None`
  - `TitleTime: RichText | None`

- `Outline`
  - `HorizontalOffset`, `VerticalOffset`, `MaxWidth`
  - `MaxHeight`, `MinWidth`, `ReservedWidth`, `IndentPosition`
  - `DescendantsCannotBeMoved`, `LastModifiedTime`

- `OutlineElement`
  - `NumberList: NumberList | None`

### 📝 Content

- `RichText(Node)`
  - `Text: str`
  - `TextRuns: list[TextRun]` — formatted segments
  - `ParagraphStyle: ParagraphStyle`
  - `Length: int`
  - `Alignment: HorizontalAlignment | None`
  - `Tags: list[NoteTag]`
  - `Append(text, style=None) -> RichText`
  - `Replace(old_value, new_value) -> RichText`
  - `IndexOf(...) -> int`

- `TextRun`
  - `Text: str`
  - `Style: TextStyle`

- `ParagraphStyle`
  - default paragraph-level text formatting used by `RichText.ParagraphStyle`

- `TextStyle`
  - `IsBold/IsItalic/IsUnderline/IsStrikethrough/IsSuperscript/IsSubscript: bool`
  - `IsHidden: bool`, `IsMathFormatting: bool`
  - `FontName: str | None`, `FontSize: float | None`
  - `FontColor: int | None`, `Highlight: int | None`
  - `Language: int | None`
  - `FontStyle: int`
  - `IsHyperlink: bool`, `HyperlinkAddress: str | None`

- `Image`
  - `FileName: str | None`, `Bytes: bytes`
  - `Width: float | None`, `Height: float | None`
  - `AlternativeTextTitle: str | None`, `AlternativeTextDescription: str | None`
  - `HyperlinkUrl: str | None`
  - `Tags: list[NoteTag]`
  - `Replace(image) -> None` — replace image contents

- `AttachedFile(Node)`
  - `FileName: str | None`, `Bytes: bytes`
  - `Tags: list[NoteTag]`

- `Table`
  - `Columns: list[TableColumn]`
  - `IsBordersVisible: bool`
  - `Tags: list[NoteTag]`

- `TableColumn`
  - `Width: float | None`
  - `LockedWidth: bool`

- `TableRow`, `TableCell`

- `NoteTag`
  - `Label`, `Icon`, `Status`, `Highlight`, `CreationTime`, `CompletedTime`, `FontColor`
  - `CreateYellowStar()`, `CreateQuestionMark()` — convenience factories

- `NumberList`
  - `Format: str | None`, `NumberFormat: str | None`
  - `Font: str | None`, `FontSize: float | None`, `FontColor: int | None`
  - `IsBold: bool`, `IsItalic: bool`, `Restart: int | None`
  - `GetNumberedListHeader(number) -> str`

### ⚙️ Load/save options

- `LoadOptions`
  - `DocumentPassword: str | None` (password/encryption is **not supported**)
  - `LoadHistory: bool`

- `aspose.note.saving.SaveOptions` (base)
  - abstract compatibility base type
  - `SaveFormat: SaveFormat`
  - `PageIndex: int`, `PageCount: int | None`, `FontsSubsystem`

- `aspose.note.saving.PdfSaveOptions(SaveOptions)` (subset)
  - `PageIndex: int`, `PageCount: int | None`
  - `ImageCompression`, `JpegQuality`, `PageSettings`, `PageSplittingAlgorithm`

### 🔢 Enums

- `SaveFormat`: `Pdf`
- `FileFormat`: `OneNote2010`, `OneNoteOnline`, `OneNote2007`
- `HorizontalAlignment`: `Left`, `Center`, `Right`
- `NodeType`: `Document`, `Page`, `Outline`, `OutlineElement`, `RichText`, `Image`, `Table`, `AttachedFile`

### 🚨 Exceptions

- `FileCorruptedException`
- `IncorrectDocumentStructureException`
- `IncorrectPasswordException`
- `UnsupportedFileFormatException` (has a `FileFormat` field)
- `UnsupportedSaveFormatException`

## 📚 MS OneNote Examples

More runnable scripts are available in [examples/](examples/) (MS OneNote `.one` samples).

### 📝 Extract all text from an MS OneNote document

```python
from aspose.note import Document, RichText

doc = Document("testfiles/FormattedRichText.one")
texts = [rt.Text for rt in doc.GetChildNodes(RichText)]
print("\n".join(texts))
```

### 🖼️ Save all images from an MS OneNote document to disk

```python
from aspose.note import Document, Image

doc = Document("testfiles/3ImagesWithDifferentAlignment.one")
for i, img in enumerate(doc.GetChildNodes(Image), start=1):
    name = img.FileName or f"image_{i}.bin"
    with open(name, "wb") as f:
        f.write(img.Bytes)
```

### 🏷️📄 Export an MS OneNote document to PDF

```python
from aspose.note import Document, SaveFormat
from aspose.note.saving import PdfSaveOptions

doc = Document("testfiles/TagSizes.one")
opts = PdfSaveOptions(
  JpegQuality=90,
)
doc.Save("out.pdf", opts)
```

### 📦 Load an MS OneNote document from a binary stream

```python
from pathlib import Path
from aspose.note import Document

one_path = Path("testfiles/SimpleTable.one")
with one_path.open("rb") as f:
  doc = Document(f)

print(doc.DisplayName)
print(len(list(doc)))
```

### 🧭 Traverse MS OneNote document structure (DOM) and print a simple outline

```python
from aspose.note import Document, Page, Outline, OutlineElement, RichText

doc = Document("testfiles/SimpleTable.one")

for page in doc.GetChildNodes(Page):
  title = page.Title.TitleText.Text if page.Title and page.Title.TitleText else "(no title)"
  print(f"# {title}")

  for outline in page.GetChildNodes(Outline):
    for oe in outline.GetChildNodes(OutlineElement):
      # OutlineElement may contain RichText, Table, Image, etc.
      texts = [rt.Text for rt in oe.GetChildNodes(RichText)]
      if texts:
        print("-", " ".join(t.strip() for t in texts if t.strip()))
```

### 🔎 Count MS OneNote DOM nodes with `DocumentVisitor`

```python
from aspose.note import Document, DocumentVisitor, Page, Image, RichText


class Counter(DocumentVisitor):
  def __init__(self) -> None:
    self.pages = 0
    self.rich_texts = 0
    self.images = 0

  def VisitPageStart(self, page: Page) -> None:  # noqa: N802
    self.pages += 1

  def VisitRichTextStart(self, rich_text: RichText) -> None:  # noqa: N802
    self.rich_texts += 1

  def VisitImageStart(self, image: Image) -> None:  # noqa: N802
    self.images += 1


doc = Document("testfiles/3ImagesWithDifferentAlignment.one")
counter = Counter()
doc.Accept(counter)
print(counter.pages, counter.rich_texts, counter.images)
```

### 🔗 Extract hyperlinks from formatted text in an MS OneNote document

```python
from aspose.note import Document, RichText

doc = Document("testfiles/FormattedRichText.one")
for rt in doc.GetChildNodes(RichText):
  for run in rt.TextRuns:
    if run.Style.IsHyperlink and run.Style.HyperlinkAddress:
      print(run.Text, "->", run.Style.HyperlinkAddress)
```

### 🏷️ Inspect MS OneNote tags (NoteTag) across the document

```python
from aspose.note import Document, RichText, Image, Table

doc = Document("testfiles/TagSizes.one")

def dump_tags(kind: str, tags) -> None:
  for t in tags:
    print(kind, "tag:", t.Label, t.Icon)

for rt in doc.GetChildNodes(RichText):
  dump_tags("RichText", rt.Tags)

for img in doc.GetChildNodes(Image):
  dump_tags("Image", img.Tags)

for tbl in doc.GetChildNodes(Table):
  dump_tags("Table", tbl.Tags)
```

### 🧱 Work with tables in an MS OneNote document (rows/cells)

```python
from aspose.note import Document, Table, TableRow, TableCell, RichText

doc = Document("testfiles/SimpleTable.one")

for table in doc.GetChildNodes(Table):
  print("Table columns:", [column.Width for column in table.Columns])
  for row_index, row in enumerate(table.GetChildNodes(TableRow), start=1):
    cells = row.GetChildNodes(TableCell)
    values: list[str] = []
    for cell in cells:
      cell_text = " ".join(rt.Text for rt in cell.GetChildNodes(RichText)).strip()
      values.append(cell_text)
    print(f"Row {row_index}:", values)
```

### 📎 Extract attached files from an MS OneNote document

```python
from aspose.note import Document, AttachedFile

doc = Document("testfiles/OnePageWithFile.one")

for i, af in enumerate(doc.GetChildNodes(AttachedFile), start=1):
  name = af.FileName or f"attachment_{i}.bin"
  with open(name, "wb") as f:
    f.write(af.Bytes)
  print("saved:", name)
```

### 🔢 Inspect numbered lists in an MS OneNote document

```python
from aspose.note import Document, OutlineElement

doc = Document("testfiles/NumberedListWithTags.one")

for oe in doc.GetChildNodes(OutlineElement):
  nl = oe.NumberList
  if nl is None:
    continue
  print(
    "format=", nl.Format,
    "number_format=", nl.NumberFormat,
    "restart=", nl.Restart,
  )
```

## ⚠️ Current limitations

- The implementation focuses on **reading** `.one` and building a DOM; writing back to `.one` is not implemented.
- `DocumentPassword` / encrypted documents are not supported (raises `IncorrectPasswordException`).
- Saving formats other than PDF (HTML/images/ONE) are declared for compatibility but not implemented.

## 🌐 Other platforms (official Aspose.Note)

If you need the full-featured Aspose product (writing/conversion, broader compatibility, etc.), see the official libraries:

- Aspose.Note for .NET
  - Product: https://products.aspose.com/note/net/
  - Documentation: https://docs.aspose.com/note/net/

- Aspose.Note for Java
  - Product: https://products.aspose.com/note/java/
  - Documentation: https://docs.aspose.com/note/java/

## 🛠️ Development

Run tests:

```bash
python -m pip install -e ".[pdf]"
python -m pytest -q
```

Third-party license notices (e.g., ReportLab used for PDF export) are in [THIRD_PARTY_NOTICES.md](https://github.com/aspose-note/aspose-note-python/blob/main/THIRD_PARTY_NOTICES.md).
