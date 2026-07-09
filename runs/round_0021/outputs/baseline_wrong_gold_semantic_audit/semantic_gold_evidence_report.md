# Semantic Gold Evidence Retrieval Audit

Judged wrong samples with non-empty gold evidence: 12741

The semantic judge sees each sample's saved `raw_memories` retrieval/context return and decides whether they support each gold evidence item. It counts paraphrases, summaries, and aggregated memories, while rejecting mere topical similarity or stale contradictory facts.

## Overall

| run_id | wrong+evidence | exact hit | token hit >=0.60 | semantic supported | semantic supported % | semantic partial/support | partial/support % |
|---|---:|---:|---:|---:|---:|---:|---:|
| mem0_long | 2239 | 0 | 13 | 46 | 2.05% | 188 | 8.40% |
| mem0_medium | 2091 | 0 | 23 | 239 | 11.43% | 445 | 21.28% |
| memobase_long | 2433 | 5 | 3 | 29 | 1.19% | 121 | 4.97% |
| memobase_medium | 2324 | 4 | 17 | 84 | 3.61% | 235 | 10.11% |
| memos_long | 998 | 0 | 259 | 451 | 45.19% | 564 | 56.51% |
| memos_medium | 989 | 0 | 278 | 445 | 44.99% | 565 | 57.13% |
| supermemory_medium | 1667 | 6 | 5 | 19 | 1.14% | 44 | 2.64% |

## Memory Conflict

| run_id | MC wrong+evidence | semantic supported | semantic supported % | semantic partial/support | partial/support % |
|---|---:|---:|---:|---:|---:|
| mem0_long | 534 | 7 | 1.31% | 19 | 3.56% |
| mem0_medium | 510 | 44 | 8.63% | 58 | 11.37% |
| memobase_long | 668 | 12 | 1.80% | 18 | 2.69% |
| memobase_medium | 634 | 10 | 1.58% | 20 | 3.15% |
| memos_long | 119 | 72 | 60.50% | 74 | 62.18% |
| memos_medium | 119 | 69 | 57.98% | 76 | 63.87% |
| supermemory_medium | 317 | 3 | 0.95% | 6 | 1.89% |
