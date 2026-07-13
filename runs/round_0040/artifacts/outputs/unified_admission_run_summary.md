# E1-prime Unified Post-Retrieval Admission

## Admission Coverage

- Samples audited: 1,987
- Raw memory objects: 22,385
- Canonically admitted objects: 22,385
- Dropped objects: 0
- Raw admission rate: 100.00%
- Strict samples: 896
- Strict oracle gold-memory ids: 1,908
- Strict oracle gold-memory ids admitted: 1,908
- Strict gold admission rate: 100.00%

## Answer Effect On A0-Stable-Wrong Strict Samples

| Pool | n | A6: unified conversion only | A7: conversion + authorization | A7-A6 |
|---|---:|---:|---:|---:|
| All strict stable-wrong | 867 | 271 (31.26%) | 290 (33.45%) | +19 (+2.19 pp) |
| Gold already visible | 737 | 202 (27.41%) | 219 (29.72%) | +17 (+2.31 pp) |
| Serialization loss | 130 | 69 (53.08%) | 71 (54.62%) | +2 (+1.54 pp) |

Paired A7 versus A6 McNemar on all 867 samples: b=76, c=57, exact p=0.11824. The unified authorization increment is not statistically significant at 0.05.

## Verification

- A6/A7 generation: 867/867 unique successes each
- A6/A7 final judge: 867/867 unique successes each
- Same admitted memory ids and order in A6/A7: 867/867
- Zero dropped memories in both arms: 867/867
- A7 authorization count equals oracle gold-id count: 867/867
- Condition-specific judge self-agreement: 200/200 (100%)

## Interpretation

The unified normalizer removes the raw-to-context admission loss completely. The large gain is caused primarily by making the complete raw retrieval payload visible: A6 recovers 31.26% of stable errors and 53.08% of the zero-visible serialization-loss stratum. Adding a generic authorization on top yields only a small, non-significant improvement. Admission coverage is therefore solved in this oracle experiment, while evidence selection, distractor control, and answer reasoning remain unsolved.
