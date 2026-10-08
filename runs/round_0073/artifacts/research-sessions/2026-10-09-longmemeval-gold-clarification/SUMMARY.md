# LongMemEval gold memory 字段核验

日期：2026-10-09。范围：原 LongMemEval / cleaned，不讨论 V2。状态：核验完成。

## 结论

有标准证据定位，但没有预先规定的 Mem0 / MemOS 生成记忆对象 gold ID。

- answer_session_ids：标准证据所在会话，支持会话级检索召回评估。
- haystack_sessions 中 has_answer=true：包含所需证据的对话轮次，支持轮次级召回评估。
- answer：标准答案，不等于标准记忆。
- longmemeval_oracle.json：历史只保留证据会话，不是标准后端memory对象。
- 30条拒答题没有标准答案位置，官方检索评估排除它们；不能对全部500条统一假定存在可召回gold证据。

来源：[官方数据格式](https://github.com/xiaowu0162/LongMemEval#-dataset-format)、[官方检索与拒答边界](https://github.com/xiaowu0162/LongMemEval#memory-retrieval)。

## 对 A2 的边界

以会话/轮次作为检索单位时可以直接映射证据定位；若后端将它们压缩为新memory，原始标注不自动证明该memory充分支持答案，需要保留来源映射并做独立支持审查。这是由字段粒度推得的方法论边界，不是官方提供了后端memory标注。

answer_session_ids、has_answer、answer及题型/拒答ID提示只用于oracle或事后评估，不进入部署决策。

## 核验方法与文件

研究核验流程仅用于这个单一字段问题：直接读取官方仓库数据模式与检索说明，没有展开论文筛选或引用遍历，没有下载数据或调用付费API。

papers-reviewed.json、relevant-papers.json为空，表示此次没有全文论文筛选；citation-graph.json记录所核验的官方文档来源。
