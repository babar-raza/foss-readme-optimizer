# AcmeCells FOSS for Java

<!-- readme-agent:callout hash="sha256:25e2f3a3e8cfa955777b03e96eee6ab682a7f5c9b467e1313679f640923d035c" schema="2" -->
> 🆓 Open-source catalog: [AcmeCells FOSS for Java](https://products.acmesoft.org/cells/java/)  
> 💼 Commercial edition: [AcmeCells for Java](https://products.acmesoft.com/cells/java/?utm_source=github&utm_medium=readme&utm_campaign=central-agent-lab)
<!-- readme-agent:callout -->


Open-source Java library for reading and writing spreadsheet files.

## Features

- Read XLSX workbooks
- Write XLSX workbooks
- Formula recalculation

## Installation

Add the dependency (version 2.0.0):

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

<!-- readme-agent:resources hash="sha256:25e2f3a3e8cfa955777b03e96eee6ab682a7f5c9b467e1313679f640923d035c" schema="2" -->
### Related Aspose Resources

- **Open-source (FOSS) catalog:** [AcmeCells FOSS for Java](https://products.acmesoft.org/cells/java/)
- **Commercial edition:** [AcmeCells for Java](https://products.acmesoft.com/cells/java/?utm_source=github&utm_medium=readme&utm_campaign=central-agent-lab)

AcmeCells FOSS is the open source edition of the AcmeCells family and covers everyday spreadsheet automation. Teams that need advanced pivot, charting, or priority support can move to the commercial edition, which offers a straightforward upgrade path from this library.
<!-- readme-agent:resources:end -->
