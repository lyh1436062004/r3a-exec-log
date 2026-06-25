# R3a-v2.2 第一优先级人工审计准备报告

## 1. 本轮目的

本轮只做第一优先级疑似反证候选的人工审计表准备，以及 round_0014 标签分布统计口径核查。

未发接口调用，未重新生成回答，未修改 R3a 选择器、提示词、检索器或记忆库。

## 2. 输入文件

- `D:\幻觉\outputs\r3a_v2_2_full_offline_opportunity_census\manual_audit_candidates.csv`
- `D:\幻觉\outputs\r3a_v2_2_full_offline_opportunity_census\full_opportunity_census_summary.json`
- `D:\幻觉\outputs\r3a_v2_2_full_offline_opportunity_census\full_opportunity_census_report.md`
- `D:\幻觉\outputs\r3a_v2_2_full_offline_opportunity_census\full_sample_level_census.jsonl`
- `D:\幻觉\outputs\r3a_v2_2_full_offline_opportunity_census\r3a_untriggered_suspected_counterevidence.csv`
- `D:\幻觉\data\mem0\medium\mem0_medium_qa.jsonl`

## 3. 第一优先级筛选规则

从 `manual_audit_candidates.csv` 中筛选：

`priority_group = P1_memory_conflict_omission_untriggered_suspected`

该优先级含义是：Memory Conflict、R0 omission、R3a 未触发、存在疑似反证候选。疑似候选仅用于人工审计，不是真反证标签，也不是应触发标签。

## 4. 第一优先级候选行数和唯一样本数

- 第一优先级候选行数：120
- 第一优先级唯一样本数：91
- 预期行数：120
- 行数是否匹配：true

第一优先级候选行数与 round_0014 预期 120 行一致。

## 5. 人工审计表字段说明

审计表包含自动字段和人工填写字段。自动字段来自 round_0014 候选表、全量样本普查、以及原始 QA 文件；人工字段保持空白，供后续人工填写。

`人工_最终标签` 只能使用：真反证、模糊反证、非反证但有用、非反证、无法判断。

`人工_错误来源` 只能使用：R3a漏触发、候选发现器误报、问题前提抽取错误、槽位归类错误、时间判断问题、明确反驳判断问题、检索证据不足、不属于R3a、无法判断。

## 6. 统计口径核查

- round_0014 已报告分布：`{'correct': 743, 'hallucination': 542, 'omission': 1424}`
- Memory Conflict + 未触发 + 疑似候选重新计算：`{'correct': 200, 'hallucination': 62, 'omission': 387}`
- 全量未触发 + 疑似候选重新计算：`{'correct': 743, 'hallucination': 542, 'omission': 1424}`
- round_0014 字段名/报告位置是否正确：false

结论：round_0014 中该字段实际对应全量未触发且存在疑似候选的 baseline_label 分布，不是 Memory Conflict 子集分布；字段名或报告中的上下文应修正为“全量未触发疑似候选 baseline_label 分布”。

## 7. 当前不能得出的结论

不能说第一优先级候选是真反证。
不能说 R3a 漏触发。
不能说 R3a 应该修改。
不能说 R3a 已成功。
不能根据候选发现器直接扩大实验。

## 8. 下一步人工填写说明

请人工填写 `p1_manual_audit_sheet.xlsx`，重点判断候选记忆是否明确反驳问题前提，以及是否应该触发 R3a。

如果 P1 中“真反证且应该触发”的比例很高：说明 R3a 在最重要的遗漏修复场景中漏触发，下一步应修 R3a。

如果 P1 中大多数是“非反证”或“只是相关”：说明高召回候选发现器误报高，R3a 暂不应修改。

如果 P1 中大量是“模糊反证”：说明需要定义边界，不要直接放宽选择器。

如果 P1 中大量属于时间更新：应交给 R3b，不要强行塞给 R3a。

## 9. 生成文件列表

- `D:\幻觉\outputs\r3a_v2_2_p1_manual_audit_prep\p1_manual_audit_sheet.xlsx`
- `D:\幻觉\outputs\r3a_v2_2_p1_manual_audit_prep\p1_manual_audit_sheet.csv`
- `D:\幻觉\outputs\r3a_v2_2_p1_manual_audit_prep\p1_audit_prep_summary.json`
- `D:\幻觉\outputs\r3a_v2_2_p1_manual_audit_prep\p1_audit_prep_report.md`
- `D:\幻觉\outputs\r3a_v2_2_p1_manual_audit_prep\round_0014_label_distribution_check.md`
- `D:\幻觉\outputs\r3a_v2_2_p1_manual_audit_prep\round_0014_label_distribution_check.json`
