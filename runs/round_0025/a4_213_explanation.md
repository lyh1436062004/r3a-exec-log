# Why Only 213 A4 Samples Received Visible Authorization

A4 keeps all retrieved memories in their original order. A memory is considered for a relation label only when its id is in `gold_memory_ids`, which was selected by oracle semantic comparison against gold evidence.

The full pool contains 1,987 samples:

- 1,091 have no strict-supported gold memory, so no memory can receive a relation label.
- 896 have at least one strict-supported gold memory.

For those 896 samples, `label_to_license` returns one of four internal labels:

- `CONDITION` when a condition cue is present.
- `REFUTE` for Memory Conflict.
- `SELECT` for Dynamic Update.
- `ASSERT` for all other cases.

Only the first three labels have text templates. `ASSERT` has no entry in `LICENSE_TEMPLATES`, so it inserts no visible instruction and leaves the context equivalent to A0.

Consequently:

- 213 strict samples contain at least one visible `REFUTE`, `SELECT`, or `CONDITION` annotation.
- 683 strict samples are ASSERT-only and contain no visible authorization.

The overlapping visible-label counts are 140 REFUTE, 51 SELECT, and 27 CONDITION. They sum to 218 rather than 213 because five samples contain more than one visible label type across different retained memories.
