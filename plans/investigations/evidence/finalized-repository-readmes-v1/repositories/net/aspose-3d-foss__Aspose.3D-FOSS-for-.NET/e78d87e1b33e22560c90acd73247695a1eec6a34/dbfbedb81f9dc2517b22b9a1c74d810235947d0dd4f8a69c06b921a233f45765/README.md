# Aspose.3D FOSS for .NET

[![NuGet: Aspose.3D.FOSS](https://img.shields.io/nuget/v/Aspose.3D.FOSS.svg?label=NuGet)](https://www.nuget.org/packages/Aspose.3D.FOSS) ![Platform: .NET](https://img.shields.io/badge/Platform-.NET-blue) [![Repository: Source](https://img.shields.io/badge/Repository-Source-blue)](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-.NET/tree/e78d87e1b33e22560c90acd73247695a1eec6a34) [![License: MIT](https://img.shields.io/badge/License-MIT-blue)](LICENSE) [![Contributors: aspose-3d-foss/Aspose.3D-FOSS-for-.NET](https://img.shields.io/github/contributors/aspose-3d-foss/Aspose.3D-FOSS-for-.NET.svg)](https://github.com/aspose-3d-foss/Aspose.3D-FOSS-for-.NET/graphs/contributors)

Aspose.3D FOSS for .NET provides Scene graph management for developers using .NET.

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
    input_1["FBX files"]
    input_2["OBJ files"]
    input_3["STL files"]
    input_4["glTF files"]
  end

  product["Aspose.3D FOSS for .NET"]

  subgraph Capabilities["Core capabilities"]
    capability_1["Scene graph management"]
    capability_2["Common file format support (OBJ, STL, FBX, glTF)"]
    capability_3["Node hierarchy and entity attachment"]
    capability_4["Reads FBX files"]
    capability_5["Writes FBX files"]
    capability_6["Reads OBJ files"]
  end

  subgraph Outputs["Outputs and accessible content"]
    output_1["FBX files"]
    output_2["OBJ files"]
    output_3["STL files"]
    output_4["glTF files"]
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

- Scene graph management.
- Common file format support (OBJ, STL, FBX, glTF).
- Node hierarchy and entity attachment.

## Installation

Install the package published for this repository:

```bash
dotnet add package Aspose.3D.FOSS --version 26.1.0
```

The package was verified against NuGet.

## Quick start

### Minimal verified example

```dotnet
using Aspose.ThreeD; var scene = new Scene(); scene.Save(System.IO.Path.GetTempFileName());
```

## Scope and limitations

- License/trial management APIs not available

[Aspose.3D FOSS for .NET](https://products.aspose.org/3d/net/) and [Aspose.3D Enterprise Edition](https://products.aspose.com/3d/net/) are separate products. This README documents the FOSS implementation; do not assume API or feature parity beyond verified behavior.

## License

This project is available under the [MIT License](LICENSE). It permits use, modification, distribution, and commercial use when the license and copyright notice are retained.
