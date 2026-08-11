# Aspose.BarCode FOSS for Python

[![Version: 0.1.0](https://img.shields.io/badge/Version-0.1.0-blue)](https://github.com/aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python/tree/53f2c3350b8171f2c8275e7b1a178f218695ac45) ![Platform: Python](https://img.shields.io/badge/Platform-Python-blue) ![Requires: Python >=3.12](https://img.shields.io/badge/Requires-Python%20%3E%3D3.12-blue) [![License: MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE) [![Contributors: aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python](https://img.shields.io/github/contributors/aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python.svg)](https://github.com/aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python/graphs/contributors)

![Aspose.BarCode FOSS for Python](https://products.aspose.org/media/barcode/python/banner-readme.png)

Aspose.BarCode FOSS for Python is an open-source library for developers using Python. It writes PNG (image/PNG) files and SVG (image/SVG+XML) files.

## Navigation

- [At a Glance](#at-a-glance)
- [Key Capabilities](#key-capabilities)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Additional Examples](#additional-examples)
- [API Reference](#api-reference)
- [Documentation and Resources](#documentation-and-resources)
- [Scope and Limitations](#scope-and-limitations)
- [Development and Testing](#development-and-testing)
- [License](#license)

## At a Glance

```mermaid
flowchart LR
  subgraph INPUTS["Inputs & Formats"]
    direction TB
    I1["<div style='width:150px'>Code 128 content</div>"]
    I2["<div style='width:150px'>Code 39 (base<br/>43-character set)</div>"]
    I3["<div style='width:150px'>EAN-13, EAN-8,<br/>UPC-A, and UPC-E</div>"]
  end
  PRODUCT["Aspose.BarCode FOSS<br/>for Python"]
  subgraph CORE["Core Capabilities"]
    direction LR
    subgraph CORE_LEFT[" "]
      direction TB
      C1["Code 128 generation<br/>with automatic"]
      C2["Code 39 (base<br/>43-character set)"]
      C3["EAN-13, EAN-8, UPC-A,<br/>and UPC-E"]
      C1 ~~~ C2
      C2 ~~~ C3
    end
    subgraph CORE_RIGHT[" "]
      direction TB
      C4["SVG rendering for all<br/>supported"]
      C5["PNG rendering for all<br/>supported"]
      C6["Custom renderer<br/>support via render()"]
      C4 ~~~ C5
      C5 ~~~ C6
    end
    CORE_LEFT ~~~ CORE_RIGHT
  end
  subgraph OUTPUTS["Outputs"]
    direction TB
    O1["<div style='width:150px'>SVG (image/SVG+XML)</div>"]
    O2["<div style='width:150px'>PNG (image/PNG)</div>"]
  end
  I1 --> PRODUCT
  PRODUCT --> CORE
  CORE --> O1
  classDef product fill:#1F4E79,color:#FFFFFF,stroke:#163A5B,stroke-width:2px,font-weight:bold;
  classDef input fill:#EAF2F8,color:#17324D,stroke:#7EA6C4,stroke-width:1.5px;
  classDef capability fill:#F7F9FC,color:#243447,stroke:#AAB7C4,stroke-width:1.25px;
  classDef output fill:#EAF6EF,color:#244A32,stroke:#78A889,stroke-width:1.5px,font-weight:bold;
  class PRODUCT product;
  class I1,I2,I3 input;
  class C1,C2,C3,C4,C5,C6 capability;
  class O1,O2 output;
  style INPUTS fill:#F8FBFD,stroke:#7EA6C4,stroke-width:1.5px
  style CORE fill:#FFFFFF,stroke:#5F7791,stroke-width:2px
  style CORE_LEFT fill:transparent,stroke:transparent
  style CORE_RIGHT fill:transparent,stroke:transparent
  style OUTPUTS fill:#F7FBF8,stroke:#78A889,stroke-width:1.5px
  linkStyle 5,6,7 stroke:#526D82,stroke-width:2px
```

## Key Capabilities

- **Work with Code 128 generation with automatic optimal Code Set switching** - Build the corresponding content through the public object model.
- **Work with Code 39 (base 43-character set) and Extended (full ASCII) generation** - Build the corresponding content through the public object model.
- **Work with EAN-13, EAN-8, UPC-A, and UPC-E generation with optional check digit input** - Build the corresponding content through the public object model.
- **Work with SVG rendering for all supported symbologies** - Produce supported output through the public API.
- **Work with PNG rendering for all supported symbologies** - Produce supported output through the public API.
- **Work with Custom renderer support via render() method** - Use the public `Renderer` API in application workflows.

## Installation

Install the package directly from its source repository:

```bash
git clone https://github.com/aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python.git
cd Aspose.BarCode-FOSS-for-Python
git checkout --detach 53f2c3350b8171f2c8275e7b1a178f218695ac45
python -m pip install .
```

Use source installation for the `aspose-barcode-foss` distribution.

Required runtime dependencies declared in `pyproject.toml`: `Pillow>=10.1.0`.

## Quick Start

```python
from aspose_barcode_foss import SvgRenderer

renderer = SvgRenderer()
```

## Additional Examples

Expand this section to view examples for exploring another repository workflow, supported Symbologies, rendering options, code 128, and browsing repository example files, plus 6 more workflows.

<details>
<summary>View additional examples and results</summary>

### Explore Another Repository Workflow

```python
from aspose_barcode_foss import code128

barcode = code128("Hello-World")
svg = barcode.to_svg()
png = barcode.to_png()
```

### Explore Another Repository Workflow with Open

```python
with open("barcode.svg", "w", encoding="utf-8") as f:
    f.write(barcode.to_svg())

with open("barcode.png", "wb") as f:
    f.write(barcode.to_png())
```

### Explore Another Repository Workflow with To_png

```python
from aspose_barcode_foss import qr

png = qr("https://example.com").to_png()
```

### Supported Symbologies

```python
from aspose_barcode_foss import generate

barcode = generate("code128", "ABC-123")
barcode = generate("qr", "https://example.com")
```

### Render Options

```python
from aspose_barcode_foss import code128, RenderOptions

barcode = code128("Hello-World")
svg = barcode.to_svg(options=RenderOptions(scale=2.0, show_text=True))
png = barcode.to_png(options=RenderOptions(dpi=300, module_width=3.0))
```

### Code 128

```python
from aspose_barcode_foss import code128, Code128Options, Code128EncodeMode

barcode = code128("Mixed123ABC", encode=Code128Options(encode_mode=Code128EncodeMode.AUTO))

barcode = code128("12345678", encode=Code128Options(encode_mode=Code128EncodeMode.CODE_C))
```

### QR Code

```python
from aspose_barcode_foss import qr, QrOptions, QrErrorCorrectionLevel, QrEncodeMode

barcode = qr(
    "PAYLOAD",
    encode=QrOptions(
        error_correction_level=QrErrorCorrectionLevel.H,
        version=None,
        mask=None,
        encoding_mode=QrEncodeMode.AUTO,
    ),
)
```

### Code 39

```python
from aspose_barcode_foss import code39, code39ext, Code39Options

barcode = code39("ABC-123", encode=Code39Options(add_check_digit=True))

barcode = code39ext("Item #42")
```

### EAN / UPC

```python
from aspose_barcode_foss import ean13, Ean13Options

barcode = ean13("590123412345")

barcode = ean13("5901234123457", encode=Ean13Options(allow_check_digit_input=True))
```

### Error Handling

```python
from aspose_barcode_foss import code128, generate, InvalidInputError, SymbologyNotFoundError

try:
    code128("")
except InvalidInputError as e:
    print(e)

try:
    generate("datamatrix", "data")
except SymbologyNotFoundError as e:
    print(e)
```

### Repository Example Files

- [`all_symbologies.py`](examples/all_symbologies.py)
- [`error_handling.py`](examples/error_handling.py)
- [`quickstart.py`](examples/quickstart.py)
- [`render_options.py`](examples/render_options.py)

</details>

## API Reference

The package documents 51 public types across 4 namespaces. Package namespaces include `aspose_barcode_foss`. See the complete API reference under Documentation and Resources for members, signatures, and inherited APIs.

<details>
<summary>View public API by namespace</summary>

### Aspose.Barcode Namespace (`aspose_barcode_foss`)

| Type | Description |
| --- | --- |
| `Barcode` | Represents a Barcode in the public aspose barcode FOSS API for Aspose.Barcode. Supports converting content to PDF, encoding page content as PNG, and converting content to SVG. |
| `BarcodeError` | Signals a barcode error condition; derives from `Exception`. |
| `Code128EncodeMode` | Enumerates code128 encode mode values. |
| `Code128Options` | Configures Code128 operations through the Aspose.Barcode API. Inherits from `EncodeOptions`. |
| `Code39EncodeMode` | Enumerates code39 encode mode values. |
| `Code39Options` | Configures Code39 operations through the Aspose.Barcode API. Inherits from `EncodeOptions`. |
| `Ean13Options` | Configures Ean13 operations through the Aspose.Barcode API. Inherits from `EncodeOptions`. |
| `Ean8Options` | Configures Ean8 operations through the Aspose.Barcode API. Inherits from `EncodeOptions`. |
| `EncodeOptions` | Configures Encode operations through the Aspose.Barcode API. |
| `EncodingError` | Represents an Encoding Error in the public aspose barcode FOSS API for Aspose.Barcode. Inherits from `BarcodeError`. |
| `InvalidInputError` | Represents an Invalid Input Error in the public aspose barcode FOSS API for Aspose.Barcode. Inherits from `BarcodeError`. |
| `PdfRenderer` | Renders PDF content through the Aspose.Barcode API. Inherits from `Renderer`. |
| `PngRenderer` | Renders PNG content through the Aspose.Barcode API. Inherits from `Renderer`. |
| `QrEncodeMode` | Enumerates qr encode mode values. |
| `QrErrorCorrectionLevel` | Enumerates qr error correction level values. |
| `QrOptions` | Configures Qr operations through the Aspose.Barcode API. Inherits from `EncodeOptions`. |
| `RenderOptions` | Configures Render operations through the Aspose.Barcode API. |
| `Renderer` | Renders barcode content through the Aspose.Barcode API. Inherits from `ABC`. |
| `RenderingError` | Represents a Rendering Error in the public aspose barcode FOSS API for Aspose.Barcode. Inherits from `BarcodeError`. |
| `ResolvedRenderOptions` | Configures Resolved Render operations through the Aspose.Barcode API. |
| `SvgRenderer` | Renders SVG content through the Aspose.Barcode API. Inherits from `Renderer`. |
| `SymbologyNotFoundError` | Represents a Symbology Not Found Error in the public aspose barcode FOSS API for Aspose.Barcode. Inherits from `BarcodeError`. |
| `UnsupportedCapabilityError` | Represents an Unsupported Capability Error in the public aspose barcode FOSS API for Aspose.Barcode. Inherits from `BarcodeError`. |
| `UnsupportedFeatureError` | Represents an Unsupported Feature Error in the public aspose barcode FOSS API for Aspose.Barcode. Inherits from `BarcodeError`. |
| `UpcaOptions` | Configures Upca operations through the Aspose.Barcode API. Inherits from `EncodeOptions`. |
| `UpceOptions` | Configures Upce operations through the Aspose.Barcode API. Inherits from `EncodeOptions`. |

### Aspose.Barcode.Exceptions Namespace (`aspose_barcode_foss.exceptions`)

| Type | Description |
| --- | --- |
| `BarcodeError` | The `aspose_barcode_foss.exceptions` namespace re-exports `BarcodeError` from the primary `aspose_barcode_foss` namespace. |
| `EncodingError` | The `aspose_barcode_foss.exceptions` namespace re-exports `EncodingError` from the primary `aspose_barcode_foss` namespace. |
| `InvalidInputError` | The `aspose_barcode_foss.exceptions` namespace re-exports `InvalidInputError` from the primary `aspose_barcode_foss` namespace. |
| `RenderingError` | The `aspose_barcode_foss.exceptions` namespace re-exports `RenderingError` from the primary `aspose_barcode_foss` namespace. |
| `SymbologyNotFoundError` | The `aspose_barcode_foss.exceptions` namespace re-exports `SymbologyNotFoundError` from the primary `aspose_barcode_foss` namespace. |
| `UnsupportedCapabilityError` | The `aspose_barcode_foss.exceptions` namespace re-exports `UnsupportedCapabilityError` from the primary `aspose_barcode_foss` namespace. |
| `UnsupportedFeatureError` | The `aspose_barcode_foss.exceptions` namespace re-exports `UnsupportedFeatureError` from the primary `aspose_barcode_foss` namespace. |

### Aspose.Barcode.Options Namespace (`aspose_barcode_foss.options`)

| Type | Description |
| --- | --- |
| `Code128EncodeMode` | The `aspose_barcode_foss.options` namespace re-exports `Code128EncodeMode` from the primary `aspose_barcode_foss` namespace. |
| `Code128Options` | The `aspose_barcode_foss.options` namespace re-exports `Code128Options` from the primary `aspose_barcode_foss` namespace. |
| `Code39EncodeMode` | The `aspose_barcode_foss.options` namespace re-exports `Code39EncodeMode` from the primary `aspose_barcode_foss` namespace. |
| `Code39Options` | The `aspose_barcode_foss.options` namespace re-exports `Code39Options` from the primary `aspose_barcode_foss` namespace. |
| `Ean13Options` | The `aspose_barcode_foss.options` namespace re-exports `Ean13Options` from the primary `aspose_barcode_foss` namespace. |
| `Ean8Options` | The `aspose_barcode_foss.options` namespace re-exports `Ean8Options` from the primary `aspose_barcode_foss` namespace. |
| `EncodeOptions` | The `aspose_barcode_foss.options` namespace re-exports `EncodeOptions` from the primary `aspose_barcode_foss` namespace. |
| `QrEncodeMode` | The `aspose_barcode_foss.options` namespace re-exports `QrEncodeMode` from the primary `aspose_barcode_foss` namespace. |
| `QrErrorCorrectionLevel` | The `aspose_barcode_foss.options` namespace re-exports `QrErrorCorrectionLevel` from the primary `aspose_barcode_foss` namespace. |
| `QrOptions` | The `aspose_barcode_foss.options` namespace re-exports `QrOptions` from the primary `aspose_barcode_foss` namespace. |
| `RenderOptions` | The `aspose_barcode_foss.options` namespace re-exports `RenderOptions` from the primary `aspose_barcode_foss` namespace. |
| `ResolvedRenderOptions` | The `aspose_barcode_foss.options` namespace re-exports `ResolvedRenderOptions` from the primary `aspose_barcode_foss` namespace. |
| `UpcaOptions` | The `aspose_barcode_foss.options` namespace re-exports `UpcaOptions` from the primary `aspose_barcode_foss` namespace. |
| `UpceOptions` | The `aspose_barcode_foss.options` namespace re-exports `UpceOptions` from the primary `aspose_barcode_foss` namespace. |

### Aspose.Barcode.Renderers Namespace (`aspose_barcode_foss.renderers`)

| Type | Description |
| --- | --- |
| `PdfRenderer` | The `aspose_barcode_foss.renderers` namespace re-exports `PdfRenderer` from the primary `aspose_barcode_foss` namespace. |
| `PngRenderer` | The `aspose_barcode_foss.renderers` namespace re-exports `PngRenderer` from the primary `aspose_barcode_foss` namespace. |
| `Renderer` | The `aspose_barcode_foss.renderers` namespace re-exports `Renderer` from the primary `aspose_barcode_foss` namespace. |
| `SvgRenderer` | The `aspose_barcode_foss.renderers` namespace re-exports `SvgRenderer` from the primary `aspose_barcode_foss` namespace. |

</details>

## Documentation and Resources

- **[Getting started guide](https://docs.aspose.org/barcode/python/)** - installation, walkthroughs, and feature guides for this library.
- **[How-to guides and FAQ](https://kb.aspose.org/barcode/python/)** - task-focused answers for common product questions.
- **[Full API reference](https://reference.aspose.org/barcode/python/)** - the complete browsable reference for the public API.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-barcode-foss/Aspose.BarCode-FOSS-for-Python/issues) on GitHub.

## Scope and Limitations

The library targets the workflows listed above. Ten specific constraints are listed below.

- Explicit quiet_zone overrides can shrink below the Code 128 10X minimum; enforcement is not implemented yet.
- A fixed 3:1 wide:narrow ratio is used; the spec's configurable 2.0:1–3.0:1 range is not implemented.
- The nominal 1X inter-character gap is used; the spec's gap-widening allowances are not implemented.
- Explicit quiet_zone overrides can shrink below the Code 39 10X minimum; enforcement is not implemented.
- Bar/space compensation (ISO/IEC 15420:2009 4.3.6, Table 8) is not implemented.
- Text layout is not implemented for symbology.
- GS1, ECI, bytes / binary input, FNC handling, Code Set A/C, Shift, and code-set switching are unsupported.
- Only the SVG backend is implemented for Code 128.
- GS1, ECI, bytes / binary input, and structured append are unsupported.
- Only the SVG backend is implemented for Code 39.

The package manifest classifies this release as **Beta**. The distribution includes the [`src/aspose_barcode_foss/py.typed`](src/aspose_barcode_foss/py.typed) type marker.

For requirements beyond the FOSS scope described above, explore the [full-featured Aspose.BarCode Enterprise Edition](https://products.aspose.com/barcode/). It is a separate product, so features and APIs may differ.

## Development and Testing

The repository includes 48 test files.

### Tests

- [`tests/api/test_api_entrypoints.py`](tests/api/test_api_entrypoints.py)
- [`tests/api/test_barcode_service.py`](tests/api/test_barcode_service.py)
- [`tests/api/test_code128_api_success.py`](tests/api/test_code128_api_success.py)
- [`tests/api/test_symbology_registry.py`](tests/api/test_symbology_registry.py)
- [`tests/conftest.py`](tests/conftest.py)
- [`tests/encoding/test_code128_golden_vectors.py`](tests/encoding/test_code128_golden_vectors.py)
- [Browse all test files](tests)

### Focused Commands and Repository Scripts

```bash
python -m pip install -e .
```

## License

This project is available under the [MIT License](LICENSE). It permits use, modification, distribution, and commercial use when the license and copyright notice are retained.
