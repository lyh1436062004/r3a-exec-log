# R3a Round Analysis: round_0005

## File Changes

- `M	outputs/r3a_v2_dev_replay/r3a_v2_selected_evidence_replay.jsonl`
- `M	outputs/r3a_v2_dev_replay/r3a_v2_selected_evidence_replay_report.md`
- `M	outputs/r3a_v2_dev_replay/r3a_v2_full_selector_replay.jsonl`
- `M	outputs/r3a_v2_dev_replay/r3a_v2_full_selector_replay_report.md`
- `M	outputs/r3a_v2_dev_replay/r3a_v2_new_audit_candidates.csv`
- `M	tools/analyze_round.py`
- `M	.github/workflows/r3a_round_analyzer.yml`
- `A	runs/round_0005/run_summary.json`
- `A	runs/round_0005/file_change.txt`
- `A	runs/round_0005/diff.txt`

## Selected-Evidence Replay

- report: `outputs/r3a_v2_dev_replay/r3a_v2_selected_evidence_replay_report.md`
- true retention: 12/18 (66.67%)
- false rejection: 130/131 (99.24%)
- false retention: 1/131 (0.76%)
- retained precision strict: 12/13 (92.31%)
- retained acceptable rate: 16/17 (94.12%)
- kept count: 17

## Full-Selector Replay

- report: `outputs/r3a_v2_dev_replay/r3a_v2_full_selector_replay_report.md`
- v2 triggered count: 20
- matched_original_v1_selected count: 13
- matched original v1 selected: None
- full report metric protocol ok: True
- banned metric terms found: []

## Metric Consistency

- metric consistency ok: True
- mismatches: []

## Leakage Check

- selector files checked: []
- leakage ok: True
- leakage hits: {}

