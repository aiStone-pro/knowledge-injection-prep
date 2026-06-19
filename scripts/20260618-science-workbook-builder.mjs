import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const ROOT = "/Users/pengjia/EduAgent";

const JOBS = [
  {
    base: path.join(ROOT, "outputs/20260618-highschool-physics-knowledge-v1"),
    dataFile: "highschool_physics_standard_data.json",
    outputFile: "highschool_physics_knowledge_v0.1.xlsx",
    title: "MathGPT 高中物理知识构建 v0.1",
  },
  {
    base: path.join(ROOT, "outputs/20260618-junior-chemistry-knowledge-v1"),
    dataFile: "junior_chemistry_standard_data.json",
    outputFile: "junior_chemistry_knowledge_v0.1.xlsx",
    title: "MathGPT 初中化学知识构建 v0.1",
  },
  {
    base: path.join(ROOT, "outputs/20260618-highschool-chemistry-knowledge-v1"),
    dataFile: "highschool_chemistry_standard_data.json",
    outputFile: "highschool_chemistry_knowledge_v0.1.xlsx",
    title: "MathGPT 高中化学知识构建 v0.1",
  },
];

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

function cols(spec) {
  return spec.map(([key, width, header = key]) => ({ key, header, width }));
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
  applyWidths(sheet, widths);
  try {
    const table = sheet.tables.add(rangeAddress, true);
    table.name = `tbl_science_${tableSeq++}`;
  } catch {
    // Table creation is convenience formatting; range values remain authoritative.
  }
}

function addDataSheet(workbook, name, rows, columns) {
  const sheet = workbook.worksheets.add(name);
  const matrix = [
    columns.map((column) => column.header),
    ...rows.map((row) => columns.map((column) => cellValue(row[column.key]))),
  ];
  const endColumn = colLetter(columns.length - 1);
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

function addReadme(workbook, job, data) {
  const sheet = workbook.worksheets.add("README");
  const rows = [
    [job.title, ""],
    ["生成日期", data.summary.build_date],
    ["范围", data.summary.display_name],
    ["官方来源", data.summary.source],
    ["处理范围", "仅课程标准；不处理好未来/CK12 知识点、映射、方法边界"],
    ["人工整理候选列顺序", "standard_unit_id, stage, grade_min, grade_max, domain, theme, section_type, item_no, pdf_page, book_page, statement, keywords"],
    ["statement 规则", "移除“简单”、例号引用；压缩态度/责任/价值类表述；保留末尾标点"],
    ["standard_units", data.standard_units.length],
    ["人工整理候选", data["人工整理候选"].length],
    ["备注", data.summary.note],
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
  applyWidths(sheet, [240, 820]);

  const domainCounts = countBy(data.standard_units, "domain");
  const start = rows.length + 3;
  sheet.getRange(`A${start}:B${start + domainCounts.length}`).values = [
    ["domain", "standard_units"],
    ...domainCounts,
  ];
  sheet.getRange(`A${start}:B${start + domainCounts.length}`).format = {
    font: { name: "Arial", size: 10, color: "#111827" },
    borders: { preset: "inside", style: "thin", color: "#E5E7EB" },
  };
  sheet.getRange(`A${start}:B${start}`).format.fill = { type: "solid", color: "#D9EAF7" };
}

const standardColumns = cols([
  ["standard_unit_id", 170],
  ["source_file", 220],
  ["pdf_page", 75],
  ["book_page", 80],
  ["stage", 90],
  ["grade_min", 80],
  ["grade_max", 80],
  ["domain", 150],
  ["module", 210],
  ["theme_no", 80],
  ["theme", 300],
  ["section_type", 100],
  ["item_no", 90],
  ["item_title", 230],
  ["statement", 720],
  ["keywords", 320],
  ["ocr_confidence", 110],
  ["review_status", 170],
]);

const promptColumns = cols([
  ["standard_unit_id", 170],
  ["stage", 90],
  ["grade_min", 80],
  ["grade_max", 80],
  ["domain", 150],
  ["theme", 300],
  ["section_type", 100],
  ["item_no", 90],
  ["pdf_page", 75],
  ["book_page", 80],
  ["statement", 760],
  ["keywords", 320],
]);

const qualityColumns = cols([
  ["check", 280],
  ["value", 240],
  ["status", 100],
  ["detail", 720],
]);

async function buildJob(job) {
  tableSeq = 1;
  const dataPath = path.join(job.base, "data", job.dataFile);
  const data = JSON.parse(await fs.readFile(dataPath, "utf8"));
  const workbook = Workbook.create();
  addReadme(workbook, job, data);
  addDataSheet(workbook, "standard_units", data.standard_units, standardColumns);
  addDataSheet(workbook, "人工整理候选", data["人工整理候选"], promptColumns);
  addDataSheet(workbook, "quality_checks", data.quality_checks, qualityColumns);

  for (const sheetName of ["README", "standard_units", "人工整理候选", "quality_checks"]) {
    const check = await workbook.inspect({
      kind: "table",
      range: `${sheetName}!A1:L12`,
      include: "values,formulas",
      tableMaxRows: 12,
      tableMaxCols: 12,
    });
    console.log(check.ndjson);
  }
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 200 },
    summary: "final formula error scan",
  });
  console.log(errors.ndjson);

  const previewDir = path.join(job.base, "tmp", "workbook_previews");
  await fs.mkdir(previewDir, { recursive: true });
  for (const sheetName of workbook.worksheets.items.map((sheet) => sheet.name)) {
    const preview = await workbook.render({ sheetName, range: "A1:L18", scale: 1 });
    await fs.writeFile(path.join(previewDir, `${sheetName}.png`), Buffer.from(await preview.arrayBuffer()));
  }
  const output = await SpreadsheetFile.exportXlsx(workbook);
  const outputPath = path.join(job.base, job.outputFile);
  await output.save(outputPath);

  const bytes = await fs.readFile(outputPath);
  const imported = await SpreadsheetFile.importXlsx(bytes);
  const recheck = await imported.inspect({
    kind: "table",
    range: "人工整理候选!A1:L6",
    include: "values,formulas",
    tableMaxRows: 6,
    tableMaxCols: 12,
  });
  console.log(recheck.ndjson);
  console.log(`saved ${outputPath}`);
}

for (const job of JOBS) {
  await buildJob(job);
}
