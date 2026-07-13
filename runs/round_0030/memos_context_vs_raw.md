# Memos `context_str_full` vs `raw_memories`

## `raw_memories`

This is the structured payload retained from the Memos search API. The baseline concatenates `memory_detail_list` and `preference_detail_list`. Entries retain ids, memory values, preference and reasoning fields, timestamps, scores, tags, and other metadata.

It answers the retriever-level question: what objects did the memory service return?

## `context_str_full`

This is the final rendered string passed into `PROMPT_MEMOS` for answer generation. It contains the user header, each memory text recognized by the baseline serializer, and the Memos preference note.

The baseline serializer checks only `memory`, `memory_value`, `memory_key`, `content`, and `text`. It does not serialize objects that contain only `preference` and `reasoning`. Those objects remain in `raw_memories` but are absent from `context_str_full`.

## Measured Visibility

Among 896 samples classified as strict-supported using `raw_memories`:

- 536 have all oracle-matched gold memory ids visible in `context_str_full`.
- 227 have some visible and some hidden.
- 133 have no oracle-matched gold memory id visible.
- Therefore 763 have at least one visible supporting memory, while 133 do not.
- Overall, 360 samples have at least one supporting raw memory omitted from the answer-model context.

## Correct Metric Boundary

- Use `raw_memories` to measure retrieval-system recall.
- Use `context_str_full` to measure evidence availability to the answer model.
- For a retrieval-to-generation usage-gap experiment, the primary population should be the 763 generator-visible strict samples, not all 896 raw-level strict samples.

The earlier A0 reconstruction used an expanded serializer that recognized `preference/reasoning`, thereby exposing memories that the original baseline answer model had not seen. This caused the invalid replay mismatch.
