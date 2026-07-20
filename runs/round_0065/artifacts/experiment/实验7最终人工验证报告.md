# Experiment 7 - Final Human Validation Integration

## Validation integrity

- Completed rows: 43/43
- Unique case IDs: 43/43
- Original A-P cells changed: 0
- Transparent derived adjudications: 1 (submitted workbook preserved unchanged)
- Filled workbook SHA-256: `b62a470532d7ee4b9832b33805b8a5d818f2651e78de8909607b933dbe03cf74`

## Machine-human agreement

| Target | Agreement | Rate | Wilson 95% CI |
|---|---:|---:|---:|
| Raw coverage | 43/43 | 100.00% | [91.80%, 100.00%] |
| Rendered coverage | 42/43 | 97.67% | [87.94%, 99.59%] |
| Final A/B/C/D label | 41/43 | 95.35% | [84.54%, 98.72%] |
| Concrete label, excluding uncertain | 41/41 | 100.00% | [91.43%, 100.00%] |

## Reviewed sample

- Human labels: {'C_rendered_not_used': 14, 'B_present_not_rendered': 15, 'uncertain': 2, 'A_evidence_missing': 12}
- Confidence: {'medium': 22, 'high': 21}
- The 13 machine raw-partial/missing cases were reviewed as a census; the raw-contained stratum used a fixed 30/145 sample.

## Adjudication note

- `memos_long:2093` submitted `human_rendered_coverage=partial`, while both the exact context and the submitted note show that the gold activity 'organizing charity sports events' was retained. The derived analysis therefore uses `contained`; the submitted workbook is archived without modification.

## Three reporting views

| View | A | B | C | D | uncertain | Meaning |
|---|---:|---:|---:|---:|---:|---|
| Machine census | 12 | 73 | 72 | 1 | 0 | Automatic labels for all 158 |
| Hybrid case-level | 12 | 72 | 72 | 0 | 2 | Human overrides 43 reviewed cases |
| Design-weighted estimate | 12.00 | 72.50 | 67.67 | 0.00 | 5.83 | Expands the 30/145 sample by its sampling weight |

## Post-retrieval repairable estimate (B+C)

- Machine census: 145/158 (91.77%)
- Hybrid case-level: 144/158 (91.14%)
- Design-weighted: 140.17/158 (88.71%)
- Projected 95% interval: [76.47%, 91.23%]

## Two unresolved benchmark cases

- `memos_long:2093`: machine `B_present_not_rendered` -> human `uncertain` (Raw: 包含mentoring young athletes和organizing charity sports events两类活动；Rendered: 同时保留两类活动，没有丢失关键事实；Final: direct_gold_answers中的Mentoring young athletes有证据支持，不能判为D；UA3答案可由证据支持，无法按错误类别裁决。Time: 未发现时间冲突。)
- `memos_medium:3401`: machine `D_judge_error` -> human `uncertain` (Raw: 包含first-person shooters及其社交互动、新见解的关系；Rendered: 未直接保留完整gold表述，但保留相关偏好信息；Final: direct_gold_answers中的First-person shooters由证据支持，不能判为D；gold_answer与direct答案粒度不同，无法确认UA3错误。Time: 按问题日期判断，未使用create/update_time。)

## Recommended paper wording

After one transparent coverage adjudication, the human validation reproduced 43/43 raw-coverage and 42/43 rendered-coverage judgments. Final attribution agreed on 41/43 cases; the two remaining cases were not assigned to a competing failure class but marked uncertain because the benchmark gold answer and an evidence-supported alternative answer differed in granularity. Report the hybrid 144/158 as the case-level observed figure, and the 88.71% design-weighted estimate with its interval as the sampling-adjusted sensitivity analysis.

## Resource usage

- GPU hours: 0
- API calls: 0
- This integration is deterministic and local.
