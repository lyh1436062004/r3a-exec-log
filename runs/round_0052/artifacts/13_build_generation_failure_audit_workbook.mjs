import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";


const artifactSpecifier = process.env.CODEX_NODE_MODULES
  ? pathToFileURL(path.join(process.env.CODEX_NODE_MODULES, "@oai", "artifact-tool", "dist", "artifact_tool.mjs")).href
  : "@oai/artifact-tool";
const { SpreadsheetFile, Workbook } = await import(artifactSpecifier);


const [inputDir, outputPath, previewDir] = process.argv.slice(2);
if (!inputDir || !outputPath || !previewDir) {
  throw new Error("usage: node builder.mjs <input_dir> <output_xlsx> <preview_dir>");
}

async function readJsonl(filePath) {
  const text = await fs.readFile(filePath, "utf8");
  return text.split(/\r?\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function seededShuffle(rows, seed) {
  let state = seed >>> 0;
  const random = () => {
    state = (1664525 * state + 1013904223) >>> 0;
    return state / 0x100000000;
  };
  const out = [...rows];
  for (let index = out.length - 1; index > 0; index -= 1) {
    const target = Math.floor(random() * (index + 1));
    [out[index], out[target]] = [out[target], out[index]];
  }
  return out;
}

function goldEvidenceText(row) {
  if (typeof row.gold_evidence_rendered === "string" && row.gold_evidence_rendered.trim()) {
    return row.gold_evidence_rendered;
  }
  const evidence = Array.isArray(row.gold_evidence) ? row.gold_evidence : [];
  return evidence.map((item, index) => `Evidence ${index + 1}: ${item}`).join("\n");
}

function applyHeader(range) {
  range.format = {
    fill: "#175C67",
    font: { bold: true, color: "#FFFFFF" },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "inside", style: "thin", color: "#D7E1E3" },
  };
  range.format.rowHeightPx = 34;
}

function applyBody(range) {
  range.format = {
    font: { color: "#17212B", size: 10 },
    verticalAlignment: "top",
    wrapText: true,
    borders: { insideHorizontal: { style: "thin", color: "#E5E9EB" } },
  };
}

function addTable(sheet, address, name) {
  const table = sheet.tables.add(address, true, name);
  table.style = "TableStyleMedium2";
  table.showFilterButton = true;
  table.showBandedRows = true;
  return table;
}

const cases = await readJsonl(path.join(inputDir, "case_summary.jsonl"));
const calls = await readJsonl(path.join(inputDir, "call_details.jsonl"));
if (cases.length !== 381) throw new Error(`expected 381 case rows, got ${cases.length}`);
if (calls.length !== 1143) throw new Error(`expected 1143 call rows, got ${calls.length}`);
const auditRows = seededShuffle(cases, 20260714);

const workbook = Workbook.create();
const instructions = workbook.worksheets.add("审核说明");
const audit = workbook.worksheets.add("人工审核");
const machine = workbook.worksheets.add("机器判定");
const details = workbook.worksheets.add("调用明细");
const summary = workbook.worksheets.add("汇总");
for (const sheet of [instructions, audit, machine, details, summary]) sheet.showGridLines = false;

instructions.getRange("A1:H1").merge();
instructions.getRange("A1").values = [["Generation Failure 人工审核说明"]];
instructions.getRange("A1:H1").format = {
  fill: "#123C46",
  font: { bold: true, color: "#FFFFFF", size: 18 },
  verticalAlignment: "center",
};
instructions.getRange("A1:H1").format.rowHeightPx = 46;
const instructionRows = [
  ["审核目标", "判断 benchmark gold evidence 是否充分，并独立审核 deepseek-v4-flash 三次回答是否仍失败。"],
  ["盲审纪律", "先只查看“人工审核”页，不要打开“机器判定”；完成本人的标签后再比较 LongCat-2.0。"],
  ["步骤 1", "阅读 Question、Gold answer 与全部 Gold evidence，填写：充分 / 部分 / 不充分 / 不确定。"],
  ["步骤 2", "逐一审核三次回答。C=语义完整正确；O=未回答、Unknown 或仅缺失部分且没有错误事实；H=包含具体错误或无证据断言。"],
  ["步骤 3", "查看“建议最终分类”，填写“人工最终分类”和置信度；建议值可以人工覆盖，但需在备注说明原因。"],
  ["步骤 4", "完成后再查看“机器判定”，重点复核人工与 LongCat-2.0 不一致的条目。"],
  ["robust_generation_failure", "证据充分，且三次人工标签全部不是 C。"],
  ["generation_instability", "证据充分，三次回答中既有 C 又有非 C。"],
  ["ua3_representation_or_admission_failure", "证据充分，三次回答全部 C；原 UA3 错误更接近表示或准入问题。"],
  ["evidence_definition_failure", "gold evidence 仅部分充分、不充分或无法确认。"],
  ["unresolved", "回答、证据或人工标签不完整，暂不能归因。"],
];
instructions.getRange(`A3:B${instructionRows.length + 2}`).values = instructionRows;
instructions.getRange("A3:A13").format = { fill: "#DDECEF", font: { bold: true, color: "#123C46" }, wrapText: true };
instructions.getRange("B3:B13").format = { wrapText: true, verticalAlignment: "top" };
instructions.getRange("A3:B13").format.borders = { preset: "all", style: "thin", color: "#C8D6D9" };
instructions.getRange("A1:A13").format.columnWidthPx = 225;
instructions.getRange("B1:B13").format.columnWidthPx = 760;
instructions.freezePanes.freezeRows(1);

const auditHeaders = [
  "审核序号", "case_id", "dataset", "question_type", "Question", "Gold answer", "Gold evidence",
  "原 UA3 回答", "新回答 1", "新回答 2", "新回答 3", "人工_证据充分性", "人工_Run1", "人工_Run2",
  "人工_Run3", "建议最终分类", "人工_最终分类", "置信度", "审核人", "审核日期", "审核备注", "审核完成",
];
const auditValues = auditRows.map((row, index) => [
  index + 1, row.case_id, row.dataset, row.question_type, row.question, row.gold_answer, goldEvidenceText(row),
  row.source_ua3_answer, row.run_1_answer, row.run_2_answer, row.run_3_answer, "", "", "", "", "", "", "", "", null, "", "",
]);
audit.getRange(`A1:V${auditValues.length + 1}`).values = [auditHeaders, ...auditValues];
for (let row = 2; row <= auditValues.length + 1; row += 1) {
  audit.getRange(`P${row}`).formulas = [[
    `=IF(COUNTA(L${row}:O${row})<4,"未完成",IF(OR(L${row}="部分",L${row}="不充分",L${row}="不确定"),"evidence_definition_failure",IF(L${row}<>"充分","unresolved",IF(COUNTIF(M${row}:O${row},"C")=0,"robust_generation_failure",IF(COUNTIF(M${row}:O${row},"C")=3,"ua3_representation_or_admission_failure","generation_instability")))))`,
  ]];
  audit.getRange(`V${row}`).formulas = [[
    `=IF(AND(L${row}<>"",M${row}<>"",N${row}<>"",O${row}<>"",Q${row}<>"",R${row}<>""),"完成","未完成")`,
  ]];
}
applyHeader(audit.getRange("A1:V1"));
applyBody(audit.getRange(`A2:V${auditValues.length + 1}`));
audit.getRange(`L2:O${auditValues.length + 1}`).format.fill = "#FFF7D6";
audit.getRange(`Q2:U${auditValues.length + 1}`).format.fill = "#FFF7D6";
audit.getRange(`L2:L${auditValues.length + 1}`).dataValidation = { rule: { type: "list", values: ["充分", "部分", "不充分", "不确定"] } };
audit.getRange(`M2:O${auditValues.length + 1}`).dataValidation = { rule: { type: "list", values: ["C", "H", "O"] } };
audit.getRange(`Q2:Q${auditValues.length + 1}`).dataValidation = { rule: { type: "list", values: ["robust_generation_failure", "generation_instability", "ua3_representation_or_admission_failure", "evidence_definition_failure", "unresolved"] } };
audit.getRange(`R2:R${auditValues.length + 1}`).dataValidation = { rule: { type: "list", values: ["高", "中", "低"] } };
audit.getRange(`T2:T${auditValues.length + 1}`).format.numberFormat = "yyyy-mm-dd";
audit.getRange(`V2:V${auditValues.length + 1}`).conditionalFormats.add("containsText", { text: "完成", format: { fill: "#D9F2E4", font: { color: "#17643B", bold: true } } });
audit.getRange(`V2:V${auditValues.length + 1}`).conditionalFormats.add("containsText", { text: "未完成", format: { fill: "#FCE2E2", font: { color: "#9B2525" } } });
addTable(audit, `A1:V${auditValues.length + 1}`, "HumanAuditTable");
audit.freezePanes.freezeRows(1);
audit.freezePanes.freezeColumns(2);
const auditWidths = [70, 145, 75, 180, 310, 230, 440, 220, 220, 220, 220, 115, 80, 80, 80, 235, 235, 75, 95, 100, 260, 90];
auditWidths.forEach((width, index) => { audit.getRangeByIndexes(0, index, auditValues.length + 1, 1).format.columnWidthPx = width; });
audit.getRange(`A2:V${auditValues.length + 1}`).format.rowHeightPx = 84;

const machineHeaders = [
  "case_id", "证据充分性", "缺失信息", "充分性理由", "自动最终分类", "Run1标签", "Run1理由", "Run2标签", "Run2理由",
  "Run3标签", "Run3理由", "充分性模型", "Run1裁判模型", "Run2裁判模型", "Run3裁判模型",
];
const machineValues = auditRows.map((row) => [
  row.case_id, row.sufficiency_verdict, row.sufficiency_missing_information, row.sufficiency_rationale, row.automatic_classification,
  row.run_1_judge_label, row.run_1_judge_rationale, row.run_2_judge_label, row.run_2_judge_rationale,
  row.run_3_judge_label, row.run_3_judge_rationale, row.sufficiency_response_model, row.run_1_judge_model,
  row.run_2_judge_model, row.run_3_judge_model,
]);
machine.getRange(`A1:O${machineValues.length + 1}`).values = [machineHeaders, ...machineValues];
applyHeader(machine.getRange("A1:O1"));
applyBody(machine.getRange(`A2:O${machineValues.length + 1}`));
addTable(machine, `A1:O${machineValues.length + 1}`, "MachineJudgmentTable");
machine.freezePanes.freezeRows(1);
machine.freezePanes.freezeColumns(1);
const machineWidths = [145, 105, 260, 360, 240, 90, 320, 90, 320, 90, 320, 150, 150, 150, 150];
machineWidths.forEach((width, index) => { machine.getRangeByIndexes(0, index, machineValues.length + 1, 1).format.columnWidthPx = width; });
machine.getRange(`A2:O${machineValues.length + 1}`).format.rowHeightPx = 72;

const detailHeaders = Object.keys(calls[0]);
const detailValues = calls.map((row) => detailHeaders.map((header) => row[header] ?? ""));
const lastDetailColumn = String.fromCharCode(64 + detailHeaders.length);
details.getRange(`A1:${lastDetailColumn}${detailValues.length + 1}`).values = [detailHeaders, ...detailValues];
applyHeader(details.getRange(`A1:${lastDetailColumn}1`));
applyBody(details.getRange(`A2:${lastDetailColumn}${detailValues.length + 1}`));
addTable(details, `A1:${lastDetailColumn}${detailValues.length + 1}`, "CallDetailsTable");
details.freezePanes.freezeRows(1);
details.freezePanes.freezeColumns(2);
details.getRange(`A1:${lastDetailColumn}${detailValues.length + 1}`).format.columnWidthPx = 145;
for (const header of ["question", "gold_answer", "model_answer", "judge_rationale"]) {
  const index = detailHeaders.indexOf(header);
  if (index >= 0) details.getRangeByIndexes(0, index, detailValues.length + 1, 1).format.columnWidthPx = header === "question" ? 300 : 260;
}

summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["Generation Failure 审核汇总"]];
summary.getRange("A1:H1").format = { fill: "#123C46", font: { bold: true, color: "#FFFFFF", size: 18 } };
summary.getRange("A3:B6").values = [
  ["候选总数", 381],
  ["已完成人工审核", null],
  ["审核完成率", null],
  ["机器 robust failure", null],
];
summary.getRange("B4").formulas = [[`=COUNTIF('人工审核'!$V$2:$V$382,"完成")`]];
summary.getRange("B5").formulas = [["=B4/B3"]];
summary.getRange("B6").formulas = [[`=COUNTIF('机器判定'!$E$2:$E$382,"robust_generation_failure")`]];
summary.getRange("A3:A6").format = { fill: "#DDECEF", font: { bold: true, color: "#123C46" } };
summary.getRange("A3:B6").format.borders = { preset: "all", style: "thin", color: "#C8D6D9" };
summary.getRange("B5").format.numberFormat = "0.0%";
const classes = ["robust_generation_failure", "generation_instability", "ua3_representation_or_admission_failure", "evidence_definition_failure", "unresolved"];
summary.getRange("A9:C9").values = [["最终分类", "机器数量", "人工数量"]];
summary.getRange("A10:A14").values = classes.map((value) => [value]);
for (let row = 10; row <= 14; row += 1) {
  summary.getRange(`B${row}`).formulas = [[`=COUNTIF('机器判定'!$E$2:$E$382,A${row})`]];
  summary.getRange(`C${row}`).formulas = [[`=COUNTIF('人工审核'!$Q$2:$Q$382,A${row})`]];
}
applyHeader(summary.getRange("A9:C9"));
summary.getRange("A10:C14").format.borders = { preset: "all", style: "thin", color: "#D5DEE0" };
const datasets = ["medium", "long"];
summary.getRange("E9:G9").values = [["数据集", "候选数", "人工 robust failure"]];
summary.getRange("E10:E11").values = datasets.map((value) => [value]);
for (let row = 10; row <= 11; row += 1) {
  summary.getRange(`F${row}`).formulas = [[`=COUNTIF('人工审核'!$C$2:$C$382,E${row})`]];
  summary.getRange(`G${row}`).formulas = [[`=COUNTIFS('人工审核'!$C$2:$C$382,E${row},'人工审核'!$Q$2:$Q$382,"robust_generation_failure")`]];
}
applyHeader(summary.getRange("E9:G9"));
summary.getRange("E10:G11").format.borders = { preset: "all", style: "thin", color: "#D5DEE0" };
const questionTypes = ["Basic Fact Recall", "Generalization & Application", "Multi-hop Inference", "Memory Conflict", "Dynamic Update"];
summary.getRange("E14:G14").values = [["问题类型", "候选数", "人工 robust failure"]];
summary.getRange("E15:E19").values = questionTypes.map((value) => [value]);
for (let row = 15; row <= 19; row += 1) {
  summary.getRange(`F${row}`).formulas = [[`=COUNTIF('人工审核'!$D$2:$D$382,E${row})`]];
  summary.getRange(`G${row}`).formulas = [[`=COUNTIFS('人工审核'!$D$2:$D$382,E${row},'人工审核'!$Q$2:$Q$382,"robust_generation_failure")`]];
}
applyHeader(summary.getRange("E14:G14"));
summary.getRange("E15:G19").format.borders = { preset: "all", style: "thin", color: "#D5DEE0" };
summary.getRange("A1:A19").format.columnWidthPx = 270;
summary.getRange("B1:C19").format.columnWidthPx = 130;
summary.getRange("E1:E19").format.columnWidthPx = 240;
summary.getRange("F1:G19").format.columnWidthPx = 145;
summary.freezePanes.freezeRows(1);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const auditInspect = await workbook.inspect({ kind: "table", sheetId: "人工审核", range: "A1:V8", include: "values,formulas", tableMaxRows: 8, tableMaxCols: 22, maxChars: 5000 });
console.log(auditInspect.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan" });
console.log(errors.ndjson);
const previewRanges = {
  "审核说明": "A1:H13",
  "人工审核": "A1:V12",
  "机器判定": "A1:O12",
  "调用明细": `A1:${lastDetailColumn}12`,
  "汇总": "A1:H20",
};
for (const [sheetName, range] of Object.entries(previewRanges)) {
  const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(JSON.stringify({ outputPath, cases: cases.length, calls: calls.length, previews: 5 }));
