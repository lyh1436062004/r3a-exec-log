# round_0017 Analysis: P1 Audit Integration and Decision Freeze

## Scope

This round integrates the P1 manual audit results prepared in round_0015 and filled in round_0016. It freezes the decision for R3a-v2.2.

No API calls were made. No AB experiment was run. R3a selector, prompt, retriever, and memory store were not modified.

## Key Findings

- P1 candidate rows: 120
- P1 unique samples: 91
- Raw manual final labels: `{'非反证': 75, '非反证但有用': 43, '模糊反证': 1, '真反证': 1}`
- Raw manual should-trigger labels: `{'否': 118, '不确定': 1, '是': 1}`
- Final true counterevidence should-trigger rows: 0
- Confirmed R3a missed true counterevidence rows: 0
- Dominant case: `candidate_finder_false_positives`

## Decision

`do_not_revise_r3a_v2_2`

P1 does not support revising R3a-v2.2. The main result is high false positives from the high-recall candidate finder, not large confirmed R3a missed-trigger evidence.

## Next Step

`evaluate_r3a_v2_2_triggered_samples_utility`

Validate whether the 78 R3a-v2.2 triggered samples actually improve answer quality before any selector revision.
