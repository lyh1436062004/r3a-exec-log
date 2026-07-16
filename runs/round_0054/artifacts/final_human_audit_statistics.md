# Generation Failure 最终人工审计统计

数据源：`最终汇总表-人工机器复核整合.xlsx` 的 `最终汇总表` 工作表。

统计口径：381 条 Generation failure 候选，最终分类以人工机器复核整合后的 `最终分类` 列为准。

## 核心结论

- 最终确认的 `robust_generation_failure` 为 **133/381（34.91%）**，Wilson 95% CI 为 **30.29%–39.82%**。
- 相对于 763 条 visible strict 样本，稳健生成失败占 **133/763（17.43%）**，Wilson 95% CI 为 **14.90%–20.28%**。
- 相对于 MEMOS 两个数据集的 1,987 条 baseline 错误样本，稳健生成失败占 **133/1,987（6.69%）**，Wilson 95% CI 为 **5.68%–7.88%**。
- 在最终判定证据充分的 291 条中，稳健生成失败为 **133/291（45.70%）**。

## 最终分类

| 最终分类 | 数量 | 占 381 |
|---|---:|---:|
| robust_generation_failure | 133 | 34.91% |
| ua3_representation_or_admission_failure | 158 | 41.47% |
| evidence_definition_failure | 90 | 23.62% |
| generation_instability | 0 | 0.00% |
| unresolved | 0 | 0.00% |

## 证据充分性

| 最终证据充分性 | 数量 | 占 381 |
|---|---:|---:|
| 充分 | 291 | 76.38% |
| 部分 | 66 | 17.32% |
| 不充分 | 24 | 6.30% |

## 三次回答标签

共 1,143 个生成回答：`C` 506（44.27%）、`O` 553（48.38%）、`H` 84（7.35%）。

| 重复生成 | C | O | H |
|---|---:|---:|---:|
| Run 1 | 169 | 184 | 28 |
| Run 2 | 168 | 185 | 28 |
| Run 3 | 169 | 184 | 28 |

## 分层结果

| 数据集 | 候选数 | robust failure | 比例 |
|---|---:|---:|---:|
| Medium | 190 | 65 | 34.21% |
| Long | 191 | 68 | 35.60% |

| 问题类型 | 候选数 | robust failure | 比例 |
|---|---:|---:|---:|
| Basic Fact Recall | 75 | 15 | 20.00% |
| Dynamic Update | 29 | 13 | 44.83% |
| Generalization & Application | 183 | 62 | 33.88% |
| Memory Conflict | 40 | 22 | 55.00% |
| Multi-hop Inference | 54 | 21 | 38.89% |

## 人工复核修正

- 机器原判：robust 151、instability 4、UA3 representation/admission 144、evidence definition 82。
- 最终整合：robust 133、instability 0、UA3 representation/admission 158、evidence definition 90。
- 最终分类与机器分类一致 356/381（93.44%），共修正 25 条最终分类。
- 最终证据充分性与机器判定一致 371/381（97.38%），共修正 10 条。

机器到最终分类的 25 条变化包括：robust→UA3 13 条、robust→evidence definition 7 条、instability→robust 2 条、instability→evidence definition 2 条、evidence definition→UA3 1 条。

## 状态说明

全部 381 条均已有证据充分性、三次回答标签、最终分类和置信度，没有 unresolved。工作簿仍有 7 条的 `最终采用来源` 标记为“复核建议（待人工确认）”；它们当前均被计入 `evidence_definition_failure`。因此 **133 条是按当前 `最终分类` 列得到的最新整合口径**。若这 7 条尚未真正完成签字确认，报告应称为“当前整合版”；其中 4 条的建议分类原为 robust，理论上的待确认敏感区间为 133–137 条。
