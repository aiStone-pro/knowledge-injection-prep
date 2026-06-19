import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const ROOT = path.resolve("..");
const DATA_PATH = path.join(ROOT, "data", "physics_knowledge_data.json");
const OUTPUT_PATH = path.join(ROOT, "physics_knowledge_v0.1.xlsx");
const PREVIEW_DIR = path.join(ROOT, "tmp", "workbook_previews");

const data = JSON.parse(await fs.readFile(DATA_PATH, "utf8"));
const workbook = Workbook.create();
let tableSeq = 1;

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
  if (typeof value === "string" && value.length > 32000) {
    return value.slice(0, 31950) + " ...[truncated]";
  }
  return value;
}

function applyWidths(sheet, widths) {
  widths.forEach((width, index) => {
    const col = colLetter(index);
    sheet.getRange(`${col}:${col}`).format.columnWidthPx = width;
  });
}

function styleTable(sheet, rangeAddress, widths) {
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
    table.name = `tbl_phy_${tableSeq++}`;
  } catch {
    // Table styling is helpful for review, but the worksheet data is the source of truth.
  }
}

function addDataSheet(name, rows, columns) {
  const sheet = workbook.worksheets.add(name);
  const headers = columns.map((column) => column.header);
  const matrix = [
    headers,
    ...rows.map((row) => columns.map((column) => cellValue(row[column.key]))),
  ];
  const endColumn = colLetter(headers.length - 1);
  const rangeAddress = `A1:${endColumn}${matrix.length}`;
  sheet.getRange(rangeAddress).values = matrix;
  styleTable(sheet, rangeAddress, columns.map((column) => column.width));
  return sheet;
}

function countBy(rows, key) {
  return Object.entries(
    rows.reduce((acc, row) => {
      const value = row[key] || "";
      acc[value] = (acc[value] || 0) + 1;
      return acc;
    }, {}),
  ).sort((a, b) => String(a[0]).localeCompare(String(b[0]), "zh-Hans-CN"));
}

function addReadme() {
  const sheet = workbook.worksheets.add("README");
  const rows = [
    ["MathGPT 义务教育物理知识构建 v0.1", ""],
    ["生成日期", "2026-06-18"],
    ["范围", "义务教育物理课程标准 2022；初中 7-9 年级整体粒度"],
    ["官方来源", data.metadata.source_pdf],
    ["补充来源", data.metadata.source_md],
    ["核心原则", "PDF 决定官方学段边界；MD 只补充细粒度知识点、题型、方法和别名"],
    ["抽取页段", `${data.metadata.content_pdf_page_range}；${data.metadata.book_page_offset}`],
    ["审核状态", "本工作簿是 OCR + 规则抽取 + 机器候选映射版本；上线前需人工审核 review_queue 和 method_boundary"],
    ["人工整理候选规则", "只取 section_type=内容要求；statement 移除“简单”、例号引用，并补齐末尾标点"],
    ["standard_units", data.standard_units.length],
    ["人工整理候选", data["人工整理候选"].length],
    ["vendor_nodes", data.vendor_nodes.length],
    ["knowledge_mappings", data.knowledge_mappings.length],
    ["canonical_nodes", data.canonical_knowledge_nodes.length],
    ["method_boundaries", data.method_boundaries.length],
    ["review_queue", data.review_queue.length],
    ["使用建议", "先看 人工整理候选.statement 是否可作为 prompt 白名单；再判断 vendor_nodes/knowledge_mappings 是否值得继续投入"],
  ];
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
  applyWidths(sheet, [230, 760]);

  const sectionCounts = countBy(data.standard_units, "section_type");
  const relationCounts = countBy(data.knowledge_mappings, "relation");
  const start = rows.length + 3;
  sheet.getRange(`A${start}:B${start + sectionCounts.length}`).values = [
    ["standard_units.section_type", "count"],
    ...sectionCounts,
  ];
  sheet.getRange(`D${start}:E${start + relationCounts.length}`).values = [
    ["mapping.relation", "count"],
    ...relationCounts,
  ];
  sheet.getRange(`A${start}:E${start + Math.max(sectionCounts.length, relationCounts.length)}`).format = {
    font: { name: "Arial", size: 10, color: "#111827" },
    borders: { preset: "inside", style: "thin", color: "#E5E7EB" },
  };
  sheet.getRange(`A${start}:B${start}`).format.fill = { type: "solid", color: "#D9EAF7" };
  sheet.getRange(`D${start}:E${start}`).format.fill = { type: "solid", color: "#FCE4D6" };
  return sheet;
}

function cols(spec) {
  return spec.map(([key, width, header = key]) => ({ key, header, width }));
}

const standardColumns = cols([
  ["standard_unit_id", 170],
  ["source_file", 180],
  ["pdf_page", 75],
  ["book_page", 80],
  ["stage", 90],
  ["grade_min", 80],
  ["grade_max", 80],
  ["domain", 130],
  ["theme_no", 80],
  ["theme", 180],
  ["topic", 180],
  ["section_type", 90],
  ["item_no", 75],
  ["statement", 620],
  ["examples", 560],
  ["keywords", 260],
  ["ocr_confidence", 100],
  ["review_status", 170],
]);

const promptColumns = cols([
  ["candidate_id", 160],
  ["standard_unit_id", 170],
  ["stage", 90],
  ["grade_min", 80],
  ["grade_max", 80],
  ["domain", 130],
  ["theme_no", 80],
  ["theme", 180],
  ["item_no", 75],
  ["statement", 680],
  ["source_statement", 680],
  ["source_examples", 560],
  ["pdf_page", 75],
  ["book_page", 80],
  ["review_status", 170],
  ["human_statement", 680],
]);

const vendorColumns = cols([
  ["vendor_node_id", 130],
  ["source_file", 140],
  ["vendor_stage", 80],
  ["path", 620],
  ["raw_name", 220],
  ["clean_name", 220],
  ["aliases", 260],
  ["clean_rule", 180],
  ["depth", 70],
  ["node_type", 150],
  ["inferred_domain", 130],
  ["children_count", 95],
  ["review_status", 170],
]);

const mappingColumns = cols([
  ["mapping_id", 130],
  ["vendor_node_id", 130],
  ["vendor_path", 620],
  ["standard_unit_id", 170],
  ["standard_domain", 130],
  ["standard_theme", 180],
  ["standard_statement", 620],
  ["relation", 120],
  ["confidence", 90],
  ["risk", 80],
  ["review_status", 170],
  ["candidate_rank", 90],
  ["candidate_2", 520],
  ["candidate_3", 520],
  ["evidence", 620],
]);

const canonicalColumns = cols([
  ["knowledge_id", 150],
  ["canonical_name", 280],
  ["aliases", 260],
  ["subject", 80],
  ["domain", 130],
  ["theme", 180],
  ["node_type", 120],
  ["allowed_grade_min", 120],
  ["allowed_grade_max", 120],
  ["source_authority", 180],
  ["standard_unit_id", 170],
  ["status", 150],
  ["version", 80],
]);

const methodColumns = cols([
  ["method_id", 130],
  ["method_name", 240],
  ["method_type", 240],
  ["allowed_grade_min", 120],
  ["allowed_grade_max", 120],
  ["forbidden_before_grade", 150],
  ["reason", 620],
  ["related_vendor_node_id", 150],
  ["vendor_path", 620],
  ["review_status", 180],
  ["version", 80],
]);

const reviewColumns = cols([
  ["review_id", 130],
  ["priority", 75],
  ["vendor_node_id", 130],
  ["vendor_stage", 90],
  ["vendor_path", 620],
  ["node_type_machine", 150],
  ["standard_unit_id", 170],
  ["standard_domain", 130],
  ["standard_theme", 180],
  ["standard_statement", 620],
  ["relation_machine", 130],
  ["confidence", 90],
  ["risk", 80],
  ["reviewer_relation", 150],
  ["reviewer_grade_min", 140],
  ["reviewer_grade_max", 140],
  ["reviewer_note", 360],
  ["decision", 160],
]);

const qualityColumns = cols([
  ["check", 260],
  ["value", 220],
  ["status", 100],
  ["detail", 620],
]);

addReadme();
addDataSheet("standard_units", data.standard_units, standardColumns);
addDataSheet("人工整理候选", data["人工整理候选"], promptColumns);
addDataSheet("vendor_nodes", data.vendor_nodes, vendorColumns);
addDataSheet("knowledge_mappings", data.knowledge_mappings, mappingColumns);
addDataSheet("canonical_nodes", data.canonical_knowledge_nodes, canonicalColumns);
addDataSheet("method_boundary", data.method_boundaries, methodColumns);
addDataSheet("review_queue", data.review_queue, reviewColumns);
addDataSheet("quality_checks", data.quality_checks, qualityColumns);

for (const sheetName of [
  "README",
  "standard_units",
  "人工整理候选",
  "knowledge_mappings",
  "method_boundary",
  "review_queue",
  "quality_checks",
]) {
  const check = await workbook.inspect({
    kind: "table",
    range: `${sheetName}!A1:H12`,
    include: "values,formulas",
    tableMaxRows: 12,
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
for (const sheetName of workbook.worksheets.items.map((sheet) => sheet.name)) {
  const preview = await workbook.render({ sheetName, range: "A1:H18", scale: 1 });
  await fs.writeFile(
    path.join(PREVIEW_DIR, `${sheetName}.png`),
    Buffer.from(await preview.arrayBuffer()),
  );
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(OUTPUT_PATH);
console.log(`saved ${OUTPUT_PATH}`);
