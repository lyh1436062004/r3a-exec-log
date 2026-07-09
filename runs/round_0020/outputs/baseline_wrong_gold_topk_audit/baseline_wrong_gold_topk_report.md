# Baseline Wrong Samples vs Gold Evidence in Top-k

## Answer

HaluMem source data alone is not enough to identify baseline-wrong samples; it must be joined with baseline outputs and judge labels. Existing baseline QA JSONL files do contain those labels plus the retriever/context returns saved as `raw_memories`, so the audit can be computed offline without re-querying paid retrievers.

## Retriever Sources

| run_id | retrieved set audited |
|---|---|
| mem0_medium | top_k=20 raw Mem0 search results |
| supermemory_medium | top_k=20 Supermemory search results |
| memobase_medium | Memobase context window, max_token_size=500 |
| memos_medium | Memos search memory_detail_list + preference_detail_list |
| mem0_long | historical Mem0 retrieved context parsed from string |
| memobase_long | Memobase context window, max_token_size=500 |
| memos_long | Memos search memory_detail_list + preference_detail_list |

## Overall Summary

| run_id | records | wrong | wrong rate | wrong with evidence | exact evidence hit | exact / evidence-wrong | supporting hit >=0.60 | supporting / evidence-wrong |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mem0_medium | 3467 | 2263 | 65.27% | 2091 | 0 | 0.00% | 23 | 1.10% |
| supermemory_medium | 3467 | 2128 | 61.38% | 1667 | 6 | 0.36% | 5 | 0.30% |
| memobase_medium | 3467 | 2451 | 70.70% | 2324 | 4 | 0.17% | 17 | 0.73% |
| memos_medium | 3467 | 1197 | 34.53% | 989 | 0 | 0.00% | 278 | 28.11% |
| mem0_long | 3467 | 2390 | 68.94% | 2239 | 0 | 0.00% | 13 | 0.58% |
| memobase_long | 3467 | 2575 | 74.27% | 2433 | 5 | 0.21% | 3 | 0.12% |
| memos_long | 3467 | 1209 | 34.87% | 998 | 0 | 0.00% | 259 | 25.95% |

## Memory Conflict Subset

| run_id | MC records | wrong | wrong rate | wrong with evidence | exact hit | supporting hit >=0.60 | supporting / evidence-wrong |
|---|---:|---:|---:|---:|---:|---:|---:|
| mem0_medium | 769 | 510 | 66.32% | 510 | 0 | 4 | 0.78% |
| supermemory_medium | 769 | 317 | 41.22% | 317 | 0 | 1 | 0.32% |
| memobase_medium | 769 | 634 | 82.44% | 634 | 1 | 4 | 0.63% |
| memos_medium | 769 | 119 | 15.47% | 119 | 0 | 46 | 38.66% |
| mem0_long | 769 | 534 | 69.44% | 534 | 0 | 2 | 0.37% |
| memobase_long | 769 | 668 | 86.87% | 668 | 2 | 2 | 0.30% |
| memos_long | 769 | 119 | 15.47% | 119 | 0 | 40 | 33.61% |

## Files

- Detail CSV: `outputs\baseline_wrong_gold_topk_audit\baseline_wrong_samples_gold_topk.csv`
- By-question-type CSV: `outputs\baseline_wrong_gold_topk_audit\baseline_wrong_gold_topk_by_question_type.csv`
- Machine summary: `outputs\baseline_wrong_gold_topk_audit\baseline_wrong_gold_topk_summary.json`
