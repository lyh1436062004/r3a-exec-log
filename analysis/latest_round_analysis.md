# R3a Round Analysis: round_0002

## File Changes

- `﻿A	outputs/r3a_v2_dev_replay/r3a_v2_full_selector_replay.jsonl`
- `A	outputs/r3a_v2_dev_replay/r3a_v2_full_selector_replay_report.md`
- `A	outputs/r3a_v2_dev_replay/r3a_v2_new_audit_candidates.csv`
- `A	outputs/r3a_v2_dev_replay/r3a_v2_selected_evidence_replay.jsonl`
- `A	outputs/r3a_v2_dev_replay/r3a_v2_selected_evidence_replay_report.md`
- `M	脚本/3.0/run_r3a_v2_dev_replay.py`

## Selected-Evidence Replay

- report: `outputs/r3a_v2_dev_replay/r3a_v2_selected_evidence_replay_report.md`
- true retention: 9/18 (50.00%)
- false rejection: 126/131 (96.18%)
- false retention: 5/131 (3.82%)
- retained precision strict: 9/14 (64.29%)
- retained acceptable rate: 13/18 (72.22%)
- kept count: 18

## Full-Selector Replay

- report: `outputs/r3a_v2_dev_replay/r3a_v2_full_selector_replay_report.md`
- v2 triggered count: 30
- matched original v1 selected: None
- metric protocol ok: True
- banned metric terms found: []

## Leakage Check

- selector files checked: []
- leakage ok: True
- leakage hits: {}

