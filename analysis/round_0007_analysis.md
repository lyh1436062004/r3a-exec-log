# Round 0007 Analysis: R3a-v2.2 Audit Acceptance + AB5 Smoke

## Audit Gate
- strict precision: 72.73%
- acceptable rate: 85.00%
- false_counterevidence count: 3
- decision: pass

## AB5 Smoke Scope
- system: mem0 medium
- sample size: 200
- seed metadata: 20260618
- sample method: first 200 records via runner --limit; runner has no --seed option
- selector version: r3a_v2.2_premise_refutation

## Overall Metrics
- R0 correct/hallucination/omission: 76 / 32 / 92
- A_gated correct/hallucination/omission: 76 / 32 / 92
- B_gated_v2_2 correct/hallucination/omission: 76 / 32 / 92

## Gate Behavior
- trigger count: 2
- trigger rate: 1.00%
- top reject reasons: premise_anchor_mismatch=492, slot_mismatch=284, absence_not_refutation=81

## Safety
- repair count: 0
- harm count: 0
- net repair: 0

## Decision
revise_selector

Reason: audit gate passed and no harm was observed, but B_gated_v2_2 did not improve R0 correct rate and trigger rate was below the 5%-15% smoke threshold.
