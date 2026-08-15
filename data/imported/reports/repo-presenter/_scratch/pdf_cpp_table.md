### Core API

| Class | Description |
|---|---|
| `Artifact` | Class with 14 methods. | <<<GENERIC
| `ArtifactCollection` | Class with 7 methods and 1 property. | <<<GENERIC
| `BaseParagraph` | Class with 23 methods and 1 property. | <<<GENERIC
| `BitmapInfo` | BitmapInfo enables creation of raw bitmap images with specified pixel format, width, height, and pixel data, supporting image handling without external dependencies. |
| `BmpDevice` | Class with 1 method. | <<<GENERIC
| `BorderInfo` | Class with 10 methods. | <<<GENERIC
| `Cell` | Class with 27 methods. | <<<GENERIC
| `Cells` | Class with 9 methods. | <<<GENERIC
| `Color` | Class with 147 methods. | <<<GENERIC
| `Device` | The Device base class provides a virtual destructor, ensuring proper cleanup of derived raster‑device objects such as PngDevice or JpegDevice. |
| `Document` | Document metadata can be read via `Document.Info()` and the accessor methods `Title()`, `Author()`, `Creator()`, `Producer()`, `Subject()`, and `Keywords()`. |
| `DocumentDevice` | Class with 4 methods. | <<<GENERIC
| `DocumentInfo` | Class with 24 methods and 1 property. | <<<GENERIC
| `DocumentPrivilege` | Class with 34 methods. | <<<GENERIC
| `EmbeddedFileCollection` | Class with 9 methods. | <<<GENERIC
| `FileSpecification` | FileSpecification objects allow setting metadata for embedded files, including MIME type, description, Unicode name, and compression via the Encoding property. |
| `FloatingBox` | Class with 12 methods. | <<<GENERIC
| `Font` | The Font class lets developers query whether a font is embedded in the PDF and whether it is subsetted, enabling compliance checks for PDF/A. |
| `FontRepository` | Class with 2 methods. | <<<GENERIC
| `GraphInfo` | Class with 25 methods. | <<<GENERIC
| `Hyperlink` | Class with 6 methods and 1 property. | <<<GENERIC
| `ImageDevice` | Class with 10 methods. | <<<GENERIC
| `JpegDevice` | Class with 1 method. | <<<GENERIC
| `LoadOptions` | Class with 3 methods. | <<<GENERIC
| `MarginInfo` | MarginInfo allows precise control of page margins with double-precision getters and setters for left, right, top, and bottom values. |
| `Margins` | Class with 8 methods. | <<<GENERIC
| `Metadata` | Metadata class implements a dictionary-like interface with Add(key, value), Remove(key), and TryGetValue(key, value) for managing XMP metadata entries. |
| `NamedDestinationCollection` | Class with 6 methods and 1 property. | <<<GENERIC
| `OutlineCollection` | Class in the Pdf CPP API. | <<<GENERIC
| `OutlineItemCollection` | Class with 18 methods. | <<<GENERIC
| `Outlines` | Class with 12 methods. | <<<GENERIC
| `Page` | Page labels (e.g., Roman numerals, custom prefixes) are managed through PageLabel and PageLabelCollection classes. |
| `PageCollection` | The PageCollection class provides methods to add a new blank page, insert a page at a specific position, and delete pages by number or range. |
| `PageDevice` | PageDevice.Process(page, outputFileName) can render a page directly to a file path. |
| `PageLabel` | PageLabel.StartingValue() gets or sets the numeric start for a page label sequence. |
| `PageLabelCollection` | PageLabelCollection.GetLabel(pageIndex) retrieves the PageLabel assigned to a specific page. |
| `PageSize` | PageSize.Width() and Height() get or set the page dimensions, while IsLandscape() indicates orientation. |
| `Paragraphs` | Class with 6 methods. | <<<GENERIC
| `PngDevice` | Class with 3 methods. | <<<GENERIC
| `Point` | Class with 6 methods. | <<<GENERIC
| `Position` | The Position class provides XIndent and YIndent getters and setters to fine‑tune the horizontal and vertical offset of annotations. |
| `Rectangle-Aspose_Pdf` | Class with 28 methods. | <<<GENERIC
| `RenderingOptions` | Class with 26 methods. | <<<GENERIC
| `Resolution` | Resolution stores horizontal and vertical DPI via X() and Y() getters and setters. |
| `Resources` | Class with 3 methods and 1 property. | <<<GENERIC
| `Row` | Class with 23 methods. | <<<GENERIC
| `Rows` | Rows and Row classes provide a table model for building PDF tables with per‑cell styling, borders, and padding. |
| `SvgLoadOptions` | SvgLoadOptions allows SVG files to be imported with optional page‑size adjustment via the AdjustPageSize property. |
| `Table` | The Table class lets developers construct PDF tables with full control over rows, column widths, borders, cell padding, and default text state. |
| `TextAbsorber` | Class with 6 methods and 1 property. | <<<GENERIC
| `TextBuilder` | Class with 2 methods. | <<<GENERIC
| `TextDevice` | Class with 3 methods. | <<<GENERIC
| `TextFragment` | Class with 7 methods. | <<<GENERIC
| `TextFragmentAbsorber` | Class with 4 methods. | <<<GENERIC
| `TextFragmentCollection` | Class with 2 methods. | <<<GENERIC
| `TextFragmentState` | Class with 1 method. | <<<GENERIC
| `TextParagraph` | Class with 18 methods. | <<<GENERIC
| `TextState` | The TextState class provides getters and setters for font, font size, foreground/background/stroking colors, and text decorations such as underline, strike‑out, subscript, and superscript. |
| `TiffDevice` | Class with 11 methods. | <<<GENERIC
| `TiffSettings` | Class with 13 methods. | <<<GENERIC
| `WatermarkArtifact` | Class in the Pdf CPP API. | <<<GENERIC
| `XImage` | XImage exposes the pixel dimensions of an image via Width() and Height() methods. |
| `XImageCollection` | XImageCollection manages multiple XImage objects, providing Add, Replace, Delete, and Clear operations. |
| `XmpValue` | XmpValue provides conversion helpers: ToString(), ToInteger(), ToDouble(), ToArray(), and type‑query methods such as IsString() and IsArray(). |

#### Enumerations

| Enumeration | Description |
|---|---|
| `AFRelationship` | Enum with 7 members. |
| `BorderSide` | Enum with 7 members. |
| `ColorDepth` | Enum with 5 members. |
| `CompressionType` | Enum with 5 members. |
| `CryptoAlgorithm` | Enum with 4 members. |
| `FileEncoding` | Enum with 2 members. |
| `FormPresentationMode` | Enum with 2 members. |
| `HorizontalAlignment` | Enum with 6 members. |
| `NumberingStyle` | Enum with 6 members. |
| `PageCoordinateType` | PageCoordinateType enum values MediaBox and CropBox let developers choose which page rectangle is used for coordinate calculations. |
| `PasswordType` | Enum with 4 members. |
| `PdfFormat` | Enum with 27 members. |
| `Permissions` | Enum with 8 members. |
| `Rotation` | Rotation enum provides four orientation values: None, on90, on180, on270. |
| `ShapeType` | Enum with 3 members. |
| `VerticalAlignment` | Enum with 4 members. |

### Annotations

| Class | Description |
|---|---|
| `Annotation` | Class with 36 methods. | <<<GENERIC
| `AnnotationCollection` | Class with 11 methods. | <<<GENERIC
| `AnnotationSelector` | Class with 35 methods and 1 property. | <<<GENERIC
| `BleedMarkAnnotation` | BleedMarkAnnotation.Accept(visitor) implements the visitor pattern, allowing external visitor objects to process the annotation without exposing its internal structure. |
| `Border` | Border appearance can be customized by setting its Width, Style, Effect, EffectIntensity, and corner radii via the Border class methods. |
| `CaretAnnotation` | Class with 5 methods. | <<<GENERIC
| `Characteristics` | Class with 3 methods. | <<<GENERIC
| `CircleAnnotation` | Class with 1 method. | <<<GENERIC
| `ColorBarAnnotation` | Class with 3 methods. | <<<GENERIC
| `CommonFigureAnnotation` | Class with 5 methods. | <<<GENERIC
| `CornerPrinterMarkAnnotation` | Class with 2 methods. | <<<GENERIC
| `DefaultAppearance` | Class with 8 methods. | <<<GENERIC
| `ExplicitDestination` | Class with 3 methods. | <<<GENERIC
| `FileAttachmentAnnotation` | FileAttachmentAnnotation.File() gets or sets the attached file via a FileSpecification object, allowing embedding of external resources in a PDF. |
| `FitBExplicitDestination` | Class with 1 method. | <<<GENERIC
| `FitBHExplicitDestination` | Class with 2 methods. | <<<GENERIC
| `FitBVExplicitDestination` | Class with 2 methods. | <<<GENERIC
| `FitExplicitDestination` | Class with 1 method. | <<<GENERIC
| `FitHExplicitDestination` | Class with 2 methods. | <<<GENERIC
| `FitRExplicitDestination` | Class with 5 methods. | <<<GENERIC
| `FitVExplicitDestination` | Class with 2 methods. | <<<GENERIC
| `FreeTextAnnotation` | Class with 23 methods. | <<<GENERIC
| `GoToAction` | Class with 4 methods. | <<<GENERIC
| `GoToURIAction` | Class with 4 methods. | <<<GENERIC
| `HighlightAnnotation` | Class with 1 method. | <<<GENERIC
| `InkAnnotation` | InkAnnotation represents free‑hand ink strokes; its InkList property holds a StrokeList that can be read or replaced. |
| `JavascriptAction` | JavascriptAction encapsulates a JavaScript snippet attached to PDF objects; the script can be retrieved or updated via Script() getter/setter. |
| `LineAnnotation` | Class with 25 methods. | <<<GENERIC
| `LinkAnnotation` | LinkAnnotation enables clickable areas in a PDF that can trigger a PdfAction or navigate to a named destination. |
| `MarkupAnnotation` | MarkupAnnotation provides methods to set review state, opacity, title, and rich text for comment‑type annotations. |
| `MovieAnnotation` | MovieAnnotation lets you embed a video file in a PDF, with properties for title, poster flag, aspect ratio, and rotation. |
| `NamedAction` | Class with 3 methods. | <<<GENERIC
| `NamedDestination` | Class with 2 methods. | <<<GENERIC
| `PageInformationAnnotation` | Class with 1 method. | <<<GENERIC
| `PdfAction` | PdfAction.GetECMAScriptString() returns the JavaScript code attached to a PDF action, enabling inspection or modification of interactive scripts. |
| `PolyAnnotation` | Class with 11 methods. | <<<GENERIC
| `PolygonAnnotation` | Class with 1 method. | <<<GENERIC
| `PolylineAnnotation` | Class with 1 method. | <<<GENERIC
| `PopupAnnotation` | Class with 5 methods. | <<<GENERIC
| `PrinterMarkAnnotation` | PrinterMarkAnnotation can insert printer marks such as trim, bleed, registration, or colour bars into an entire document or a single page via AddPrinterMarks. |
| `RedactionAnnotation` | RedactionAnnotation lets you permanently remove content while optionally overlaying custom text, fill colour, border colour and font size. |
| `RegistrationMarkAnnotation` | Class with 3 methods. | <<<GENERIC
| `RichMediaAnnotation` | RichMediaAnnotation enables embedding of Flash or other rich media with activation events and custom variables. |
| `ScreenAnnotation` | Class with 3 methods. | <<<GENERIC
| `SoundAnnotation` | Class with 3 methods. | <<<GENERIC
| `SquareAnnotation` | Class with 1 method. | <<<GENERIC
| `SquigglyAnnotation` | Class with 1 method. | <<<GENERIC
| `StampAnnotation` | Class with 5 methods. | <<<GENERIC
| `StrikeOutAnnotation` | Class with 1 method. | <<<GENERIC
| `SubmitFormAction` | Class with 5 methods. | <<<GENERIC
| `TextAnnotation` | Class with 5 methods. | <<<GENERIC
| `TextMarkupAnnotation` | Class with 4 methods. | <<<GENERIC
| `TextStyle` | Class with 9 methods. | <<<GENERIC
| `TrimMarkAnnotation` | TrimMarkAnnotation and UnderlineAnnotation both support the visitor pattern via an Accept method that forwards the annotation to a visitor object. |
| `UnderlineAnnotation` | Class with 1 method. | <<<GENERIC
| `WatermarkAnnotation` | WatermarkAnnotation enables adding a visual watermark to a PDF page and lets developers control its transparency. |
| `WidgetAnnotation` | WidgetAnnotation provides access to AcroForm field attributes such as ReadOnly, Required, Exportable, and DefaultAppearance. |
| `XYZExplicitDestination` | XYZExplicitDestination supplies explicit page view coordinates via Left(), Top() and Zoom() methods. |

#### Enumerations

| Enumeration | Description |
|---|---|
| `AnnotationFlags` | AnnotationFlags enum includes a Locked flag that, when set, prevents further modifications to the annotation's properties. |
| `AnnotationState` | Enum with 7 members. |
| `AnnotationStateModel` | Enum with 3 members. |
| `AnnotationType` | Enum with 33 members. |
| `BorderEffect` | Enum with 2 members. |
| `BorderStyle` | Enum with 5 members. |
| `CapStyle` | Enum with 2 members. |
| `CaptionPosition` | Enum with 2 members. |
| `CaretSymbol` | Enum with 2 members. |
| `ColorsOfCMYK` | Enum with 4 members. |
| `ExplicitDestinationType` | Enum with 8 members. |
| `FileIcon` | Enum with 4 members. |
| `FreeTextIntent` | Enum with 4 members. |
| `HighlightingMode` | Enum with 5 members. |
| `Justification` | Enum with 3 members. |
| `LineEnding` | Enum with 10 members. |
| `LineIntent` | Enum with 3 members. |
| `PolyIntent` | Enum with 4 members. |
| `PredefinedAction` | Enum with 71 members. |
| `PrinterMarkCornerPosition` | Enum with 4 members. |
| `PrinterMarkSidePosition` | Enum with 4 members. |
| `PrinterMarksKind` | Enum with 7 members. |
| `ReplyType` | ReplyType enum distinguishes between Reply, Group, and Undefined reply categories. |
| `RichTextFontStyles` | Enum with 4 members. |
| `SoundIcon` | Enum with 2 members. |
| `StampIcon` | Enum with 14 members. |
| `TextAlignment` | Enum with 3 members. |
| `TextIcon` | Enum with 15 members. |

### Drawing

| Class | Description |
|---|---|
| `Circle` | Class with 7 methods. | <<<GENERIC
| `Ellipse` | Class with 9 methods. | <<<GENERIC
| `Graph` | Class with 16 methods. | <<<GENERIC
| `Line` | Class with 3 methods. | <<<GENERIC
| `Rectangle-Aspose_Pdf_Drawing` | Class with 11 methods. | <<<GENERIC
| `Shape` | Class with 4 methods. | <<<GENERIC

### Facades

| Class | Description |
|---|---|
| `AlignmentType` | Class with 4 methods. | <<<GENERIC
| `Bookmark` | Class with 35 methods. | <<<GENERIC
| `Bookmarks` | Bookmarks can be organized hierarchically; use Bookmark.ChildItem() or Bookmark.ChildItems() to access nested Bookmarks and set properties such as Action, Destination, and display flags like BoldFlag and ItalicFlag. |
| `Facade` | Facade.BindPdf overloads accept either a file path string (srcFile) or an existing Aspose::Pdf::Document (srcDoc) to load PDF content. |
| `FormEditor` | Class with 53 methods. | <<<GENERIC
| `FormFieldFacade` | Class with 30 methods and 26 properties. | <<<GENERIC
| `PdfAnnotationEditor` | PdfAnnotationEditor can import annotations from FDF or XFDF files and flatten them into the page content, removing interactive elements. |
| `PdfBookmarkEditor` | PdfBookmarkEditor.CreateBookmarkOfPage(title, pageNumber) adds a new bookmark that points to the specified page. |
| `PdfContentEditor` | PdfContentEditor.ReplaceText(srcText, destText) searches the entire document and replaces matching strings, returning true when at least one replacement occurs. |
| `PdfConverter` | Class with 37 methods. | <<<GENERIC
| `PdfExtractor` | PdfExtractor extracts text by calling ExtractText() and then GetText(outputFile) to write the extracted plain‑text to a file. |
| `PdfFileEditor` | Class with 72 methods. | <<<GENERIC
| `PdfFileInfo` | PdfFileInfo provides getters and setters for standard metadata fields such as Author, Creator, and custom keys via GetMetaInfo(name) and SetMetaInfo(name, value). |
| `PdfFileSecurity` | Class with 20 methods. | <<<GENERIC
| `PdfFileSignature` | Class with 41 methods. | <<<GENERIC
| `PdfFileStamp` | Class with 26 methods and 8 properties. | <<<GENERIC
| `PdfPageEditor` | Class with 28 methods and 16 properties. | <<<GENERIC
| `PdfXmpMetadata` | Class with 15 methods. | <<<GENERIC
| `SaveableFacade` | SaveableFacade offers a simple interface to persist PDF objects to a file path via Save(destFile). |
| `SignatureName` | SignatureName.HasSignature() returns true if the PDF contains a detached PKCS#7 signature, and ToString() provides a textual representation of the signature name. |
| `VerticalAlignmentType` | VerticalAlignmentType offers static factory methods Top(), Center(), and Bottom() to obtain alignment objects, and ToString() to obtain their textual representation. |

#### Enumerations

| Enumeration | Description |
|---|---|
| `Algorithm` | Enum with 2 members. |
| `AutoRotateMode` | Enum with 3 members. |
| `BlendingColorSpace` | Enum with 4 members. |
| `DataType` | Enum with 6 members. |
| `DefaultMetadataProperties` | Enum with 9 members. |
| `EncodingType` | Enum with 7 members. |
| `FieldType` | Enum with 13 members. |
| `FontStyle` | Enum with 16 members. |
| `ImageMergeMode` | Enum with 3 members. |
| `KeySize` | Enum with 3 members. |
| `PositioningMode` | Enum with 3 members. |
| `PropertyFlag` | Enum with 4 members. |
| `StampType` | Enum with 2 members. |
| `SubmitFormFlag` | Enum with 6 members. |
| `WordWrapMode` | WordWrapMode enum defines two text wrapping strategies: Default and ByWords. |

### Forms

| Class | Description |
|---|---|
| `BarcodeField` | Class with 6 methods. | <<<GENERIC
| `ButtonField` | Class with 11 methods. | <<<GENERIC
| `CheckboxField` | Class with 16 methods. | <<<GENERIC
| `ChoiceField` | Class with 14 methods. | <<<GENERIC
| `ComboBoxField` | Class with 5 methods. | <<<GENERIC
| `DateField` | Class with 4 methods. | <<<GENERIC
| `DocMDPSignature` | Class with 1 method. | <<<GENERIC
| `ExternalSignature` | Class in the Pdf CPP API. | <<<GENERIC
| `Field` | Field.Recalculate() recomputes the value of a form field and returns true on success. |
| `FileSelectBoxField` | Class with 1 method. | <<<GENERIC
| `Form` | Form text box fields can have a barcode added programmatically by calling `AddBarcode(code)` on a `TextBoxField` instance. |
| `IconFit` | IconFit allows fine‑grained control of form field scaling; developers can set ScalingReason, ScalingMode, and leftover margins before rendering. |
| `ListBoxField` | Class with 3 methods. | <<<GENERIC
| `NumberField` | Class with 3 methods. | <<<GENERIC
| `Option` | Class with 8 methods. | <<<GENERIC
| `OptionCollection` | Class with 9 methods. | <<<GENERIC
| `PKCS1` | Class with 1 method. | <<<GENERIC
| `PKCS7` | Class with 1 method. | <<<GENERIC
| `PKCS7Detached` | Class with 1 method. | <<<GENERIC
| `PasswordBoxField` | Class with 1 method. | <<<GENERIC
| `RadioButtonField` | Class with 7 methods. | <<<GENERIC
| `RadioButtonOptionField` | Class with 5 methods. | <<<GENERIC
| `RichTextBoxField` | RichTextBoxField provides a form field that stores rich text with styling, justification, and formatted value. |
| `Signature` | Signature objects allow creation and verification of detached PKCS#7 signatures on PDF documents. |
| `SignatureCustomAppearance` | Class with 37 methods. | <<<GENERIC
| `SignatureField` | Class with 2 methods. | <<<GENERIC
| `TextBoxField` | Class with 15 methods. | <<<GENERIC
| `XFA` | XFA provides access to XML‑based XFA form data; calling FieldNames() yields a list of all field identifiers present in the XFA document. |

#### Enumerations

| Enumeration | Description |
|---|---|
| `BoxStyle` | Enum with 6 members. |
| `DocMDPAccessPermissions` | The DocMDPAccessPermissions enum defines the allowed modifications on a signed PDF: NoChanges prevents any edits, FillingInForms allows form filling, and AnnotationModification permits annotation changes. |
| `FormType` | Enum with 3 members. |
| `IconCaptionPosition` | Enum with 7 members. |
| `ScalingMode` | ScalingMode enum defines Proportional and Anamorphic scaling options for image transformations. |
| `ScalingReason` | ScalingReason enum indicates when scaling should be applied: Always, IconIsBigger, IconIsSmaller, or Never. |
| `SubjectNameElements` | Enum with 7 members. |
| `Symbology` | Enum with 3 members. |

