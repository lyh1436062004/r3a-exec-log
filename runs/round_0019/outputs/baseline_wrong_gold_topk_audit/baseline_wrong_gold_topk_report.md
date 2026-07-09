# Baseline Wrong Samples vs Gold Evidence in Top-k

## Answer

HaluMem source data alone is not enough to identify baseline-wrong samples; it must be joined with baseline outputs and judge labels. Existing baseline QA JSONL files do contain those labels plus retrieved `raw_memories`, so the audit can be computed offline.

## Overall Summary

| run_id | records | wrong | wrong rate | wrong with evidence | any strict hit | any strict / evidence-wrong | any coverage hit >=0.60 | coverage / evidence-wrong |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mem0_medium | 3467 | 2263 | 65.27% | 2091 | 0 | 0.00% | 23 | 1.10% |
| supermemory_medium | 3467 | 2128 | 61.38% | 1667 | 6 | 0.36% | 5 | 0.30% |
| memobase_medium | 3467 | 2451 | 70.70% | 2324 | 4 | 0.17% | 17 | 0.73% |
| memos_medium | 3467 | 1197 | 34.53% | 989 | 0 | 0.00% | 278 | 28.11% |
| mem0_long | 3467 | 2390 | 68.94% | 2239 | 0 | 0.00% | 13 | 0.58% |
| memobase_long | 3467 | 2575 | 74.27% | 2433 | 5 | 0.21% | 3 | 0.12% |
| memos_long | 3467 | 1209 | 34.87% | 998 | 0 | 0.00% | 259 | 25.95% |

## Files

- Detail CSV: `outputs\baseline_wrong_gold_topk_audit\baseline_wrong_samples_gold_topk.csv`
- By-question-type CSV: `outputs\baseline_wrong_gold_topk_audit\baseline_wrong_gold_topk_by_question_type.csv`
- Machine summary: `outputs\baseline_wrong_gold_topk_audit\baseline_wrong_gold_topk_summary.json`
