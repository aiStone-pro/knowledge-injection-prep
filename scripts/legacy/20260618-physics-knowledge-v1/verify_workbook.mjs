import fs from "node:fs/promises";
import { SpreadsheetFile } from "@oai/artifact-tool";

const bytes = await fs.readFile("../physics_knowledge_v0.1.xlsx");
const workbook = await SpreadsheetFile.importXlsx(bytes);

for (const sheetName of ["README", "standard_units", "人工整理候选", "quality_checks"]) {
  const check = await workbook.inspect({
    kind: "table",
    range: `${sheetName}!A1:H8`,
    include: "values,formulas",
    tableMaxRows: 8,
    tableMaxCols: 8,
  });
  console.log(check.ndjson);
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "reimport formula error scan",
});
console.log(errors.ndjson);
