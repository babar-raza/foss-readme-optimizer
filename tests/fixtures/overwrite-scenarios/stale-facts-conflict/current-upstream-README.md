# AcmeCells FOSS for Java

Open-source Java library for reading and writing spreadsheet files.

## Features

- Read XLSX workbooks
- Write XLSX workbooks
- Formula recalculation
- PDF rendering

## Installation

Add the dependency (version 1.2.0):

```xml
<dependency>
  <groupId>org.acmesoft</groupId>
  <artifactId>acmecells-foss</artifactId>
  <version>1.2.0</version>
</dependency>
```

## Quick start

```java
Workbook wb = Workbook.load("report.xlsx");
wb.sheet(0).cell("A1").set("hello");
wb.save("out.xlsx");
```

## Known limitations

- No CSV export support

## Documentation

See https://docs.acmesoft.org/cells/v1/

## License

MIT License — see LICENSE.
