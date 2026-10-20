# A2 MVP 结果报告

数字只来自已存在且输入身份可对齐的缓存；缺失不填零、不代填O。

执行CODEX_TASK_A2_MVP_AMENDMENT_01.md：主α=0.20、memos校准τ=0.15；只断言coverage/累计错误数单调，比例下降保留为非阻断诊断。核心控制器冻结于round_0073。

## 0. 环境与配置

预检日期：2026-10-09；Python：D:/conda_envs/o1/python.exe。

可用端点（仅名称与地址）：[{"key_variable": "OPENAI_API_KEY", "url_variable": "OPENAI_BASE_URL", "base_url": "https://api.deepseek.com"}]

依赖 import 实测：{"openai": "2.37.0", "dotenv": "available", "numpy": "2.3.5", "pandas": "3.0.1", "scipy": "1.17.1", "requests": "2.32.5", "sklearn": "1.8.0", "rank_bm25": "missing", "datasets": "4.7.0", "hypothesis": "missing"}

缺包回退：{"retriever": "pure-Python TF-IDF and cosine", "tests": "ordinary Python assertions"}

serializer 实测：{"passed": true, "samples": 1987, "byte_exact": 1987, "pref_note": 1986, "visible_supported": 763, "serialization_loss": 133}

实际调用缓存中的生成器模型：deepseek-chat

实际有有效判定缓存的生成器：deepseek-chat

缓存记录中的judge模型：["deepseek-chat"]

配置：`D:\幻觉\outputs\a2_mvp_v1\run_config.json`；git基础提交：`e04380ab7e201f4073fff3adc9451c5c83478719`；未提交脚本以SHA256为准；23版本SHA256：`983ed07e4d8dbee666359d8ae9057ceb33f3b6f56444e64a278f007cb9a6adc0`。

实际token可测用量：{"measured_usage": {"generations": {"prompt_tokens": 4521876, "completion_tokens": 50417, "total_tokens": 4572293}, "verdicts": {"prompt_tokens": 861118, "completion_tokens": 221431, "total_tokens": 1082549}, "estimates": {"prompt_tokens": 7477885, "completion_tokens": 4072777, "total_tokens": 11550662}, "pool_support_audit": {"prompt_tokens": 5841930, "completion_tokens": 674081, "total_tokens": 6516011}}, "scope": "Provider-reported generation/judge attempt ledgers when present, otherwise unique retained caches; per-case estimate caches plus unique failed-cache recovery journals; support last_execution once (attempt-ledger fallback). No cache+ledger double counting. Histories lost before recovery journals were available may be incomplete; this is not a billing statement. No usage returned by transport failures is unknown, not asserted zero."}

## 0.5 池定义与等价性校验

新池按检索支持条件（strict/partial、非空事实证据、serializer_ok）构造，不按baseline对错过滤。

修订案确认4062条池的范围：排除no_gold_retrieved；原错题池与本池不等价是非阻断发现。全轮对比统一使用fresh B0，归档判定仅作历史参考。

池统计：{"dataset": "memos", "source_n": 6934, "pool_n": 4062, "retrieval_strata": {"strict_supported": 3507, "partial_supported": 555}, "archived_baseline_labels": {"correct": 2933, "hallucination": 988, "omission": 141}, "exclusion_counts": {"empty_gold_evidence": 1656, "no_gold_retrieved": 1216}, "pool_sha256": "d7cee7d676670a3d37e82b9dd82118cc1176a86ccb3e1538079c29adfb43c6c8", "source_audit_complete": true}

完整差集/ID证据：`D:\幻觉\outputs\a2_mvp_v1\pools\memos_pool_equivalence.json`与analysis/*_summary.json；正文只报告计数。

真实分组与时间代理统计（保留source，旧池探针不能冒充新池）：{"n_cases": 4062, "n_raw": 46647, "memory_key_rate": 0.5200763178768195, "entity_anchors_rate": 0.5200763178768195, "multi_record_group_count": 5064, "group_size_distribution": {"1": 28202, "2": 2216, "3": 1279, "4": 790, "5": 477, "6": 302}, "adapter": {"n_records": 46647, "time_source": {"meta_ingest": 46647}, "time_proxy_count": 46647, "time_proxy_rate": 1.0, "capability_mask": {"text": true, "event_time": false, "ingest_time": true, "entity_anchors": true, "source_session": true, "retrieval_score": true, "confidence": true}, "capability_rates": {"text": 1.0, "event_time": 0.0, "ingest_time": 1.0, "entity_anchors": 0.5200763178768195, "source_session": 1.0, "retrieval_score": 1.0, "confidence": 0.5200763178768195}}, "source": "D:\\幻觉\\outputs\\a2_mvp_v1\\pools\\memos_pool.jsonl"}

Fresh B0等价性：完整=True；旧wrong=1987，新fresh wrong=1226，相等=False；差集旧中缺少1154，新增393。未完整重放时不可宣称已验证。

## 1. 阶段 A 冒烟结果（150条）

memos / deepseek-chat / 150条

| 臂 | 已判定 | 目标子集 | 缺失 | C数量/率[Wilson95%] | H数量/率[Wilson95%] | O数量/率[Wilson95%] | ΔC pp[配对95%] | ΔH pp[配对95%] | ΔO pp[配对95%] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | 150 | 150 | 0 | 90 / 60.00% [52.00,67.50] | 47 / 31.33% [24.45,39.14] | 13 / 8.67% [5.13,14.26] | 0.00 [-3.24,3.24] | 0.00 [-3.24,3.24] | 0.00 [-3.24,3.24] |
| B1 | 150 | 150 | 0 | 91 / 60.67% [52.68,68.12] | 33 / 22.00% [16.12,29.28] | 26 / 17.33% [12.11,24.19] | 0.67 [-9.32,10.61] | -9.33 [-19.09,1.03] | 8.67 [-0.74,17.51] |
| B2 | 150 | 150 | 0 | 95 / 63.33% [55.38,70.62] | 46 / 30.67% [23.85,38.45] | 9 / 6.00% [3.19,11.01] | 3.33 [-6.31,12.76] | -0.67 [-9.86,8.57] | -2.67 [-9.61,4.45] |
| A2 | 150 | 150 | 0 | 90 / 60.00% [52.00,67.50] | 40 / 26.67% [20.24,34.26] | 20 / 13.33% [8.80,19.70] | 0.00 [-7.14,7.14] | -4.67 [-12.69,3.66] | 4.67 [-3.15,12.18] |
| A2-nogate | 0 | 150 | 150 | 未执行 | 未执行 | 未执行 | 未得 | 未得 | 未得 |
| A2-nosal | 0 | 150 | 150 | 未执行 | 未执行 | 未执行 | 未得 | 未得 | 未得 |
| A2-nolic | 0 | 150 | 150 | 未执行 | 未执行 | 未执行 | 未得 | 未得 | 未得 |
| A2-noblock | 0 | 150 | 150 | 未执行 | 未执行 | 未执行 | 未得 | 未得 | 未得 |

| 验收项 | 通过 |
| --- | --- |
| four_arms_complete_no_leakage_no_crashes | True |
| A2_noop_strictly_between_zero_and_one | True |
| A2_actions_non_degenerate | True |
| current_pool_multirecord_groups_exist | True |
| invariants_mandatory_checks_satisfied | True |
| exactly_150_manifest_cases | True |
| B0_has_correct_and_wrong | True |

总体通过：True。

原始全部断言通过=False；明确按规范豁免=1。11差集按§13可豁免；必检项按修订案10a/10b真实通过，不要求10c比例单调。

## 2. memos 主实验

全池=4062；实际分析目标=400（subset400）。预算先行子集不得冒充全量。各臂缺失独立列出；不完整时率/CI仅针对已判定案例。

§9.4规定先400并报告，不是永久缩小目标；原完整全池八臂仍待按每批≤3臂、预算≤30000逐批补齐，须先真实通过所有gate。

| 臂 | 已判定 | 目标子集 | 缺失 | C数量/率[Wilson95%] | H数量/率[Wilson95%] | O数量/率[Wilson95%] | ΔC pp[配对95%] | ΔH pp[配对95%] | ΔO pp[配对95%] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | 400 | 400 | 0 | 266 / 66.50% [61.74,70.95] | 113 / 28.25% [24.06,32.85] | 21 / 5.25% [3.46,7.89] | 0.00 [-1.24,1.24] | 0.00 [-1.24,1.24] | 0.00 [-1.24,1.24] |
| B1 | 400 | 400 | 0 | 258 / 64.50% [59.69,69.03] | 77 / 19.25% [15.69,23.40] | 65 / 16.25% [12.96,20.18] | -2.00 [-7.92,3.97] | -9.00 [-14.73,-3.05] | 11.00 [5.95,15.78] |
| B2 | 400 | 400 | 0 | 280 / 70.00% [65.34,74.28] | 103 / 25.75% [21.71,30.25] | 17 / 4.25% [2.67,6.70] | 3.50 [-2.46,9.37] | -2.50 [-8.23,3.29] | -1.00 [-4.48,2.50] |
| A2 | 400 | 400 | 0 | 267 / 66.75% [61.99,71.19] | 95 / 23.75% [19.84,28.16] | 38 / 9.50% [7.00,12.77] | 0.25 [-5.00,5.50] | -4.50 [-9.74,0.86] | 4.25 [0.22,8.17] |
| A2-nogate | 0 | 400 | 400 | 未执行 | 未执行 | 未执行 | 未得 | 未得 | 未得 |
| A2-nosal | 0 | 400 | 400 | 未执行 | 未执行 | 未执行 | 未得 | 未得 | 未得 |
| A2-nolic | 0 | 400 | 400 | 未执行 | 未执行 | 未执行 | 未得 | 未得 | 未得 |
| A2-noblock | 0 | 400 | 400 | 未执行 | 未执行 | 未执行 | 未得 | 未得 | 未得 |

CHO比例用Wilson95%；Δ是同ID配对变化，其CI是discordant增/损的97.5% Wilson区间之Bonferroni差，不把有符号差值当二项比例。

| 臂 | 参照 | 同ID n | 错→对 | 对→错 | 精确McNemar p |
| --- | --- | --- | --- | --- | --- |
| B0 | B1 | 400 | 34 | 26 | 0.366294 |
| B0 | B2 | 400 | 23 | 37 | 0.092461 |
| B1 | B0 | 400 | 26 | 34 | 0.366294 |
| B1 | B2 | 400 | 29 | 51 | 0.0183161 |
| B2 | B0 | 400 | 37 | 23 | 0.092461 |
| B2 | B1 | 400 | 51 | 29 | 0.0183161 |
| A2 | B0 | 400 | 23 | 22 | 1 |
| A2 | B1 | 400 | 37 | 28 | 0.321084 |
| A2 | B2 | 400 | 19 | 32 | 0.0919145 |
| A2-nogate | B0 | 0 | 0 | 0 | 未得/不可计算 |
| A2-nogate | B1 | 0 | 0 | 0 | 未得/不可计算 |
| A2-nogate | B2 | 0 | 0 | 0 | 未得/不可计算 |
| A2-nosal | B0 | 0 | 0 | 0 | 未得/不可计算 |
| A2-nosal | B1 | 0 | 0 | 0 | 未得/不可计算 |
| A2-nosal | B2 | 0 | 0 | 0 | 未得/不可计算 |
| A2-nolic | B0 | 0 | 0 | 0 | 未得/不可计算 |
| A2-nolic | B1 | 0 | 0 | 0 | 未得/不可计算 |
| A2-nolic | B2 | 0 | 0 | 0 | 未得/不可计算 |
| A2-noblock | B0 | 0 | 0 | 0 | 未得/不可计算 |
| A2-noblock | B1 | 0 | 0 | 0 | 未得/不可计算 |
| A2-noblock | B2 | 0 | 0 | 0 | 未得/不可计算 |

McNemar将C视为成功、H/O视为失败；列出的多项检验p未经多重比较校正，不能只挑显著项。

### B0→各臂转移矩阵（行内比例）

| 臂 | 从 | 到 | 数量 | 行分母 | 行内比例 |
| --- | --- | --- | --- | --- | --- |
| B0 | correct | correct | 266 | 266 | 1 |
| B0 | correct | hallucination | 0 | 266 | 0 |
| B0 | correct | omission | 0 | 266 | 0 |
| B0 | hallucination | correct | 0 | 113 | 0 |
| B0 | hallucination | hallucination | 113 | 113 | 1 |
| B0 | hallucination | omission | 0 | 113 | 0 |
| B0 | omission | correct | 0 | 21 | 0 |
| B0 | omission | hallucination | 0 | 21 | 0 |
| B0 | omission | omission | 21 | 21 | 1 |
| B1 | correct | correct | 232 | 266 | 0.87218 |
| B1 | correct | hallucination | 13 | 266 | 0.0488722 |
| B1 | correct | omission | 21 | 266 | 0.0789474 |
| B1 | hallucination | correct | 23 | 113 | 0.20354 |
| B1 | hallucination | hallucination | 63 | 113 | 0.557522 |
| B1 | hallucination | omission | 27 | 113 | 0.238938 |
| B1 | omission | correct | 3 | 21 | 0.142857 |
| B1 | omission | hallucination | 1 | 21 | 0.047619 |
| B1 | omission | omission | 17 | 21 | 0.809524 |
| B2 | correct | correct | 243 | 266 | 0.913534 |
| B2 | correct | hallucination | 20 | 266 | 0.075188 |
| B2 | correct | omission | 3 | 266 | 0.0112782 |
| B2 | hallucination | correct | 29 | 113 | 0.256637 |
| B2 | hallucination | hallucination | 80 | 113 | 0.707965 |
| B2 | hallucination | omission | 4 | 113 | 0.0353982 |
| B2 | omission | correct | 8 | 21 | 0.380952 |
| B2 | omission | hallucination | 3 | 21 | 0.142857 |
| B2 | omission | omission | 10 | 21 | 0.47619 |
| A2 | correct | correct | 244 | 266 | 0.917293 |
| A2 | correct | hallucination | 13 | 266 | 0.0488722 |
| A2 | correct | omission | 9 | 266 | 0.0338346 |
| A2 | hallucination | correct | 20 | 113 | 0.176991 |
| A2 | hallucination | hallucination | 80 | 113 | 0.707965 |
| A2 | hallucination | omission | 13 | 113 | 0.115044 |
| A2 | omission | correct | 3 | 21 | 0.142857 |
| A2 | omission | hallucination | 2 | 21 | 0.0952381 |
| A2 | omission | omission | 16 | 21 | 0.761905 |
| A2-nogate | correct | correct | 0 | 0 | 未得/不可计算 |
| A2-nogate | correct | hallucination | 0 | 0 | 未得/不可计算 |
| A2-nogate | correct | omission | 0 | 0 | 未得/不可计算 |
| A2-nogate | hallucination | correct | 0 | 0 | 未得/不可计算 |
| A2-nogate | hallucination | hallucination | 0 | 0 | 未得/不可计算 |
| A2-nogate | hallucination | omission | 0 | 0 | 未得/不可计算 |
| A2-nogate | omission | correct | 0 | 0 | 未得/不可计算 |
| A2-nogate | omission | hallucination | 0 | 0 | 未得/不可计算 |
| A2-nogate | omission | omission | 0 | 0 | 未得/不可计算 |
| A2-nosal | correct | correct | 0 | 0 | 未得/不可计算 |
| A2-nosal | correct | hallucination | 0 | 0 | 未得/不可计算 |
| A2-nosal | correct | omission | 0 | 0 | 未得/不可计算 |
| A2-nosal | hallucination | correct | 0 | 0 | 未得/不可计算 |
| A2-nosal | hallucination | hallucination | 0 | 0 | 未得/不可计算 |
| A2-nosal | hallucination | omission | 0 | 0 | 未得/不可计算 |
| A2-nosal | omission | correct | 0 | 0 | 未得/不可计算 |
| A2-nosal | omission | hallucination | 0 | 0 | 未得/不可计算 |
| A2-nosal | omission | omission | 0 | 0 | 未得/不可计算 |
| A2-nolic | correct | correct | 0 | 0 | 未得/不可计算 |
| A2-nolic | correct | hallucination | 0 | 0 | 未得/不可计算 |
| A2-nolic | correct | omission | 0 | 0 | 未得/不可计算 |
| A2-nolic | hallucination | correct | 0 | 0 | 未得/不可计算 |
| A2-nolic | hallucination | hallucination | 0 | 0 | 未得/不可计算 |
| A2-nolic | hallucination | omission | 0 | 0 | 未得/不可计算 |
| A2-nolic | omission | correct | 0 | 0 | 未得/不可计算 |
| A2-nolic | omission | hallucination | 0 | 0 | 未得/不可计算 |
| A2-nolic | omission | omission | 0 | 0 | 未得/不可计算 |
| A2-noblock | correct | correct | 0 | 0 | 未得/不可计算 |
| A2-noblock | correct | hallucination | 0 | 0 | 未得/不可计算 |
| A2-noblock | correct | omission | 0 | 0 | 未得/不可计算 |
| A2-noblock | hallucination | correct | 0 | 0 | 未得/不可计算 |
| A2-noblock | hallucination | hallucination | 0 | 0 | 未得/不可计算 |
| A2-noblock | hallucination | omission | 0 | 0 | 未得/不可计算 |
| A2-noblock | omission | correct | 0 | 0 | 未得/不可计算 |
| A2-noblock | omission | hallucination | 0 | 0 | 未得/不可计算 |
| A2-noblock | omission | omission | 0 | 0 | 未得/不可计算 |

### Do-no-harm 与最坏转移 O→H

| 臂 | B0正确已配对 | C→H | C→O | O→H |
| --- | --- | --- | --- | --- |
| B0 | 266 | 0 | 0 | 0 |
| B1 | 266 | 13 | 21 | 1 |
| B2 | 266 | 20 | 3 | 3 |
| A2 | 266 | 13 | 9 | 2 |
| A2-nogate | 0 | 未得/不可计算 | 未得/不可计算 | 未得/不可计算 |
| A2-nosal | 0 | 未得/不可计算 | 未得/不可计算 | 未得/不可计算 |
| A2-nolic | 0 | 未得/不可计算 | 未得/不可计算 | 未得/不可计算 |
| A2-noblock | 0 | 未得/不可计算 | 未得/不可计算 | 未得/不可计算 |

### Flip rate 与动作分布

stable_wrong定义：archived wrong AND fresh B0 replay wrong; two observations, not three-repeat stability

| 臂 | 子池 | 配对/预期 | 救回 | flip rate | Wilson95% |
| --- | --- | --- | --- | --- | --- |
| B0 | stable_wrong | 92/92 | 0 | 0 | 0.0, 0.04008138928562172 |
| B0 | B0_wrong | 134/134 | 0 | 0 | 0.0, 0.027868675023899322 |
| B0 | B0_wrong_strict_supported | 100/100 | 0 | 0 | 3.469446951953614e-18, 0.03699349820698568 |
| B1 | stable_wrong | 92/92 | 11 | 0.119565 | 0.06809134808816239, 0.20153579593350626 |
| B1 | B0_wrong | 134/134 | 26 | 0.19403 | 0.13599200760807545, 0.2691216591975943 |
| B1 | B0_wrong_strict_supported | 100/100 | 22 | 0.22 | 0.150012823846054, 0.31070353514985793 |
| B2 | stable_wrong | 92/92 | 22 | 0.23913 | 0.16355145893303868, 0.33562143982467696 |
| B2 | B0_wrong | 134/134 | 37 | 0.276119 | 0.20746374022003577, 0.3572535769548446 |
| B2 | B0_wrong_strict_supported | 100/100 | 30 | 0.3 | 0.2189488529493276, 0.3958485463334666 |
| A2 | stable_wrong | 92/92 | 9 | 0.0978261 | 0.052323757089611615, 0.1755677951618667 |
| A2 | B0_wrong | 134/134 | 23 | 0.171642 | 0.11718348574039014, 0.24440191278276766 |
| A2 | B0_wrong_strict_supported | 100/100 | 18 | 0.18 | 0.1170022549894635, 0.2666735838630073 |
| A2-nogate | stable_wrong | 0/92 | 0 | 未得/不可计算 | None, None |
| A2-nogate | B0_wrong | 0/134 | 0 | 未得/不可计算 | None, None |
| A2-nogate | B0_wrong_strict_supported | 0/100 | 0 | 未得/不可计算 | None, None |
| A2-nosal | stable_wrong | 0/92 | 0 | 未得/不可计算 | None, None |
| A2-nosal | B0_wrong | 0/134 | 0 | 未得/不可计算 | None, None |
| A2-nosal | B0_wrong_strict_supported | 0/100 | 0 | 未得/不可计算 | None, None |
| A2-nolic | stable_wrong | 0/92 | 0 | 未得/不可计算 | None, None |
| A2-nolic | B0_wrong | 0/134 | 0 | 未得/不可计算 | None, None |
| A2-nolic | B0_wrong_strict_supported | 0/100 | 0 | 未得/不可计算 | None, None |
| A2-noblock | stable_wrong | 0/92 | 0 | 未得/不可计算 | None, None |
| A2-noblock | B0_wrong | 0/134 | 0 | 未得/不可计算 | None, None |
| A2-noblock | B0_wrong_strict_supported | 0/100 | 0 | 未得/不可计算 | None, None |

| 臂 | VOUCH | KEEP | DEMOTE | QUALIFY | REFUTE | BLOCK | no-op率 | BLOCK占比均值/范围 | 代理时序裁决 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | None / [None,None] | 0 |
| B1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | None / [None,None] | 0 |
| B2 | 1367 | 0 | 0 | 0 | 353 | 2848 | 0.1075 | 0.6281711760461761 / [0.0,1.0] | 0 |
| A2 | 17 | 426 | 0 | 829 | 114 | 693 | 0.58 | 0.15507449494949493 / [0.0,1.0] | 0 |
| A2-nogate | 0 | 0 | 0 | 0 | 0 | 0 | 未得/不可计算 | None / [None,None] | 0 |
| A2-nosal | 0 | 0 | 0 | 0 | 0 | 0 | 未得/不可计算 | None / [None,None] | 0 |
| A2-nolic | 0 | 0 | 0 | 0 | 0 | 0 | 未得/不可计算 | None / [None,None] | 0 |
| A2-noblock | 0 | 0 | 0 | 0 | 0 | 0 | 未得/不可计算 | None / [None,None] | 0 |

## 3. 错误分解协议

规范矛盾：§10.3的‘准入/使用失败’和‘生成失败’重叠，且四类不覆盖baseline正确样本，因此四个原始谓词不能诚实加总为100%。分别输出原始谓词与明确互斥层级＋正确/未知残余。

请求范围为memos全池4062条；A2只在实际子集有观测，未运行部分保持unknown。

| 原始谓词 | 命中 | 未知 | 占全池 |
| --- | --- | --- | --- |
| retrieval_failure | 0 | 555 | 0 |
| serialization_loss | 221 | 555 | 0.0544067 |
| admission_usage_failure | 781 | 555 | 0.19227 |
| generation_failure | 84 | 3522 | 0.0206795 |

| 互斥层级/残余 | 数量 | 占全池 |
| --- | --- | --- |
| unresolved_or_missing_evidence | 997 | 0.245446 |
| baseline_correct_residual | 2836 | 0.698178 |
| serialization_loss | 144 | 0.0354505 |
| generation_failure_after_A2 | 69 | 0.0169867 |
| admission_usage_failure_recovered_by_A2 | 16 | 0.00393895 |

原始多谓词重叠69条；互斥合计4062。可见性语义：At least one strict gold-memory position is visible, matching the existing visibility audit; not proof of complete answer sufficiency. Partial-only rows without strict positions remain unknown.

## 4. oracle–learned 归因分解

| 配置 | Stage0 | Stage1 | Stage2 | Stage3 | flip |
| --- | --- | --- | --- | --- | --- |
| B0 | — | — | — | — | 0（定义） |
| A3历史 | baseline | oracle | hard map | 真实 | 46.13%：历史参照 |
| UA3历史 | canonical | oracle | hard map | 真实 | 53.29%：历史参照 |
| B2本次 | 真实 | 真实 | argmax固定映射 | 真实 | 见真实strict子池flip表 |
| A2本次 | 真实 | 真实 | 真实 | 真实 | 见真实strict子池flip表 |
| ORACLE_REL | 真实 | oracle | 真实 | 真实 | 未重跑，无该配置分数 |

UA3不能冒充‘oracle关系＋真实Stage2’。仅在case_id与question/gold/raw/context均相等、两次B0均错的共同ID集合重算描述性差值；它不是单阶段因果损耗。历史两百分比也不保证同分母。

| 历史→当前 | 同输入ID n | 历史flip | 当前flip | 描述性损耗pp |
| --- | --- | --- | --- | --- |
| A3→B2 | 55 | 0.345455 | 0.2 | 14.5455 |
| A3→A2 | 55 | 0.345455 | 0.0909091 | 25.4545 |
| UA3→B2 | 68 | 0.470588 | 0.25 | 22.0588 |
| UA3→A2 | 68 | 0.470588 | 0.102941 | 36.7647 |

## 5. 校准

case_id SHA256前8位mod2固定cal/test；只用cal求阈值。该算法是经验风险门控，不能未经证明声称严格conformal有限样本保证；经验noop_err也不必随阈值单调。

memos校准实测（pilot/full范围不可混用）：{"alpha": 0.2, "tau": 0.15, "coverage": 0.5625, "noop_err": 0.1909722222222222, "n_cal": 2048, "n_cal_baseline_wrong": 616, "n_cal_noop": 1152, "degenerate_flag": false, "test": {"tau": 0.15, "coverage": 0.5645481628599801, "noop_err": 0.18997361477572558, "n": 2014, "n_noop": 1137, "n_noop_wrong": 216}, "monotonicity_violations": {"count": 6, "first": {"previous_tau": 0.0, "tau": 0.05, "previous_noop_err": 0.4090909090909091, "noop_err": 0.1032258064516129}, "detail_file": "D:\\幻觉\\outputs\\a2_mvp_v1\\calibration\\memos.json"}, "feasibility_diagnostic": {"candidate_grid_includes_empty_minus_inf": true, "positive_coverage_feasible_candidates": 4, "feasible_interval_count": 2, "feasible_set_contiguous_on_candidate_grid": false, "conservative_prefix_tau": "-inf", "conservative_prefix_coverage": 0.0, "conservative_prefix_noop_err": 0.0}, "n_estimator_failed": 0, "failure_override_note": "failed estimates bypass even tau=-inf; curve above is the exact risk<=tau formula", "guarantee_note": "Empirical cal-split selection per task book, not a distribution-free finite-sample conformal proof", "pool": "memos", "scope": "full", "version": "task-book-exact-empirical-gate-v1", "seed": 20260709, "input_hash": "c0eccf7e5fc0e06dafe6ca8cd76f49025d504824422b55a3dc2020e46990e7f7", "baseline_sources": ["fresh_b0"], "n_total": 4062}

| alpha | tau | cal_coverage | cal_noop_err | test_coverage | test_noop_err | n_cal | n_test | degenerate_flag | scope | candidate_grid_includes_empty_minus_inf | positive_coverage_feasible_candidates | feasible_interval_count | feasible_set_contiguous_on_candidate_grid | conservative_prefix_tau | conservative_prefix_coverage | conservative_prefix_noop_err |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.05 | -inf | 0.0 | 0.0 | 0.0 | 0.0 | 2048 | 2014 | True | full | True | 0 | 1 | True | -inf | 0.0 | 0.0 |
| 0.1 | -inf | 0.0 | 0.0 | 0.0 | 0.0 | 2048 | 2014 | True | full | True | 0 | 1 | True | -inf | 0.0 | 0.0 |
| 0.2 | 0.15 | 0.5625 | 0.1909722222222222 | 0.5645481628599801 | 0.18997361477572558 | 2048 | 2014 | False | full | True | 4 | 2 | False | -inf | 0.0 | 0.0 |
| 0.3 | 0.8 | 0.98583984375 | 0.29668152550767707 | 0.9826216484607746 | 0.3006568974229409 | 2048 | 2014 | False | full | True | 17 | 2 | False | -inf | 0.0 | 0.0 |

## 6. 消融

| 臂 | 指标 | 配对n | 相对B0 Δ pp | 95% CI |
| --- | --- | --- | --- | --- |
| A2-nogate | correct | 0 | 未得/不可计算 | None,None |
| A2-nogate | hallucination | 0 | 未得/不可计算 | None,None |
| A2-nogate | omission | 0 | 未得/不可计算 | None,None |
| A2-nosal | correct | 0 | 未得/不可计算 | None,None |
| A2-nosal | hallucination | 0 | 未得/不可计算 | None,None |
| A2-nosal | omission | 0 | 未得/不可计算 | None,None |
| A2-nolic | correct | 0 | 未得/不可计算 | None,None |
| A2-nolic | hallucination | 0 | 未得/不可计算 | None,None |
| A2-nolic | omission | 0 | 未得/不可计算 | None,None |
| A2-noblock | correct | 0 | 未得/不可计算 | None,None |
| A2-noblock | hallucination | 0 | 未得/不可计算 | None,None |
| A2-noblock | omission | 0 | 未得/不可计算 | None,None |

## 7. λ_O 敏感性

| 配置 | 指标 | 实际配对n | Δ pp |
| --- | --- | --- | --- |
| A2 | hallucination | 400 | -4.5 |
| A2 | omission | 400 | 4.25 |

## 8. 估计器内在评估

关系accuracy/macro-F1仅为粗代理，不作为估计器质量结论；当前目标集中缺少四个关系类的独立标注。risk AUC与oracle修复关联也是事后诊断，不证明框架成立或方法因果收益。

`D:\幻觉\outputs\a2_mvp_v1\analysis\memos__deepseek-chat_intrinsic.json`：{"pool": "memos", "generator": "deepseek-chat", "estimator_model": "deepseek-chat", "pool_n": 4062, "valid_estimate_n": 4062, "failed_estimate_n": 0, "oracle_relation_proxy": {"n": 10849, "accuracy": 0.4856668817402526, "macro_F1_all_six_labels": 0.13298740905744796, "macro_F1_represented_union": 0.13298740905744796, "per_class": [{"relation": "SUPPORT", "target_n": 8720, "predicted_n": 5415, "precision": 0.9602954755309326, "recall": 0.5963302752293578, "f1": 0.7357622921825256}, {"relation": "REFUTE", "target_n": 0, "predicted_n": 2194, "precision": 0.0, "recall": 0.0, "f1": 0.0}, {"relation": "SUPERSEDED", "target_n": 2129, "predicted_n": 91, "precision": 0.7582417582417582, "recall": 0.032409581963363084, "f1": 0.062162162162162166}, {"relation": "CURRENT", "target_n": 0, "predicted_n": 71, "precision": 0.0, "recall": 0.0, "f1": 0.0}, {"relation": "MISBIND", "target_n": 0, "predicted_n": 13, "precision": 0.0, "recall": 0.0, "f1": 0.0}, {"relation": "INSUFFICIENT", "target_n": 0, "predicted_n": 3065, "precision": 0.0, "recall": 0.0, "f1": 0.0}], "confusion": {"SUPPORT": {"SUPPORT": 5200, "REFUTE": 2192, "SUPERSEDED": 22, "CURRENT": 61, "MISBIND": 12, "INSUFFICIENT": 1233}, "REFUTE": {"SUPPORT": 0, "REFUTE": 0, "SUPERSEDED": 0, "CURRENT": 0, "MISBIND": 0, "INSUFFICIENT": 0}, "SUPERSEDED": {"SUPPORT": 215, "REFUTE": 2, "SUPERSEDED": 69, "CURRENT": 10, "MISBIND": 1, "INSUFFICIENT": 1832}, "CURRENT": {"SUPPORT": 0, "REFUTE": 0, "SUPERSEDED": 0, "CURRENT": 0, "MISBIND": 0, "INSUFFICIENT": 0}, "MISBIND": {"SUPPORT": 0, "REFUTE": 0, "SUPERSEDED": 0, "CURRENT": 0, "MISBIND": 0, "INSUFFICIENT": 0}, "INSUFFICIENT": {"SUPPORT": 0, "REFUTE": 0, "SUPERSEDED": 0, "CURRENT": 0, "MISBIND": 0, "INSUFFICIENT": 0}}}, "non_gold_question_type_mapping": {"dynamic update": "SUPERSEDED", "knowledge-update": "SUPERSEDED", "memory binding": "MISBIND", "entity misbinding": "MISBIND", "insufficient information": "INSUFFICIENT", "unanswerable": "INSUFFICIENT", "abstention": "INSUFFICIENT"}, "skipped_non_gold_by_type": {"Memory Conflict": 10854, "Basic Fact Recall": 9423, "Generalization & Application": 12277, "Multi-hop Inference": 3244}, "oracle_proxy_warning": "Gold positions are SUPPORT by the requested diagnostic convention even when real relations may be REFUTE/CURRENT. Task type is a coarse proxy; not every non-gold update memory is necessarily obsolete. Unidentified non-gold relations are skipped; model predictions never construct targets. This is partial proxy agreement, not six-way independently annotated accuracy.", "sufficiency_oracle_repair": {"oracle_arm": "UA3", "same_input_case_id_join_n": 616, "point_biserial_r": 0.062156072721612915, "oracle_repaired_n": 296, "missing_reason": null, "scope": "Historical wrong AND fresh B0 wrong; exact question/gold/raw/context match; oracle arm has a real verdict. No inferred recovery from a predicted relation."}, "risk_vs_fresh_B0": {"n": 4062, "B0_wrong_n": 1226, "auc_including_failed_safe_defaults": 0.6885256156570038, "auc_successful_estimates_only": 0.6885256156570038, "score_groups": {"B0_correct": {"n": 2836, "mean": 0.1857052186177715, "min": 0.0, "max": 0.95}, "B0_wrong": {"n": 1226, "mean": 0.2709543230016313, "min": 0.0, "max": 0.9}}, "missing_reason": null}, "input_hash": "025b957a7b2483d78344846641fec469f0c3ba19af2e960803e700a3177d2ed5", "script_sha256": "19aeb91561c9300fa61adf6182c432e081346dd065a470781facf34b1dda4a89", "estimated_calls": 0, "missing_estimate_n": 0, "stale_estimate_n": 0, "rejected_stale_B0_n": 0}

## 9. 跨生成器（或跨记忆系统）

仅1个生成器端点可用，阶段D按任务书跳过；换同端点别名不是跨家族验证。

## 10. LongMemEval（或阻断＋阶段E）

LongMemEval获取状态（修订案最多3种策略尝试；失败后继续阶段E，不阻断主线）：{"status": "blocked", "fallback": "E", "dataset": "xiaowu0162/longmemeval-cleaned", "variant": "cleaned S", "network_attempts_policy": "one; no repeat", "reason": "ConnectTimeout: HTTPSConnectionPool(host='huggingface.co', port=443): Max retries exceeded with url: /api/datasets/xiaowu0162/longmemeval-cleaned (Caused by ConnectTimeoutError(<HTTPSConnection(host='huggingface.co', port=443) at 0x2d93ddbe750>, 'Connection to huggingface.co timed out. (connect timeout=60)'))", "llm_calls": 0}

阶段E mem0替代：目标池存在=True，B1/A2实际目标集判定完整=False。未完成则任务仍有待办。

阶段E memobase替代：目标池存在=True，B1/A2实际目标集判定完整=False。未完成则任务仍有待办。

阶段E supermemory替代：目标池存在=True，B1/A2实际目标集判定完整=False。未完成则任务仍有待办。

不得把oracle retrieval reading failure说成首次发现；LME更新题允许包含旧信息，正确拒答算C不算O；数据修订/文件hash与recall@20见pool/config实测。

## 11. 意外发现与失败案例

| case_id | 问题 | B0→A2 | 实际回答B0 / A2 | 动作与诊断 | nolic正确关联 |
| --- | --- | --- | --- | --- | --- |
| memos_long:1289 | What type of clothing might Ananya prefer for a film industry event on August 5, 2027? | correct→hallucination | Relaxed, non-formal clothing. / Colorful kurtas, as she prefers vibrant, culturally resonant styles. | {'KEEP': 3, 'QUALIFY': 5, 'BLOCK': 4}  | False |
| memos_long:163 | How might Martin's family background influence his future decisions in healthcare initiatives? | correct→omission | Deep medical family background drives healthcare focus. / Deep medical family influence. | {'QUALIFY': 11, 'KEEP': 1}  | False |
| memos_long:2259 | How might Williams Daniel's promotion to lead director influence his work-life balance in 2026? | correct→omission | Improved work-life balance through delegation. / Insufficient evidence; memories don't confirm Williams was promoted to lead director. | {'QUALIFY': 10, 'BLOCK': 2}  | False |
| memos_long:239 | How might Johnson Joseph enhance guest experiences at Albi B&B by integrating folk music after June 6, 2032? | correct→hallucination | Offer local culture via storytelling. / By offering cultural enrichment and storytelling. | {'VOUCH': 1, 'QUALIFY': 7, 'KEEP': 3, 'REFUTE': 1}  | False |
| memos_long:2683 | How might Oleksandr's appreciation for cats influence his choice of home decor after Feb 01, 2033? | correct→hallucination | Cat-themed decor for comfort. / Bird-friendly decor with cat comfort. | {'KEEP': 2, 'QUALIFY': 9, 'BLOCK': 1}  | False |

A2错而nolic对仅是license关联回归候选，不足以证明单独license因果；模板授权可能放大错误后验，代理写入时间也可能误当事件时间。

## 12. 结论与下一步

Stage1/2真实实现后，A2相对B1在400个同ID案例的ΔC=2.250pp，精确McNemar p=0.321084。

相对强B1增益小于3pp，未达到任务书所述差距；不得弱化B1制造收益。

不是标签拟合的证据应来自物理隔离输入、真实Stage1/2、强B1/真实B2对照与同ID结果；历史神谕分数不构成当前方法收益。短板及下一步以实际错误与缺失分析为准。

主α=0.20由修订案在观察round_0074结果后指定；阈值仍只在cal求解，但这不是新的、未查看的独立确认性test。cal/test接近仅作观测，不据此证明无过拟合。

完善阶段清单（本轮不执行）：1.结构化二阶风险分数增强；2.记忆正文事件时间来源增强；3.100–200条真实关系人工标注；4.补入no_gold_retrieved测量完整检索失败；5.获得其他家族端点后跨生成器。

## 13. 阻断、规范矛盾与未完成项

- memos原始全池八臂范围尚未完成；400条仅先行报告，不能替代完整目标。

- LongMemEval获取未完成；修订案授权最多3种策略，随后不再重试。阶段E本轮必做，三系统须逐项核验真实产出。

- 已知非阻断发现：100%写入代理时间、risk分辨率有限、粗代理目标不完整、池范围差异、部分α退化。比例下降已由修订案废除为断言；原公式与完整诊断保留，完善项本轮不执行。
