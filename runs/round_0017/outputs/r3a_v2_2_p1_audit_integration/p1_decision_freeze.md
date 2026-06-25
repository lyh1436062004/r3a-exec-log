# P1 决策冻结：不修改 R3a-v2.2

## 冻结结论

`decision = do_not_revise_r3a_v2_2`

P1 人工审计结果不支持修改 R3a-v2.2。

## 依据

- P1 候选行数：120
- P1 唯一样本数：91
- 非反证 + 非反证但有用：118 / 120 (98.33%)
- 最终确认真反证且应该触发：0
- 确认 R3a 漏掉真反证：0

P1 的主导情况是：`candidate_finder_false_positives`。

## 禁止外推

不能把疑似候选当真反证。

不能把 P1 结果写成 R3a 已成功。

不能把 P1 结果写成 R3a 大量漏触发。

不能据此修改 selector、prompt、retriever 或 memory store。

## 下一步冻结后的建议

不要继续审 P2/P3。

不要启动 R3b。

下一步做：`evaluate_r3a_v2_2_triggered_samples_utility`。

也就是验证 R3a-v2.2 已触发的 78 个样本是否真的带来回答收益。
