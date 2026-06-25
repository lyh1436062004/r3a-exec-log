# R3a-v2.2 记忆冲突分层覆盖审计报告

## 1. 本轮目的
本轮只解释 R3a-v2.2 在 200 条 AB5 smoke 中的 Memory Conflict 覆盖情况，不证明 R3a 有效性，不修改正式 selector。

## 2. 输入文件
- smoke: D:\幻觉\outputs\r3a_v2_2_ab5_smoke\r3a_v2_2_ab5_smoke.jsonl
- diagnostic: D:\幻觉\outputs\r3a_v2_2_smoke_diagnostics\r3a_v2_2_trigger_diagnostic.jsonl

## 3. 方法说明
- 离线读取已有 smoke 与 low-trigger diagnostic。
- question_type 只用于事后分层统计和人工审计抽样。
- 未发 API，未重新生成回答，未修改 selector、prompt、retriever 或 memory store。

## 4. 200 条 smoke 的题型分布
- 总样本数: 200
- Memory Conflict: 49 (24.50%)
- Basic Fact Recall: 49 (24.50%)
- Memory Boundary: 46 (23.00%)
- Generalization & Application: 34 (17.00%)
- Multi-hop Inference: 16 (8.00%)
- Dynamic Update: 6 (3.00%)
- Memory Conflict 数量: 49 (24.50%)

## 5. Memory Conflict 子集规模与触发率
- Memory Conflict 总数: 49
- R3a 触发数: 2
- R3a 触发率: 4.08%
- 未触发数: 47
- 全体触发率: 1.00%
- 全体潜在机会比例: 9.00%
- Memory Conflict 潜在机会比例: 36.73%

## 6. Memory Conflict 子集中的 R0 / B_gated 标签流转
- R0 correct / hallucination / omission: 14 / 7 / 28
- B_gated_v2_2 correct / hallucination / omission: 14 / 7 / 28
- MC 中 R0 omission 但 R3a 未触发: 28
- MC 中 R0 hallucination 但 R3a 未触发: 7

## 7. Memory Conflict 子集拒绝原因分布
{
  "premise_extraction_error": 15,
  "slot_mapping_error": 13,
  "no_counterevidence_in_raw_memories": 11,
  "temporal_gate_too_strict": 5,
  "explicit_refutation_gate_too_strict": 3,
  "already_triggered": 2
}

## 8. 问题前提抽取错误分析
- premise_extraction_error: 15 (30.61%)
- 典型样本:
- idx=0 qa_key=1:1:3 premise={"entity": "Martin Mark", "object_or_activity": "health", "slot": "health_status", "claimed_value": "health", "polarity": "positive", "temporal_condition": null, "event_condition": null, "scope": null, "premise_type": "health_status", "raw_question": "Did Martin Mark establish a global health initiative with his partner in 2025?", "anchor_tokens": ["martin", "mark", "health"], "slot_tokens": ["health", "status", "statu"], "value_tokens": ["health"], "temporal_tokens": []} question=Did Martin Mark establish a global health initiative with his partner in 2025?
- idx=11 qa_key=1:3:2 premise={"entity": "Martin Mark", "object_or_activity": "pet sep 2025", "slot": "generic_yesno", "claimed_value": "pet sep 2025", "polarity": "positive", "temporal_condition": "on Sep 07; Sep 07, 2025", "event_condition": null, "scope": null, "premise_type": "generic_yesno", "raw_question": "Did Martin Mark mention a preference for reptiles as pets on Sep 07, 2025?", "anchor_tokens": ["martin", "mark", "pet", "sep", "2025"], "slot_tokens": ["generic", "yesno", "martin", "mark", "preference", "reptiles", "reptil", "pets", "pet", "sep", "2025"], "value_tokens": ["pet", "sep", "2025"], "temporal_tokens": ["sep", "2025"]} question=Did Martin Mark mention a preference for reptiles as pets on Sep 07, 2025?
- idx=45 qa_key=1:21:2 premise={"entity": "Martin", "object_or_activity": "negative may 2028", "slot": "generic_yesno", "claimed_value": "negative may 2028", "polarity": "positive", "temporal_condition": "after May 05; May 05, 2028", "event_condition": "after May 05", "scope": null, "premise_type": "generic_yesno", "raw_question": "Did Martin's perception of boxing remain purely negative after May 05, 2028?", "anchor_tokens": ["martin", "negative", "may", "2028"], "slot_tokens": ["generic", "yesno", "martin's", "martin'", "perception", "boxing", "box", "remain", "purely", "negative", "may", "2028"], "value_tokens": ["negative", "may", "2028"], "temporal_tokens": ["may", "2028"]} question=Did Martin's perception of boxing remain purely negative after May 05, 2028?
- idx=46 qa_key=1:22:1 premise={"entity": "Martin", "object_or_activity": "consult march 2028", "slot": "generic_yesno", "claimed_value": "consult march 2028", "polarity": "positive", "temporal_condition": "on March 10; March 10, 2028", "event_condition": null, "scope": null, "premise_type": "generic_yesno", "raw_question": "Did Martin retire early from Huaxin Consulting on March 10, 2028?", "anchor_tokens": ["martin", "consult", "march", "2028"], "slot_tokens": ["generic", "yesno", "martin", "retire", "early", "huaxin", "consulting", "consult", "march", "2028"], "value_tokens": ["consult", "march", "2028"], "temporal_tokens": ["march", "2028"]} question=Did Martin retire early from Huaxin Consulting on March 10, 2028?
- idx=47 qa_key=1:22:2 premise={"entity": "Martin", "object_or_activity": "early april 2028", "slot": "generic_yesno", "claimed_value": "early april 2028", "polarity": "positive", "temporal_condition": "on April 20; April 20, 2028", "event_condition": null, "scope": null, "premise_type": "generic_yesno", "raw_question": "Did Martin's social network encourage him to retire early on April 20, 2028?", "anchor_tokens": ["martin", "early", "april", "2028"], "slot_tokens": ["generic", "yesno", "martin's", "martin'", "social", "network", "encourage", "retire", "early", "april", "2028"], "value_tokens": ["early", "april", "2028"], "temporal_tokens": ["april", "2028"]} question=Did Martin's social network encourage him to retire early on April 20, 2028?
- 当前自动诊断显示 premise extraction 错误不是主因，但仍需人工审计候选表确认。

## 9. 槽位归类错误分析
- slot_mapping_error: 13 (26.53%)
- generic_yesno 可疑归类: 1
- health_status / preference_status 可疑归类: 9
- 当前看 slot_mismatch 既包含合理拒绝，也包含少量可能由槽位设计导致的误拒，不能直接据此放宽 selector。

## 10. raw_memories 中反证存在性分析
- 明确/可能有反证但未触发: 19
- 没有可识别反证: 11
- 不确定，需要人工审计: 17

## 11. 未触发 Memory Conflict 的失败来源归因
- dominant_failure_source: premise_extraction_error
- temporal_gate_too_strict: 5
- explicit_refutation_gate_too_strict: 3
- actually_not_r3a_case: 0

## 12. 典型失败样本
详见 mc_manual_audit_candidates.csv。该表按 R0 omission 未触发、R0 hallucination 未触发、R0 correct 高相似未触发、已触发样本排序。

## 13. 当前是否能接受“机会太少”解释
- can_accept_low_opportunity_explanation: False
- 解释: Memory Conflict 子集中没有可识别反证的样本占主导，同时潜在应触发样本数量较低。因此“机会太少 / 已检索记忆中反证不足”仍可作为当前主要解释，但需要人工审计候选表验证。

## 14. 下一步建议
- recommended_next_decision: revise_premise_or_slot_or_refutation_after_manual_audit
- 建议先人工审计 mc_manual_audit_candidates.csv，再决定是否修 premise extraction / slot mapping / explicit refutation gate。

## 15. 不能得出的结论
- 不能说 R3a-v2.2 已成功。
- 不能把所有 Memory Conflict 都当作 R3a 目标。
- 不能从本轮结果直接扩大 AB5 或跑 full 3467。
- 不能把 question_type / gold_answer / baseline_label 用进 selector 决策。

## 16. 生成文件列表
- mc_coverage_audit_report.md
- mc_coverage_audit_summary.json
- mc_sample_level_diagnostic.jsonl
- mc_manual_audit_candidates.csv
- mc_failure_source_table.csv
