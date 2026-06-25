# Round 0009 Analysis: R3a-v2.2 Memory Conflict Stratified Coverage Audit

## Scope
- input round: round_0008
- total smoke samples: 200
- Memory Conflict samples: 49 (24.50%)
- API calls: 0
- selector logic changed: false
- prompt/retriever/memory-store changed: false

## MC Trigger Coverage
- MC triggered count: 2
- MC trigger rate: 4.08%
- MC non-triggered count: 47
- overall trigger rate: 1.00%

## MC Labels
- R0 correct / hallucination / omission: 14 / 7 / 28
- B_gated_v2_2 correct / hallucination / omission: 14 / 7 / 28
- MC R0 omission but untriggered: 28
- MC R0 hallucination but untriggered: 7

## Coverage Diagnosis
- possible retrieved counterevidence: 19
- no retrieved counterevidence: 11
- unclear / manual audit needed: 17
- premise extraction errors: 15
- slot mapping errors: 13
- temporal gate too strict: 5
- explicit refutation gate too strict: 3

## Decision
- dominant failure source: premise_extraction_error
- can accept low-opportunity explanation: False
- recommended next decision: revise_premise_or_slot_or_refutation_after_manual_audit

Interpretation: MC-specific stratification weakens the previous broad low-opportunity explanation. The Memory Conflict subset contains a non-trivial band of possible retrieved counterevidence and many premise/slot failures; manual audit of mc_manual_audit_candidates.csv is needed before modifying selector logic.
