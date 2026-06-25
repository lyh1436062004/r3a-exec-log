# R3a-v2.2 记忆冲突人工审计整合与结论修正

## 1. 本轮目的

本轮接续 round_0009，只整合人工二审结果并修正研究判断；未修改 R3a selector、prompt、retriever 或 memory store，未发接口调用，未重新生成回答。

## 2. 输入

- 人工二审表：`C:\Users\78443\Downloads\R3a_v2_2_MC人工审计表_二审最终修订版.xlsx`
- round_0009 summary：`D:\幻觉\outputs\r3a_v2_2_mc_stratified_coverage_audit\mc_coverage_audit_summary.json`
- round_0009 report：`D:\幻觉\outputs\r3a_v2_2_mc_stratified_coverage_audit\mc_coverage_audit_report.md`
- round_0009 candidates：`D:\幻觉\outputs\r3a_v2_2_mc_stratified_coverage_audit\mc_manual_audit_candidates.csv`

## 3. 人工二审总体统计

- 候选记忆总行数：102
- 唯一样本数：45
- 二审后修改原人工字段的行数：7
- 最终认为“明确有已检索反证”的候选行数：2
- 最终认为“真反证”的候选行数：2
- 最终认为“模糊反证”的候选行数：4
- 最终认为“应该触发 R3a”的候选行数：2
- 最终认为“不该触发 R3a”的候选行数：96
- 最终“不确定”的候选行数：4
- 最终认为自动拒绝“合理”的候选行数：98（96.08%）
- 最终认为自动拒绝“部分合理”的候选行数：4

## 4. 样本级核查

- 包含“真反证”的唯一样本数：2
- 包含“应该触发 R3a”的唯一样本数：2
- 2 条最终真反证是否都来自已经触发的样本：是
- 是否存在“真反证但 R3a 未触发”：否
- 是否存在“应该触发 R3a 但未触发”：否
- 未触发但人工判断不确定 / 模糊反证的样本数：4

## 5. 4 条“模糊反证 / 不确定”样本

这些样本不足以支持立即修改选择器：它们仍是边界案例，未形成“明确真反证漏触发”。

| excel_row | sample_id | question_id | R3a triggered | final_t | final_u | question |
|---|---:|---|---|---|---|---|
| 12 | 44 | 1:21:3 | False | 模糊反证 | 不确定 | Was Martin closed to new experiences and uninterested in sports that challenge him mentally after May 05, 2028? |
| 26 | 75 | 1:30:5 | False | 模糊反证 | 不确定 | Did Martin's mental health improve after his promotion in March 2029? |
| 93 | 46 | 1:22:1 | False | 模糊反证 | 不确定 | Did Martin retire early from Huaxin Consulting on March 10, 2028? |
| 96 | 48 | 1:22:3 | False | 模糊反证 | 不确定 | Did Martin officially begin his retirement on June 1, 2028? |

## 6. round_0009 自动诊断对比

round_0009 自动诊断给出的 dominant failure source 是 `premise_extraction_error`，并建议 `revise_premise_or_slot_or_refutation_after_manual_audit`。

人工二审后发现：

1. 多数候选记忆并不是反证；
2. 96 / 102 候选行最终被判为“不该触发”；
3. 98 / 102 候选行自动拒绝被判为“合理”；
4. 2 条真反证 / 2 条应该触发样本已经触发；
5. 因此前提抽取和槽位归类虽然存在不精确，但暂未构成大规模确认漏触发。

## 7. 自动失败来源是否造成明确漏触发

| auto_failure_source | candidate_rows | human_true_counterevidence_rows | human_should_trigger_rows | confirmed_missed_true_rows | confirmed_missed_should_rows |
|---|---:|---:|---:|---:|---:|
| premise_extraction_error | 38 | 0 | 0 | 0 | 0 |
| no_counterevidence_in_raw_memories | 22 | 0 | 0 | 0 | 0 |
| slot_mapping_error | 22 | 0 | 0 | 0 | 0 |
| temporal_gate_too_strict | 13 | 0 | 0 | 0 | 0 |
| explicit_refutation_gate_too_strict | 5 | 0 | 0 | 0 | 0 |
| already_triggered | 2 | 2 | 2 | 0 | 0 |

结论：自动诊断中的 `premise_extraction_error` 和 `slot_mapping_error` 反映了抽取 / 归类不精确，但在这批人工二审覆盖样本中，没有造成“人工确认真反证但未触发”或“人工确认应该触发但未触发”的明确漏触发。

## 8. 修正后的研究判断

当前不能继续采用 round_0009 的自动结论：“低触发主要由问题前提抽取错误导致”。

更稳妥的新结论是：R3a-v2.2 在这批人工审计覆盖的记忆冲突候选上，没有发现明确的大量漏掉真反证问题。低触发主要来自候选记忆本身并非明确反证。问题前提抽取和槽位归类确实有不精确现象，但不能据此立即修改选择器。

## 9. 当前决策

- decision_update：`do_not_revise_selector_yet`
- recommended_next_decision：`full_offline_opportunity_census_or_uncertain_case_audit`

暂不修改 R3a-v2.2。先把人工审计结果整合进日志。下一步做更大范围的离线机会普查，确认完整 Mem0 Medium 的记忆冲突样本中，到底有多少已检索反证机会，以及 R3a 是否漏掉真反证。

## 10. 后续候选方向，本轮不执行

方向 A：全量离线机会普查。在不发接口、不重新生成回答的前提下，对 Mem0 Medium 全量样本，尤其是 Memory Conflict 子集，统计 Memory Conflict 总数、R3a 触发数、人工或半自动可疑反证候选数、R0 omission 中可疑反证候选数、R3a 未触发但可疑反证候选数。

方向 B：边界案例专项审计。只审计 4 条“模糊反证 / 不确定”样本，判断它们是否代表需要扩展 R3a，还是应该保持拒绝。
