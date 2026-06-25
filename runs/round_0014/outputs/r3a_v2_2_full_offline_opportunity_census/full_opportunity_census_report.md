# R3a-v2.2 全量离线反证机会普查报告

## 1. 本轮目的
本轮接续 round_0013，对 Mem0 Medium 全量样本做离线反证机会普查。目标是生成后续人工审计候选表，而不是证明 R3a 有效，也不是修改 R3a。

## 2. 输入文件
- 全量 QA: `D:\幻觉\data\mem0\medium\mem0_medium_qa.jsonl`
- R3a-v2.2 selector: `D:\幻觉\脚本\3.0\r3a_v2_selector.py`
- round_0013 人工审计整合输出: `outputs/r3a_v2_2_mc_human_audit_integration/`

## 3. 方法说明
- 离线读取全量 QA 和已检索 `raw_memories`。
- 使用当前 `select_counterevidence_v2` 记录 R3a 正式触发结果。
- 额外实现高召回可疑候选发现器，只用于人工审计候选生成。
- `question_type` 和 `baseline_label` 仅用于事后分组统计和审计优先级，不进入 R3a 正式判断。
- 未发 API，未重新生成回答，未修改 selector、prompt、retriever 或 memory store。

## 4. 全量题型分布
总样本数: 3467

- Memory Boundary: 828 (23.88%)
- Memory Conflict: 769 (22.18%)
- Basic Fact Recall: 746 (21.52%)
- Generalization & Application: 746 (21.52%)
- Multi-hop Inference: 198 (5.71%)
- Dynamic Update: 180 (5.19%)

## 5. R3a 全量触发情况
- R3a 全量触发数: 78
- R3a 全量触发率: 2.25%
- R3a 触发样本 baseline_label 分布: `{'correct': 34, 'hallucination': 9, 'omission': 35}`

## 6. Memory Conflict 子集触发情况
- Memory Conflict 总数: 769
- Memory Conflict 占比: 22.18%
- Memory Conflict 中 R3a 触发数: 78
- Memory Conflict 中 R3a 触发率: 10.14%
- Memory Conflict 中未触发数: 691

## 7. 可疑反证候选发现结果
- Memory Conflict 中存在可疑反证候选的样本数: 727
- Memory Conflict 中未触发且存在可疑反证候选的样本数: 649
- R3a 未触发但有可疑反证候选的样本 baseline_label 分布: `{'correct': 743, 'hallucination': 542, 'omission': 1424}`
- Memory Conflict 中可疑反证候选数量分布: `{'3': 155, '4': 166, '2': 145, '6': 41, '5': 88, '7': 17, '0': 42, '8': 9, '1': 96, '11': 3, '12': 1, '9': 6}`

重要说明：可疑反证候选不等于真反证；可疑反证候选不等于 R3a 应该触发；可疑反证候选只用于后续人工审计。

## 8. R0 omission / hallucination 中的可疑修复机会
- Memory Conflict + R0 omission + R3a 未触发 + 可疑反证候选样本数: 387
- Memory Conflict + R0 hallucination + R3a 未触发 + 可疑反证候选样本数: 62
- Memory Conflict + R0 correct + R3a 未触发 + 可疑反证候选样本数: 200

## 9. R3a 已触发样本清单摘要
已输出 `r3a_triggered_samples.csv`。这些是当前 R3a-v2.2 正式触发样本，不由高召回发现器决定。

## 10. R3a 未触发但有可疑反证候选的样本摘要
已输出 `r3a_untriggered_suspected_counterevidence.csv`。这些样本只表示“值得人工审计”，不能直接视为漏触发。

## 11. 与 round_0013 人工审计结论的一致性检查
round_0013 的人工审计结论是不修改 R3a。本轮普查不是要推翻该结论，而是扩大范围检查全量 Mem0 Medium 中是否存在未发现的漏触发真反证。如果本轮只发现可疑候选，不能直接说明 R3a 漏判，必须经人工审计后才能判断。

## 12. 人工审计候选表说明
人工审计候选表输出为 `manual_audit_candidates.csv`，共 380 行，覆盖 273 个唯一样本。

优先级分布:

- P1_memory_conflict_omission_untriggered_suspected: 120
- P2_memory_conflict_hallucination_untriggered_suspected: 80
- P3_memory_conflict_correct_untriggered_suspected: 50
- P4_memory_conflict_r3a_triggered: 80
- P5_non_memory_conflict_high_suspicion: 50

## 13. 当前不能得出的结论
- 不能说 R3a-v2.2 要修改。
- 不能说 R3a-v2.2 已成功。
- 不能把可疑候选直接当成真反证。
- 不能把可疑候选直接当成 R3a 应该触发。
- 不能把时间更新类候选强行塞给 R3a；其中一部分可能属于 R3b。

## 14. 下一步建议
推荐下一步: `audit_first_priority_candidates_before_any_selector_change`。

若第一优先级候选较多，应先人工审计 `manual_audit_candidates.csv` 的第一优先级，不要直接改 R3a。人工审计应估计高召回候选发现器的误报率，并判断可疑样本中是否存在真正的“已检索反证但 R3a 未触发”。

## 15. 生成文件列表
- `full_opportunity_census_report.md`
- `full_opportunity_census_summary.json`
- `full_sample_level_census.jsonl`
- `memory_conflict_candidate_samples.csv`
- `manual_audit_candidates.csv`
- `r3a_triggered_samples.csv`
- `r3a_untriggered_suspected_counterevidence.csv`
