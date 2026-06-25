# R3a-v2 Full-Selector Replay Report

This report runs v2 over full raw_memories.
Human labels refer only to the old v1 selected evidence, not necessarily to the v2 selected evidence.
Therefore this report must not report v2 precision from old labels.

## Summary

- total rows: 180
- v2 triggered count: 20
- v2 trigger rate: 11.11%
- matched_original_v1_selected count: 13
- matched_original_v1_selected rate among triggered: 65.00%

## Triggered rows by transition_type

| transition_type | triggered |
|---|---:|
| A_gated hallucination?B correct | 6 |
| R0 correct?B hallucination | 4 |
| R0 omission?B correct | 7 |
| R0 omission?B hallucination | 3 |

## Triggered rows by old v1-selected-evidence label

| old label | triggered |
|---|---:|
| ambiguous_counterevidence | 6 |
| false_counterevidence | 2 |
| true_counterevidence | 12 |

## Reject Reason Distribution

| reject_reason | count |
|---|---:|
| slot_mismatch | 64 |
| absence_not_refutation | 33 |
| premise_anchor_mismatch | 28 |
| not_refuting | 26 |
| object_specificity_mismatch | 5 |
| temporal_mismatch | 4 |

## Rows triggered by v2 where the old v1-selected evidence was labeled false_counterevidence

- sample_id=R3A-076 qa_key=11:39:3 matched_original_v1_selected=False selected=User enjoys watching technology documentaries for insights into future innovations, psychological thrillers for complex characters and unexpected twists that challenge analytical skills, and science‑fiction films for exploring human advance
- sample_id=R3A-100 qa_key=20:50:3 matched_original_v1_selected=True selected=User enjoys documentaries for in‑depth learning, romantic comedies for humor and heartwarming stories, and avoids horror films because they are too intense, as well as action‑packed thrillers due to their violent, high‑tension focus.

