# Experiment 7 Matrix and Resource Plan

| Run ID | Factor | Value | Fixed config | Expected outcome |
|---|---|---|---|---|
| E7-AUTO-ALL | evidence view | raw payload + exact UA3 rendering | frozen 158 pool; seed 20260720 | separate A/B/C/D failure ownership |
| E7-HUMAN-A | validation stratum | up to 30 deterministic raw partial/missing cases; census if fewer | frozen 158 pool; seed 20260720 | estimate false missing judgments |
| E7-HUMAN-CONTAINED | validation stratum | 30 deterministic samples from raw contained | frozen 158 pool; seed 20260720 | estimate false containment judgments |

## Resource estimate

- GPU: 0 hours
- API calls: 159
- Rough input tokens: 568,706
- Maximum output tokens: 121,344
- Expected storage: 5.68 MB
- Cost: not hard-coded; compute from recorded token usage and the provider account's current rates

## Execution

```powershell
& "D:\conda_envs\o1\python.exe" "脚本\3.0\14_run_containment_audit.py" --phase all --yes
& "D:\conda_envs\o1\python.exe" "脚本\3.0\15_analyze_containment_audit.py"
```

## Analysis

Primary output is the A/B/C/D census. Secondary analyses stratify by dataset, question type, raw/rendered coverage, and temporal-information loss. Human validation uses two fixed 30-case strata.
