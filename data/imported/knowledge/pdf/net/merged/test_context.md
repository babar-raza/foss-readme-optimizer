# Snippet Test Context — Aspose.PDF FOSS for .NET

## Source

All 100 extracted snippets (`snippets/snippet_*.cs`) are derived from **xUnit test methods**
in `tests/` of the FOSS repository. The repository does not contain standalone usage examples
or documentation sample files.

## Known Test-Only Classes (NOT in public API)

The following classes appear in snippets but are **test infrastructure** — they are defined in
`tests/Helpers/` and are NOT exported in the `Aspose.Pdf.Foss` NuGet package:

| Class | File | Purpose |
|-------|------|---------|
| `PdfBuilder` | `tests/Helpers/PdfBuilder.cs` | Builds minimal in-memory PDF byte arrays for test setup |

## Impact on Content Generation

Content generators MUST NOT use `PdfBuilder` in public-facing code examples.
When using snippets, strip or replace the following patterns:

- `PdfBuilder.BuildMinimal()` → replace with `Document.Create().ToArray()`
- `PdfBuilder.BuildWithTextContent(...)` → replace with `Document.Open(bytes)` where bytes comes from a `Document.Create()`
- `PdfBuilder.Build*` → equivalent pattern using only the public `Document` API

## Test Framework Boilerplate

All snippets include xUnit test decorations (`[Fact]`, `Assert.*`). These are NOT part
of the public API. When presenting code examples in docs/blog/KB pages, extract only
the meaningful API usage lines and wrap them in a standalone `using` block.

## Verified Clean Pattern

```csharp
// Create a new PDF document
using var doc = Document.Create();
doc.Pages.Add();
byte[] bytes = doc.ToArray();

// Open an existing PDF
using var existing = Document.Open("/path/to/file.pdf");
int pageCount = existing.Pages.Count;
```

These patterns use only verified public API members from `api_surface.json`.
