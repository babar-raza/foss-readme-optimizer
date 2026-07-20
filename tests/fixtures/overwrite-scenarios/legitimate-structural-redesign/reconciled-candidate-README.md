# AcmeCells FOSS for Java

> Spreadsheets for Java: XLSX read/write and formula recalculation. MIT licensed.

## Contents
- [Install](#install) · [First steps](#first-steps) · [Limits](#limits) · [Docs](#docs)

## Install

```xml
<dependency>
  <groupId>org.acmesoft</groupId>
  <artifactId>acmecells-foss</artifactId>
  <version>1.2.0</version>
</dependency>
```

## First steps

```java
Workbook wb = Workbook.load("report.xlsx");
wb.sheet(0).cell("A1").set("hello");
wb.save("out.xlsx");
```

## Limits

- No CSV export support

## Docs

https://docs.acmesoft.org/cells/v1/ — full reference.

## License

MIT License — see LICENSE.

<!-- central-agent:resources fp="sha256:c11e0d1863c973d6" v="1" -->

## Resources

- [AcmeCells FOSS for Java](https://products.acmesoft.org/cells/java/)
- [AcmeCells for Java](https://products.acmesoft.com/cells/java/?utm_source=github&utm_medium=readme&utm_campaign=central-agent-lab)

AcmeCells FOSS is the open source edition of the AcmeCells family and covers everyday spreadsheet automation. Teams that need advanced pivot, charting, or priority support can move to the commercial edition, which offers a straightforward upgrade path from this library.

<!-- central-agent:resources:end -->
