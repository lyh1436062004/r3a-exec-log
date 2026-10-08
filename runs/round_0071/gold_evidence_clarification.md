# LongMemEval 的 gold memory / gold evidence

日期：2026-10-08。范围：前一轮建议的原始 LongMemEval / cleaned 数据，不将结论自动套用到 LongMemEval-V2。

结论：有 gold 证据位置标注和 oracle 证据会话数据；更准确称为 gold evidence，而不是预先替所有记忆后端生成的一条统一 gold memory 文本。

| 官方字段 / 文件 | 含义 |
|---|---|
| `answer_session_ids` | 支撑该题答案的证据会话 ID，用于会话级召回评估 |
| 对话轮次上的 `has_answer: true` | 该轮含所需证据，用于轮次级召回评估 |
| `longmemeval_oracle.json` | 只保留证据会话的诊断数据；保留的是会话而不是仅答案句 |
| `answer` | gold answer，不是 memory |

30个 abstention 问题没有通常意义上的答案证据位置，官方检索评估排除它们。不能强行给不可回答题配一条含正确答案的 gold memory；历史中的纠错线索与答案位置不是同一概念。

这对实验7的用途是：可以构造 gold-session 和 gold-turn 诊断，并检查检索是否包含标注证据、实际上下文是否保留了相关内容。会话 ID 命中不是文本充分性的证明，仍需审查呈现内容。

如 MemOS/Mem0 对源对话进行了抽取、合并或摘要，其内部 memory IDs 不自动等同于上述 session IDs。要评价后端生成记忆的 gold 命中，需要源会话/轮次 provenance 映射与内容充分性审查，不能只比 ID。

正式推理时不得把 `answer`、`has_answer`、`answer_session_ids` 交给 controller 或回答模型。gold 仅用于事后评估或明确标识的 oracle 诊断，不能把 oracle 得分当作真实检索方法收益。

本轮只核对文档，没有下载或解析完整数据，没有运行实验，也没有修改记忆库、检索器或项目代码。

依据：[作者仓库 Dataset Format](https://github.com/xiaowu0162/LongMemEval#-dataset-format)、[Memory Retrieval](https://github.com/xiaowu0162/LongMemEval#memory-retrieval)。本轮读取了[原始 README](https://raw.githubusercontent.com/xiaowu0162/LongMemEval/main/README.md)中的对应说明。documentation-lookup 所依赖的 Context7 工具当前未配置，改为直接查阅作者一手文档。
