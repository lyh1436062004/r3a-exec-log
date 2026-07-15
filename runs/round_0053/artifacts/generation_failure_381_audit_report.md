# Generation-Failure 381 人工审核报告 (Kiro-AI 代审)

- 审核日期: 2026-07-15
- 审核人: Kiro-AI代审
- 数据来源: `outputs/e1_memos_generation_failure_oracle_v1/case_summary.jsonl` (381 例)
- 产出工作簿: `临时/人工审查/审查生成错误率/审核-多轮回答评估-G.xlsx` (`人工审核` sheet)

## 方法

对每个 case 独立执行以下判定（不盲从机器 LongCat-2.0 标签）：

1. **证据充分性 (L)**: 判断 `gold_evidence` 能否在满足问题时间/人物/条件/范围约束下**完整推出** `gold_answer`。取值：充分 / 部分 / 不充分 / 不确定。不做字面匹配。
2. **三次回答标签 (M/N/O)**: 逐一对照 gold_answer：
   - C = 语义完整且正确；
   - O = 未回答 / Unknown / 正确但缺失部分且无错误事实；
   - H = 含具体错误或无证据断言。
3. **最终分类 (Q)**，由 (L, M/N/O) 按固定规则确定（与工作簿 P 列公式一致）：
   - 证据∈{部分,不充分,不确定} → evidence_definition_failure
   - 证据=充分 且 三次全 C → ua3_representation_or_admission_failure
   - 证据=充分 且 零 C → robust_generation_failure
   - 证据=充分 且 C 混合 → generation_instability
4. **置信度 (R)**: 高/中/低。

执行方式：381 例分 13 批，由并行标注 worker 按同一 rubric 独立判定；最终分类由脚本统一按规则计算，保证与 P 列公式一致。

## 结果汇总（含用户保留的第 2 行）

- 证据充分性: 充分 308 · 部分 50 · 不充分 23
- 最终分类 (Q): robust_generation_failure 145 · ua3_representation_or_admission_failure 162 · evidence_definition_failure 74 · generation_instability 0
- 置信度: 高 228 · 中 129 · 低 24
- 与机器 automatic_classification 一致率: 343/381 = 90.0%

### 主要分歧（机器 → 人工）
- robust_generation_failure → ua3_representation_or_admission_failure: 17（回答实为语义完整，原 UA3 错误更接近表示/准入问题）
- evidence_definition_failure → robust_generation_failure: 8
- generation_instability → robust_generation_failure: 4
- evidence_definition_failure → ua3_representation_or_admission_failure: 4
- robust_generation_failure → evidence_definition_failure: 3
- 机器普遍将"证据内但不完整"的回答误判为 hallucination，人工改判 omission。
- 多处 gold/evidence 错配（如 honey vs maple、Jazz/Italian/chess 证据缺失）判为 evidence_definition_failure。
- 修正机器对"三次相同回答给出不一致标签"的问题。

## 备注

- 第 2 行 (`memos_medium:2634`) 为用户原始示例，保留未改。
- 写入前工作簿曾被另一较宽松的 `Kiro-AI` pass 填充（204/381 行与本审核不同，多将"正确但不完整"判为 C、证据判"充分"更宽松）；因其与用户第 2 行严格示例冲突，已用本严格审核覆盖，覆盖前状态已备份 (`*_prewrite_*.xlsx`)。
