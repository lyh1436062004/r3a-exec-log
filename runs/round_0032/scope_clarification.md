# Post-Retrieval Scope Clarification

The omitted count is 133, not 113. These samples are within the A2 project boundary because the retriever returned supporting evidence in `raw_memories`, but the baseline adapter did not serialize any matched supporting memory into `context_str_full`.

The 896 raw-strict samples should be separated into mutually exclusive strata:

- 536 complete-visible: all oracle-matched supporting memories are visible to the answer model.
- 227 partial-visible: at least one is visible and at least one is omitted.
- 133 zero-visible: all oracle-matched supporting memories are omitted.

All three strata are post-retrieval opportunities. However, they answer different research questions:

- The 133 zero-visible cases measure serialization/admission recovery.
- The 763 samples with at least one visible supporting memory measure the evidence-use gap.
- The 227 partial-visible cases belong to both analyses and should be reported explicitly rather than silently merged.

The defensible overall claim is that A2 controls the path from retrieved memory objects to model-visible, authorized context. It should not describe the 133 cases as failures by an LLM that had already seen the evidence.
