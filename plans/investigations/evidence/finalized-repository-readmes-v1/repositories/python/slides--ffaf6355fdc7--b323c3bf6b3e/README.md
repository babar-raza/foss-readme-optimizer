# Aspose.Slides FOSS for Python

[![PyPI: aspose-slides-foss](https://img.shields.io/pypi/v/aspose-slides-foss.svg?label=PyPI)](https://pypi.org/project/aspose-slides-foss/) ![Python versions](https://img.shields.io/pypi/pyversions/aspose-slides-foss.svg) ![Requires: Python >=3.10](https://img.shields.io/badge/Requires-Python%20%3E%3D3.10-blue) [![License: MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE) [![Contributors: aspose-slides-foss/Aspose.Slides-FOSS-for-Python](https://img.shields.io/github/contributors/aspose-slides-foss/Aspose.Slides-FOSS-for-Python.svg)](https://github.com/aspose-slides-foss/Aspose.Slides-FOSS-for-Python/graphs/contributors)

Aspose.Slides FOSS for Python provides Shapes creation and manipulation for developers using Python.

## Navigation

- [At a glance](#at-a-glance)
- [Key capabilities](#key-capabilities)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Scope and limitations](#scope-and-limitations)
- [Development and testing](#development-and-testing)
- [License](#license)

## At a glance

```mermaid
flowchart LR
  subgraph Inputs["Inputs and formats"]
    input_1["PPTX files"]
  end

  product["Aspose.Slides FOSS for Python"]

  subgraph Capabilities["Core capabilities"]
    capability_1["Shapes creation and manipulation"]
    capability_2["Connector creation"]
    capability_3["Fill formatting"]
    capability_4["Background management"]
    capability_5["Reads PPTX files"]
    capability_6["Writes PPTX files"]
  end

  subgraph Outputs["Outputs and accessible content"]
    output_1["PPTX files"]
    output_2["PPSX files"]
    output_3["PPTM files"]
    output_4["PPSM files"]
    output_5["POTX files"]
  end

  input_1 --- product
  product --- capability_1
  product --- capability_2
  product --- capability_3
  product --- capability_4
  product --- capability_5
  product --- capability_6
  product --- output_1
  product --- output_2
  product --- output_3
  product --- output_4
  product --- output_5
```

## Key capabilities

- Shapes creation and manipulation.
- Connector creation.
- Fill formatting.
- Background management.

## Installation

```bash
python -m pip install aspose-slides-foss
```

Requires Python 3.10 or later.

Required runtime dependencies declared in `pyproject.toml`: `lxml>=4.9`.

## Quick start

### Minimal verified example

```python
from aspose.slides_foss import ShapeType
import aspose.slides_foss as slides
from aspose.slides_foss.export import SaveFormat

with slides.Presentation() as prs:
    slide = prs.slides[0]
    shape = slide.shapes.add_auto_shape(ShapeType.RECTANGLE, 50, 50, 300, 100)
    shape.add_text_frame("Hello, world!")
    prs.save("shapes.pptx", SaveFormat.PPTX)
```

## Scope and limitations

[Aspose.Slides FOSS for Python](https://products.aspose.org/slides/python/) and [Aspose.Slides Enterprise Edition](https://products.aspose.com/slides/python/) are separate products. This README documents the FOSS implementation; do not assume API or feature parity beyond verified behavior.

## Development and testing

The repository includes 29 test files.

<details>
<summary>View development and testing resources</summary>

### Tests

- [`tests/conftest.py`](tests/conftest.py)
- [`tests/test_animation.py`](tests/test_animation.py)
- [`tests/test_axis_formatting.py`](tests/test_axis_formatting.py)
- [`tests/test_background.py`](tests/test_background.py)
- [`tests/test_bubble_scatter.py`](tests/test_bubble_scatter.py)
- [`tests/test_chart_markers.py`](tests/test_chart_markers.py)
- [`tests/test_chart_plot_area.py`](tests/test_chart_plot_area.py)
- [`tests/test_charts.py`](tests/test_charts.py)
- [Browse all test files](tests)


</details>

## License

This project is available under the [MIT License](LICENSE). It permits use, modification, distribution, and commercial use when the license and copyright notice are retained.
