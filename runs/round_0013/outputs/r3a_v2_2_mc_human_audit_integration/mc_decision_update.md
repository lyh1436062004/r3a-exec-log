# R3a-v2.2 决策更新

## Decision

`do_not_revise_selector_yet`

## Why

人工二审覆盖的 102 条候选记忆中，96 条最终判定为不该触发，98 条自动拒绝被判定合理。最终 2 条真反证和 2 条应该触发均来自已触发样本，没有确认的“真反证但未触发”或“应该触发但未触发”。

## Revision to round_0009

round_0009 的自动诊断将 dominant failure source 归为 `premise_extraction_error`。人工二审后，这不能再作为最终结论。前提抽取和槽位归类不精确确实存在，但本批样本没有证明它们造成明确的大量漏触发。

## Current stance

暂不修改 R3a-v2.2 selector、prompt、retriever 或 memory store。下一步优先做全量离线机会普查，或对 4 条模糊 / 不确定边界案例做专项审计。
