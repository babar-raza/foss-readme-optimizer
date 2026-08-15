# Adapted from aspose.org: reports/repo-presenter/_scratch/fix_pdf_net_table.py @ 7f72da4e1423546104b40fa8cebf5b9ae3ce9c91
# Imported under the authorization recorded in
# plans/investigations/evidence/imported-corpus-v1/licensing-resolution-state.md

import re
from pathlib import Path

SP = Path("C:/Users/prora/AppData/Local/Temp/claude/d--onedrive-Documents-GitHub-aspose-org/d0a4bedb-b896-46f0-a8d1-513863007d0b/scratchpad")

FIXES = {
"BorderPartStyle": "HTML-converter border-style descriptor: width in points, `Color`, and `LineType` (solid/dashed/dotted/etc.) for one edge of an HTML table/element border.",
"DocumentCollection": "Enumerable collection of `Document` instances; `GetEnumerator()` throws `NotImplementedException` in this edition (see Scope and Limitations).",
"InterruptMonitor": "Cooperative cancellation handle whose `Interrupt()` method is a no-op stub in this edition.",
"InvalidFormTypeOperationException": "Thrown when an operation is attempted on the wrong form type (e.g. an XFA-only operation on an AcroForm, or vice versa).",
"InvalidPasswordException": "Thrown when a password-protected operation is attempted without supplying a valid password (e.g. reading `HasEditPassword` on an encrypted PDF whose open password has not been provided).",
"LaunchActionOperationConverter": "Static helper exposing the raw \"open\"/\"print\" operation strings used by `LaunchAction` and converting a `LaunchActionOperation` value to its string form.",
"Layer": "A PDF layer (Optional Content Group) exposed through `Page.Layers`; either freshly constructed and populated via `Contents`, or bound to an existing optional-content group whose visibility, lock state, and contents round-trip through that group.",
"LoadOptions": "Base load-configuration type (warning handler, font-license-verification toggle, source `LoadFormat`) shared by format-specific load-options classes such as `HtmlLoadOptions`.",
"PdfSaveOptions": "PDF-specific save configuration: default fallback font name (`DefaultFontName`) and a temp-file path (`TempPath`) used for save-time artifacts.",
"ProgressEventHandlerInfo": "Progress-event payload (document ID, `ProgressEventType`, current/maximum value) delivered to `UnifiedSaveOptions.ConversionProgressEventHandler` during conversion.",
"ResourceLoadingResult": "Result returned by an HTML `LoadOptions.ResourceLoadingStrategy` callback: the resolved resource bytes plus optional encoding, MIME type, and load-cancellation/exception info.",
"ResourceSavingInfo": "Per-resource callback payload used during save (content stream/bytes, proposed file name, resource kind) that lets the caller cancel emitting the resource.",
"SvgImageSavingInfo": "Payload passed to `SvgSaveOptions.EmbeddedImagesSavingStrategy`: the embedded image's stream, proposed file name, and image-format hint.",
"UnifiedSaveOptions": "Shared save configuration for the unified HTML/SVG/Markdown-family converters: OCR-sublayer extraction, multithreading flag, and adjacent-background-image merging.",
"UnsupportedFontTypeException": "Thrown when a file cannot be opened as a font because its format is not a supported font program (e.g. an Adobe Font Metrics file supplied on its own, with no accompanying outline data).",
"WarningInfo": "A single warning raised during load/save: its `WarningType` category and message text, delivered to an `IWarningCallback`.",
"IWarningCallback": "Callback interface invoked with a `WarningInfo` during load/save, returning a `ReturnAction` (continue/abort) to the caller.",
"GoToAction": "Action that navigates the viewer to an explicit destination, a page, or a named destination within the document (`/GoTo`).",
"JavascriptAction": "Action that carries a JavaScript source string to run when triggered (`/JavaScript`).",
"LaunchAction": "Action that launches an external file, optionally in a new viewer window (`/Launch`).",
"UriAction": "Action that opens a URI when triggered (`/URI`).",
"BleedMarkAnnotation": "Printer's bleed-mark annotation placed at a page corner (`/PrinterMark` subtype); position is stored only, not rendered.",
"CaretAnnotation": "Markup annotation showing where text or graphics have been inserted (`/Caret`).",
"CircleAnnotation": "Elliptical markup annotation inscribed within its bounding rectangle (`/Circle`).",
"ExplicitDestination": "Represents an explicit destination in a PDF document (e.g. `[page /Fit]`, `[page /XYZ left top zoom]`).",
"FixedPrint": "Print-scaling metadata for a rich-media/screen annotation appearance: a transform `Matrix` plus horizontal/vertical translation.",
"FreeTextAnnotation": "Markup annotation that displays text directly on the page without a separate popup window (`/FreeText`).",
"InkAnnotation": "Markup annotation representing one or more freehand \"ink\" strokes (`/Ink`).",
"LineAnnotation": "Markup annotation drawing a straight line between two points, with optional line-ending styles (`/Line`).",
"LinkAnnotation": "Annotation representing a clickable hyperlink region on a page (`/Link`).",
"MarkupAnnotation": "Common base for annotations that support a title, subject, reply thread, and popup window (e.g. highlight, ink, line, stamp, text).",
"MovieAnnotation": "Annotation that plays a movie file when activated (`/Movie`).",
"PDF3DAnnotation": "Annotation embedding interactive 3D artwork (`/3D`); exposes the artwork/activation surface (see Scope and Limitations for rendering support).",
"PageInformationAnnotation": "Printer-mark annotation that renders the source file name and page metadata onto the page at save time (`/PrinterMark` subtype).",
"PolygonAnnotation": "Markup annotation drawing a closed multi-sided shape (`/Polygon`).",
"PolylineAnnotation": "Markup annotation drawing an open multi-segment line (`/PolyLine`).",
"PopupAnnotation": "Popup-window annotation associated with a markup annotation's comment (`/Popup`).",
"RegistrationMarkAnnotation": "Printer's registration-mark annotation placed at a page side (`/PrinterMark` subtype); position is stored only.",
"RichMediaAnnotation": "Annotation embedding rich media (video/Flash/3D) content (`/RichMedia`).",
"SoundAnnotation": "Annotation that plays an embedded sound when activated (`/Sound`), backed by a `SoundData` sample.",
"SoundData": "Raw audio sample data (bits per channel, channel count, sample rate, encoding) embedded in a `SoundAnnotation`.",
"StampAnnotation": "Markup annotation displaying a rubber-stamp icon or custom appearance (`/Stamp`).",
"TextAnnotation": "\"Sticky note\" markup annotation shown as an icon that opens a popup with its text (`/Text`).",
"TrimMarkAnnotation": "Printer's trim-mark annotation placed at a page corner (`/PrinterMark` subtype); position is stored only.",
"WidgetAnnotation": "Annotation representing an interactive form field's on-page appearance (`/Widget`).",
"AlignmentType": "Horizontal-alignment selector for legacy facade APIs (e.g. `PdfPageEditor`); a type-safe enum whose only valid values are `Left`, `Center`, `Right` -- superseded by `HorizontalAlignment`.",
"PdfPrintPageInfo": "Per-page info (page number) passed to a `PdfQueryPageSettingsEventHandler` during printing.",
"VerticalAlignmentType": "Vertical-alignment selector for legacy facade APIs (e.g. `PdfPageEditor`); a type-safe enum whose only valid values are `Top`, `Center`, `Bottom` -- superseded by `VerticalAlignment`.",
"IFacade": "Base contract for the legacy Facades API: bind a source document (`Document`, file path, or `Stream`) and `Close()` it.",
"ISaveableFacade": "`IFacade` extended with `Save` overloads to a file path or `Stream`.",
"CheckboxField": "AcroForm checkbox field, constructible unbound or bound to a `Document` (via `Form.Fields`).",
"ChoiceField": "AcroForm choice-field base (list box/combo box) exposing selectable options.",
"PKCS1": "Signature configuration using a raw RSA (`adbe.x509.rsa_sha1`) signature, loaded from a PFX certificate and password.",
"PKCS7": "Signature configuration using a non-detached PKCS#7/CMS (`adbe.pkcs7.sha1`) signature, loaded from a PFX certificate and password.",
"RadioButtonField": "AcroForm radio-button field -- a `ChoiceField` whose kid widgets are populated via `AddOption`.",
"BitmapInfo": "Raw bitmap payload (pixel bytes, width, height, `PixelFormat`) used by the bitmap-interop layer.",
"IIndexBitmapConverter": "Interface for converting an indexed-color `Bitmap` to 1/4/8-bpp representations.",
"AnnotElement": "Tagged-PDF structure element with role `/Annot`, marking content that describes an annotation.",
"ArtElement": "Tagged-PDF structure element with role `/Art`, marking an article or other page-content grouping.",
"AttributeName": "A typed value for a standard attribute name (the `/Name`-valued entries in an attribute object, e.g. `/Placement /Block`), implemented as a set of singletons so callers can compare by reference.",
"BibEntryElement": "Tagged-PDF structure element with role `/BibEntry`, marking a bibliography entry.",
"BlockQuoteElement": "Tagged-PDF structure element with role `/BlockQuote`, marking an extended quotation.",
"CaptionElement": "Tagged-PDF structure element with role `/Caption`, marking a table or figure caption.",
"CodeElement": "Tagged-PDF structure element with role `/Code`, marking a computer-code fragment.",
"DivElement": "Tagged-PDF structure element with role `/Div`, a generic block-level grouping.",
"FigureElement": "Tagged-PDF structure element with role `/Figure`; can bind a raster/vector image via `SetImage`.",
"FormElement": "Tagged-PDF structure element with role `/Form`, marking an interactive form field's content.",
"FormulaElement": "Tagged-PDF structure element with role `/Formula`; can bind a raster/vector image via `SetImage`.",
"HeaderElement": "Tagged-PDF heading structure element with role `/H` or a leveled `/H1`-`/H6`.",
"IndexElement": "Tagged-PDF structure element with role `/Index`, marking an index list.",
"LinkElement": "Tagged-PDF structure element with role `/Link`; stores a `Hyperlink` target and `AlternateDescriptions` for the link.",
"ListElement": "Tagged-PDF structure element with role `/L`, marking a list.",
"ListLBodyElement": "Tagged-PDF structure element with role `/LBody`, marking a list item's body.",
"ListLIElement": "Tagged-PDF structure element with role `/LI`, marking a list item.",
"ListLblElement": "Tagged-PDF structure element with role `/Lbl`, marking a list-item label.",
"NoteElement": "Tagged-PDF structure element with role `/Note`, marking a footnote or endnote.",
"ParagraphElement": "Tagged-PDF structure element with role `/P`, marking a paragraph.",
"PartElement": "Tagged-PDF structure element with role `/Part`, marking a large document division.",
"PrivateElement": "Tagged-PDF structure element with role `/Private`, marking application-private content excluded from standard structure semantics.",
"QuoteElement": "Tagged-PDF structure element with role `/Quote`, marking an inline quotation.",
"ReferenceElement": "Tagged-PDF structure element with role `/Reference`, marking a cross-reference.",
"RubyElement": "Tagged-PDF structure element with role `/Ruby`, marking East-Asian ruby (phonetic guide) text.",
"TOCElement": "Tagged-PDF structure element with role `/TOC`, marking a table of contents.",
"TOCIElement": "Tagged-PDF structure element with role `/TOCI`, marking a table-of-contents item.",
"TableElement": "Tagged-PDF structure element with role `/Table`; carries table-level layout style (borders, alignment, repeating rows/columns) and `CreateTBody`/`CreateTHead`/`CreateTFoot` helpers.",
"TableTBodyElement": "Tagged-PDF structure element with role `/TBody`, marking a table body section; `CreateTR` appends a row.",
"TableTFootElement": "Tagged-PDF structure element with role `/TFoot`, marking a table footer section; `CreateTR` appends a row.",
"TableTHElement": "Tagged-PDF structure element with role `/TH`, a table header cell; carries cell-level style (borders, alignment, span).",
"TableTHeadElement": "Tagged-PDF structure element with role `/THead`, marking a table header section; `CreateTR` appends a row.",
"TableTRElement": "Tagged-PDF structure element with role `/TR`, a table row; carries row-level style and `CreateTD`/`CreateTH` helpers.",
"WarichuElement": "Tagged-PDF structure element with role `/Warichu`, marking Japanese warichu (split annotative) text.",
"OutlineCollection": "Enumerable collection of a document's top-level `OutlineItemCollection` bookmarks (`Document.Outlines`).",
"PaperSize": "Named paper size (name, width, height, kind) used by the legacy printing facades.",
"ICustomSecurityHandler": "Pluggable custom security handler -- implement this to handle non-Standard `/Filter` entries (e.g. Public-Key handlers `/Adobe.PPKLite`); the built-in Standard handler covers RC4/AES password encryption without one.",
"CustomFontSubstitutionBase": "Base type for a custom font-substitution rule; override `TrySubstitute` to supply a replacement `Font` for an unresolved `OriginalFontSpecification`.",
"FontSubstitutionCollection": "Read-only, indexable collection of `FontSubstitution` rules consulted when resolving a missing font.",
"OriginalFontSpecification": "Describes the font a substitution rule is asked to replace: its name, whether it was embedded, and whether substitution is unavoidable.",
"Position": "A text fragment's X/Y indent position, tracking whether it was explicitly set by the caller versus left at its constructed default.",
"SimpleFontSubstitution": "Font-substitution rule that maps one exact original font name to one substitution font name, optionally forced by save-option configuration.",
"XFormPlacement": "Empty internal marker type passed when cloning a vector `GraphicElement` into an XForm context; carries no data in this edition.",
}

lines = (SP / "pdf_net_table.md").read_text(encoding="utf-8").splitlines()
row_re = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|(?:\s*<<<(GENERIC|TRUNCATED|STRIPPED_EXAMPLE))?\s*$")

out = []
fixed_count = 0
unmatched = []
for line in lines:
    m = row_re.match(line)
    if m and m.group(3):
        cls = m.group(1)
        if cls in FIXES:
            out.append(f"| `{cls}` | {FIXES[cls]} |")
            fixed_count += 1
        else:
            unmatched.append(cls)
            out.append(line)
    else:
        out.append(line)

(SP / "pdf_net_table_fixed.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("fixed:", fixed_count, "unmatched flagged:", unmatched, "total FIXES keys:", len(FIXES))
