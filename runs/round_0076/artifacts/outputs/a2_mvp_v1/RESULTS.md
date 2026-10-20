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

配置：`D:\幻觉\outputs\a2_mvp_v1\run_config.json`；git基础提交：`e04380ab7e201f4073fff3adc9451c5c83478719`；未提交脚本以SHA256为准；23版本SHA256：`19838ca0752a78fe5d923797f92894a92aa9c607c61200a7566926aef9c3fb76`。

实际token可测用量：{"measured_usage": {"generations": {"prompt_tokens": 39159254, "completion_tokens": 371751, "total_tokens": 39531005}, "verdicts": {"prompt_tokens": 5563683, "completion_tokens": 1416962, "total_tokens": 6980645}, "estimates": {"prompt_tokens": 7477885, "completion_tokens": 4072777, "total_tokens": 11550662}, "pool_support_audit": {"prompt_tokens": 5841930, "completion_tokens": 674081, "total_tokens": 6516011}}, "scope": "Provider-reported generation/judge attempt ledgers when present, otherwise unique retained caches; per-case estimate caches plus unique failed-cache recovery journals; support last_execution once (attempt-ledger fallback). No cache+ledger double counting. Histories lost before recovery journals were available may be incomplete; this is not a billing statement. No usage returned by transport failures is unknown, not asserted zero."}

## 0.5 池定义与等价性校验

新池按检索支持条件（strict/partial、非空事实证据、serializer_ok）构造，不按baseline对错过滤。

修订案确认4062条池的范围：排除no_gold_retrieved；原错题池与本池不等价是非阻断发现。全轮对比统一使用fresh B0，归档判定仅作历史参考。

池统计：{"dataset": "memos", "source_n": 6934, "pool_n": 4062, "retrieval_strata": {"strict_supported": 3507, "partial_supported": 555}, "archived_baseline_labels": {"correct": 2933, "hallucination": 988, "omission": 141}, "exclusion_counts": {"empty_gold_evidence": 1656, "no_gold_retrieved": 1216}, "pool_sha256": "d7cee7d676670a3d37e82b9dd82118cc1176a86ccb3e1538079c29adfb43c6c8", "source_audit_complete": true}

本轮源记录离线复验：6934/6934逐字节一致，失败0，额外API调用0；源文件SHA256保存在analysis/full_source_serializer_verify.json。

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

全池=4062；实际分析目标=4062（full_pool_requested）。预算先行子集不得冒充全量。各臂缺失独立列出；不完整时率/CI仅针对已判定案例。

| 臂 | 已判定 | 目标子集 | 缺失 | C数量/率[Wilson95%] | H数量/率[Wilson95%] | O数量/率[Wilson95%] | ΔC pp[配对95%] | ΔH pp[配对95%] | ΔO pp[配对95%] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | 4062 | 4062 | 0 | 2836 / 69.82% [68.39,71.21] | 1003 / 24.69% [23.39,26.04] | 223 / 5.49% [4.83,6.23] | 0.00 [-0.12,0.12] | 0.00 [-0.12,0.12] | 0.00 [-0.12,0.12] |
| B1 | 4062 | 4062 | 0 | 2688 / 66.17% [64.70,67.61] | 721 / 17.75% [16.61,18.96] | 653 / 16.08% [14.98,17.24] | -3.64 [-5.44,-1.83] | -6.94 [-8.68,-5.19] | 10.59 [8.99,12.16] |
| B2 | 4062 | 4062 | 0 | 2900 / 71.39% [69.98,72.76] | 996 / 24.52% [23.22,25.87] | 166 / 4.09% [3.52,4.74] | 1.58 [-0.15,3.29] | -0.17 [-1.87,1.52] | -1.40 [-2.37,-0.44] |
| A2 | 4062 | 4062 | 0 | 2849 / 70.14% [68.71,71.53] | 906 / 22.30% [21.05,23.61] | 307 / 7.56% [6.78,8.41] | 0.32 [-1.23,1.87] | -2.39 [-3.93,-0.84] | 2.07 [0.90,3.23] |
| A2-nogate | 4062 | 4062 | 0 | 2909 / 71.61% [70.21,72.98] | 863 / 21.25% [20.02,22.53] | 290 / 7.14% [6.39,7.97] | 1.80 [0.06,3.53] | -3.45 [-5.17,-1.71] | 1.65 [0.39,2.90] |
| A2-nosal | 4062 | 4062 | 0 | 2862 / 70.46% [69.04,71.84] | 910 / 22.40% [21.15,23.71] | 290 / 7.14% [6.39,7.97] | 0.64 [-0.91,2.18] | -2.29 [-3.82,-0.76] | 1.65 [0.50,2.79] |
| A2-nolic | 4062 | 4062 | 0 | 2899 / 71.37% [69.96,72.74] | 977 / 24.05% [22.76,25.39] | 186 / 4.58% [3.98,5.27] | 1.55 [0.05,3.05] | -0.64 [-2.12,0.84] | -0.91 [-1.87,0.05] |
| A2-noblock | 4062 | 4062 | 0 | 2853 / 70.24% [68.81,71.62] | 877 / 21.59% [20.35,22.88] | 332 / 8.17% [7.37,9.06] | 0.42 [-1.13,1.97] | -3.10 [-4.62,-1.58] | 2.68 [1.49,3.88] |

CHO比例用Wilson95%；Δ是同ID配对变化，其CI是discordant增/损的97.5% Wilson区间之Bonferroni差，不把有符号差值当二项比例。

### A2 对三种参照的同ID配对变化

| 参照 | 指标 | 配对n | Δ pp | 配对95% CI |
| --- | --- | --- | --- | --- |
| B0 | correct | 4062 | 0.320039 | -1.2317370670258287,1.8710251737001693 |
| B0 | hallucination | 4062 | -2.38799 | -3.928396024563833,-0.8416767713908493 |
| B0 | omission | 4062 | 2.06795 | 0.8994337885398794,3.2313509007404635 |
| B1 | correct | 4062 | 3.96356 | 2.0842105890345284,5.83312673208613 |
| B1 | hallucination | 4062 | 4.55441 | 2.7889502123255148,6.308611305732387 |
| B1 | omission | 4062 | -8.51797 | -10.101462766831565,-6.91343607234699 |
| B2 | correct | 4062 | -1.25554 | -2.8943673828345515,0.38639096434291487 |
| B2 | hallucination | 4062 | -2.21566 | -3.888340532130816,-0.5375002063838376 |
| B2 | omission | 4062 | 3.4712 | 2.3573047216858036,4.576512435320486 |

主表全池包括cal与test；固定hash划分不改变，test未参与τ求解，但α由观察此前风险诊断后的修订案指定，不能称为全新未查看的确认性测试。

| 固定划分 | 参照 | 配对n | A2 ΔC pp | 配对95% CI | McNemar p |
| --- | --- | --- | --- | --- | --- |
| cal | B0 | 2048 | 1.36719 | -0.8238579301703519,3.551541732427421 | 0.0621798 |
| cal | B1 | 2048 | 4.58984 | 1.8878817729278325,7.269342420363756 | 3.29755e-07 |
| cal | B2 | 2048 | -0.683594 | -3.023481261140696,1.6596393600121635 | 0.403389 |
| test | B0 | 2014 | -0.744786 | -2.9453395733341328,1.4594730511380347 | 0.328182 |
| test | B1 | 2014 | 3.32671 | 0.7055969397187223,5.9312735260905285 | 0.000134202 |
| test | B2 | 2014 | -1.83714 | -4.135286752858426,0.47014933144138155 | 0.0166853 |

| 臂 | 参照 | 同ID n | 错→对 | 对→错 | 精确McNemar p |
| --- | --- | --- | --- | --- | --- |
| B0 | B1 | 4062 | 367 | 219 | 1.03303e-09 |
| B0 | B2 | 4062 | 228 | 292 | 0.00568035 |
| B1 | B0 | 4062 | 219 | 367 | 1.03303e-09 |
| B1 | B2 | 4062 | 266 | 478 | 6.79933e-15 |
| B2 | B0 | 4062 | 292 | 228 | 0.00568035 |
| B2 | B1 | 4062 | 478 | 266 | 6.79933e-15 |
| A2 | B0 | 4062 | 214 | 201 | 0.555875 |
| A2 | B1 | 4062 | 399 | 238 | 1.85734e-10 |
| A2 | B2 | 4062 | 209 | 260 | 0.0208567 |
| A2-nogate | B0 | 4062 | 303 | 230 | 0.00179049 |
| A2-nogate | B1 | 4062 | 450 | 229 | 1.6155e-17 |
| A2-nogate | B2 | 4062 | 199 | 190 | 0.685078 |
| A2-nosal | B0 | 4062 | 219 | 193 | 0.218028 |
| A2-nosal | B1 | 4062 | 394 | 220 | 2.09061e-12 |
| A2-nosal | B2 | 4062 | 211 | 249 | 0.084392 |
| A2-nolic | B0 | 4062 | 226 | 163 | 0.00163516 |
| A2-nolic | B1 | 4062 | 436 | 225 | 1.74645e-16 |
| A2-nolic | B2 | 4062 | 221 | 222 | 1 |
| A2-noblock | B0 | 4062 | 216 | 199 | 0.432249 |
| A2-noblock | B1 | 4062 | 383 | 218 | 1.6802e-11 |
| A2-noblock | B2 | 4062 | 222 | 269 | 0.0377905 |

McNemar将C视为成功、H/O视为失败；列出的多项检验p未经多重比较校正，不能只挑显著项。

### B0→各臂转移矩阵（行内比例）

| 臂 | 从 | 到 | 数量 | 行分母 | 行内比例 |
| --- | --- | --- | --- | --- | --- |
| B0 | correct | correct | 2836 | 2836 | 1 |
| B0 | correct | hallucination | 0 | 2836 | 0 |
| B0 | correct | omission | 0 | 2836 | 0 |
| B0 | hallucination | correct | 0 | 1003 | 0 |
| B0 | hallucination | hallucination | 1003 | 1003 | 1 |
| B0 | hallucination | omission | 0 | 1003 | 0 |
| B0 | omission | correct | 0 | 223 | 0 |
| B0 | omission | hallucination | 0 | 223 | 0 |
| B0 | omission | omission | 223 | 223 | 1 |
| B1 | correct | correct | 2469 | 2836 | 0.870592 |
| B1 | correct | hallucination | 123 | 2836 | 0.0433709 |
| B1 | correct | omission | 244 | 2836 | 0.0860367 |
| B1 | hallucination | correct | 182 | 1003 | 0.181456 |
| B1 | hallucination | hallucination | 573 | 1003 | 0.571286 |
| B1 | hallucination | omission | 248 | 1003 | 0.247258 |
| B1 | omission | correct | 37 | 223 | 0.165919 |
| B1 | omission | hallucination | 25 | 223 | 0.112108 |
| B1 | omission | omission | 161 | 223 | 0.721973 |
| B2 | correct | correct | 2608 | 2836 | 0.919605 |
| B2 | correct | hallucination | 205 | 2836 | 0.0722849 |
| B2 | correct | omission | 23 | 2836 | 0.00811001 |
| B2 | hallucination | correct | 226 | 1003 | 0.225324 |
| B2 | hallucination | hallucination | 749 | 1003 | 0.74676 |
| B2 | hallucination | omission | 28 | 1003 | 0.0279163 |
| B2 | omission | correct | 66 | 223 | 0.295964 |
| B2 | omission | hallucination | 42 | 223 | 0.188341 |
| B2 | omission | omission | 115 | 223 | 0.515695 |
| A2 | correct | correct | 2635 | 2836 | 0.929126 |
| A2 | correct | hallucination | 129 | 2836 | 0.0454866 |
| A2 | correct | omission | 72 | 2836 | 0.0253879 |
| A2 | hallucination | correct | 169 | 1003 | 0.168495 |
| A2 | hallucination | hallucination | 746 | 1003 | 0.743769 |
| A2 | hallucination | omission | 88 | 1003 | 0.0877368 |
| A2 | omission | correct | 45 | 223 | 0.201794 |
| A2 | omission | hallucination | 31 | 223 | 0.139013 |
| A2 | omission | omission | 147 | 223 | 0.659193 |
| A2-nogate | correct | correct | 2606 | 2836 | 0.9189 |
| A2-nogate | correct | hallucination | 156 | 2836 | 0.0550071 |
| A2-nogate | correct | omission | 74 | 2836 | 0.0260931 |
| A2-nogate | hallucination | correct | 243 | 1003 | 0.242273 |
| A2-nogate | hallucination | hallucination | 665 | 1003 | 0.663011 |
| A2-nogate | hallucination | omission | 95 | 1003 | 0.0947159 |
| A2-nogate | omission | correct | 60 | 223 | 0.269058 |
| A2-nogate | omission | hallucination | 42 | 223 | 0.188341 |
| A2-nogate | omission | omission | 121 | 223 | 0.542601 |
| A2-nosal | correct | correct | 2643 | 2836 | 0.931946 |
| A2-nosal | correct | hallucination | 127 | 2836 | 0.0447814 |
| A2-nosal | correct | omission | 66 | 2836 | 0.0232722 |
| A2-nosal | hallucination | correct | 171 | 1003 | 0.170489 |
| A2-nosal | hallucination | hallucination | 752 | 1003 | 0.749751 |
| A2-nosal | hallucination | omission | 80 | 1003 | 0.0797607 |
| A2-nosal | omission | correct | 48 | 223 | 0.215247 |
| A2-nosal | omission | hallucination | 31 | 223 | 0.139013 |
| A2-nosal | omission | omission | 144 | 223 | 0.64574 |
| A2-nolic | correct | correct | 2673 | 2836 | 0.942525 |
| A2-nolic | correct | hallucination | 137 | 2836 | 0.0483075 |
| A2-nolic | correct | omission | 26 | 2836 | 0.00916784 |
| A2-nolic | hallucination | correct | 168 | 1003 | 0.167498 |
| A2-nolic | hallucination | hallucination | 802 | 1003 | 0.799601 |
| A2-nolic | hallucination | omission | 33 | 1003 | 0.0329013 |
| A2-nolic | omission | correct | 58 | 223 | 0.26009 |
| A2-nolic | omission | hallucination | 38 | 223 | 0.170404 |
| A2-nolic | omission | omission | 127 | 223 | 0.569507 |
| A2-noblock | correct | correct | 2637 | 2836 | 0.929831 |
| A2-noblock | correct | hallucination | 112 | 2836 | 0.0394922 |
| A2-noblock | correct | omission | 87 | 2836 | 0.030677 |
| A2-noblock | hallucination | correct | 173 | 1003 | 0.172483 |
| A2-noblock | hallucination | hallucination | 736 | 1003 | 0.733799 |
| A2-noblock | hallucination | omission | 94 | 1003 | 0.0937188 |
| A2-noblock | omission | correct | 43 | 223 | 0.192825 |
| A2-noblock | omission | hallucination | 29 | 223 | 0.130045 |
| A2-noblock | omission | omission | 151 | 223 | 0.67713 |

### Do-no-harm 与最坏转移 O→H

| 臂 | B0正确已配对 | C→H | C→O | O→H |
| --- | --- | --- | --- | --- |
| B0 | 2836 | 0 | 0 | 0 |
| B1 | 2836 | 123 | 244 | 25 |
| B2 | 2836 | 205 | 23 | 42 |
| A2 | 2836 | 129 | 72 | 31 |
| A2-nogate | 2836 | 156 | 74 | 42 |
| A2-nosal | 2836 | 127 | 66 | 31 |
| A2-nolic | 2836 | 137 | 26 | 38 |
| A2-noblock | 2836 | 112 | 87 | 29 |

| A2实际分支 | 配对n | B0正确 | A2正确 | C→H | C→O | 错→对 |
| --- | --- | --- | --- | --- | --- | --- |
| gated_noop | 2289 | 1853 | 1842 | 35 | 6 | 30 |
| intervened | 1650 | 911 | 938 | 89 | 64 | 180 |
| safe_bypass | 123 | 72 | 69 | 5 | 2 | 4 |

no-op/bypass保存上下文字节，不保证远端再次生成相同答案。分支表是观测分解；no-op的标签变化属于重放漂移，不能归为准入动作的单独因果效果；干预分支也未随机分配。

### Flip rate 与动作分布

stable_wrong定义：archived wrong AND fresh B0 replay wrong; two observations, not three-repeat stability

| 臂 | 子池 | 配对/预期 | 救回 | flip rate | Wilson95% |
| --- | --- | --- | --- | --- | --- |
| B0 | stable_wrong | 833/833 | 0 | 0 | 0.0, 0.004590426036142666 |
| B0 | B0_wrong | 1226/1226 | 0 | 0 | 2.168404344971009e-19, 0.0031235398621036357 |
| B0 | B0_wrong_strict_supported | 925/925 | 0 | 0 | 0.0, 0.0041357529686190395 |
| B1 | stable_wrong | 833/833 | 87 | 0.104442 | 0.08545715953069588, 0.12705795542466788 |
| B1 | B0_wrong | 1226/1226 | 219 | 0.17863 | 0.1582022893484908, 0.201064716696646 |
| B1 | B0_wrong_strict_supported | 925/925 | 176 | 0.19027 | 0.1662762290781328, 0.21682624276080634 |
| B2 | stable_wrong | 833/833 | 153 | 0.183673 | 0.15885035233376069, 0.21140073352583974 |
| B2 | B0_wrong | 1226/1226 | 292 | 0.238173 | 0.21517007427113974, 0.2628114205016747 |
| B2 | B0_wrong_strict_supported | 925/925 | 255 | 0.275676 | 0.24785134621952284, 0.30535550511234405 |
| A2 | stable_wrong | 833/833 | 111 | 0.133253 | 0.11184972807753008, 0.1580239217521015 |
| A2 | B0_wrong | 1226/1226 | 214 | 0.174551 | 0.15432922377891012, 0.19680665290131727 |
| A2 | B0_wrong_strict_supported | 925/925 | 188 | 0.203243 | 0.17856242548583443, 0.23037868627608107 |
| A2-nogate | stable_wrong | 833/833 | 152 | 0.182473 | 0.15772163054056645, 0.2101395163659395 |
| A2-nogate | B0_wrong | 1226/1226 | 303 | 0.247145 | 0.22381438657321837, 0.27205559280239683 |
| A2-nogate | B0_wrong_strict_supported | 925/925 | 262 | 0.283243 | 0.25514952913478717, 0.3131298621521492 |
| A2-nosal | stable_wrong | 833/833 | 108 | 0.129652 | 0.10852902844940573, 0.15417480452094237 |
| A2-nosal | B0_wrong | 1226/1226 | 219 | 0.17863 | 0.1582022893484908, 0.201064716696646 |
| A2-nosal | B0_wrong_strict_supported | 925/925 | 181 | 0.195676 | 0.17139027222676548, 0.2224782995800805 |
| A2-nolic | stable_wrong | 833/833 | 117 | 0.140456 | 0.1185075297749966, 0.16570575377320199 |
| A2-nolic | B0_wrong | 1226/1226 | 226 | 0.184339 | 0.1636314604177049, 0.2070191267383051 |
| A2-nolic | B0_wrong_strict_supported | 925/925 | 188 | 0.203243 | 0.17856242548583443, 0.23037868627608107 |
| A2-noblock | stable_wrong | 833/833 | 108 | 0.129652 | 0.10852902844940573, 0.15417480452094237 |
| A2-noblock | B0_wrong | 1226/1226 | 216 | 0.176183 | 0.15587794984024447, 0.19851037858594664 |
| A2-noblock | B0_wrong_strict_supported | 925/925 | 183 | 0.197838 | 0.17343799304256372, 0.224737018751445 |

| 臂 | VOUCH | KEEP | DEMOTE | QUALIFY | REFUTE | BLOCK | no-op率 | BLOCK占比均值/范围 | 代理时序裁决 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | None / [None,None] | 0 |
| B1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | None / [None,None] | 0 |
| B2 | 14034 | 0 | 0 | 0 | 4198 | 28415 | 0.0992122 | 0.6131107178559173 / [0.0,1.0] | 0 |
| A2 | 130 | 5055 | 19 | 7598 | 1010 | 6753 | 0.593796 | 0.14634168760830504 / [0.0,1.0] | 24 |
| A2-nogate | 1852 | 10310 | 91 | 12561 | 4426 | 17407 | 0.0475135 | 0.3808200614145961 / [0.0,1.0] | 124 |
| A2-nosal | 130 | 5055 | 19 | 7598 | 1010 | 6753 | 0.593796 | 0.14634168760830504 / [0.0,1.0] | 24 |
| A2-nolic | 130 | 5055 | 19 | 7598 | 1010 | 6753 | 0.593796 | 0.14634168760830504 / [0.0,1.0] | 24 |
| A2-noblock | 130 | 5055 | 6772 | 7598 | 1010 | 0 | 0.563516 | 0.0 / [0.0,0.0] | 24 |

实际no-op率包含空证据/估计失败等安全bypass；校准coverage只按risk≤τ计数，两者不能直接等同。no-op也不等于答对，且其生成仍可能有重放波动。

## 3. 错误分解协议

规范矛盾：§10.3的‘准入/使用失败’和‘生成失败’重叠，且四类不覆盖baseline正确样本，因此四个原始谓词不能诚实加总为100%。分别输出原始谓词与明确互斥层级＋正确/未知残余。

请求范围为memos全池4062条；A2只在实际子集有观测，未运行部分保持unknown。

| 原始谓词 | 命中 | 未知 | 占全池 |
| --- | --- | --- | --- |
| retrieval_failure | 0 | 555 | 0 |
| serialization_loss | 221 | 555 | 0.0544067 |
| admission_usage_failure | 781 | 555 | 0.19227 |
| generation_failure | 782 | 555 | 0.192516 |

| 互斥层级/残余 | 数量 | 占全池 |
| --- | --- | --- |
| generation_failure_after_A2 | 636 | 0.156573 |
| baseline_correct_residual | 2836 | 0.698178 |
| serialization_loss | 144 | 0.0354505 |
| unresolved_or_missing_evidence | 301 | 0.0741014 |
| admission_usage_failure_recovered_by_A2 | 145 | 0.0356967 |

原始多谓词重叠636条；互斥合计4062。可见性语义：At least one strict gold-memory position is visible, matching the existing visibility audit; not proof of complete answer sufficiency. Partial-only rows without strict positions remain unknown.

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

修订案可选ORACLE_REL400未执行：冻结核心将该臂标为历史参考，且当前只有两类粗代理目标，缺少六类真实关系神谕标签；不能用粗代理冒充真实oracle或改变冻结核心来补分数。此项不影响必做主线与阶段E。

| 历史→当前 | 同输入ID n | 历史flip | 当前flip | 描述性损耗pp |
| --- | --- | --- | --- | --- |
| A3→B2 | 499 | 0.378758 | 0.180361 | 19.8397 |
| A3→A2 | 499 | 0.378758 | 0.132265 | 24.6493 |
| UA3→B2 | 616 | 0.480519 | 0.219156 | 26.1364 |
| UA3→A2 | 616 | 0.480519 | 0.160714 | 31.9805 |

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
| A2-nogate | correct | 4062 | 1.79714 | 0.05586295209106945,3.53398564692637 |
| A2-nogate | hallucination | 4062 | -3.44658 | -5.173299428234371,-1.7113417205661994 |
| A2-nogate | omission | 4062 | 1.64943 | 0.3902662890243994,2.904526260758731 |
| A2-nosal | correct | 4062 | 0.640079 | -0.9061728753217125,2.184749088670391 |
| A2-nosal | hallucination | 4062 | -2.28951 | -3.8166010412123814,-0.7567677219194262 |
| A2-nosal | omission | 4062 | 1.64943 | 0.5016738160538985,2.7931187337292327 |
| A2-nolic | correct | 4062 | 1.55096 | 0.049429889523491116,3.048658627436766 |
| A2-nolic | hallucination | 4062 | -0.640079 | -2.1194031650048366,0.8408269516561595 |
| A2-nolic | omission | 4062 | -0.910881 | -1.871630792479872,0.05211848886829233 |
| A2-noblock | correct | 4062 | 0.418513 | -1.1332365718272939,1.9692287113245055 |
| A2-noblock | hallucination | 4062 | -3.10192 | -4.616624501501463,-1.5795525324190527 |
| A2-noblock | omission | 4062 | 2.68341 | 1.4851500844867866,3.8750348099365164 |

## 7. λ_O 敏感性

| 配置 | 指标 | 实际配对n | Δ pp |
| --- | --- | --- | --- |
| A2 | hallucination | 400 | -4.5 |
| A2 | omission | 400 | 4.25 |
| A2__lambda_o_0.3 | hallucination | 400 | -3.75 |
| A2__lambda_o_0.3 | omission | 400 | 2.75 |
| A2__lambda_o_0.6 | hallucination | 400 | -3.5 |
| A2__lambda_o_0.6 | omission | 400 | 3.75 |
| A2__lambda_o_2 | hallucination | 400 | -5.5 |
| A2__lambda_o_2 | omission | 400 | 4.75 |

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

修订案阶段E无论LongMemEval是否可得都必做；三个历史错题池不能评价baseline-correct安全性或noop_err。

不得把oracle retrieval reading failure说成首次发现；LME更新题允许包含旧信息，正确拒答算C不算O；数据修订/文件hash与recall@20见pool/config实测。

## 11. 意外发现与失败案例

案例是目的性诊断展示：优先两条回归、两条救回、一条仍未修复；类内先列license关联候选，再按case_id。类别不足时补齐，不代表总体频率或因果效应。

| case_id | 问题 | B0→A2 | 实际回答B0 / A2 | 动作与诊断 | nolic正确关联 |
| --- | --- | --- | --- | --- | --- |
| memos_long:1007 | Did Donna remove her dislike for processed snacks due to a focus on taste rather than sustainability on Mar 09, 2037? | correct→omission | No; she focused on sustainability and health. / Existing memories do not confirm this; they only mention sustainability and health, not taste or removing a dislike for processed snacks. | {'BLOCK': 10, 'QUALIFY': 2}  | True |
| memos_long:1004 | What type of documentaries did Donna decide to focus on after the sustainability summit on September 29, 2036? | hallucination→correct | Films offering practical environmental solutions. / Sustainability-related documentaries. | {} risk_gate_noop | False |
| memos_long:1226 | Did Taylor David plan to avoid spontaneous trips due to their lack of benefits? | correct→omission | No. Taylor found a spontaneous trip unexpectedly relaxing and inspiring shortly before March 1, 2042, shifting their perspective positively. / No; recent trip was relaxing and inspiring. | {'REFUTE': 1, 'QUALIFY': 3, 'BLOCK': 3}  | True |
| memos_long:1015 | Did Donna establish EcoStrategic Consulting before March 01, 2038? | hallucination→correct | Yes, on July 1, 2038. / No, she established it on July 1, 2038. | {} risk_gate_noop | False |
| memos_long:1149 | What type of movies does Taylor prefer as of Dec 17, 2033? | hallucination→hallucination | Psychological thrillers. / Psychological thrillers. | {'BLOCK': 2, 'QUALIFY': 10}  | True |

A2错而nolic对仅是license关联回归候选，不足以证明单独license因果；模板授权可能放大错误后验，代理写入时间也可能误当事件时间。

## 12. 结论与下一步

Stage1/2真实实现后，A2相对B1在4062个同ID案例的ΔC=3.964pp，精确McNemar p=1.85734e-10。

同一对照下ΔH=+4.554pp、ΔO=-8.518pp；正确率提升与H/O权衡须一起解释，不能只报C。

A2相对真实B2的ΔC=-1.256pp（未校正McNemar p=0.0208567）；相对B1为正不等于优于B2或全面有效。

不是标签拟合的证据应来自物理隔离输入、真实Stage1/2、强B1/真实B2对照与同ID结果；历史神谕分数不构成当前方法收益。短板及下一步以实际错误与缺失分析为准。

主α=0.20由修订案在观察round_0074结果后指定；阈值仍只在cal求解，但这不是新的、未查看的独立确认性test。cal/test接近仅作观测，不据此证明无过拟合。

完善阶段清单（本轮不执行）：1.结构化二阶风险分数增强；2.记忆正文事件时间来源增强；3.100–200条真实关系人工标注；4.补入no_gold_retrieved测量完整检索失败；5.获得其他家族端点后跨生成器。

## 13. 阻断、规范矛盾与未完成项

- LongMemEval修订案限次获取尚未完成；最多累计3种策略，随后不再重试。阶段E本轮必做。

- 必做阶段E mem0全池B1/A2尚未完整生成判定。

- 必做阶段E memobase全池B1/A2尚未完整生成判定。

- 必做阶段E supermemory全池B1/A2尚未完整生成判定。

- 已知非阻断发现：memos为100%写入代理时间、risk分辨率有限、粗代理目标不完整、池范围差异、部分α退化。比例下降已由修订案废除为断言；原公式与完整诊断保留，完善项本轮不执行。其他系统的现有text_cue触发情况见能力探针，不等于本轮新增时间增强。
