# R3a Round Analysis: round_0007

## File Changes

- `M AGENTS.md`
- ` M outputs/r3a_v2_dev_replay/r3a_v2_dev_replay_report.md`
- ` M outputs/r3a_v2_dev_replay/r3a_v2_full_selector_replay.jsonl`
- ` M outputs/r3a_v2_dev_replay/r3a_v2_full_selector_replay_report.md`
- ` M outputs/r3a_v2_dev_replay/r3a_v2_new_audit_candidates.csv`
- ` M outputs/r3a_v2_dev_replay/r3a_v2_selected_evidence_replay.jsonl`
- ` M outputs/r3a_v2_dev_replay/r3a_v2_selected_evidence_replay_report.md`
- ` M tests/test_r3a_v2_selector.py`
- ` D 指令/第七次---DU诊断（纯统计不发API）.md`
- ` D "指令/第三次---推广V1到Dynamic Update和Memory Boundary.md"`
- ` D "指令/第二次---跑 Dynamic Update  Memory Boundary.md"`
- ` D 指令/第二次修复实验指令.md`
- ` D 指令/第五次---基础评测执行指令.md`
- ` D 指令/第八次---DU专项normal_qa的prompt_AB实验.md`
- ` D 指令/第六次---5系统真实API评测指令.md`
- ` D 指令/第六次---多系统评测执行指令（完整版）.md`
- ` D 指令/第十一次---Mem0_Long离线A2挂载评测.md`
- ` D 指令/第十二次---Memobase本地部署与安装验证.md`
- ` D 指令/第十五次---完整Context资产采集（离线拦截基础设施）.md`
- ` D 指令/第十四次---A2后端信号自适应阶段1（纯config零改本体）.md`
- ` D 指令/第十次---环境修复与验证.md`
- ` D 指令/第四次---多系统评测设计与执行.md`
- ` M 脚本/3.0/r3a_v2_selector.py`
- `?? outputs/baseline_full/baseline_full_run_summary.md`
- `?? outputs/baseline_full/memobase_baseline_runbook_2026-06-01.md`
- `?? outputs/baseline_sharded_v2/mem0_medium/key_04_user4/run.log`
- `?? outputs/baseline_sharded_v2/mem0_medium/key_10_user10/run.log`
- `?? outputs/baseline_sharded_v2/mem0_medium/manifest.json`
- `?? outputs/r3a_v2_2_ab5_smoke/`
- `?? outputs/supermemory_long_user0_key_capacity_test/manifest.json`
- `?? r3a-exec-log/`
- `?? run_mem0_long_gold_only_rejudge.py`
- `?? 临时/人工审查/r3a_v2_new_audit_candidates.xlsx`
- `?? 临时/人工审查/三审--V2.md`
- `?? 临时/人工审查/审查20条.md`
- `?? 修正V3/_run_mem0_tuning.py`
- `?? 修正V3/_run_proj_mem0.py`
- `?? 修正V3/_run_proj_supermemory.py`
- `?? 修正V3/_run_supermemory_heldout.py`
- `?? 修正V3/adaptive_stage1_runner.py`
- `?? 修正V3/adaptive_threshold_proj.py`
- `?? 修正V3/build_context_assets.py`
- `?? 指令/从前6.19/`
- `?? 指令/修改R3a/`
- `?? 脚本/2.0-修复版/_diag_sm_threshold.py`
- `?? 脚本/2.0-修复版/_test_a2_offline_replay.py`
- `?? 脚本/2.0-修复版/_test_mem0_a2_qa_user0.py`
- `?? 脚本/2.0-修复版/_test_mem0_quota_user0_long.py`
- `?? 脚本/2.0-修复版/_test_sm_a2_qa_user0.py`
- `?? 脚本/2.0-修复版/_test_sm_a2_qa_user0_v2.py`
- `?? 脚本/2.0-修复版/_test_sm_quota_1user.py`
- `?? 脚本/2.0-修复版/_verify_sm_key_isolation.py`
- `?? 脚本/2.0-修复版/run_mem0_medium_3way_offline.py`
- `?? 脚本/2.0-修复版/run_mem0_medium_ab_offline.py`
- `?? 脚本/2.0-修复版/run_memobase_long_baseline.py`
- `?? 脚本/2.0-修复版/run_memobase_medium_baseline.py`
- `?? 脚本/2.0-修复版/run_sm_baseline_full.py`
- `?? 脚本/2.0-修复版/smoke_memobase.py`
- `?? 脚本/2.0-修复版/smoke_memos.py`
- `?? 脚本/2.0-修复版/smoke_supermemory.py`
- `?? 脚本/2.0-修复版/smoke_zep.py`

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

- metric consistency ok: False
- mismatches: [{'metric': 'full_selector.v2_triggered_count', 'run_summary_value': None, 'report_value': 20}, {'metric': 'full_selector.matched_original_v1_selected_count', 'run_summary_value': None, 'report_value': 13}, {'metric': 'selected.kept_count', 'run_summary_value': None, 'report_value': 17}]

## Leakage Check

- selector files checked: []
- leakage ok: True
- leakage hits: {}

