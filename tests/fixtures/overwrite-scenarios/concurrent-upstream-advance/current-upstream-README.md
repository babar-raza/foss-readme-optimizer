# AcmeCells FOSS for Java

Open-source Java library for spreadsheets: XLSX read/write, formulas, and CSV export.

## Features

- Read XLSX workbooks
- Write XLSX workbooks
- Formula recalculation
- CSV export

## Installation

Add the dependency (version 2.0.0):

```xml
<dependency>
  <groupId>org.acmesoft</groupId>
  <artifactId>acmecells-foss</artifactId>
  <version>2.0.0</version>
</dependency>
```

## Quick start

```java
Workbook wb = Workbook.load("report.xlsx");
wb.exportCsv("out.csv");
```

## Documentation

See https://docs.acmesoft.org/cells/v2/

## License

MIT License — see LICENSE.
