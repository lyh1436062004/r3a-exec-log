# UA3 eight-step code walkthrough

UA3 is the unified-parser version of A3:

1. Select baseline-error cases with benchmark evidence and semantic retrieval audit data.
2. Restrict the primary experiment to `strict_supported` and optionally skip A0-replay-correct cases.
3. Read the complete `raw_memories` payload and assign positional IDs `m1..mN`.
4. Resolve `UA3` to base condition `A3`, using `gold_memory_ids` from the full raw payload.
5. Set the memory order to `gold_ids` only, dropping every non-gold raw memory.
6. Assign a fixed license to every admitted gold memory: CONDITION cue first, otherwise Memory Conflict to REFUTE, Dynamic Update to SELECT, and other types to ASSERT.
7. Extract each admitted memory with the canonical parser, inject non-ASSERT license text, exclude `pref_note`, run leakage checks, serialize the context, and record audit metadata.
8. Build the unchanged answer prompt, call the answer model, then apply the unchanged gold-only C/H/O judge.

Verified example `memos_medium:77`:

- question type: Memory Conflict
- raw memories: 12
- oracle gold IDs: m1, m3, m6
- admitted: 3
- dropped: 9
- licenses: REFUTE = 3

Important boundary: UA3 uses oracle `gold_memory_ids` and benchmark `question_type`. It is a mechanism upper-bound experiment, not a deployable A2 inference route.
