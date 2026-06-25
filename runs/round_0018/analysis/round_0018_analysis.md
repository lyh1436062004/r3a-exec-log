# Round 0018 Analysis

Task: R3a-v2.2 triggered sample answer utility evaluation.

Validation:
- Triggered sample count: 78.
- Unique qa_key count: 78.
- All samples are Memory Conflict.
- All samples reselected by R3a-v2.2 selector_version=r3a_v2_premise_refutation.

Route setup:
- R0 reused QA baseline response/label.
- A_triggered reused existing AB5 prompt-only a_all cache for all 78 samples.
- B_triggered reused 2 v2 smoke cached outputs and generated 76 targeted v2 evidence-admission outputs.
- B_memory_only was skipped.

Headline result:
- B vs R0: correct +2/78, hallucination -1/78, omission -1/78, net repairs +2.
- B vs A: correct -8/78, hallucination -16/78, omission +24/78, net repairs -8.

Interpretation note:
B_triggered is conservative relative to A_triggered: it strongly reduces hallucination against prompt-only, but often converts answers into omissions. Manual review should focus on B omissions where selected evidence may actually support a concrete corrective answer.
