# Aspose.Cells FOSS for Python

[![PyPI: aspose-cells-foss](https://img.shields.io/pypi/v/aspose-cells-foss.svg?label=PyPI)](https://pypi.org/project/aspose-cells-foss/) ![Python versions](https://img.shields.io/pypi/pyversions/aspose-cells-foss.svg) ![Requires: Python >=3.7](https://img.shields.io/badge/Requires-Python%20%3E%3D3.7-blue) [![License: MIT](https://img.shields.io/badge/License-MIT-blue)](License/LICENSE.txt) [![Contributors: aspose-cells-foss/Aspose.Cells-FOSS-for-Python](https://img.shields.io/github/contributors/aspose-cells-foss/Aspose.Cells-FOSS-for-Python.svg)](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python/graphs/contributors)

![Aspose.Cells FOSS for Python](https://products.aspose.org/media/cells/python/banner-readme.png)

Aspose.Cells FOSS for Python is an open-source library for developers using Python. It reads XLSX files and CSV files and writes XLSX files, CSV files, JSON files, and Markdown files.

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
- [Contributing](#contributing)
- [License](#license)

## At a Glance

```mermaid
flowchart LR
  subgraph INPUTS["Inputs & Formats"]
    direction TB
    I1["XLSX<br/>Format"]
    I2["CSV<br/>Format"]
  end
  PRODUCT["Aspose.Cells FOSS<br/>for Python"]
  subgraph CORE["Core Capabilities"]
    direction LR
    subgraph CORE_LEFT[" "]
      direction TB
      C1["Read and write cell<br/>values"]
      C2["Add, remove, rename,<br/>and manage"]
      C3["Create and modify<br/>charts"]
      C1 ~~~ C2
      C2 ~~~ C3
    end
    subgraph CORE_RIGHT[" "]
      direction TB
      C4["Add dropdown lists,<br/>number ranges"]
      C5["Encrypt and decrypt<br/>XLSX workbooks"]
      C6["Export workbooks to<br/>CSV, JSON"]
      C4 ~~~ C5
      C5 ~~~ C6
    end
    CORE_LEFT ~~~ CORE_RIGHT
  end
  subgraph OUTPUTS["Outputs"]
    direction TB
    O1["<div style='width:150px'>XLSX</div>"]
    O2["<div style='width:150px'>CSV</div>"]
    O3["<div style='width:150px'>JSON</div>"]
    O4["<div style='width:150px'>Markdown</div>"]
  end
  I1 --> PRODUCT
  PRODUCT --> CORE
  CORE --> O1
  classDef product fill:#1F4E79,color:#FFFFFF,stroke:#163A5B,stroke-width:2px,font-weight:bold;
  classDef input fill:#EAF2F8,color:#17324D,stroke:#7EA6C4,stroke-width:1.5px;
  classDef capability fill:#F7F9FC,color:#243447,stroke:#AAB7C4,stroke-width:1.25px;
  classDef output fill:#EAF6EF,color:#244A32,stroke:#78A889,stroke-width:1.5px,font-weight:bold;
  class PRODUCT product;
  class I1,I2 input;
  class C1,C2,C3,C4,C5,C6 capability;
  class O1,O2,O3,O4 output;
  style INPUTS fill:#F8FBFD,stroke:#7EA6C4,stroke-width:1.5px
  style CORE fill:#FFFFFF,stroke:#5F7791,stroke-width:2px
  style CORE_LEFT fill:transparent,stroke:transparent
  style CORE_RIGHT fill:transparent,stroke:transparent
  style OUTPUTS fill:#F7FBF8,stroke:#78A889,stroke-width:1.5px
  linkStyle 5,6,7 stroke:#526D82,stroke-width:2px
```

## Key Capabilities

- **Export workbooks to CSV, JSON, and Markdown** - Create files in the listed output formats. Available through the public `Workbook` and `WorkbookPr` APIs.
- **Encrypt and decrypt XLSX workbooks with AES password protection** - Protect PDF content with RC4 or AES encryption. Available through the public `WorkbookProtection`, `Workbook`, and `Protection` APIs.
- **Export XLSX files** - Create files in the listed output formats. Available through the public `Cell` and `Cells` APIs.
- **Add, remove, rename, and manage worksheets** - Organize workbook sheets by adding, removing, and renaming worksheet entries. Available through the public `Worksheet` API.
- **Create and modify charts** - Build chart objects from worksheet data and update their presentation. Available through the public `Chart` API.
- **Read XLSX tables, rows, and cells** - Traverse tables, rows, and cells. Available through the public `AutoFilter`, `Style`, and `Table` APIs.
- **Read numbered lists and outline elements in XLSX documents** - Inspect numbered lists and outline structures.

## Installation

```bash
python -m pip install aspose-cells-foss
```

Requires Python 3.7 or later.

Install optional dependencies by scenario:

- Installing the `dev` extra: `python -m pip install "aspose-cells-foss[dev]"`

Required runtime dependencies declared in `pyproject.toml`: `pycryptodome>=3.15.0`, `olefile>=0.46`.

## Quick Start

```python
from aspose.cells_foss import Font

font = Font()
```

## Additional Examples

Expand this section to view examples for creating a new excel file, reading an existing excel file, apply styling, add data validation (dropdown list), and browsing repository example files, plus 2 more workflows.

<details>
<summary>View additional examples and results</summary>

### Create a New Excel File

```python
from aspose.cells_foss import Workbook

workbook = Workbook()

worksheet = workbook.worksheets[0]

worksheet.cells["A1"].value = "Hello"
worksheet.cells["B1"].value = "World"
worksheet.cells["A2"].value = 42
worksheet.cells["B2"].value = 3.14

workbook.save("output.xlsx")
```

### Read an Existing Excel File

```python
from aspose.cells_foss import Workbook

workbook = Workbook("input.xlsx")

worksheet = workbook.worksheets[0]

value = worksheet.cells["A1"].value
print(f"Cell A1 contains: {value}")
```

### Apply Styling

```python
from aspose.cells_foss import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
cell = worksheet.cells["A1"]

cell.value = "Styled Text"

style = cell.get_style()
style.font.bold = True
style.font.color = "#FF0000"
style.font.size = 14
cell.apply_style(style)

workbook.save("styled.xlsx")
```

### Add Data Validation (Dropdown List)

```python
from aspose.cells_foss import Workbook, DataValidationType

workbook = Workbook()
worksheet = workbook.worksheets[0]

validation = worksheet.data_validations.add("A1:A10")
validation.type = DataValidationType.LIST
validation.formula1 = '"Option1,Option2,Option3"'

workbook.save("validation.xlsx")
```

### Export to CSV

```python
from aspose.cells_foss import Workbook

workbook = Workbook("input.xlsx")
workbook.save_as_csv("output.csv")
```

### Password Protection

```python
from aspose.cells_foss import Workbook

workbook = Workbook()
worksheet = workbook.worksheets[0]
worksheet.cells["A1"].value = "Confidential Data"

workbook.save("protected.xlsx", password="mypassword")

workbook2 = Workbook("protected.xlsx", password="mypassword")
```

### Repository Example Files

- [`__init__.py`](examples/__init__.py)
- [`output_path_helper.py`](examples/output_path_helper.py)
- [`test_alignment_properties.py`](examples/test_alignment_properties.py)
- [`test_auto_filter.py`](examples/test_auto_filter.py)
- [`test_border_settings.py`](examples/test_border_settings.py)
- [`test_cell_protection_locked.py`](examples/test_cell_protection_locked.py)
- [`test_cell_values.py`](examples/test_cell_values.py)
- [`test_comment_size.py`](examples/test_comment_size.py)
- [`test_comments.py`](examples/test_comments.py)
- [`test_conditional_formatting.py`](examples/test_conditional_formatting.py)
- [`test_create_all_charts.py`](examples/test_create_all_charts.py)
- [`test_create_exceltable.py`](examples/test_create_exceltable.py)
- [`test_create_picture.py`](examples/test_create_picture.py)
- [`test_create_shape.py`](examples/test_create_shape.py)
- [`test_create_sparkline.py`](examples/test_create_sparkline.py)
- [`test_csv_import_export.py`](examples/test_csv_import_export.py)
- [`test_data_validation.py`](examples/test_data_validation.py)
- [`test_document_properties.py`](examples/test_document_properties.py)
- [`test_encryption.py`](examples/test_encryption.py)
- [`test_fill_settings.py`](examples/test_fill_settings.py)
- [`test_font_settings.py`](examples/test_font_settings.py)
- [`test_hyperlinks.py`](examples/test_hyperlinks.py)
- [`test_manual_page_breaks.py`](examples/test_manual_page_breaks.py)
- [`test_merge_cells.py`](examples/test_merge_cells.py)
- [`test_number_formats.py`](examples/test_number_formats.py)
- [`test_print_area.py`](examples/test_print_area.py)
- [`test_workbook_protection.py`](examples/test_workbook_protection.py)
- [`test_worksheet_management.py`](examples/test_worksheet_management.py)
- [`test_worksheet_properties.py`](examples/test_worksheet_properties.py)
- [`test_worksheet_protection.py`](examples/test_worksheet_protection.py)
- [`test_xlsx_to_json.py`](examples/test_xlsx_to_json.py)
- [`test_xlsx_to_markdown.py`](examples/test_xlsx_to_markdown.py)

</details>

## API Reference

The package documents 56 public types across 1 namespaces. Package namespaces include `aspose.cells_foss`. See the complete API reference under Documentation and Resources for members, signatures, and inherited APIs.

<details>
<summary>View public API by namespace</summary>

### Aspose.Cells Namespace (`aspose.cells_foss`)

| Type | Description |
| --- | --- |
| `AgileEncryptionParameters(cipher_algorithm=CipherAlgorithm.AES_256, hash_algorithm=HashAlgorithm.SHA512, spin_count=100000)` | Represents an Agile Encryption Parameters in the public cells FOSS API for Aspose.Cells. Inherits from `EncryptionParameters`. |
| `CSVHandler` | Represents a CSV Handler in the public cells FOSS API for Aspose.Cells. Supports loading CSV, loading CSV from string, and saving CSV. |
| `CSVLoadOptions()` | Configures CSV Load operations through the Aspose.Cells API. |
| `CSVSaveOptions()` | Configures CSV output through the Aspose.Cells API. |
| `Cell(value=None, formula=None)` | Represents a Cell in the public cells FOSS API for Aspose.Cells. Supports applying style, clearing content, and clearing comment. |
| `Cells(worksheet=None)` | Represents a Cells in the public cells FOSS API for Aspose.Cells. Supports clearing content, clearing horizontal page breaks, and clearing vertical page breaks. |
| `Chart(chart_type, upper_left_row, upper_left_column, lower_right_row, lower_right_column)` | Represents a Chart in the public cells FOSS API for Aspose.Cells. Supports adding axis and adding series. |
| `ChartAxis()` | Represents a Chart Axis in the public cells FOSS API for Aspose.Cells. |
| `ChartCollection(worksheet)` | Represents a Chart Collection in the public cells FOSS API for Aspose.Cells. Supports adding areas, adding bars, and adding box whiskers. |
| `ChartErrorBars()` | Represents a Chart Error Bars in the public cells FOSS API for Aspose.Cells. |
| `ChartSeries(values, category_data=None, name=None, chart=None, chart_type=None, x_values=None, series_idx=None, series_order=None)` | Represents a Chart Series in the public cells FOSS API for Aspose.Cells. Supports adding error bars. |
| `ChartType` | Enumerates chart type values. |
| `ChartView3D(chart)` | Represents a Chart View3 D in the public cells FOSS API for Aspose.Cells. |
| `CipherAlgorithm(name, key_bits, alg_id)` | Enumerates cipher algorithm values. |
| `DataValidation(sqref=None)` | Represents a Data Validation in the public cells FOSS API for Aspose.Cells. |
| `DataValidationAlertStyle` | Enumerates data validation alert style values. |
| `DataValidationCollection()` | Represents a Data Validation Collection in the public cells FOSS API for Aspose.Cells. Supports adding validations, clearing content, and retrieving validation. |
| `DataValidationImeMode` | Enumerates data validation ime mode values. |
| `DataValidationOperator` | Enumerates data validation operator values. |
| `DataValidationType` | Enumerates data validation type values. |
| `FillType` | Enumerates fill type values. |
| `Font(name='Calibri', size=11, color='FF000000', bold=False, italic=False, underline=False, strikethrough=False)` | Represents a cells font through the Aspose.Cells API. |
| `HashAlgorithm(name, hash_bytes, alg_id)` | Enumerates hash algorithm values. |
| `HorizontalPageBreakCollection(worksheet)` | Represents a Horizontal Page Break Collection in the public cells FOSS API for Aspose.Cells. Supports clearing content, removing content, and converting content to list. |
| `JsonHandler` | Represents a JSON Handler in the public cells FOSS API for Aspose.Cells. Supports saving JSON and saving JSON to dict. |
| `JsonSaveOptions()` | Configures JSON output through the Aspose.Cells API. |
| `MarkdownHandler` | Represents a Markdown Handler in the public cells FOSS API for Aspose.Cells. Supports saving markdown and saving markdown to string. |
| `MarkdownSaveOptions()` | Configures Markdown output through the Aspose.Cells API. |
| `MsoDrawingType` | Enumerates mso drawing type values. |
| `MsoFillFormat()` | Represents a Mso Fill Format in the public cells FOSS API for Aspose.Cells. |
| `MsoLineDashStyle` | Enumerates mso line dash style values. |
| `MsoLineFormat()` | Represents a Mso Line Format in the public cells FOSS API for Aspose.Cells. |
| `NSeries(chart)` | Represents an N Series in the public cells FOSS API for Aspose.Cells. |
| `NumberFormat` | Represents a Number Format in the public cells FOSS API for Aspose.Cells. Supports retrieving builtin format, checking whether builtin format, and lookuping builtin format. |
| `Picture(worksheet, image_bytes, image_extension, upper_left_row, upper_left_column, lower_right_row, lower_right_column, name=None)` | Represents a Picture in the public cells FOSS API for Aspose.Cells. |
| `PictureCollection(worksheet)` | Represents a Picture Collection in the public cells FOSS API for Aspose.Cells. |
| `SaveFormat` | Enumerates save format values. |
| `Shape(drawing_type=MsoDrawingType.RECTANGLE, upper_left_row=0, upper_left_column=0, lower_right_row=5, lower_right_column=5)` | Represents a Shape in the public cells FOSS API for Aspose.Cells. |
| `ShapeCollection(worksheet)` | Represents a Shape Collection in the public cells FOSS API for Aspose.Cells. Supports adding text boxes. |
| `ShapeFont()` | Represents a Shape font through the Aspose.Cells API. |
| `Sparkline(data_range, cell_reference)` | Represents a Sparkline in the public cells FOSS API for Aspose.Cells. |
| `SparklineEmptyCells` | Enumerates sparkline empty cells values. |
| `SparklineGroup()` | Represents a Sparkline Group in the public cells FOSS API for Aspose.Cells. Supports adding sparklines. |
| `SparklineGroupCollection(worksheet)` | Represents a Sparkline Group Collection in the public cells FOSS API for Aspose.Cells. Supports adding groups. |
| `SparklineType` | Enumerates sparkline type values. |
| `StandardEncryptionParameters(cipher_algorithm=CipherAlgorithm.AES_128, hash_algorithm=HashAlgorithm.SHA1, spin_count=50000)` | Represents a Standard Encryption Parameters in the public cells FOSS API for Aspose.Cells. Inherits from `EncryptionParameters`. |
| `Style()` | Represents a Style in the public cells FOSS API for Aspose.Cells. Supports setting border, setting border color, and setting border style. |
| `Table(name, ref, has_headers=True)` | Represents a Table in the public cells FOSS API for Aspose.Cells. |
| `Worksheet(name='Sheet1')` | Represents a Worksheet in the public cells FOSS API for Aspose.Cells. Supports calculating formula, clearing print area, and clearing tab color. |
| `Workbook(file_path=None, password=None)` | Represents a Workbook in the public cells FOSS API for Aspose.Cells. Supports adding worksheets, copying worksheet, and creating worksheet. |
| `VerticalPageBreakCollection(worksheet)` | Represents a Vertical Page Break Collection in the public cells FOSS API for Aspose.Cells. Supports clearing content, removing content, and converting content to list. |
| `TableCollection(worksheet)` | Represents a Table Collection in the public cells FOSS API for Aspose.Cells. Supports adding with ranges. |
| `TextAlignmentType` | Enumerates text alignment type values. |
| `TextAnchorType` | Enumerates text anchor type values. |
| `TableColumn(col_id, name)` | Represents a Table Column in the public cells FOSS API for Aspose.Cells. |
| `TableStyleInfo()` | Represents a Table Style Info in the public cells FOSS API for Aspose.Cells. |

</details>

## Documentation and Resources

- **[Getting started guide](https://docs.aspose.org/cells/python/)** - installation, walkthroughs, and feature guides for this library.
- **[How-to guides and FAQ](https://kb.aspose.org/cells/python/)** - task-focused answers for common product questions.
- **[Full API reference](https://reference.aspose.org/cells/python/)** - the complete browsable reference for the public API.
- Found a bug or have a feature request? [Open an issue](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Python/issues) on GitHub.

## Scope and Limitations

The library targets the workflows listed above. Three specific constraints are listed below.

- Unsupported chart type for creations are rejected.
- Only Agile encryption is currently supported.
- Only line, bar, pie, area and stock charts are currently supported.

The package manifest classifies this release as **Beta**.

For requirements beyond the FOSS scope described above, explore the [full-featured Aspose.Cells Enterprise Edition](https://products.aspose.com/cells/python/). It is a separate product, so features and APIs may differ.

## Development and Testing

### Focused Commands and Repository Scripts

```bash
python -m pip install -e .
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository

2. Create your feature branch (`git checkout -b feature/amazing-feature`)

3. Commit your changes (`git commit -m 'Add some amazing feature'`)

4. Push to the branch (`git push origin feature/amazing-feature`)

5. Open a Pull Request

## License

This project is available under the [MIT License](License/LICENSE.txt). It permits use, modification, distribution, and commercial use when the license and copyright notice are retained.
