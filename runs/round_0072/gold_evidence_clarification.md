# LongMemEval 是否提供 gold memory

核验日期：2026-10-09。范围：原版 LongMemEval 及官方 cleaned 发布；不混用 LongMemEval-V2。

结论：提供 gold evidence 标注，但不是任何记忆后端加工之后的 gold_memory_id。

| 字段或文件 | 含义 |
| --- | --- |
| answer_session_ids | 标准证据所在的会话 ID，用于会话级检索评估 |
| haystack_sessions 内的 has_answer: true | 包含所需证据的具体消息，用于消息级检索评估 |
| answer | 标准答案，不等同于证据条目 |
| longmemeval_oracle.json | 仅提供证据会话的 oracle retrieval 数据 |

应用边界：
- 可以离线核验检索是否命中标准证据。
- 会话命中不保证实际选出的消息或压缩记忆保留了答案信息，须检查消息标注和内容映射。
- 如果后端改写、合并或摘要原始消息，应保留来源对应关系；官方不提供后端加工条目的标准 ID。
- 官方说明 30 条 abstention 问题没有标准答案位置，并从检索评估中排除；不能一概判作检索失败。
- 对 A2，gold 标注只用于事后评估或明确标注的 oracle 对照，不能作为部署时的控制器输入。

证据来源：
- [作者官方 README：数据格式](https://github.com/xiaowu0162/LongMemEval#-dataset-format)
- [作者官方 README：检索评估](https://github.com/xiaowu0162/LongMemEval#memory-retrieval)

方法：按研究问题核验流程读取作者官方数据格式及检索评估说明。该问题是数据字段核验，不涉及大规模文献综述，未进行 PubMed 检索、引文扩展或实验调用。所有结论来自上述官方说明；对 A2 的使用边界是本项目的评估建议。

本轮仅新增核验记录，不修改实验代码、不运行模型 API、不下载数据集。正在进行的 A2 MVP 实现不属于本轮提交范围。
