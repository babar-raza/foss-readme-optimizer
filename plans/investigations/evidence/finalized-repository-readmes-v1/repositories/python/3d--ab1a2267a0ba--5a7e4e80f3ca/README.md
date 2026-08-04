# Aspose.3D FOSS for Python

[![Version: 26.1.0](https://img.shields.io/badge/Version-26.1.0-blue)](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/tree/ab1a2267a0ba6302311d0c7c4ad01494974c7d76) ![Platform: Python](https://img.shields.io/badge/Platform-Python-blue) [![License: MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE) [![Contributors: aspose-3d-foss/Aspose.3D-FOSS-for-Python](https://img.shields.io/github/contributors/aspose-3d-foss/Aspose.3D-FOSS-for-Python.svg)](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python/graphs/contributors)

Aspose.3D FOSS for Python provides 3D primitives including Box, Cylinder, Sphere, Plane, Dish, Circle, Ellipse, Frustum for developers using Python.

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
    input_1["GLTF - GL Transmission Format (glTF 2.0) files"]
    input_2["OBJ - Wavefront OBJ with full material support files"]
    input_3["STL - Stereo Lithography format files"]
    input_4["3MF - 3D Manufacturing Format files"]
  end

  product["Aspose.3D FOSS for Python"]

  subgraph Capabilities["Core capabilities"]
    capability_1["3D primitives including Box, Cylinder, Sphere, Plane, Dish, Circle, Ellipse,"]
    capability_2["File format import and export for OBJ, GLTF, STL, and 3MF"]
    capability_3["Animation system with keyframe support"]
    capability_4["Writes GLTF - GL Transmission Format (glTF 2.0) files"]
    capability_5["Reads GLTF - GL Transmission Format (glTF 2.0) files"]
    capability_6["Reads OBJ - Wavefront OBJ with full material support files"]
  end

  subgraph Outputs["Outputs and accessible content"]
    output_1["GLTF - GL Transmission Format (glTF 2.0) files"]
    output_2["STL - Stereo Lithography format files"]
    output_3["3MF - 3D Manufacturing Format files"]
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
```

## Key capabilities

- 3D primitives including Box, Cylinder, Sphere, Plane, Dish, Circle, Ellipse, Frustum.
- File format import and export for OBJ, GLTF, STL, and 3MF.
- Animation system with keyframe support.

## Installation

Install the verified immutable repository revision from a local checkout:

```bash
git clone https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-Python.git
cd Aspose.3D-FOSS-for-Python
git checkout --detach ab1a2267a0ba6302311d0c7c4ad01494974c7d76
python -m pip install .
```

`aspose-3d-foss` was installed and exercised from this exact source revision in an isolated, network-disabled verification environment. The matching PyPI receipt did not find a published package, so this README does not present a PyPI package installation command.

## Quick start

### Minimal verified example

```python
from aspose.threed import Scene

scene = Scene()
```

## Scope and limitations

[Aspose.3D FOSS for Python](https://products.aspose.org/3d/python/) and [Aspose.3D Enterprise Edition](https://products.aspose.com/3d/python-net/) are separate products. This README documents the FOSS implementation; do not assume API or feature parity beyond verified behavior.

## Development and testing

The repository includes 34 test files.

<details>
<summary>View development and testing resources</summary>

### Tests

- [`tests/test_3mf_exporter.py`](tests/test_3mf_exporter.py)
- [`tests/test_3mf_importer.py`](tests/test_3mf_importer.py)
- [`tests/test_3mf_material_export.py`](tests/test_3mf_material_export.py)
- [`tests/test_3mf_materials.py`](tests/test_3mf_materials.py)
- [`tests/test_3mf_roundtrip.py`](tests/test_3mf_roundtrip.py)
- [`tests/test_array_list_adapter.py`](tests/test_array_list_adapter.py)
- [`tests/test_collada_exporter.py`](tests/test_collada_exporter.py)
- [`tests/test_collada_importer.py`](tests/test_collada_importer.py)
- [Browse all test files](tests)


</details>

## License

This project is available under the [MIT License](LICENSE). It permits use, modification, distribution, and commercial use when the license and copyright notice are retained.
