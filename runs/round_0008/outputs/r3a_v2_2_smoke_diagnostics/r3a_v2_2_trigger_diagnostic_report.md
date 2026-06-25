# R3a-v2.2 Low-Trigger Diagnostic Report

## 1. Scope

This diagnostic explains low trigger behavior in the 200-sample AB5 smoke. It does not prove R3a-v2.2 effectiveness.

## 2. Inputs

- smoke jsonl: D:\幻觉\outputs\r3a_v2_2_ab5_smoke\r3a_v2_2_ab5_smoke.jsonl
- selector version metadata: r3a_v2.2_premise_refutation

## 3. Method

- Offline-only analysis of existing AB5 smoke rows.
- Reused existing per-row `a2_rejected` gate traces from the smoke output.
- No API calls were made.
- No prompt/retriever/memory-store changes were made.
- Benchmark labels were used only for post-hoc reporting and opportunity estimates, not selector decisions.

## 4. Trigger Summary

- total samples: 200
- triggered samples: 2
- trigger rate: 1.00%
- selected evidence count distribution: {'0': 198, '1': 2}
- relation distribution: {'REFUTES_PREMISE': 2}

## 5. Reject Reason Distribution

- non-triggered samples: 198
- per-sample dominant reject reason: {'triggered_or_no_rejections': 153, 'premise_anchor_mismatch': 29, 'slot_mismatch': 17, 'absence_not_refutation': 1}
- per-memory reject reason distribution: {'premise_anchor_mismatch': 492, 'slot_mismatch': 284, 'absence_not_refutation': 81, 'temporal_mismatch': 52, 'not_refuting': 23, 'object_specificity_mismatch': 2}

## 6. Near-Miss Analysis

- near-miss candidate rows: 122
- near-miss type counts: {'no_candidate_overlap': 153, 'absence_not_refutation': 25, 'related_but_not_refuting': 11, 'slot_value_near_miss': 8, 'triggered': 2, 'temporal_near_miss': 1}
- possible R3a opportunities: 18

## 7. Repair Opportunity Estimate

- R0 omission potential opportunities: 14
- R0 hallucination potential opportunities: 4
- R0 correct harm-risk cases if relaxed: 2

## 8. Low-Trigger Root Cause Attribution

- retrieved_evidence_genuinely_insufficient: 153 (76.50%)
- selector_too_strict: 20 (10.00%)
- router_or_premise_extraction_failure: 0 (0.00%)
- sample_contains_few_r3a_opportunity_cases: 182 (91.00%)
- non_r3a_relation_cases: 0 (0.00%)
- diagnostic_inconclusive: 0 (0.00%)
- dominant low-trigger cause: retrieved_evidence_genuinely_insufficient
- top reject reasons: {'premise_anchor_mismatch': 492, 'slot_mismatch': 284, 'absence_not_refutation': 81, 'temporal_mismatch': 52, 'not_refuting': 23, 'object_specificity_mismatch': 2}

## 9. Leakage / Label Use Check

- No benchmark labels were used by selector decisions in this diagnostic.
- `r0_label`, `a_gated_label`, and `b_gated_label` were used only for post-hoc statistics.
- No gold_answer/question_type/baseline_label was used for selector/router/gate decisions.

## 10. Recommended Next Decision

- keep_selector_and_change_sampling

## 11. What Not To Conclude

- This diagnostic does not prove R3a-v2.2 effectiveness.
- This diagnostic only explains low trigger behavior in the 200-sample AB5 smoke.
- Do not run full scale or larger smoke from this report alone.
- Do not treat O_oracle as an upper bound.

## 12. Files Generated

- r3a_v2_2_trigger_diagnostic.jsonl
- r3a_v2_2_trigger_diagnostic_report.md
- r3a_v2_2_near_miss_candidates.csv
- r3a_v2_2_low_trigger_summary.json
