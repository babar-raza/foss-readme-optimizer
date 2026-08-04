# Aspose.Words FOSS for Python

[![PyPI: aspose-words-foss](https://img.shields.io/pypi/v/aspose-words-foss.svg?label=PyPI)](https://pypi.org/project/aspose-words-foss/) ![Python versions](https://img.shields.io/pypi/pyversions/aspose-words-foss.svg) ![Requires: Python >=3.10,<3.13](https://img.shields.io/badge/Requires-Python%20%3E%3D3.10%2C%3C3.13-blue) [![License: MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE) [![Contributors: aspose-words-foss/Aspose.Words-FOSS-for-Python](https://img.shields.io/github/contributors/aspose-words-foss/Aspose.Words-FOSS-for-Python.svg)](https://github.com/aspose-words-foss/Aspose.Words-FOSS-for-Python/graphs/contributors)

Aspose.Words FOSS for Python provides Document loading from file path for developers using Python.

## Navigation

- [At a glance](#at-a-glance)
- [Key capabilities](#key-capabilities)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Scope and limitations](#scope-and-limitations)
- [License](#license)

## At a glance

```mermaid
flowchart LR
  subgraph Inputs["Inputs and formats"]
    input_1["DOC files"]
    input_2["DOCX files"]
    input_3["RTF files"]
    input_4["Plain text files"]
  end

  product["Aspose.Words FOSS for Python"]

  subgraph Capabilities["Core capabilities"]
    capability_1["Document loading from file path"]
    capability_2["SaveFormat constants for output formats"]
    capability_3["LoadOptions for input format specification"]
    capability_4["Stream-based document loading"]
    capability_5["Markdown export with formatting"]
    capability_6["PDF export via fpdf2"]
  end

  subgraph Outputs["Outputs and accessible content"]
    output_1["DOCX files"]
    output_2["PDF files"]
    output_3["Plain text files"]
    output_4["Markdown files"]
  end

  input_1 --- product
  input_2 --- product
  input_3 --- product
  input_4 --- product
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
```

## Key capabilities

- Document loading from file path.
- SaveFormat constants for output formats.
- LoadOptions for input format specification.
- Stream-based document loading.
- Markdown export with formatting.
- PDF export via fpdf2.

## Installation

```bash
python -m pip install aspose-words-foss
```

Requires Python >=3.10,<3.13.

Optional dependency groups declared in `pyproject.toml`:
- `dev`: `python -m pip install "aspose-words-foss[dev]"`

Required runtime dependencies declared in `pyproject.toml`: `olefile>=0.46`, `fpdf2>=2.7.5`, `pydantic>=2.0.0`.

## Quick start

### Minimal verified example

```python
import aspose.words_foss as aw

opts = aw.loading.LoadOptions()
```

## Scope and limitations

The package manifest classifies this release as **Beta**.

[Aspose.Words FOSS for Python](https://products.aspose.org/words/python/) and [Aspose.Words Enterprise Edition](https://products.aspose.com/words/python/) are separate products. This README documents the FOSS implementation; do not assume API or feature parity beyond verified behavior.

## License

This project is available under the [MIT License](LICENSE). It permits use, modification, distribution, and commercial use when the license and copyright notice are retained.
