# round_0015 Analysis: R3a-v2.2 P1 Manual Audit Prep

## Scope

This round continued from round_0014. It prepared the first-priority manual audit sheet from round_0014 `manual_audit_candidates.csv` and checked the label-distribution scope in round_0014 reporting.

No API calls were made. No answers were regenerated. R3a selector, prompt, retriever, and memory store were not modified.

## P1 Audit Sheet

- P1 priority group: `P1_memory_conflict_omission_untriggered_suspected`
- P1 candidate rows: 120
- P1 unique samples: 91
- Expected P1 rows: 120
- Row count matches round_0014: True

The generated workbook and CSV keep suspected candidates as manual-audit leads only. They are not true-counterevidence labels and are not R3a should-trigger labels.

## Label Distribution Check

- round_0014 reported distribution: `{'correct': 743, 'hallucination': 542, 'omission': 1424}`
- Recomputed Memory Conflict + untriggered + suspected distribution: `{'correct': 200, 'hallucination': 62, 'omission': 387}`
- Recomputed all-sample + untriggered + suspected distribution: `{'correct': 743, 'hallucination': 542, 'omission': 1424}`

Conclusion: round_0014 中该字段实际对应全量未触发且存在疑似候选的 baseline_label 分布，不是 Memory Conflict 子集分布；字段名或报告中的上下文应修正为“全量未触发疑似候选 baseline_label 分布”。

## Next Step

Human fill `p1_manual_audit_sheet.xlsx` before making any selector change.
