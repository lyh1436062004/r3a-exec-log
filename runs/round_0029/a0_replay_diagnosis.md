# A0 Replay Diagnosis

## Intended Meaning

A0 was intended to reproduce the baseline: same retrieved context, same question, same answer prompt, same model, and no intervention. The protocol uses A0 to define `stable_wrong`.

## Actual Implementation

The saved baseline sample contains `context_str_full`, which is the context actually shown to the original answer model. Current A0 does not reuse this field. It calls `build_context`, which serializes every item in `raw_memories` and appends the Memos note.

This changes the model input. In the inspected examples, preference memories present in `raw_memories` but absent from the original `context_str_full` were added to A0.

## Measured Mismatch

Across all 1,987 samples, only one A0 context is byte-identical to its saved baseline context and 50 match after trimming outer whitespace.

Within the 896 strict-supported samples:

- 0 are byte-identical.
- 4 match after trimming outer whitespace.
- 298 are judged correct in A0 despite being selected from the original baseline wrong set.
- In 294 of those 298, the generated answer changed.
- In 4, the answer text stayed identical but the judge outcome changed.

Therefore the 298 changes are primarily new generations under changed contexts, with model and judge nondeterminism as additional factors. They are not evidence that an intervention fixed the original errors.

## Required Correction

A corrected A0 must pass `A0_context == context_str_full` and, ideally, full prompt SHA256 equality against the original baseline prompt. Do not rebuild A0 from `raw_memories`.

All current `stable_wrong`, A1-A4 flip rates, and McNemar results should be labeled replay-confounded until A0 and treatment contexts are rebuilt from the exact saved baseline context and rerun.
