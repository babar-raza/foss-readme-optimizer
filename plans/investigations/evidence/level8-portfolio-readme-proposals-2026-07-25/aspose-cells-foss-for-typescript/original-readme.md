# Aspose.Cells FOSS for TypeScript

Aspose.Cells FOSS is an open-source TypeScript library for creating, loading, editing, and saving Excel `.xlsx` workbooks without requiring Microsoft Excel.

## Highlights

- Aspose.Cells-compatible API surface for common XLSX scenarios
- `.xlsx` load/save from file paths and streams
- Cell values, formulas, styles, merges, and number formats comments, pictures
- Conditional formatting, data validation, hyperlinks, names, tables, charts, shapes, comments, pictures
- HTML import and export support

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript.git
cd Aspose.Cells-FOSS-for-TypeScript
npm install
```

## Quick Start

### Create, style, and save a workbook

```typescript
import { Workbook, Style } from "./aspose_cells";

const workbook = new Workbook();
const sheet = workbook.worksheets.get(0)!;

sheet.name = "Products";
sheet.putValue("A1", "Product");
sheet.putValue("B1", "Price");
sheet.putValue("A2", "Apple");
sheet.putValue("B2", 2.99);
sheet.putValue("A3", "Orange");
sheet.putValue("B3", 1.99);
const cellB4 = sheet.getCell2("B4");
cellB4.setFormula("=SUM(B2:B3)");

const headerStyle = new Style();
headerStyle.setBold(true);
headerStyle.setFontColor("FFFFFFFF");
headerStyle.setForegroundColor("FF2278D4");

const cellA1 = sheet.getCell2("A1");
cellA1.setStyle(headerStyle);
const cellB1 = sheet.getCell2("B1");
cellB1.setStyle(headerStyle);

await workbook.save("products.xlsx");
```

### Load and update a workbook

```typescript
import { Workbook } from "./aspose_cells";

const workbook = await Workbook.load("input.xlsx");
const sheet = workbook.worksheets.get(0)!;

const cell = sheet.getCell2("A1");
cell.putValue("Updated");

console.log("Loaded value:", sheet.getCell(0, 0)?.value);

await workbook.save("updated.xlsx");
```

## Supported Areas

- Workbook and worksheet management
- Cells and formulas
- Style model (font, fill, borders, alignment, number formats, protection)
- Worksheet settings (column widths, row heights, merged cells, auto filter, hidden rows)
- Hyperlinks and defined names
- Data validation and conditional formatting
- Page setup and print-related settings
- Tables (`ListObjects`)
- Pictures / images
- Document properties
For runnable examples, see [`examples/`](examples/):

- `examples/cell_values.ts`
- `examples/styles.ts`
- `examples/data_validation.ts`
- `examples/auto_filter.ts`
- `examples/hyperlinks.ts`
- `examples/worksheet_management.ts`
- `examples/protection.ts`
- `examples/export.ts`
- `examples/html_export.ts`

## Build from Source

Run commands from the repository root:

```bash
npm install
npx tsc --noEmit
```

## Compatibility

- Node.js 18+
- TypeScript 5+

## License

MIT. See [License/LICENSE.txt](https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript/blob/master/License/LICENSE.txt).

## Support

- Issues: <https://github.com/aspose-cells-foss/Aspose.Cells-FOSS-for-TypeScript/issues>
