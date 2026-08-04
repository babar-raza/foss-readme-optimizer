# Aspose.Cells FOSS for Java

[![Maven Central: org.aspose:aspose-cells-foss](https://img.shields.io/maven-central/v/org.aspose/aspose-cells-foss.svg?label=Maven%20Central)](https://central.sonatype.com/artifact/org.aspose/aspose-cells-foss) ![Platform: Java](https://img.shields.io/badge/Platform-Java-blue) ![Requires: Java 17](https://img.shields.io/badge/Requires-Java%2017-blue) [![License: MIT](https://img.shields.io/badge/License-MIT-blue)](License/LICENSE.txt) [![Contributors: aspose-cells-foss/Aspose.Cells-FOSS-for-Java](https://img.shields.io/github/contributors/aspose-cells-foss/Aspose.Cells-FOSS-for-Java.svg)](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-Java/graphs/contributors)

Aspose.Cells FOSS for Java is a Java 17 spreadsheet library for developers using Java to create, load, modify, and save Excel .xlsx workbooks. It supports reading and writing XLSX files, cell values (strings, numbers, booleans, dates, formulas), defined names, and chart creation for 21 standard chart types.

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
    input_1["XLSX files"]
  end

  product["Aspose.Cells FOSS for Java"]

  subgraph Capabilities1["Core capabilities 1 of 2"]
    capability_1["Read XLSX"]
    capability_2["Write XLSX"]
    capability_3["Cell values (strings, numbers, booleans, dates, formulas)"]
    capability_4["Defined names"]
    capability_5["Chart creation (21 types via ChartCollection.add())"]
    capability_6["Load diagnostics and repair reporting"]
  end

  subgraph Capabilities2["Core capabilities 2 of 2"]
    capability_7["Cell values for strings, numbers, booleans, date/time values, and formulas"]
    capability_8["Chart creation for 21 standard chart types via ChartCollection.add()"]
    capability_9["Load diagnostics, repair reporting, preservation of unsupported package parts"]
  end

  subgraph Outputs["Outputs and accessible content"]
    output_1["XLSX files"]
  end

  input_1 --- product
  product --- capability_1
  product --- capability_2
  product --- capability_3
  product --- capability_4
  product --- capability_5
  product --- capability_6
  product --- capability_7
  product --- capability_8
  product --- capability_9
  product --- output_1
```

## Key capabilities

- Cell values for strings, numbers, booleans, date/time values, and formulas.
- Defined names.
- Chart creation for 21 standard chart types via ChartCollection.add().
- Load diagnostics, repair reporting, and preservation of unsupported package parts.

## Installation

Install the package published for this repository:

```xml
<dependency>
  <groupId>org.aspose</groupId>
  <artifactId>aspose-cells-foss</artifactId>
  <version>26.7.0</version>
</dependency>
```

The coordinate was verified against Maven Central.

## Quick start

### Minimal verified example

```java
import org.aspose.cells_foss.Cell;
import org.aspose.cells_foss.Style;
import org.aspose.cells_foss.Workbook;
import org.aspose.cells_foss.Worksheet;

public class Main {
    public static void main(String[] args) {
        try (Workbook workbook = new Workbook()) {
            Worksheet sheet = workbook.getWorksheets().get(0);
            sheet.setName("Report");

            sheet.getCells().get("A1").putValue("Revenue");
            sheet.getCells().get("B1").putValue(12500.75);

            Cell total = sheet.getCells().get("B1");
            Style style = total.getStyle();
            style.getFont().setBold(true);
            style.setCustom("#,##0.00");
            total.setStyle(style);

            sheet.getCells().getRows().get(0).setHeight(22.0);
            sheet.getCells().getColumns().get(1).setWidth(14.5);

            workbook.save("report.xlsx");
        }
    }
}
```

## Scope and limitations

[Aspose.Cells FOSS for Java](https://products.aspose.org/cells/java/) and [Aspose.Cells Enterprise Edition](https://products.aspose.com/cells/java/) are separate products. This README documents the FOSS implementation; do not assume API or feature parity beyond verified behavior.

## License

This project is available under the [MIT License](License/LICENSE.txt). It permits use, modification, distribution, and commercial use when the license and copyright notice are retained.
