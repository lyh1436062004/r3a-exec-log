# Round 0008 Analysis: R3a-v2.2 Low-Trigger Diagnostic

## Scope
- input round: round_0007
- selector version: r3a_v2.2_premise_refutation
- input smoke rows: 200
- API calls: 0
- selector logic changed: false
- prompt/retriever/memory-store changed: false

## Trigger Behavior
- triggered samples: 2
- trigger rate: 1.00%
- selected evidence distribution: 0=198, 1=2
- relation distribution: REFUTES_PREMISE=2

## Reject Reasons
- top per-memory reasons: premise_anchor_mismatch=492, slot_mismatch=284, absence_not_refutation=81, temporal_mismatch=52, not_refuting=23
- per-sample dominant reasons: triggered_or_no_rejections=153, premise_anchor_mismatch=29, slot_mismatch=17, absence_not_refutation=1

## Near Miss / Opportunity
- near-miss candidate rows: 122
- potential R3a opportunity count: 18
- R0 omission opportunities: 14
- R0 hallucination opportunities: 4
- R0 correct harm-risk cases if relaxed: 2

## Root Cause
- retrieved evidence genuinely insufficient: 153 / 200 (76.50%)
- selector too strict: 20 / 200 (10.00%)
- router or premise extraction failure: 0 / 200 (0.00%)
- sample contains few R3a opportunity cases: 182 / 200 (91.00%)
- dominant low-trigger cause: retrieved_evidence_genuinely_insufficient

## Decision
keep_selector_and_change_sampling

Interpretation: the 1.00% smoke trigger rate is mainly explained by the first-200 smoke sample containing very few usable R3a opportunities and many rows with no viable counterevidence candidate. There is a smaller near-miss band that can be manually audited before deciding whether selector changes are justified.
