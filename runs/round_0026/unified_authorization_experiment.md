# Unified Explicit-Authorization Experiment

## Research Question

When gold evidence is already present in the retrieved top-k context, does explicitly authorizing the model to use that evidence improve answer correctness?

Primary hypothesis: with retrieved memory content, count, order, answer prompt, model, and decoding configuration fixed, a uniform authorization instruction improves correctness relative to a matched neutral marker attached to exactly the same oracle-selected memories.

## Population

Run only the 896 `strict_supported` Memos samples. Every included sample has at least one retrieved memory judged to fully support at least one gold-evidence item.

Define the primary stable-wrong subset after execution as samples judged non-correct in both identical baseline replays (`B0` and `B0R`). This excludes one-pass replay noise without conditioning on either treatment result.

## Fixed Templates

Neutral marker:

`[检索标记] 该记忆位于当前检索结果中。`

Unified authorization:

`[使用授权] 该记忆可以用于回答当前问题。`

The same template is used for every selected memory. Do not branch on question type, conflict type, timestamps, condition cues, gold answer, or gold-evidence text.

## Experiment Matrix

| Run | Varied factor | Context construction | Expected role |
|---|---|---|---|
| B0 | none | Original raw memories, original order | Baseline |
| B0R | replay only | Byte-identical to B0 | Noise floor |
| N | selected-memory marker | Prefix the neutral marker to every `gold_memory_id` | Oracle-selection/highlighting control |
| U | authorization semantics | Prefix the unified authorization to the same ids | Authorization treatment |

All other memory text remains byte-identical. No memory is filtered, moved, added, rewritten, or deleted.

## Causal Comparisons

- `B0R vs B0`: identical-input replay variation.
- `N vs B0`: effect of oracle selection/highlighting and added formatting.
- `U vs N`: primary authorization-semantic effect.
- `U vs B0`: total oracle highlighting plus authorization effect; secondary only.

Do not call `U vs B0` a pure authorization effect.

## Required Assertions

- All 896 samples have at least one `gold_memory_id`.
- Every U sample contains the unified template at least once.
- Every N sample contains the neutral template at exactly the same memory positions as U.
- U and N have equal memory counts, order, and raw memory text.
- No `ASSERT`, `REFUTE`, `SELECT`, or `CONDITION` branch remains in this experiment.
- No annotation contains the gold answer or any gold-evidence substring.
- `context_hash(U) != context_hash(B0)` and `context_hash(N) != context_hash(B0)` for all 896 samples.

## Analysis

Primary endpoint: paired correctness of U versus N on the 896 strict-supported samples, tested with exact McNemar (`b = U correct/N wrong`, `c = U wrong/N correct`). Report the paired risk difference and bootstrap 95% confidence interval.

Primary error-recovery endpoint: on the double-replay stable-wrong subset, report U and N flip rates and their paired difference.

Secondary outputs: hallucination-to-correct, omission-to-correct, regressions among baseline-correct samples, results by dataset and question type, and a manual audit of all U/N discordant cases or at least 100 if the set is larger.

## Resource Estimate

Four conditions times 896 samples require 3,584 answer-generation calls and 3,584 judge calls, for 7,168 API calls total. Based on observed A4 token usage, expected volume is about 6.22 million tokens. Monetary cost depends on the configured API endpoint and its current billing rate.

Run the baseline pair first, then N and U. Cache every request by case id, condition, context hash, model, and prompt-template hash. Re-run all U/N discordant cases once as a stability check before final reporting.

## Intended Commands After Implementation

```powershell
& "D:\conda_envs\o1\python.exe" "D:\幻觉\脚本\3.0\06_generate_a4_unified.py"
& "D:\conda_envs\o1\python.exe" "D:\幻觉\脚本\3.0\07_judge_a4_unified.py"
& "D:\conda_envs\o1\python.exe" "D:\幻觉\脚本\3.0\08_analyze_a4_unified.py"
```
