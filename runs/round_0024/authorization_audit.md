# E1 Memos Authorization Audit

## Implementation

`collect_memory_ids` creates `gold_memory_ids` from semantic-judge results whose status is `supported`. The semantic judge compared retrieved memories against gold evidence.

In A3 and A4, only those `gold_memory_ids` are passed through `label_to_license`:

- A condition cue in the question or memory produces `CONDITION`.
- HaluMem `question_type == "Memory Conflict"` produces `REFUTE`.
- HaluMem `question_type == "Dynamic Update"` produces `SELECT`.
- All other cases produce `ASSERT`.

For A4 specifically, `build_memory_sequence` keeps all original `raw_memories` in their original order. Non-gold memories remain unannotated. The selected relation template is inserted immediately before each oracle-selected gold memory, and the original Memos note block is preserved.

Visible templates:

- `REFUTE`: explicitly permits and requires rejecting a false premise.
- `SELECT`: declares the memory to be the latest valid state.
- `CONDITION`: requires stating the condition under which the evidence holds.
- `ASSERT`: no template exists, so no visible annotation is added.

## Coverage

Among 1,987 successful A3 generations:

- 896 are `strict_supported`.
- 213 strict samples contain at least one visible `REFUTE`, `SELECT`, or `CONDITION` annotation.
- 683 strict samples contain only `ASSERT`, which adds no visible annotation.
- 140 samples contain `REFUTE`.
- 51 samples contain `SELECT`.
- 27 samples contain `CONDITION`.

Direct A0/A4 context-hash comparison shows:

- 213 A4 contexts differ from A0 and contain visible authorization.
- 1,774 A4 contexts are byte-equivalent in content hash to A0.
- Within the 896 strict-supported samples, 213 differ and 683 are unchanged.

Restricting to the 1,573 A0 stable-wrong cases:

- 140 received a visible A4 annotation; 47 flipped to correct (`33.57%`).
- 1,433 had A4 context identical to A0; 13 flipped to correct (`0.91%`), which is replay variation rather than an authorization effect.
- Thus 47 of the reported 60 full-pool A4 flips are attributable to cases where the authorization intervention actually changed the input.

Among the 140 visibly authorized stable-wrong cases, results by question type were: Memory Conflict 42/85, Dynamic Update 5/41, and 0/14 across the remaining question types.

Counts for REFUTE, SELECT, and CONDITION overlap when a sample contains multiple retained memories with different labels.

## Classification

The templates themselves do not include the gold answer or rewrite gold evidence. Leakage checks enforce that boundary. However, the decision about which retrieved memory receives a relation label is based on `gold_memory_ids`, and two relation types also use HaluMem gold question-type metadata. Therefore this is oracle relationship authorization under the supplied rubric. It is valid as an oracle upper-bound intervention, but it is not a deployable authorization method.

A3 also combines two interventions: oracle filtering from A2 plus visible relation authorization on only 213 strict samples. Consequently, A3 versus A2 measures the incremental effect of those labels, while A3's absolute flip rate must not be described as the effect of authorization alone.

For A4, the clean authorization-only descriptive rate is 47/140 among stable-wrong cases whose context actually changed. The original 60/1,573 rate mixes authorization-bearing cases with identical-context replay noise.
