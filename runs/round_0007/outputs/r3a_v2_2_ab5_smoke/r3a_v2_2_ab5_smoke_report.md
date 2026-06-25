# R3a-v2.2 AB5 Smoke Report

## Scope

- system: mem0 medium
- sample size: 200
- seed: 20260618
- sample method: first 200 records via --limit; runner has no --seed option
- selector version: r3a_v2.2_premise_refutation
- no benchmark labels used by selector: yes
- oracle route: skipped

## Overall metrics

| condition | correct | hallucination | omission |
|---|---:|---:|---:|
| R0 | 76 / 38.00% | 32 / 16.00% | 92 / 46.00% |
| A_gated | 76 / 38.00% | 32 / 16.00% | 92 / 46.00% |
| B_gated_v2_2 | 76 / 38.00% | 32 / 16.00% | 92 / 46.00% |

## Transition analysis

| transition | count |
|---|---:|
| R0 omission -> B_gated_v2_2 correct | 0 |
| R0 hallucination -> B_gated_v2_2 correct | 0 |
| R0 correct -> B_gated_v2_2 hallucination | 0 |
| A_gated hallucination -> B_gated_v2_2 correct | 0 |
| A_gated correct -> B_gated_v2_2 hallucination | 0 |

## Gate behavior

- total rows: 200
- B_gated_v2_2 triggered count: 2
- trigger rate: 1.00%
- average selected evidence count: 0.010

### Relation distribution

| relation | count |
|---|---:|
| REFUTES_PREMISE | 2 |

### Reject reason distribution

| reject_reason | count |
|---|---:|
| premise_anchor_mismatch | 492 |
| slot_mismatch | 284 |
| absence_not_refutation | 81 |
| temporal_mismatch | 52 |
| not_refuting | 23 |
| object_specificity_mismatch | 2 |

## Safety check

- harm count: R0 correct -> B_gated_v2_2 hallucination = 0
- repair count: R0 omission/hallucination -> B_gated_v2_2 correct = 0
- net repair = 0

## Audit acceptance

- strict precision: 8/11 = 72.73%
- acceptable rate: 17/20 = 85.00%
- false_counterevidence count: 3
- pass: yes

## Decision

- revise_selector
