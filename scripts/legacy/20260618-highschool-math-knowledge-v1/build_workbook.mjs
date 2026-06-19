import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const ROOT = path.resolve("..");
const DATA_PATH = path.join(ROOT, "data", "highschool_math_knowledge_data.json");
const OUTPUT_PATH = path.join(ROOT, "highschool_math_knowledge_v0.1.xlsx");
const PREVIEW_DIR = path.join(ROOT, "tmp", "workbook_previews");

const data = JSON.parse(await fs.readFile(DATA_PATH, "utf8"));
const workbook = Workbook.create();

function colLetter(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const mod = (value - 1) % 26;
    result = String.fromCharCode(65 + mod) + result;
    value = Math.floor((value - mod) / 26);
  }
  return result;
}

function cellValue(value) {
  if (value === null || value === undefined) return "";
  if (Array.isArray(value)) return value.join("；");
  if (typeof value === "object") return JSON.stringify(value);
  return value;
}

function applyWidths(sheet, widths) {
  widths.forEach((width, index) => {
    sheet.getRange(`${colLetter(index)}:${colLetter(index)}`).format.columnWidthPx = width;
  });
}

function styleRange(sheet, rangeAddress, widths) {
  const range = sheet.getRange(rangeAddress);
  range.format = {
    font: { name: "Arial", size: 10, color: "#111827" },
    verticalAlignment: "top",
    wrapText: true,
    borders: { preset: "inside", style: "thin", color: "#E5E7EB" },
  };
  range.getRow(0).format = {
    fill: { type: "solid", color: "#1F4E79" },
    font: { name: "Arial", size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
  sheet.freezePanes.freezeRows(1);
  if (widths) applyWidths(sheet, widths);
  try {
    const table = sheet.tables.add(rangeAddress, true);
    table.name = `tbl_${sheet.name.replace(/[^A-Za-z0-9_]/g, "_")}`;
  } catch {
    // Table styling is useful but not required for data integrity.
  }
}

function addDataSheet(name, rows, columns) {
  const sheet = workbook.worksheets.add(name);
  const matrix = [
    columns.map((column) => column.header),
    ...rows.map((row) => columns.map((column) => cellValue(row[column.key]))),
  ];
  const endCol = colLetter(columns.length - 1);
  const rangeAddress = `A1:${endCol}${matrix.length}`;
  sheet.getRange(rangeAddress).values = matrix;
  styleRange(sheet, rangeAddress, columns.map((column) => column.width));
  return sheet;
}

function addReadme() {
  const rows = [
    ["普通高中数学知识构建 v0.1", ""],
    ["生成日期", data.summary.build_date],
    ["范围", "仅高中数学；未写入义务教育数学工作簿"],
    ["来源", data.summary.source],
    ["PDF 页范围", data.summary.pdf_page_range],
    ["抽取对象", "普通高中数学课程标准课程内容：必修课程、选择性必修课程、选修课程"],
    ["prompt 规则", "人工整理候选.statement 已移除“简单”、例/案例编号，并补齐末尾标点"],
    ["standard_units", data.summary.standard_units_count],
    ["人工整理候选", data.summary.prompt_candidates_count],
    ["course_structure", data.summary.course_structure_count],
    ["备注", "standard_units 保留机器抽取原文；人工整理候选用于后续人工审核和最终合并"],
  ];
  const sheet = workbook.worksheets.add("README");
  sheet.getRange(`A1:B${rows.length}`).values = rows;
  sheet.getRange("A1:B1").format = {
    fill: { type: "solid", color: "#1F4E79" },
    font: { name: "Arial", size: 14, bold: true, color: "#FFFFFF" },
  };
  sheet.getRange(`A2:A${rows.length}`).format = {
    fill: { type: "solid", color: "#EAF2F8" },
    font: { name: "Arial", size: 10, bold: true, color: "#111827" },
  };
  sheet.getRange(`A1:B${rows.length}`).format.wrapText = true;
  applyWidths(sheet, [220, 720]);

  const categoryCounts = Object.entries(
    data.standard_units.reduce((acc, row) => {
      acc[row.course_category] = (acc[row.course_category] || 0) + 1;
      return acc;
    }, {}),
  );
  const start = rows.length + 3;
  sheet.getRange(`A${start}:B${start + categoryCounts.length}`).values = [
    ["course_category", "standard_units"],
    ...categoryCounts,
  ];
  sheet.getRange(`A${start}:B${start + categoryCounts.length}`).format = {
    font: { name: "Arial", size: 10, color: "#111827" },
    borders: { preset: "inside", style: "thin", color: "#E5E7EB" },
  };
  sheet.getRange(`A${start}:B${start}`).format.fill = { type: "solid", color: "#D9EAF7" };
  return sheet;
}

const standardColumns = [
  ["standard_unit_id", 180],
  ["course_category", 130],
  ["track", 70],
  ["theme", 190],
  ["unit", 190],
  ["subtopic", 240],
  ["section_type", 90],
  ["item_no", 75],
  ["pdf_page", 75],
  ["book_page", 80],
  ["statement", 620],
  ["prompt_statement_candidate", 620],
  ["is_optional_content", 120],
  ["review_status", 170],
].map(([key, width]) => ({ key, header: key, width }));

const promptColumns = [
  ["standard_unit_id", 180],
  ["stage", 70],
  ["grade_min", 80],
  ["grade_max", 80],
  ["course_category", 130],
  ["track", 70],
  ["theme", 190],
  ["unit", 190],
  ["subtopic", 240],
  ["section_type", 90],
  ["item_no", 75],
  ["pdf_page", 75],
  ["book_page", 80],
  ["statement", 620],
  ["source_statement", 620],
  ["is_optional_content", 120],
  ["review_status", 180],
].map(([key, width]) => ({ key, header: key, width }));

const structureColumns = [
  ["course_category", 130],
  ["track", 70],
  ["theme", 190],
  ["unit", 220],
  ["subtopic", 280],
].map(([key, width]) => ({ key, header: key, width }));

const qualityColumns = [
  ["check", 260],
  ["value", 180],
  ["note", 640],
].map(([key, width]) => ({ key, header: key, width }));

addReadme();
addDataSheet("course_structure", data.course_structure, structureColumns);
addDataSheet("standard_units", data.standard_units, standardColumns);
addDataSheet("人工整理候选", data["人工整理候选"], promptColumns);
addDataSheet("quality_checks", data.quality_checks, qualityColumns);

for (const sheetName of ["README", "course_structure", "standard_units", "人工整理候选", "quality_checks"]) {
  const check = await workbook.inspect({
    kind: "table",
    range: `${sheetName}!A1:H18`,
    include: "values,formulas",
    tableMaxRows: 18,
    tableMaxCols: 8,
  });
  console.log(check.ndjson);
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

await fs.mkdir(PREVIEW_DIR, { recursive: true });
for (const sheet of workbook.worksheets.items) {
  const preview = await workbook.render({ sheetName: sheet.name, range: "A1:H20", scale: 1 });
  await fs.writeFile(path.join(PREVIEW_DIR, `${sheet.name}.png`), Buffer.from(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(OUTPUT_PATH);
console.log(`saved ${OUTPUT_PATH}`);
