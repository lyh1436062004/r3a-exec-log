# A2 MVP 结果报告

日期：2026-10-09。全池Stage1、B0生成与判分完成；第10项真实不变量失败，停止在四臂冒烟之前。任务未完成，没有A2收益结论。

## 0. 环境与配置

- Python：D:/conda_envs/o1/python.exe。唯一实际端点为OPENAI_API_KEY / OPENAI_BASE_URL，https://api.deepseek.com；生成器、估计器与judge均为deepseek-chat，temperature=0，并发≤12。凭据不输出、不上传。
- 实测依赖：openai 2.37.0、dotenv可用、numpy 2.3.5、pandas 3.0.1、scipy 1.17.1、requests 2.32.5、sklearn 1.8.0、datasets 4.7.0。缺rank_bm25、hypothesis；没有安装新包，采用纯Python检索与普通断言。
- 15个指定文件已实现。本轮仅增强21/22/23运行器与测试的恢复、预检、用量记录；七个核心控制器文件与round_0073哈希一致。00–15、旧common、memory store、memos retriever均未改。
- 配置：outputs/a2_mvp_v1/run_config.json；项目Git基线e04380ab7e201f4073fff3adc9451c5c83478719；新增源码身份以SHA256及round_0074快照为准。
- 复用2832条成功估计、3000条成功B0。907条失败估计已逐字节备份；新增1230条估计、1062条B0、4062条judge全部成功。当前三项均4062条，无缺失或失败回退。
- 本次新增已记录tokens：估计3,534,335；生成834,225；judge 828,969；合计5,197,529。累计：支持审查6,516,011、估计11,550,662、生成3,234,776、judge 828,969，共22,130,418。仅为已持久化返回用量，不是账单；中断时未落盘用量未知。
- 历史账户阻断已解除；所有付费进程已结束。证据：api_run_blocker.json、analysis/resume_cache_audit.json、analysis/resume_execution_summary.json。

## 0.5 池定义与等价性校验

按strict_supported / partial_supported、非空gold evidence、serializer_ok建池，不按baseline对错筛选。来源6934条，排除空证据1656、无检回支持1216；新池4062条：strict 3507、partial 555。

归档baseline为C2933/H988/O141；fresh B0为C2836/H1003/O223，即正确2836、错误1226。新错题集合不等于原1987条：原集合1154条未进入新错题集合，新错题新增393条，对称差1547条，数量净差761。来源范围及重放生成/判定可能造成差异，未全部归因于单一因素。第11项已执行，按§13记录为非阻断豁免，而非“等价通过”。

原6934条序列化字节一致；旧1987条校验亦通过，pref_note 1986、visible_supported 763、serialization_loss 133仅为旧池统计。新池4062条B0上下文与冻结context_str_full字节一致、无标注。

新池SHA256：d7cee7d676670a3d37e82b9dd82118cc1176a86ccb3e1538079c29adfb43c6c8。真实记忆46647条；memory_key有值率与entity_anchors非空率均52.0076%；大小≥2的组5064个。time_source全部meta_ingest，time_is_proxy=True占100%，不能把写入代理当作已验证的事件时间。

## 1. 阶段 A 冒烟结果（150条）

尚未运行四臂真实冒烟。19项离线检查通过；全池哈希、固定模板泄漏（0命中）、真实分组通过。第10项实测失败，6处noop_err下降；第11项完成但因不等价按§13豁免；pending=0，full_pool_verified=false。未声称测试全绿，未绕过验收进入干预实验。

## 2. memos 主实验（新池全部）

仅B0完成，95% Wilson区间如下：

| 判定 | 条数/4062 | 比例 | 95%区间 |
|---|---:|---:|---:|
| C | 2836 | 69.8178% | 68.3880%–71.2102% |
| H | 1003 | 24.6923% | 23.3905%–26.0419% |
| O | 223 | 5.4899% | 4.8305%–6.2334% |

B1/B2/A2与四个消融臂未取得成绩；ΔC/ΔH/ΔO、McNemar、转移矩阵、O→H、do-no-harm、flip、动作与BLOCK分布不可计算。未执行不填0。全阶段预估69054次调用，须先固定400条并报告，再分阶段完成全4062条；400条不替代完整目标。

## 3. 错误分解协议

事后原始谓词：严格gold序列化丢失221条；gold可见且B0错781条。partial定位555条未知；检索支持池内未观测严格检索失败，不代表全数据无检索问题；没有A2结果，生成失败分解未完成。

四原谓词可能重叠且不覆盖baseline正确样本，不能原样合计100%。显式互斥层级为：baseline正确残余2836、序列化丢失144、未知或证据未齐1082，合计4062。这不是已完成的四类错误归因。逐条记录见analysis/memos__deepseek-chat_decomposition_cases.csv。

## 4. oracle–learned 归因分解

A3=46.13%、UA3=53.29%仅作历史参考，不与当前新池混算收益；未重跑ORACLE_REL。历史UA3不是“神谕关系＋真实Stage2”的成绩。B2/A2真实flip及逐阶段损耗仍未取得。

## 5. 校准

保持原公式与case_id SHA256前8位mod2划分：cal 2048、test 2014。原算法实测：

| α | τ | cal coverage | cal noop_err | test coverage | test noop_err | 退化 |
|---|---:|---:|---:|---:|---:|---|
| 0.05 | -∞ | 0% | 0%* | 0% | 0%* | 是 |
| 0.10 | -∞ | 0% | 0%* | 0% | 0%* | 是 |
| 0.20 | 0.15 | 56.2500% | 19.0972% | 56.4548% | 18.9974% | 否 |
| 0.30 | 0.80 | 98.5840% | 29.6682% | 98.2622% | 30.0657% | 否 |

*空no-op集合按指定max(1,n)公式记0，不代表观测到零风险。

**主设定α=0.10：门控退化为全程干预，τ=-∞、degenerate_flag=true。** 没有调高α绕过失败。α=0.30的test错误率超过30%，不能宣称严格有限样本保证。

第10项首个真实反例：τ=0时no-op 22条、错9条，错误率40.9091%；τ=0.05时155条、错16条，降至10.3226%。新增133条中仅7条错，累计比例因此下降。经验累计比例没有普遍单调保证。未平滑、改公式、改risk或放宽断言。完整曲线、6处下降与原阈值见analysis/invariant_10_actual_noop_curve.json、analysis/memos_calibration_monotonicity.json、calibration/memos.json。

## 6. 消融

A2-nogate / A2-nosal / A2-nolic / A2-noblock未执行真实生成判分，ΔC/ΔH/ΔO未取得。

## 7. λ_O 敏感性

0.3 / 0.6 / 1.0 / 2.0四档同400条实验未执行，ΔH/ΔO未取得。

## 8. 估计器内在评估

4062条当前输入哈希匹配的成功估计；10849个事后粗代理位置，accuracy=48.5667%、六类macro-F1=0.132987。代理目标仅SUPPORT 8720、SUPERSEDED 2129；gold统一映射SUPPORT但真实可能REFUTE/CURRENT，部分题型仅提供粗提示。四个目标类没有独立标注，不能称为六类真实关系准确率。混淆矩阵与逐条记录已保存。

risk对fresh B0错误的AUC=0.688526（4062条、错误1226）。risk均值：B0正确0.185705、错误0.270954。与同输入、历史错且fresh B0也错的UA3记录精确配对616条，历史修复296条；sufficiency与修复的点二列相关r=0.062156。这些是事后关联，不证明A2收益或因果效果。

## 9. 跨生成器（或跨记忆系统）

仅1个实际端点，阶段D跳过。阶段E离线池：mem0 4476、memobase 4940、supermemory 184；仅历史baseline错题。B1/A2未运行；后续只能在这些池报告flip，不能报告有效noop_err或do-no-harm。

## 10. LongMemEval（或阻断＋阶段E）

单次Hugging Face元数据访问ConnectTimeout；未反复下载，按任务书转必需阶段E，E未完成。适配与纯Python TF-IDF/top_k=20离线验证通过，但未取得真实数据版本/hash，不称实际benchmark验证完成。

LongMemEval提供answer_session_ids、has_answer及标准answer，oracle文件仅保留证据会话；这是gold evidence，不是MemOS等后端生成的gold memory对象ID。官方检索评估排除30条拒答题。定位仅用于oracle/事后评估，不进入部署输入。来源：[官方数据格式](https://github.com/xiaowu0162/LongMemEval#-dataset-format)、[官方检索说明](https://github.com/xiaowu0162/LongMemEval#memory-retrieval)。

## 11. 意外发现与失败案例

未运行A2，至少5条真实A2案例交付未满足，不用Stage1或B0例子冒充。已确认负结果：全部时间为写入代理；noop_err有6处下降；α=0.10无可行正覆盖阈值；fresh B0错题集合不同；LongMemEval单次下载失败。

## 12. 结论与下一步

已完成真实估计、全池baseline与判分，尚无A2相对强B1收益数字，不能宣布有效、泛化或完整交付。物理隔离输入、核心哈希不变与无泄漏检查支撑实现边界，不代替效果证据。

先由用户明确处理第10项冲突；获得合规方向后才恢复150四臂验收、400先行/全池八臂、敏感性、必需阶段E和真实A2案例。冻结集合、代价矩阵、固定模板、主α及划分均未更改。

## 13. 阻断与未完成项

当前不是额度阻断。第10项“经验noop_err逐点单调不减”与原公式及真实数据冲突，测试以exit=1失败，不能靠合规代码修复保证不存在下降；需要用户修订规范或给出其他处置。详见analysis/invariant_10_spec_conflict.md。

按§13，池不等价和门控退化本身不是阻断；第10项尚无豁免。全部付费进程结束，未越过验收、未改测试、未标记目标complete。仍缺150四臂、干预主实验、消融、敏感性、阶段E与5条A2案例。
