import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const ROOT = path.resolve("..");
const DATA_PATH = path.join(ROOT, "data", "math_knowledge_data.json");
const OUTPUT_PATH = path.join(ROOT, "mathgpt_math_knowledge_v0.1.xlsx");
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

function styleTable(sheet, rangeAddress, tableName, widths) {
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
    table.name = tableName;
  } catch {
    // Tables are a convenience; keep the populated worksheet if table creation fails.
  }
}

function addDataSheet(name, rows, columns, widths) {
  const sheet = workbook.worksheets.add(name);
  const headers = columns.map((column) => column.header);
  const matrix = [
    headers,
    ...rows.map((row) => columns.map((column) => cellValue(row[column.key]))),
  ];
  const endColumn = colLetter(headers.length - 1);
  const rangeAddress = `A1:${endColumn}${matrix.length}`;
  sheet.getRange(rangeAddress).values = matrix;
  styleTable(sheet, rangeAddress, `tbl_${name.replace(/[^A-Za-z0-9_]/g, "_")}`, widths);
  return sheet;
}

function addReadme() {
  const sheet = workbook.worksheets.add("README");
  const rows = [
    ["MathGPT 数学知识构建 v0.1", ""],
    ["生成日期", data.summary.build_date],
    ["范围", "仅数学；物理/化学未处理"],
    ["官方来源", data.summary.standard_source],
    ["补充来源", data.summary.vendor_source],
    ["核心原则", "PDF 决定官方学段边界；MD 只补充细粒度知识点、题型、方法和别名"],
    ["初中粒度", "课程标准只提供第四学段 7-9 年级，未自动拆初一/初二/初三"],
    ["审核状态", "本工作簿是机器抽取/候选映射版本；上线前需人工审核 review_queue 和高风险 method_boundary"],
    ["standard_units", data.summary.standard_units_count],
    ["vendor_nodes", data.summary.vendor_nodes_count],
    ["knowledge_mappings", data.summary.mappings_count],
    ["canonical_knowledge_nodes", data.summary.canonical_nodes_count],
    ["method_boundaries", data.summary.method_boundaries_count],
    ["review_queue", data.summary.review_queue_count],
    ["使用建议", "先筛 review_queue.risk=high 与 relation_machine=method/enrichment/out_of_scope，再抽检 auto_candidate 映射"],
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
  applyWidths(sheet, [220, 680]);

  const relationCounts = Object.entries(
    data.knowledge_mappings.reduce((acc, row) => {
      acc[row.relation] = (acc[row.relation] || 0) + 1;
      return acc;
    }, {}),
  ).map(([relation, count]) => [relation, count]);
  const riskCounts = Object.entries(
    data.knowledge_mappings.reduce((acc, row) => {
      acc[row.risk] = (acc[row.risk] || 0) + 1;
      return acc;
    }, {}),
  ).map(([risk, count]) => [risk, count]);

  const start = rows.length + 3;
  sheet.getRange(`A${start}:B${start + relationCounts.length}`).values = [
    ["relation", "count"],
    ...relationCounts,
  ];
  sheet.getRange(`D${start}:E${start + riskCounts.length}`).values = [
    ["risk", "count"],
    ...riskCounts,
  ];
  sheet.getRange(`A${start}:E${start + Math.max(relationCounts.length, riskCounts.length)}`).format = {
    font: { name: "Arial", size: 10, color: "#111827" },
    borders: { preset: "inside", style: "thin", color: "#E5E7EB" },
  };
  sheet.getRange(`A${start}:B${start}`).format.fill = { type: "solid", color: "#D9EAF7" };
  sheet.getRange(`D${start}:E${start}`).format.fill = { type: "solid", color: "#FCE4D6" };
  try {
    sheet.charts.add("bar", {
      title: "Mapping Relation Counts",
      categories: relationCounts.map((row) => row[0]),
      series: [{ name: "count", values: relationCounts.map((row) => row[1]) }],
      hasLegend: false,
      from: { row: 17, col: 6 },
      extent: { widthPx: 520, heightPx: 280 },
    });
  } catch {
    // Chart is supplemental.
  }
  return sheet;
}

const standardColumns = [
  ["standard_unit_id", 170],
  ["stage", 90],
  ["grade_min", 80],
  ["grade_max", 80],
  ["domain", 110],
  ["theme", 150],
  ["section_type", 90],
  ["item_no", 70],
  ["pdf_page", 75],
  ["book_page", 80],
  ["statement", 560],
  ["keywords", 260],
  ["ocr_confidence", 95],
  ["review_status", 150],
].map(([key, width]) => ({ key, header: key, width }));

const vendorColumns = [
  ["vendor_node_id", 130],
  ["vendor_stage", 80],
  ["path_text", 520],
  ["raw_name", 180],
  ["clean_name", 180],
  ["node_type", 150],
  ["inferred_domain", 120],
  ["children_count", 90],
  ["aliases", 220],
  ["clean_rule", 180],
  ["source_line", 90],
  ["review_status", 150],
].map(([key, width]) => ({ key, header: key, width }));

const vendorById = new Map(data.vendor_nodes.map((row) => [row.vendor_node_id, row]));
const unitById = new Map(data.standard_units.map((row) => [row.standard_unit_id, row]));
const mappingRows = data.knowledge_mappings.map((mapping) => {
  const vendor = vendorById.get(mapping.vendor_node_id) || {};
  const unit = unitById.get(mapping.standard_unit_id) || {};
  return {
    ...mapping,
    vendor_stage: vendor.vendor_stage || "",
    vendor_path: vendor.path_text || "",
    node_type_machine: vendor.node_type || "",
    standard_stage: unit.stage || "",
    standard_domain: unit.domain || vendor.inferred_domain || "",
    standard_theme: unit.theme || "",
    standard_statement: unit.statement || "",
    pdf_page: unit.pdf_page || "",
    book_page: unit.book_page || "",
  };
});

const mappingColumns = [
  ["mapping_id", 130],
  ["relation", 120],
  ["confidence", 90],
  ["risk", 80],
  ["review_status", 165],
  ["vendor_stage", 90],
  ["node_type_machine", 140],
  ["vendor_path", 520],
  ["standard_stage", 90],
  ["standard_domain", 120],
  ["standard_theme", 160],
  ["standard_statement", 560],
  ["pdf_page", 75],
  ["book_page", 80],
  ["vendor_node_id", 130],
  ["standard_unit_id", 180],
  ["knowledge_id", 160],
  ["evidence", 620],
].map(([key, width]) => ({ key, header: key, width }));

const canonicalColumns = [
  ["knowledge_id", 160],
  ["canonical_name", 190],
  ["aliases", 260],
  ["subject", 75],
  ["domain", 120],
  ["theme", 160],
  ["node_type", 120],
  ["allowed_grade_min", 120],
  ["allowed_grade_max", 120],
  ["source_authority", 210],
  ["status", 190],
  ["standard_unit_id", 180],
  ["related_vendor_node_ids", 260],
  ["version", 160],
].map(([key, width]) => ({ key, header: key, width }));

const methodColumns = [
  ["method_id", 130],
  ["method_name", 190],
  ["method_type", 210],
  ["allowed_grade_min", 120],
  ["allowed_grade_max", 120],
  ["forbidden_before_grade", 150],
  ["reason", 600],
  ["related_vendor_nodes", 260],
  ["review_status", 180],
  ["version", 160],
].map(([key, width]) => ({ key, header: key, width }));

const reviewColumns = [
  ["mapping_id", 130],
  ["vendor_path", 520],
  ["vendor_stage", 90],
  ["node_type_machine", 150],
  ["standard_stage", 90],
  ["standard_domain", 120],
  ["standard_theme", 160],
  ["standard_statement", 560],
  ["source_page", 90],
  ["relation_machine", 130],
  ["confidence", 90],
  ["risk", 80],
  ["reviewer_relation", 150],
  ["reviewer_grade_min", 140],
  ["reviewer_grade_max", 140],
  ["reviewer_note", 360],
  ["decision", 180],
].map(([key, width]) => ({ key, header: key, width }));

addReadme();
addDataSheet("stage_theme_table", data.stage_theme_table, [
  ["domain", 120],
  ["stage", 90],
  ["grade_min", 80],
  ["grade_max", 80],
  ["themes", 360],
].map(([key, width]) => ({ key, header: key, width })), [120, 90, 80, 80, 360]);
addDataSheet("standard_units", data.standard_units, standardColumns, standardColumns.map((c) => c.width));
addDataSheet("vendor_nodes", data.vendor_nodes, vendorColumns, vendorColumns.map((c) => c.width));
addDataSheet("knowledge_mappings", mappingRows, mappingColumns, mappingColumns.map((c) => c.width));
addDataSheet("canonical_nodes", data.canonical_knowledge_nodes, canonicalColumns, canonicalColumns.map((c) => c.width));
addDataSheet("method_boundary", data.method_boundaries, methodColumns, methodColumns.map((c) => c.width));
addDataSheet("review_queue", data.review_queue, reviewColumns, reviewColumns.map((c) => c.width));
addDataSheet("quality_checks", data.quality_checks, [
  ["check", 220],
  ["value", 160],
  ["note", 620],
].map(([key, width]) => ({ key, header: key, width })), [220, 160, 620]);

for (const sheetName of [
  "README",
  "standard_units",
  "knowledge_mappings",
  "canonical_nodes",
  "method_boundary",
  "review_queue",
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

await fs.mkdir(ROOT, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(OUTPUT_PATH);
console.log(`saved ${OUTPUT_PATH}`);
