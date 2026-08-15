# Aspose.Slides FOSS for .NET

[![Build](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET/actions/workflows/ci.yml/badge.svg)](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET/blob/main/LICENSE) [![Contributors](https://img.shields.io/github/contributors/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET.svg)](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET/graphs/contributors) [![Issues](https://img.shields.io/github/issues/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET.svg)](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET/issues)

[![Aspose.Slides FOSS for .NET](https://products.aspose.org/media/slides/net/banner-readme.png)](https://products.aspose.org/slides/net/)

Aspose.Slides FOSS for .NET is the official open-source .NET library by Aspose.Slides for
creating, reading, and editing PowerPoint (`.pptx`) presentations. It is a MIT-licensed, pure-C#
library with no native extensions to compile and no dependency on Microsoft Office, COM
automation, or any proprietary runtime. It requires .NET 9.0 or later.

## Navigation

- [At a Glance](#at-a-glance)
- [Key Capabilities](#key-capabilities)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Additional Examples](#additional-examples)
- [API Reference](#api-reference)
- [Documentation & Resources](#documentation--resources)
- [Scope and Limitations](#scope-and-limitations)
- [Development and Testing](#development-and-testing)
- [License](#license)

## At a Glance

```mermaid
flowchart TD
  subgraph StartingPoints["Starting Points"]
    direction TB
    i1["An existing PPTX presentation"]
  end
  PRODUCT["Aspose.Slides FOSS for .NET"]
  subgraph Capabilities["Core Capabilities"]
    direction LR
    subgraph capl[" "]
      direction TB
      c1["Presentation I/O"]
      c2["Slides"]
      c3["Shapes"]
      c4["Text"]
      c5["Fill"]
      c6["Lines"]
      c7["Effects"]
    end
    subgraph capr[" "]
      direction TB
      c8["3D"]
      c9["Document properties"]
      c10["Notes slides"]
      c11["Comments"]
      c12["Images"]
      c13["Round-trip safety"]
    end
  end
  subgraph Outputs["Outputs"]
    direction TB
    o1["PPTX presentation files"]
  end
  StartingPoints --> PRODUCT --> Capabilities --> Outputs
```

## Key Capabilities

Features cover the full authoring surface — from presentation I/O and shape creation to fill,
line, and 3D formatting, notes, comments, and document properties.

- **Presentation I/O** — Open, create, and save `.pptx` files with full round-trip fidelity.
- **Slides** — Add, remove, clone, reorder, and iterate slides via `SlideCollection`.
- **Shapes** — AutoShapes, PictureFrames, Tables, and Connectors.
- **Text** — `TextFrame`, `Paragraph`, and `Portion` with character-, paragraph-, and text-frame-level formatting (including bullets).
- **Fill and line formatting** — Solid, gradient, pattern, and picture fills; configurable line width, dash style, arrows, join style, and alignment.
- **Effects** — Outer shadow, glow, soft edge, blur, reflection, and inner shadow.
- **3D** — Bevel, camera, light rig, material, and extrusion depth.
- **Document properties** — Core, app, and custom properties.
- **Notes and comments** — Per-slide speaker notes with header/footer management, and threaded comments with authors, timestamps, and positions.
- **Images** — Embed from file, bytes, or stream.
- **Round-trip safety** — Unknown XML parts encountered during load are preserved verbatim on save, so opening and re-saving a file never strips content this library does not yet understand.

## Installation

A NuGet package has not been published yet. Build from source:

```bash
git clone https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET.git
cd Aspose.Slides-FOSS-for-.NET
dotnet build Aspose.Slides.Foss.sln -c Release
```

Then add a project reference to `src/Aspose.Slides.Foss/Aspose.Slides.Foss.csproj` from your own
application. The library requires .NET 9.0 or later and has no native extensions to compile.

## Quick Start

```csharp
using Aspose.Slides.Foss;
using Aspose.Slides.Foss.Export;

// Open an existing presentation
using var prs = new Presentation("input.pptx");
Console.WriteLine($"Slides: {prs.Slides.Count}");
prs.Save("output.pptx", SaveFormat.Pptx);

// Create a new presentation
using var newPrs = new Presentation();
var slide = newPrs.Slides[0];
newPrs.Save("new.pptx", SaveFormat.Pptx);
```

Always wrap a `Presentation` in a `using` statement so its resources are reliably freed.

## Additional Examples

The usage examples below build directly on the Quick Start snippet above, covering shapes,
text formatting, tables, connectors, fills, effects, notes, comments, document properties, and
slide operations.

### Add a Shape

`AddAutoShape()` takes a `ShapeType` enum, then x/y position and width/height in points (1 point
= 1/72 inch). Call `AddTextFrame()` to create the text frame and set its initial text in one
call — the frame is `null` until `AddTextFrame()` is called.

```csharp
using Aspose.Slides.Foss;
using Aspose.Slides.Foss.Export;

using var prs = new Presentation();
var slide = prs.Slides[0];
var shape = slide.Shapes.AddAutoShape(ShapeType.Rectangle, 50, 50, 300, 100);
shape.AddTextFrame("Hello, world!");
prs.Save("shapes.pptx", SaveFormat.Pptx);
```

<details>
<summary>View Additional Examples</summary>

### Text Formatting

Text formatting works at the `Portion` level — the smallest unit of a run of characters.

```csharp
using Aspose.Slides.Foss;
using Aspose.Slides.Foss.Drawing;
using Aspose.Slides.Foss.Export;

using var prs = new Presentation();
var shape = prs.Slides[0].Shapes.AddAutoShape(ShapeType.Rectangle, 50, 50, 400, 150);
var tf = shape.AddTextFrame("Formatted text");
var fmt = tf.Paragraphs[0].Portions[0].PortionFormat;
fmt.FontHeight = 24;
fmt.FontBold = NullableBool.True;
fmt.FillFormat.FillType = FillType.Solid;
fmt.FillFormat.SolidFillColor.Color = Color.FromArgb(255, 0, 70, 127);
prs.Save("text.pptx", SaveFormat.Pptx);
```

### Table

```csharp
using Aspose.Slides.Foss;
using Aspose.Slides.Foss.Export;

using var prs = new Presentation();
var table = prs.Slides[0].Shapes.AddTable(50, 50, [120.0, 120.0, 120.0], [40.0, 40.0]);
table.Rows[0][0].TextFrame.Text = "Name";
table.Rows[0][1].TextFrame.Text = "Value";
prs.Save("table.pptx", SaveFormat.Pptx);
```

### Connector

```csharp
using Aspose.Slides.Foss;
using Aspose.Slides.Foss.Export;

using var prs = new Presentation();
var slide = prs.Slides[0];
var box1 = slide.Shapes.AddAutoShape(ShapeType.Rectangle, 50, 100, 150, 60);
var box2 = slide.Shapes.AddAutoShape(ShapeType.Rectangle, 350, 100, 150, 60);
var conn = slide.Shapes.AddConnector(ShapeType.BentConnector3, 0, 0, 10, 10);
conn.StartShapeConnectedTo = box1;
conn.StartShapeConnectionSiteIndex = 3;  // right
conn.EndShapeConnectedTo = box2;
conn.EndShapeConnectionSiteIndex = 1;    // left
prs.Save("connector.pptx", SaveFormat.Pptx);
```

### Fill

```csharp
using Aspose.Slides.Foss;
using Aspose.Slides.Foss.Drawing;
using Aspose.Slides.Foss.Export;

using var prs = new Presentation();
var shape = prs.Slides[0].Shapes.AddAutoShape(ShapeType.Rectangle, 50, 50, 300, 150);
shape.FillFormat.FillType = FillType.Solid;
shape.FillFormat.SolidFillColor.Color = Color.FromArgb(255, 30, 120, 200);
prs.Save("fill.pptx", SaveFormat.Pptx);
```

Also supports `FillType.Gradient`, `FillType.Pattern`, and `FillType.Picture`.

### Effects and 3D

```csharp
// Outer shadow
var ef = shape.EffectFormat;
ef.EnableOuterShadowEffect();
ef.OuterShadowEffect.BlurRadius = 10;
ef.OuterShadowEffect.Distance = 5;

// 3D bevel
var td = shape.ThreeDFormat;
td.BevelTop.BevelType = BevelPresetType.Circle;
td.BevelTop.Height = 6;
td.BevelTop.Width = 6;
```

### Line Formatting

```csharp
var lf = shape.LineFormat;
lf.Width = 2.5f;
lf.DashStyle = LineDashStyle.DashDot;
lf.FillFormat.FillType = FillType.Solid;
lf.FillFormat.SolidFillColor.Color = Color.Red;
```

### Notes

```csharp
using Aspose.Slides.Foss;
using Aspose.Slides.Foss.Export;

using var prs = new Presentation();
var notes = prs.Slides[0].NotesSlideManager.AddNotesSlide();
notes.NotesTextFrame.Text = "Speaker notes go here.";
prs.Save("notes.pptx", SaveFormat.Pptx);
```

### Comments

```csharp
using Aspose.Slides.Foss;
using Aspose.Slides.Foss.Drawing;
using Aspose.Slides.Foss.Export;

using var prs = new Presentation();
var author = prs.CommentAuthors.AddAuthor("Jane Smith", "JS");
var slide = prs.Slides[0];
author.Comments.AddComment("Review this slide", slide, new PointF(2.0f, 2.0f), DateTime.Now);
prs.Save("comments.pptx", SaveFormat.Pptx);
```

### Document Properties

```csharp
using Aspose.Slides.Foss;
using Aspose.Slides.Foss.Export;

using var prs = new Presentation();
prs.DocumentProperties.Title = "Q1 Results";
prs.DocumentProperties.Author = "Finance Team";
prs.DocumentProperties.SetCustomPropertyValue("Version", 3);
prs.Save("deck.pptx", SaveFormat.Pptx);
```

### Slide Operations

```csharp
prs.Slides.AddEmptySlide(prs.LayoutSlides[0]);  // add slide
prs.Slides.RemoveAt(1);                          // remove by index
var cloned = prs.Slides.AddClone(prs.Slides[0]); // clone slide
slide.Hidden = true;                              // hide slide
```

</details>

## API Reference

The library exposes a Presentation API built around `Presentation`, `Slide`, `Shape`, `TextFrame`,
`Paragraph`, and `Portion` — the conceptual model PowerPoint itself uses. The public API surface
includes 264 classes; the essentials are summarized below.

<details>
<summary>View the Supported Public API Surface (Essentials)</summary>

### Aspose.Slides.Foss

| Class | Description |
|---|---|
| `AdjustValue` | Represents a geometry shape adjustment value backed by an XML guide definition element. |
| `AdjustValueCollection` | Represents a collection of shape's adjustment values. |
| `AutoShape` | Represents an AutoShape — a preset or custom geometric shape that may contain text. |
| `BaseHandoutNotesSlideHeaderFooterManager` | Represents the base class for handout and notes slide header/footer managers. |
| `BasePortionFormat` | Common text-run formatting properties backed by an OOXML &lt;a:rPr&gt; element. |
| `BaseShapeLock` | Represents the base class for locks that determine which operations are disabled on a shape. |
| `BaseSlide` | Base class for Slide, LayoutSlide, and MasterSlide providing common slide functionality. |
| `Blur` | Represents a blur effect that is applied to the entire shape, including its fill. |
| `BulletFormat` | Manages paragraph bullet formatting backed by OOXML bullet elements. |
| `Camera` | Represents 3D camera properties for a shape. |
| `Cell` | Represents a single cell within a table in a PowerPoint presentation. |
| `CellCollection` | Represents a read-only collection of table cells associated with a parent slide and slide part. |
| `CellFormat` | Represents the formatting properties of a table cell, providing access to fill formatting and six border line formats (left, top, right, bottom, diagonal-down, diagonal-up). |
| `Color` | Immutable value type representing an ARGB color. |
| `ColorFormat` | Represents a color format used in presentation elements. |
| `Column` | Represents a table column as a collection of cells (one per row). |
| `ColumnCollection` | Represents a collection of columns in a table. |
| `ColumnFormat` | Represents the formatting properties of a table column. |
| `Comment` | Represents a comment on a slide. |
| `CommentAuthor` | Represents an author of comments in a presentation. |
| `CommentAuthorCollection` | Represents a collection of comment authors backed by a CommentAuthorsPart. |
| `CommentCollection` | Represents a collection of comments authored by a single author across all slides in a presentation. |
| `Connector` | Represents a connector shape that can link two shapes via connection sites. |
| `ConnectorLock` | Determines which operations are disabled on the parent connector shape. |
| `CustomData` | Represents custom data associated with a shape. |
| `DocumentProperties` | Represents the metadata properties of a presentation, wrapping OPC core, app, and custom property parts with lazy initialization. |
| `EffectFormat` | Represents effect formatting properties backed by an effectLst element. |
| `FillFormat` | Represents fill formatting options. |
| `FillOverlay` | Represents a Fill Overlay effect. |
| `FontData` | Represents a font definition with a typeface name. |
| `GeometryShape` | Represents the base class for shapes that have geometric properties. |
| `GlobalLayoutSlideCollection` | Aggregates all layout slides across all master slides in a presentation. |
| `Glow` | Represents a glow effect, in which a color blurred outline is added outside the edges of the object. |
| `GradientFormat` | Represents a gradient format. |
| `GradientStop` | Represents a single gradient stop within a gradient fill. |
| `GradientStopCollection` | Manages a collection of &lt;a:gs&gt; child elements within an &lt;a:gsLst&gt; XML element. |
| `GraphicalObject` | Abstract base class for graphical objects on a slide. |
| `GraphicalObjectLock` | Represents a lock that determines which operations are disabled on a graphical object. |
| `GroupShape` | Represents a group shape that contains a collection of shapes. |
| `HeadingPair` | Represents a 'Heading pair' property of the document. |
| `IImage` | Represents a raster or vector image. |
| `IImageCollection` | Represents a collection of IPPImage objects. |
| `IPPImage` | Represents a presentation-embedded image stored in an OPC package part. |
| `IParagraph` | Represents a paragraph of text. |
| `IPortion` | Represents a portion (run) of text inside a paragraph. |
| `IPresentation` | Represents a presentation document. |
| `IPresentationComponent` | Represents any component that belongs to a presentation. |
| `ISlideComponent` | Represents any component that belongs to a slide. |
| `ISlidesPicture` | Represents a picture reference within a slide. |
| `IThemeable` | Represents objects that can be themed. |
| `Image` | Concrete image wrapper holding raw bytes and metadata. |
| `ImageCollection` | Concrete collection managing presentation images within an OPC package. |
| `ImageTransformOperation` | Represents an image transform operation effect. |
| `Images` | Provides static factory methods for creating Image instances. |
| `InnerShadow` | Represents an inner shadow effect. |
| `LayoutSlide` | Represents a layout slide in a presentation. |
| `LayoutSlideCollection` | Base class for collections of layout slides. |
| `LightRig` | Represents a light rig. |
| `LineFillFormat` | Represents properties for lines filling. |
| `LineFormat` | Represents line formatting properties. |
| `LoadOptions` | Represents options that can be used to control how a presentation is loaded. |
| `MasterLayoutSlideCollection` | Represents a collections of all layout slides of defined master slide. |
| `MasterSlide` | Represents a master slide in a presentation. |
| `MasterSlideCollection` | Represents a collection of master slides in a presentation. |
| `NotesSize` | Represents the size of a notes slide. |
| `NotesSlide` | Represents a notes slide in a presentation. |
| `NotesSlideHeaderFooterManager` | Manages visibility and text content of header, footer, date-time, and slide number placeholders on a notes slide. |
| `NotesSlideManager` | Manages notes slide operations for a slide. |
| `OuterShadow` | Represents an outer shadow effect. |
| `PPImage` | Concrete presentation-embedded image backed by an OPC package part. |
| `PVIObject` | Concrete base class providing property-value-inheritance infrastructure. |
| `Paragraph` | Represents a paragraph of text. |
| `ParagraphCollection` | Represents a collection of paragraphs. |
| `ParagraphFormat` | Represents the formatting properties for a paragraph. |
| `PatternFormat` | Represents a pattern fill format. |
| `Picture` | Concrete picture reference backed by an a:blip XML element in a slide's XML. |
| `PictureFillFormat` | Represents a picture fill style. |
| `PictureFrame` | Represents a picture frame shape. |
| `PictureFrameLock` | Determines which operations are disabled on the parent picture frame. |
| `Placeholder` | Represents a placeholder on a slide. |
| `PointF` | Represents a 2D point with float coordinates. |
| `Portion` | Represents a portion (run) of text inside a text paragraph. |
| `PortionCollection` | Represents a mutable collection of portions belonging to a slide component. |
| `PortionFormat` | This class contains the text portion formatting properties. |
| `Presentation` | Represents a Microsoft PowerPoint presentation document. |
| `PresetShadow` | Represents a preset shadow effect. |
| `Reflection` | Represents a reflection effect. |
| `Row` | Represents a table row as a collection of cells. |
| `RowCollection` | Represents a collection of rows in a table. |
| `RowFormat` | Represents the formatting properties of a table row. |
| `SaveOptions` | Represents options that control how a presentation is saved. |
| `Section` | Represents a section of slides in a presentation. |
| `SectionCollection` | Represents a collection of sections in a presentation. |
| `Shape` | Base class for all shapes on a slide. |
| `ShapeBevel` | Represents the bevel (relief) properties of a shape's face. |
| `ShapeCollection` | Represents an ordered, mutable collection of IShape objects belonging to a slide or group shape. |
| `ShapeFrame` | Represents the geometric frame properties of a shape. |
| `ShapeStyle` | Represents a shape's style reference. |
| `Size` | Represents a 2D size with integer dimensions. |
| `SizeF` | Represents a 2D size with float dimensions. |
| `Slide` | Represents a slide in a presentation. |
| `SlideCollection` | Represents a collection of slides in a presentation. |
| `SoftEdge` | Represents a soft edge effect. |
| `Table` | Represents a table shape on a slide. |
| `TableFormat` | Represents format of a table. |
| `TextFrame` | Represents the text body of a shape. |
| `TextFrameFormat` | Contains the TextFrame's formatting properties. |
| `ThreeDFormat` | Represents 3-D formatting properties for a shape. |

#### Interfaces

| Interface | Description |
|---|---|
| `IAdjustValue` | Represents a single adjustment value for a geometry shape. |
| `IAdjustValueCollection` | Represents a collection of shape adjustment values. |
| `IAutoShape` | Represents an AutoShape. |
| `IBaseHandoutNotesSlideHeaderFooterManager` | Represents a base interface for handout and notes slide header and footer management. |
| `IBaseHeaderFooterManager` | Represents a base interface for header and footer management. |
| `IBasePortionFormat` | Defines common text run formatting properties. |
| `IBaseSlide` | Represents a base slide. |
| `IBaseSlideHeaderFooterManager` | Represents a base interface for slide-level header and footer management. |
| `IBlur` | Represents a blur effect that is applied to the entire shape, including its fill. |
| `IBulkTextFormattable` | Represents an object that can apply text formatting in bulk to all contained text. |
| `IBulletFormat` | Represents paragraph bullet formatting properties. |
| `ICamera` | Represents the 3-D camera properties for a shape. |
| `ICell` | Represents a single cell in a table. |
| `ICellCollection` | Represents a collection of table cells. |
| `ICellFormat` | Represents the formatting of a table cell. |
| `IColorFormat` | Represents a color format used in presentation elements. |
| `IColumn` | Represents a single column in a table. |
| `IColumnCollection` | Represents a collection of table columns. |
| `IColumnFormat` | Represents the formatting properties of a table column. |
| `IComment` | Represents a comment on a slide. |
| `ICommentAuthor` | Represents an author of comments. |
| `ICommentAuthorCollection` | Represents a collection of comment authors. |
| `ICommentCollection` | Represents a collection of comments. |
| `IConnector` | Represents a connector shape that links two shapes. |
| `IConnectorLock` | Determines which operations are disabled on the parent connector shape. |
| `ICustomData` | Represents custom data associated with a shape. |
| `IDocumentProperties` | Represents the metadata properties of a presentation document. |
| `IEffectFormat` | Represents visual effect formatting properties for a shape. |
| `IEffectParamSource` | Represents a source of effect parameters. |
| `IFillFormat` | Represents fill formatting properties for a shape or text. |
| `IFillOverlay` | Represents a Fill Overlay effect. |
| `IFillParamSource` | Auxiliary interface for fill parameter source. |
| `IFontData` | Represents a font definition. |
| `IGeometryShape` | Represents a shape with geometric properties. |
| `IGlobalLayoutSlideCollection` | Represents a collection of all layout slides in presentation. |
| `IGlow` | Represents a glow effect, in which a color blurred outline is added outside the edges of the object. |
| `IGradientFormat` | Represents gradient fill formatting properties. |
| `IGradientStop` | Represents a single stop in a gradient fill. |
| `IGradientStopCollection` | Represents a collection of gradient stops. |
| `IGraphicalObject` | Represents a graphical object on a slide. |
| `IGraphicalObjectLock` | Determines which operations are disabled on the parent graphical object. |
| `IGroupShape` | Represents a group shape that contains other shapes. |
| `IHeadingPair` | Represents a heading pair entry describing a content grouping in a presentation. |
| `IHyperlinkContainer` | Represents an object that can contain hyperlinks. |
| `IImageTransformOperation` | Represents an image transform operation effect. |
| `IInnerShadow` | Represents an inner shadow effect. |
| `ILayoutSlide` | Represents a layout slide. |
| `ILayoutSlideCollection` | Represents a base class for collection of layout slides. |
| `ILightRig` | Represents a light rig. |
| `ILineFillFormat` | Represents properties for lines filling. |
| `ILineFormat` | Represents format of a line. |
| `ILineParamSource` | Marker interface for objects that can serve as a source of line parameters. |
| `ILoadOptions` | Represents options that can be used to control how a presentation is loaded. |
| `IMasterLayoutSlideCollection` | Represents a collection of layout slides belonging to a master slide. |
| `IMasterSlide` | Represents a master slide in a presentation. |
| `IMasterSlideCollection` | Represents a collection of master slides. |
| `INotesSize` | Represents the size of a notes slide. |
| `INotesSlide` | Represents a notes slide in a presentation. |
| `INotesSlideHeaderFooterManager` | Represents a manager for notes slide header and footer placeholders. |
| `INotesSlideManager` | Manages notes slide operations for a slide. |
| `IOuterShadow` | Represents an Outer Shadow effect. |
| `IParagraphCollection` | Represents a collection of paragraphs. |
| `IParagraphFormat` | Contains the paragraph formatting properties. |
| `IPatternFormat` | Represents a pattern fill format. |
| `IPictureFillFormat` | Represents a picture fill style. |
| `IPictureFrame` | Represents a picture frame shape. |
| `IPictureFrameLock` | Determines which editing operations are disabled on a picture frame. |
| `IPlaceholder` | Represents a placeholder on a slide. |
| `IPortionCollection` | Represents a collection of portions. |
| `IPortionFormat` | Defines the formatting properties for a text portion, combining base portion formatting with hyperlink container capabilities. |
| `IPresetShadow` | Represents a Preset Shadow effect. |
| `IReflection` | Represents a reflection effect. |
| `IRow` | Represents a row in a table. |
| `IRowCollection` | Represents a collection of table rows. |
| `IRowFormat` | Represents the formatting properties for a table row. |
| `ISaveOptions` | Represents options that control how a presentation is saved. |
| `ISection` | Represents a section of slides in a presentation. |
| `ISectionCollection` | Represents a collection of sections in a presentation. |
| `IShape` | Represents a shape on a slide. |
| `IShapeBevel` | Represents the bevel (relief) properties of a shape's face. |
| `IShapeCollection` | Represents an ordered, mutable collection of IShape objects belonging to a slide or group shape. |
| `IShapeFrame` | Represents the geometric frame properties of a shape. |
| `IShapeStyle` | Represents a shape's style reference. |
| `ISlide` | Represents a slide in a presentation. |
| `ISlideCollection` | Represents a collection of slides in a presentation. |
| `ISoftEdge` | Represents a Soft Edge effect. |
| `ITable` | Represents a table on a slide. |
| `ITableFormat` | Represents format of a table. |
| `ITextFrame` | Represents the text frame of a shape or cell. |
| `ITextFrameFormat` | Contains the TextFrame's formatting properties. |
| `IThreeDFormat` | Represents 3-D properties. |
| `IThreeDParamSource` | Marker interface for objects that provide 3D formatting parameters. |

#### Enumerations

| Enumeration | Description |
|---|---|
| `BevelPresetType` | Represents BevelPresetType enumeration. |
| `BulletType` | Represents BulletType enumeration. |
| `CameraPresetType` | Represents CameraPresetType enumeration. |
| `ColorType` | Represents ColorType enumeration. |
| `FillBlendMode` | Represents FillBlendMode enumeration. |
| `FillType` | Represents FillType enumeration. |
| `FontAlignment` | Represents FontAlignment enumeration. |
| `GradientDirection` | Represents GradientDirection enumeration. |
| `GradientShape` | Represents GradientShape enumeration. |
| `LightRigPresetType` | Represents LightRigPresetType enumeration. |
| `LightingDirection` | Represents LightingDirection enumeration. |
| `LineAlignment` | Represents LineAlignment enumeration. |
| `LineArrowheadLength` | Represents LineArrowheadLength enumeration. |
| `LineArrowheadStyle` | Represents LineArrowheadStyle enumeration. |
| `LineArrowheadWidth` | Represents LineArrowheadWidth enumeration. |
| `LineCapStyle` | Represents LineCapStyle enumeration. |
| `LineDashStyle` | Represents LineDashStyle enumeration. |
| `LineJoinStyle` | Represents LineJoinStyle enumeration. |
| `LineStyle` | Represents LineStyle enumeration. |
| `MaterialPresetType` | Represents MaterialPresetType enumeration. |
| `NullableBool` | Represents NullableBool enumeration. |
| `NumberedBulletStyle` | Represents NumberedBulletStyle enumeration. |
| `PatternStyle` | Represents PatternStyle enumeration. |
| `PictureFillMode` | Represents PictureFillMode enumeration. |
| `PresetColor` | Represents PresetColor enumeration. |
| `PresetShadowType` | Represents PresetShadowType enumeration. |
| `RectangleAlignment` | Represents RectangleAlignment enumeration. |
| `SaveFormat` | Defines constants representing all supported file formats for saving a presentation. |
| `SchemeColor` | Represents SchemeColor enumeration. |
| `ShapeType` | Represents preset geometry of geometry shapes. |
| `SlideLayoutType` | Represents SlideLayoutType enumeration. |
| `SourceFormat` | Represents SourceFormat enumeration. |
| `TableStylePreset` | Represents TableStylePreset enumeration. |
| `TextAlignment` | Represents TextAlignment enumeration. |
| `TextAnchorType` | Represents TextAnchorType enumeration. |
| `TextAutofitType` | Represents TextAutofitType enumeration. |
| `TextCapType` | Represents TextCapType enumeration. |
| `TextShapeType` | Represents TextShapeType enumeration. |
| `TextStrikethroughType` | Represents TextStrikethroughType enumeration. |
| `TextUnderlineType` | Represents TextUnderlineType enumeration. |
| `TextVerticalType` | Represents TextVerticalType enumeration. |
| `TileFlip` | Represents TileFlip enumeration. |

---

#### Detailed Member Reference

### Presentation and Slides

- `Presentation` (sealed, `IDisposable`)
  - Constructors: `Presentation()`, `Presentation(file)`, `Presentation(file, loadOptions)`, `Presentation(stream)`, `Presentation(stream, loadOptions)`
  - `Save(fname, format)` and overloads, `Dispose()`
  - Properties: `Slides: ISlideCollection`, `Masters: IMasterSlideCollection`, `LayoutSlides: IGlobalLayoutSlideCollection`, `CommentAuthors: ICommentAuthorCollection`, `DocumentProperties: IDocumentProperties`, `Images: IImageCollection`
- `SlideCollection` (sealed)
  - `AddClone(sourceSlide)`, `InsertClone(index, sourceSlide)`, `AddEmptySlide(layout)`, `InsertEmptySlide(index, layout)`, `Remove(value)`, `RemoveAt(index)`
  - Properties: `Count: int`
- `Slide` (sealed)
  - `GetSlideComments(author)`, `Remove()`
  - Properties: `SlideNumber: int`, `Hidden: bool`, `Name: string`, `Shapes: IShapeCollection?`, `NotesSlideManager: INotesSlideManager`

### Shapes

- `Shape` — base class for all shapes on a slide
  - Properties: `LineFormat: ILineFormat`, `FillFormat: IFillFormat`, `EffectFormat: IEffectFormat`, `ThreeDFormat: IThreeDFormat`, `Frame: IShapeFrame`, `Rotation: float`, `X/Y/Width/Height: float`, `Name: string`
- `ShapeCollection` (sealed)
  - `AddAutoShape(shapeType, x, y, width, height)`, `AddConnector(shapeType, x, y, width, height)`, `AddPictureFrame(shapeType, x, y, width, height, image)`, `AddTable(x, y, columnWidths, rowHeights)`, `Reorder(index, shape)`, `RemoveAt(index)`
- `AutoShape` (sealed) — `AddTextFrame(text)`; properties: `ShapeType: ShapeType`, `TextFrame: ITextFrame?`
- `Connector` (sealed) — `Reroute()`; participates in `StartShapeConnectedTo` / `EndShapeConnectedTo` wiring
- `Table` (sealed) — `MergeCells(cell1, cell2, allowSplitting)`, `SetTextFormat(source)`; properties: `Rows: IRowCollection`, `Columns: IColumnCollection`, `StylePreset: TableStylePreset`

### Text

- `TextFrame` (sealed) — properties: `Paragraphs: IParagraphCollection`, `Text: string`, `TextFrameFormat: ITextFrameFormat`
- `Paragraph` (sealed) — properties: `Portions: IPortionCollection`, `ParagraphFormat: IParagraphFormat`, `Text: string`
- `ParagraphFormat` (sealed) — properties: `Bullet: IBulletFormat`, `Alignment: TextAlignment`, `SpaceBefore/SpaceAfter: float`, `MarginLeft/MarginRight: float`
- `Portion` (sealed) — constructors `Portion()`, `Portion(text)`; property `PortionFormat: IBasePortionFormat?`
- `PortionFormat` (sealed) — properties: `FontBold/FontItalic: NullableBool`, `FontHeight: float`, `FontUnderline: TextUnderlineType`, `FillFormat: IFillFormat?`, `LatinFont: IFontData?`

### Formatting

- `FillFormat` — `FillType: FillType` (enum: `NoFill`, `Solid`, `Gradient`, `Pattern`, `Picture`, `Group`), `SolidFillColor`
- `LineFormat` — `Width`, `DashStyle: LineDashStyle`, `FillFormat: ILineFillFormat`
- `EffectFormat` — `EnableOuterShadowEffect()`, `OuterShadowEffect` (`BlurRadius`, `Distance`)
- `ThreeDFormat` — `BevelTop: IShapeBevel` (`BevelType: BevelPresetType`, `Height`, `Width`)

### Document Metadata

- `DocumentProperties` (sealed) — `GetCustomPropertyValue(name)`, `SetCustomPropertyValue(name, value)`; properties: `Title`, `Subject`, `Author`, `Keywords`, `Company`, `Manager`, `CreatedTime: DateTime?`
- `NotesSlideManager` (sealed) — `AddNotesSlide()`, `RemoveNotesSlide()`; property `NotesSlide: INotesSlide?`
- `CommentAuthorCollection` (sealed) — `AddAuthor(name, initials)`, `FindByName(name)`, `Remove(author)`
- `CommentAuthor` (sealed) — properties: `Name`, `Initials`, `Comments: ICommentCollection`
- `CommentCollection` (sealed) — `AddComment(text, slide, position, creationTime)`, `InsertComment(index, ...)`, `RemoveAt(index)`
- `Comment` (sealed) — `Remove()`; properties: `Text`, `CreatedTime: DateTime?`, `Slide: ISlide`, `Author: ICommentAuthor`, `Position: PointF`

### Enums

- `SaveFormat` — `Ppt`, `Pdf`, `Xps`, `Pptx`, `Ppsx`, `Tiff` (only `Pptx` is implemented for save in this edition — see [Scope and limitations](#scope-and-limitations))
- `ShapeType` — geometry presets such as `Rectangle`, `BentConnector3`, and others
- `FillType` — `NotDefined`, `NoFill`, `Solid`, `Gradient`, `Pattern`, `Picture`, `Group`
- `NullableBool` — `False`, `True`, `NotDefined` (used for tri-state boolean formatting properties like `FontBold`)

</details>

## Documentation & Resources

- **[Getting started guide](https://docs.aspose.org/slides/net/)** — installation, walkthroughs, and feature guides for this library.
- **[How-to guides & FAQ](https://kb.aspose.org/slides/net/)** — task-focused answers for common PowerPoint-processing questions.
- **[Full API reference](https://reference.aspose.org/slides/net/)** — the complete, browsable reference for all public types (the [API reference](#api-reference) section above covers the essentials).
- **[Contributor guide](AGENTS.md)** — architecture notes and conventions for contributors.
- **[GitHub Repository](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET)** — browse the source and project history.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-.NET/issues) on GitHub.

## Scope and Limitations

The following areas are not yet implemented in this edition:

- **Charts, SmartArt, OLE objects, and mathematical text.**
- **Animations and slide transitions.**
- **Export to non-PPTX formats** (PDF, HTML, SVG, or images) — `SaveFormat.Pptx` is the only save
  format implemented, even though the `SaveFormat` enum also lists `Ppt`, `Pdf`, `Xps`, `Ppsx`,
  and `Tiff` in the underlying source.
- **VBA macros and digital signatures.**
- **Hyperlinks and action settings.**

Unknown XML parts encountered during load are preserved verbatim on save, so round-tripping a
file never strips content this library does not yet understand.

For the complete enterprise API with full production support, see
[Aspose.Slides for .NET — Enterprise Edition](https://products.aspose.com/slides/net/).

## Development and Testing

The project's CI workflow (`.github/workflows/ci.yml`) runs on .NET 9.0 across Ubuntu and
Windows:

```bash
dotnet restore
dotnet build --no-restore --configuration Release
dotnet test tests/Aspose.Slides.Foss.Tests --no-build --configuration Release --verbosity normal
dotnet test tests/Aspose.Slides.Foss.IntegrationTests --no-build --configuration Release --verbosity normal
```

## License

This project is licensed under the [MIT License](LICENSE). The MIT License permits use, copying, modification,
distribution, sublicensing, and commercial use, provided its copyright and permission notice are
retained. The software is provided without warranty.
