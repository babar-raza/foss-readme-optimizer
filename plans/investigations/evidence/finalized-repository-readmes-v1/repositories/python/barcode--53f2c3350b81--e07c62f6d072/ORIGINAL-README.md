# aspose-barcode-foss

A pure-Python library for barcode generation. It produces deterministic,
standards-compliant barcodes and renders them as SVG or PNG.

- No system dependencies — pure Python, with [Pillow](https://python-pillow.org/) used only for PNG output.
- Fully typed (ships a `py.typed` marker).
- Linear and 2D symbologies: Code 128, Code 39, EAN-13, EAN-8, UPC-A, UPC-E, and QR Code.

## Installation

The package is not yet published to PyPI. Install it from a source checkout (run from
the repository root, where `pyproject.toml` lives):

```bash
pip install .
```

The distribution is named `aspose-barcode-foss`; the import package is
`aspose_barcode_foss`:

```python
import aspose_barcode_foss
```

## Quick Start

```python
from aspose_barcode_foss import code128

barcode = code128("Hello-World")
svg = barcode.to_svg()       # -> str
png = barcode.to_png()       # -> bytes
```

Write the output to a file:

```python
with open("barcode.svg", "w", encoding="utf-8") as f:
    f.write(barcode.to_svg())

with open("barcode.png", "wb") as f:
    f.write(barcode.to_png())
```

QR Code works the same way:

```python
from aspose_barcode_foss import qr

png = qr("https://example.com").to_png()
```

## Supported Symbologies

Each symbology has a dedicated helper; all of them are also reachable through the
generic `generate()` function by name (canonical name or one of its aliases).

| Symbology | Function | Accepted input |
|-----------|----------|----------------|
| Code 128 | `code128()` | Printable ASCII; Code Sets A/B/C with automatic optimal switching |
| Code 39 | `code39()` | The 43-character set: digits, `A`–`Z`, space, and ``- . $ / + %`` |
| Code 39 (Extended) | `code39ext()` | Full ASCII (128 characters) via two-character shift encoding |
| EAN-13 | `ean13()` | 12 digits (check digit computed), or 13 with `allow_check_digit_input=True` |
| EAN-8 | `ean8()` | 7 digits (check digit computed), or 8 with `allow_check_digit_input=True` |
| UPC-A | `upca()` | 11 digits (check digit computed), or 12 with `allow_check_digit_input=True` |
| UPC-E | `upce()` | An 11- or 12-digit number-system-0 GTIN-12, zero-suppressed to UPC-E |
| QR Code | `qr()` | Text in numeric, alphanumeric, byte (Latin-1), or Kanji mode; Model 2, versions 1–40 |

Select a symbology by name with `generate()`:

```python
from aspose_barcode_foss import generate

barcode = generate("code128", "ABC-123")
barcode = generate("qr", "https://example.com")
```

> Rendering backends: SVG and PNG are implemented for every symbology. PDF output is
> planned but not yet implemented (`to_pdf()` raises `NotImplementedError`).

## Render Options

Rendering is controlled with `RenderOptions`, passed as the keyword-only `options`
argument:

```python
from aspose_barcode_foss import code128, RenderOptions

barcode = code128("Hello-World")
svg = barcode.to_svg(options=RenderOptions(scale=2.0, show_text=True))
png = barcode.to_png(options=RenderOptions(dpi=300, module_width=3.0))
```

Available fields: `scale`, `dpi`, `module_width`, `module_height`, `quiet_zone`,
`foreground_color`, `background_color`, `transparent_background`, `show_text`,
`font_family`, `font_size`. Any field left as `None` falls back to the symbology's
default.

## Encoding Options

Each symbology helper accepts a keyword-only `encode` argument with a symbology-specific
options type.

### Code 128

```python
from aspose_barcode_foss import code128, Code128Options, Code128EncodeMode

# AUTO (default) selects the optimal Code Set sequence.
barcode = code128("Mixed123ABC", encode=Code128Options(encode_mode=Code128EncodeMode.AUTO))

# Force a specific Code Set.
barcode = code128("12345678", encode=Code128Options(encode_mode=Code128EncodeMode.CODE_C))
```

`Code128EncodeMode` values: `AUTO`, `CODE_A`, `CODE_B`, `CODE_C`, `CODE_AB`, `CODE_AC`,
`CODE_BC`.

### QR Code

```python
from aspose_barcode_foss import qr, QrOptions, QrErrorCorrectionLevel, QrEncodeMode

barcode = qr(
    "PAYLOAD",
    encode=QrOptions(
        error_correction_level=QrErrorCorrectionLevel.H,  # L / M / Q / H
        version=None,                                      # 1-40, or None to auto-fit
        mask=None,                                         # 0-7, or None to auto-select
        encoding_mode=QrEncodeMode.AUTO,                   # AUTO / NUMERIC / ALPHANUMERIC / BYTE / KANJI
    ),
)
```

### Code 39

```python
from aspose_barcode_foss import code39, code39ext, Code39Options

# Optional modulo-43 check character.
barcode = code39("ABC-123", encode=Code39Options(add_check_digit=True))

# code39ext() encodes the full ASCII set.
barcode = code39ext("Item #42")
```

### EAN / UPC

```python
from aspose_barcode_foss import ean13, Ean13Options

# Pass 12 digits and let the check digit be computed.
barcode = ean13("590123412345")

# Or pass all 13 digits and opt in to validating the supplied check digit.
barcode = ean13("5901234123457", encode=Ean13Options(allow_check_digit_input=True))
```

The same `allow_check_digit_input` option is available for `ean8()`, `upca()`, and
`upce()`.

## Custom Renderer

`to_svg()` and `to_png()` are convenience wrappers around `render()`, which accepts any
`Renderer` instance:

```python
from aspose_barcode_foss import code128, SvgRenderer, RenderOptions

renderer = SvgRenderer()
barcode = code128("Hello-World")
artifact = barcode.render(renderer, options=RenderOptions(scale=3.0))
svg = artifact.data
```

Available renderers: `SvgRenderer`, `PngRenderer`, and `PdfRenderer` (not yet
implemented).

## Error Handling

```python
from aspose_barcode_foss import code128, generate, InvalidInputError, SymbologyNotFoundError

try:
    code128("")                       # empty input
except InvalidInputError as e:
    print(e)

try:
    generate("datamatrix", "data")    # unknown symbology
except SymbologyNotFoundError as e:
    print(e)
```

Exception hierarchy (all inherit from `BarcodeError`):

| Exception | Raised when |
|-----------|-------------|
| `BarcodeError` | Base class for all library exceptions |
| `InvalidInputError` | Input fails validation (bad characters, wrong length, etc.) |
| `SymbologyNotFoundError` | Unknown symbology name passed to `generate()` |
| `UnsupportedFeatureError` | Feature exists in the spec but is not yet implemented |
| `UnsupportedCapabilityError` | Unsupported feature combination for a symbology |
| `EncodingError` | Encoder-level failure |
| `RenderingError` | Renderer-level failure |

## Requirements

- Python 3.12+
- Pillow ≥ 10.1.0 (for PNG rendering)

## License

Released under the [MIT License](LICENSE).
