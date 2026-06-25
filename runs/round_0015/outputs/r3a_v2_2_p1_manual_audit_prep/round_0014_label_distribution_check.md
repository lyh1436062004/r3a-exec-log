# round_0014 标签分布统计口径核查

## 1. 核查对象

round_0014 summary/report 中的 `r3a_untriggered_suspected_baseline_label_distribution`。

## 2. round_0014 已报告分布

```json
{
  "correct": 743,
  "hallucination": 542,
  "omission": 1424
}
```

该分布总数为 2709。

## 3. 重新计算：Memory Conflict + R3a 未触发 + 疑似反证候选

```json
{
  "correct": 200,
  "hallucination": 62,
  "omission": 387
}
```

该分布总数为 649。

## 4. 重新计算：全量样本 + R3a 未触发 + 疑似反证候选

```json
{
  "correct": 743,
  "hallucination": 542,
  "omission": 1424
}
```

该分布总数为 2709。

## 5. 结论

round_0014 中该字段实际对应全量未触发且存在疑似候选的 baseline_label 分布，不是 Memory Conflict 子集分布；字段名或报告中的上下文应修正为“全量未触发疑似候选 baseline_label 分布”。
