# A2 MVP 结果报告

状态：部分实现与验证完成，真实实验因外部账户余额不足而中断；任务未完成。日期：2026-10-09。
本文只报告已落盘的真实证据；API错误、未执行和安全回退不计作实验成绩。

## 0. 环境与配置

- Python：D:/conda_envs/o1/python.exe；凭据从 github/HaluMem/eval/.env 读取，未输出或上传凭据。
- 仅一个实际端点：OPENAI_API_KEY / OPENAI_BASE_URL，https://api.deepseek.com；真实已调用模型 deepseek-chat，temperature=0。尚未执行本轮 judge。
- 实测依赖：openai 2.37.0、dotenv 可用、numpy 2.3.5、pandas 3.0.1、scipy 1.17.1、requests 2.32.5、sklearn 1.8.0、datasets 4.7.0；缺 rank_bm25、hypothesis。没有安装新包，使用纯 Python 检索回退与普通断言。
- 15个任务指定的新文件已实现；00–15与旧 common 未改，未修改 memory store 或 memos retriever。脚本身份见 run_config.json 和本轮源文件快照。
- 原序列化校验通过：1987/1987字节一致；pref_note 1986；旧错题池 visible_supported 763、serialization_loss 133。这些是旧池结果，不冒充新池比例。
- 本轮停止时：Stage1缓存3739条，成功2832、失败安全回退907、未缓存323；B0生成记录3932条，成功3000、失败932、未记录130。两项专属进程已停止，缓存保留。
- 已记录tokens：支持审查6,516,011；Stage1 8,016,327；B0生成2,400,551；合计16,932,889。仅指已返回并持久化的用量，可能不含中断时尚未落盘的调用，不是账户账单。
- 证据：preflight.json、run_config.json、api_run_blocker.json、analysis/invariants_offline.json、analysis/invariants_full.json。

## 0.5 池定义与等价性校验

池按 strict_supported / partial_supported、非空 gold evidence、serializer_ok 构建，不以 baseline 对错筛选。

- 原始来源6934条；排除空证据1656、无检回支持1216；新池4062条：strict_supported 3507，partial_supported 555。
- 归档baseline分层：C2933、H988、O141。这不是本轮 fresh B0 判分，不能用于证明重放等价性或当前收益。
- 补充3291条实际支持审查，全部取得结果；原始6934条序列化逐字节一致。
- 归档口径下新池错题1129，与旧1987差858；这里只是建池差异。本轮B0尚无成功judge，fresh B0 correct/wrong数量及最终集合差异均未取得，不填写0或声称已验证。
- 新池SHA256：d7cee7d676670a3d37e82b9dd82118cc1176a86ccb3e1538079c29adfb43c6c8。
- 真实记忆46647条；memory_key有值率与entity_anchors非空率均52.0076%；组大小≥2的组5064个。分组大小：1/28202，2/2216，3/1279，4/790，5/477，6/302。
- time_source：meta_ingest 46647；time_is_proxy=True占100%。没有观测到真实event_time，不能把写入时间当作已验证的事件时间。
- 4062条B0 context已逐条验证与context_str_full相同、no_op=True且无标注，但生成/判分未完整。

## 1. 阶段 A 冒烟结果（150条）

尚未执行四臂真实冒烟；B1/B2/A2均无本轮成绩。不得越过验收进入干预主实验。

17项离线合成/核心检查通过。全池哈希、全部固定模板泄漏检查（0命中）与真实分组非退化通过；真实门控单调性与fresh B0集合等价性因缺少完整B0判分而pending。完整测试不是全绿，不能用离线通过冒充完整验收。

生成与评判运行器的模拟联测通过：temperature=0、重复运行零新增调用、输入变化缓存失效、旧阈值缓存隔离、错误不伪装O；这不是真实四臂实验结果。

## 2. memos 主实验（新池全部）

4062条、八臂目标未完成。各臂C/H/O、Wilson区间、ΔC/ΔH/ΔO、McNemar、转移矩阵、O→H、do-no-harm、flip、A2动作/no-op/BLOCK统计均未取得；不以“零例”代替“未观测”。

完整主阶段预计69054次调用，超过30000，后续必须先固定400条并报告，再分阶段推进全量；400条不能替代完整目标。

## 3. 错误分解协议

仅有局部事后可见性观测：221条严格gold序列化丢失；其余因partial定位或fresh B0/A2判分缺失而未完成归因。

规范原始四谓词并非互斥：“准入/使用失败”与“生成失败”可能重叠，且不覆盖baseline正确样本。分析器同时保存原始谓词与显式互斥层级、正确/未知残余；不伪造四段原谓词合计100%。逐条证据见analysis/memos__deepseek-chat_decomposition_cases.csv。

## 4. oracle–learned 归因分解

A3=46.13%、UA3=53.29%仅为历史参考，不能与当前未判分的新池混用。

B2与A2真实flip未取得。未重跑ORACLE_REL；已有UA3使用神谕hard map，不能冒充“神谕关系＋真实Stage2”的分数。只有同输入、同ID且分母一致时才能计算描述性差值；目前未取得这样的本轮判分配对。

## 5. 校准

划分与经验风险公式已严格实现：case_id SHA256前8位mod2，cal求阈值，test仅评估。尚未使用完整fresh B0标签校准；τ、coverage、noop_err、degenerate_flag以及四档α曲线均未取得。

按指定公式计算的经验noop_err并不数学保证随τ单调不减；合成反例检查已验证严格测试能发现下降。没有平滑曲线、改公式或放宽断言；真实第10项仍pending。若后续真实数据不通过，须报告规范冲突，不能伪造全绿，也不能宣称未经证明的严格conformal有限样本保证。

## 6. 消融

A2-nogate / A2-nosal / A2-nolic / A2-noblock均未执行真实生成判分。ΔC/ΔH/ΔO未取得。

## 7. λ_O 敏感性

0.3 / 0.6 / 1.0 / 2.0四档同400条敏感性实验未执行；不能推测ΔH/ΔO。

## 8. 估计器内在评估

仅分析现存缓存，不调用API。成功估计2832条；907条失败回退不计关系质量；323条缺失。

事后粗代理有7500个可归类位置：代理accuracy=47.9733%，六类macro-F1=0.133990。必须限定解释：gold位置按任务约定全部映射SUPPORT，但真实gold可能REFUTE/CURRENT；非gold仅由部分题型提示给出粗目标，其余跳过。这不是六类独立人工标注准确率，不能据此宣布真实关系判断质量。

混淆矩阵与逐条代理见analysis/memos__deepseek-chat_intrinsic_confusion.csv及_intrinsic_relation_cases.csv。sufficiency与真实oracle修复相关性、risk的fresh B0 AUC均因缺少本轮判分配对而未取得。

## 9. 跨生成器（或跨记忆系统）

仅1个端点，阶段D按任务书跳过，不虚构其他生成器。

阶段E目标池已离线构建：mem0 4476、memobase 4940、supermemory 184；仅历史baseline错题。B1/A2真实运行尚未执行；后续只能报flip，不能在这些错题池声称测得do-no-harm或有效noop_err。

## 10. LongMemEval（或阻断＋阶段E）

仅尝试一次xiaowu0162/longmemeval-cleaned元数据访问，Hugging Face ConnectTimeout；没有重复下载、没有检索或实验成绩。按照任务书转阶段E，E仍为必需且未完成。证据：longmemeval_blocker.json。

适配与纯Python TF-IDF / top_k=20代码已实现并离线验证，但没有取得真实数据修订与文件hash，不能称实际LongMemEval验证已完成。

本次用户问题核验：原LongMemEval/cleaned提供answer_session_ids（证据会话）、轮次has_answer（证据位置）与answer（标准答案），另有仅保留证据会话的longmemeval_oracle.json；不是Mem0/MemOS生成记忆对象的标准ID。拒答题无标准答案位置，官方检索评估排除30条拒答题。依据：[官方数据格式](https://github.com/xiaowu0162/LongMemEval#-dataset-format)、[官方检索说明](https://github.com/xiaowu0162/LongMemEval#memory-retrieval)。

这些gold定位只用于oracle和事后审查，不进入A2部署输入。更新题/拒答题遵循官方规则；不得把原论文已讨论的oracle reading failure说成首次发现。

## 11. 意外发现与失败案例

尚无本轮A2生成判分，未取得5条真实A2成功/失败案例。不能将Stage1安全默认或API错误包装成A2效果案例。

已观测的负面事实：全部时间来自写入代理；907条估计失败安全回退；932条B0生成错误；单次LongMemEval下载失败。余额不足是外部执行阻断，不等同于模型幻觉性能下降。

## 12. 结论与下一步

四阶段可运行实现及离线验证完成，但真实实验与交付验收未完成。尚无A2相对强B1收益数字，不能宣布有效、泛化或完整交付。

继续的前提：用户恢复当前DeepSeek账户额度；之后复用成功缓存，显式重试失败估计，补齐fresh B0与judge、完整校准和真实不变量；门槛通过后依序执行150冒烟、400先行/全池主实验及阶段E。不要更改冻结集合、代价矩阵、固定模板、划分或验收断言。

## 13. 阻断与未完成项

官方GET /user/balance返回HTTP200、is_available=false，表示余额不足以调用API（[官方字段定义](https://api-docs.deepseek.com/api/get-user-balance/)）。已停止经身份验证的两项实验进程，磁盘产物保留，没有充值或切换凭据。证据：api_run_blocker.json。

仍缺：完整fresh B0判分与等价性；完整Stage1；真实单调性/校准；150四臂验收；八臂全池与敏感性；阶段E；5条A2案例。失败不得记作C/H/O，未完成不填0，不以旧oracle分数补位。

本报告为阶段性检查点，持久目标未标记complete。
