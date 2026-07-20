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

<!-- central-agent:resources fp="sha256:7364ccf270100772" v="1" -->

## Resources

- [AcmeCells FOSS for Java](https://products.acmesoft.org/cells/java/)
- [AcmeCells for Java](https://products.acmesoft.com/cells/java/?utm_source=github&utm_medium=readme&utm_campaign=central-agent-lab)

AcmeCells FOSS for Java is the open-source edition, providing core spreadsheet functionality—including cell editing, formula calculation, and basic formatting—under an open license for community use and modification. It serves developers and organizations seeking a free, transparent foundation for embedding spreadsheet capabilities in Java applications. For those requiring advanced features like real-time collaboration, enterprise-grade security, advanced charting, and dedicated support, a commercial edition is available as an upgrade path, offering enhanced tools and professional services.

<!-- central-agent:resources:end -->
