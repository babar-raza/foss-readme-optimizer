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
