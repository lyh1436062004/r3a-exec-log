# Codex 任务书:A2 MVP 端到端实现(Stage 0–3 全部真实实现)

> **给 Codex 的执行指令。请从头读到尾再动手。**
> 本文档替代此前所有关于本任务的对话记忆。若你之前在建的是
> "Router + R3a/R3b/R3c 三模块" 架构——**那个方案已作废,立即停止**,
> 按下文重建。本文档优先级高于你自己的判断,遇到不确定处选"更简单、
> 更可复现"的那条,不要自创架构。

---

## 0. 一句话目标

把 A2「检索后记忆准入控制器」按四阶段流水线**全部实现为可运行代码**,
其中 **Stage 1(估计)与 Stage 2(决策)必须是真实的、不接触任何 benchmark 标签的实现**
(此前它们一直是被神谕化的脚手架,这是本任务要解决的核心问题),
然后用 **memos** 与 **LongMemEval** 两个数据集各跑一遍,产出带统计量的结果报告。

完成后你需要返回一个 `RESULTS.md`(格式见 §12)。

**这是一次 MVP 交付:先跑通、再精修。** 任何"锦上添花"的设计
(新 license 类型、新渲染样式、更花哨的估计器)**一律不做**,
遇到取舍时砍功能、保可跑通。

---

## 1. 硬约束(违反即任务失败)

### 1.0 环境预检(第一步就做,结果写进 RESULTS.md 第 0 节)

**不要假设环境如你所想。先跑预检,再写任何代码。**

1. **API key 与端点的真实位置**:key 在 **`github/HaluMem/eval/.env`**,不在 `ENV/`。
   `ENV/` 目录**只有两份文档**(`ENV说明.txt`、`environment.txt`),没有任何 key。
   直接复用 `e1_memos_oracle_common.make_client()`(它已正确处理此路径)。
2. **打印实际可用的 LLM 端点清单**(只打印变量名与 base_url,**绝不打印 key 值**)。
   当前预期只有**一个** LLM 端点(`OPENAI_API_KEY` + `OPENAI_BASE_URL`)。
   **若确实只有一个,则跨生成器实验(§9.2)自动降级为非阻塞项**,
   如实记录"仅 1 个生成器可用",不要去找、去猜、去编造其他端点。
3. **依赖预检**:逐个 `import` 下列包并记录结果:
   `openai`, `dotenv`, `numpy`, `pandas`, `scipy`, `requests`, `sklearn`, `rank_bm25`,
   `datasets`, `hypothesis`。
   **注意:`ENV/environment.txt` 是过期快照,与实际情况不符,不可作为依据**,
   必须以实际 `import` 结果为准。
4. **缺包处置(重要:不许为此安装新包)**:
   - 缺 `scipy` → McNemar 用现有 `exact_mcnemar_p()` 的**纯 Python 回退分支**(已实现)
   - 缺 `sklearn` / `rank_bm25` → §9.3 的检索器改用**纯 Python TF-IDF + 余弦**(约 40 行)
   - 缺 `hypothesis` → §11 的属性测试写成**普通断言脚本**(不引入测试框架)
   - 缺 `numpy` / `pandas` → 用纯 Python + `csv` 模块(I/O 量不大,够用)
   - 缺 `openai` → 这是硬阻断,停止并报告

### 1.1 冻结原则
- **只读检索结果**。永不修改 memory store,永不重跑 retriever(新数据集除外,见 §9.3),
  永不删除或改写记忆条目。
- **集合冻结**。准入层只能在检索器已返回的 `raw_memories` 集合**内部**操作
  (重排、过滤、标注、渲染)。不得注入集合之外的新记忆或新事实。
- **对象内部完整解析合法**。解析检回对象里的任意字段(正文、`memory_key`、
  `metadata` 时间戳)属于集合内部操作,不违反冻结原则。
- **唯一例外**:实验 6(直喂 `gold_evidence`)那类注入检索集外信息的做法,
  只能作为**明确标注的"非准入可达上界"**存在,不得计入准入层战果。

### 1.2 禁用 benchmark 标签
以下字段**只能**出现在 oracle 上界臂和事后分析里,**绝不能**作为可部署方法的输入特征:

- `gold_memory_ids`
- `gold_evidence` / `evidence`
- `question_type`(HaluMem)
- 任何 `distractor` / partial 标注
- `baseline_label`、`baseline_response`

**Stage 0/1/2/3 的可部署路径代码里不得出现这些字段名**。
实现方式:Stage 1 的输入函数签名只接受 `(question, [EvidenceRecord])`,
物理上拿不到标签。若你需要某个来自标签的信息来做诊断,放到
`24_intrinsic_eval.py`(事后分析)里,不要放进主流水线。

### 1.3 不泄漏答案
授权/标注文本必须**恒等于** §7.3 里列出的固定模板之一,不得包含
gold answer 或 gold evidence 的 ≥5 个连续 token 的 n-gram 重叠。
复用现有的 `check_license_leakage` 逻辑并扩展到所有新增模板。

### 1.4 可复现
- 所有生成/judge 调用 `temperature=0`。
- 所有脚本**幂等 + 断点续跑**(磁盘缓存,键含输入 hash)。
- 固定随机种子:`SEED = 20260709`(沿用现有)。
- 每个脚本运行前打印预算(调用次数估算)并输出 `run_config.json`。

### 1.5 不要做的事(反跑偏清单)
- ❌ 不要实现 `R3a` / `R3b` / `R3c` 三个独立模块。
- ❌ 不要实现 "Router 先分类、再进对应模块" 的两级架构。
- ❌ 不要让任何模块输出 MC / DU / MB 这类 benchmark 错误类型标签。
- ❌ 不要训练/微调任何模型。
- ❌ 不要新增 license 类型或新的动作名称(严格用 §6.3 的六个)。
- ❌ 不要重构 `脚本/2.0-修复版/` 或 `脚本/3.0/` 里现有的 `00_`–`15_` 脚本
  (只允许 import 复用,不允许改动)。
- ❌ 不要为了"看起来更学术"而增加组件。少即是多。

---

## 2. 目录与文件布局

新建目录 `脚本/3.0/`(已存在,直接在其中加文件)。**新增文件用 `a2_` 前缀与 `20_`–`29_` 编号**,
不得与现有 `00_`–`15_` 冲突。

```
脚本/3.0/
  a2_schema.py              # EvidenceRecord / CapabilityMask / DecisionRecord 数据类
  a2_stage0_adapter.py      # Stage 0:异构对象 → EvidenceRecord + capability mask
  a2_stage1_estimator.py    # Stage 1:风险检测 + 关系/充分度后验(真实实现)
  a2_stage2_decision.py     # Stage 2:代价矩阵 argmin + 互斥集合裁决(真实实现)
  a2_stage3_render.py       # Stage 3:结构化块渲染 + 排序 + 标注注入
  a2_pipeline.py            # 编排 Stage0→1→2→3,单一入口 run_pipeline(sample) -> context
  a2_calibrate.py           # conformal 风险门控校准
  a2_arms.py                # 实验臂定义(B0/B1/B2/A2/ORACLE_REL)
  20_build_pool.py          # 构建评估池(memos + longmemeval)
  21_run_generation.py      # 所有臂的生成(缓存)
  22_judge.py               # C/H/O 判定(缓存)
  23_analyze.py             # flip rate / Wilson CI / 转移矩阵 / McNemar / 误差分解
  24_intrinsic_eval.py      # 事后分析:估计器与 oracle 关系的一致性
  25_build_longmemeval.py   # LongMemEval 适配 + 最小检索器
  test_a2_invariants.py     # 属性/不变量测试(§10)
```

输出目录:`outputs/a2_mvp_v1/`

```
outputs/a2_mvp_v1/
  run_config.json
  pools/{memos,longmemeval}_pool.jsonl
  estimates/{pool}/{case_id}.json          # Stage 1 输出缓存
  decisions/{pool}/{arm}.jsonl             # Stage 2 输出缓存
  contexts/{pool}/{arm}.jsonl              # Stage 3 渲染结果
  generations/{pool}/{arm}__{generator}.jsonl
  verdicts/{pool}/{arm}__{generator}.jsonl
  calibration/{pool}.json                  # conformal 阈值
  analysis/*.csv
  RESULTS.md
```

**复用现有模块**(只 import,不改):
- `e1_memos_oracle_common`: `make_client` / `read_jsonl` / `append_jsonl` / `write_csv` /
  `write_json` / `sha256_text` / `evidence_texts` / `check_license_leakage` /
  `call_chat` / `call_judge` / `retry_call` / `serialize_baseline_context`
- 现有样本池:`outputs/e1_memos_full_oracle_v2/samples_memos_full.jsonl`(含 `context_str_full`)
- 可见性数据:`outputs/e1_memos_full_oracle_v2/visibility.jsonl`

---

## 3. Stage 0 — Adapter / 统一转换

### 3.1 数据模型(`a2_schema.py`)

```python
@dataclass
class EvidenceRecord:
    id: str                    # "m1".."mN",与 raw_memories 顺序一一对应
    text: str                  # 合成正文(见 3.2)
    event_time: str | None     # ISO8601 或 None
    ingest_time: str | None    # ISO8601 或 None
    time_source: str           # "meta_event" | "meta_ingest" | "text_cue" | "none"
    time_is_proxy: bool        # True 表示使用的 ingest_time 只是 event_time 的代理
    time_uncertainty: tuple[str, str] | None   # 第 2 层的时间不确定区间
    entity_anchors: list[str]  # 含 memory_key 主题锚
    source_session: str | None
    raw_index: int             # 0-based,指向 raw_memories
    # ── 免费可用的检索侧信号(来自检回对象自身,不违反冻结原则)──
    retrieval_score: float | None   # raw_memories 的 `relativity` 字段
    confidence: float | None        # `confidence` 字段
    memory_type: str | None         # `memory_type` 字段(如 fact / preference)
    tags: list[str]                 # `tags` 字段
    mask: CapabilityMask
```

```python
@dataclass
class CapabilityMask:
    text: bool
    event_time: bool
    ingest_time: bool
    entity_anchors: bool
    source_session: bool
    retrieval_score: bool
    confidence: bool
```

> **实测事实(基于本仓库现有 memos 数据,请勿再假设)**:memos 的
> `raw_memories` 对象里**普遍存在 `create_time`、`update_time`、`relativity`、
> `conversation_id`、`status`**,并且存在**两类记忆**:
> 事实类(`memory_key` / `memory_value` / `memory_type` / `confidence` / `tags`)
> 与偏好类(`preference` / `preference_type` / `reasoning`)。
> 抽样统计:`memory_key` 与 `memory_value` 约覆盖一半对象(1197/2317),
> `preference` 约覆盖另一半(1120/2317)。
> **含义:first-key-wins 缺陷确实会丢字段(两类记忆各自只能命中一条分支);
> 且 `relativity` / `confidence` 是免费可用的估计特征,必须进 schema。**

### 3.2 正文合成(消除 first-key-wins 缺陷)

**这是 Stage 0 的核心修复,必须做对。**

旧实现 `memory_text()` 是 first-key-wins 级联:取到 `memory_value` 就返回,
丢弃 `memory_key` 和 metadata 时间。新实现必须**渲染全部可得事实字段**:

```
按固定顺序遍历以下字段,收集所有非空值:
   memory, memory_value, memory_key, memory_type, tags,
   preference, preference_type, reasoning, content, text,
   metadata 内的标量字符串字段
输出格式(字段名 + 值的结构化合成):
   "<字段名>: <值>" 用 " | " 连接
   即形如: "memory_key: Housing | memory_value: moved to Berlin | memory_type: fact"
```

要求:
- 遍历顺序**固定且确定性**(按上面的顺序)。
- **带字段名前缀**(不要只拼裸值)——因为 `memory_key` 是主题锚,
  少了前缀在文本里就退化成一个无标记的短语。
- 去重:完全相同的 (字段名, 值) 只出现一次。
- 跳过空串、`null`、"None"、"N/A"、纯空白。
- `tags` 是列表 → 用 `,` 连接后作为一个值。
- 不得因为某个键非空就跳过后续键(**禁止 early return**)。
- 合成后 `text` 为空 → 该记录非法,标记 `rejected: empty_text` 并跳过,
  不得中止整批。

### 3.3 时间三层回退

按优先级,把结果写入 `event_time` / `ingest_time` / `time_source` / `time_is_proxy`:

> **重要事实(已实测,不要再假设 memos 没有时间戳)**:memos 的检回对象里
> **普遍带 `create_time` 和 `update_time`**。所以第 1 层几乎总会命中——
> 真正的问题**不是"找不到时间",而是"找到的是写入时间,不是事件时间"**。
> 这必须显式建模,不能无声地把"写入新"当成"事实新"。

1. **第 1 层** `meta_event` / `meta_ingest`:对象内部时间字段。
   在 `metadata` 及对象顶层按此键序查找:
   `event_time, event_time_iso, occurred_at, chat_time, timestamp,
    created_at, updated_at, create_time, update_time`。
   - 语义为"事件发生"的键(`event_time` / `event_time_iso` / `occurred_at` / `chat_time`)
     → 写入 `event_time`,`time_source = "meta_event"`,`time_is_proxy = False`
   - 语义为"写入/抽取"的键(`created_at` / `updated_at` / `create_time` / `update_time` / `timestamp`)
     → 写入 `ingest_time`,`time_source = "meta_ingest"`,
     **`time_is_proxy = True`**(关键:这只是事件时间的代理)
   - 两者同时存在时,时序比较用 `event_time`;仅 `ingest_time` 可用时,
     时序比较用它但必须带 `time_is_proxy = True`
   - **HaluMem 的写入顺序 ≈ 事件顺序,这是一个假设,不是事实。**
     凡依赖该代理做出的裁决都必须打标(见 §5.3)。
2. **第 2 层** `text_cue`:正文内可解析的时间线索(如 "in May 2023"、"last March"、
   "since 2019")。解析成功 → 写入 `event_time` 并填 `time_uncertainty = (lo, hi)`,
   `time_is_proxy = False`。解析失败 → 落第 3 层。
3. **第 3 层** `none`:无任何时间信号。`event_time = ingest_time = None`,
   `time_source = "none"`,`time_is_proxy = False`。

**必须满足的不变量**:每条记忆的 `time_source` 恰好是四值之一,非空、唯一。

**日志要求**:批级统计并打印 `time_source` 分布,以及
**`time_is_proxy=True` 的占比**。后者直接决定 Stage 2 时序裁决的可信度,
必须写进 `RESULTS.md`(见 §12 第 12 节)。

### 3.4 适配器接口

```python
def adapt(raw_memories: list[Any], system_kind: str) -> list[EvidenceRecord]
```

`system_kind ∈ {"memos", "mem0", "memobase", "supermemory", "longmemeval"}`。
MVP 阶段各系统的差异只体现在 §3.3 的键序与 §3.2 的字段集上,
用一张 `SYSTEM_FIELD_SPEC` 表驱动,不要写五个类。

**Capability mask 计算**:在生成的 `EvidenceRecord` 上统计该批记忆实际填充了哪些字段
(`text` 恒 true),输出一个批级 mask 到日志。这个 mask 用于 §11 的跨系统轴。

---

## 4. Stage 1 — Estimation(真实实现,本任务重点)

### 4.1 职责

对冻结集合与当前问题,输出两样东西:

1. **查询级风险 + 充分度**(驱动 §8 的门控)
2. **逐条记忆的关系后验 + 条件/绑定信号**(驱动 Stage 2)

### 4.2 接口

```python
def estimate(question: str, records: list[EvidenceRecord]) -> EstimateResult
```

**函数签名里不得出现任何 benchmark 标签字段。**

```python
@dataclass
class MemoryEstimate:
    id: str
    relation_posterior: dict[str, float]   # 6 类概率,和为 1.0
    condition_present: bool
    condition_text: str                    # 无则 ""
    condition_satisfied: str               # "TRUE" | "FALSE" | "UNKNOWN"
    entity_match: str                      # "MATCH" | "MISMATCH" | "UNCLEAR"

@dataclass
class EstimateResult:
    premise_conflict: bool                 # 问题是否含与某条记忆矛盾的前提
    sufficiency: float                     # [0,1] 当前集合是否足以作答
    risk: float                            # [0,1] 是否需要准入干预
    memories: dict[str, MemoryEstimate]    # key = memory id
    failed: bool                           # 估计是否失败(触发安全回退)
```

### 4.3 关系类别(六类,严格用这六个名字)

| 类别 | 含义 |
|---|---|
| `SUPPORT` | 该记忆直接包含回答问题所需的关键事实 |
| `REFUTE` | 该记忆与问题中隐含的某个前提直接矛盾 |
| `SUPERSEDED` | 该记忆陈述某属性的**较早**取值,而集合中另有更新的取值 |
| `CURRENT` | 该记忆陈述某属性的**最新**取值,集合中没有更新它 |
| `MISBIND` | 该记忆主题相关,但绑定到的人/物/属性与问题所问不一致 |
| `INSUFFICIENT` | 该记忆主题相关,但不含回答问题所需的事实 |

### 4.4 估计器提示词(逐字使用,允许微调措辞但不得改动输出 schema 与语义)

```
你是记忆准入系统的证据估计器。你看不到标准答案,只能依据下面的问题与记忆作答。

问题:
{question}

记忆列表(每条含位置 id、时间[可能缺失]、主题锚[可能缺失]、正文):
{memory_block}

请对每条记忆判断它与问题的关系,并给出概率分布;同时判断整体情况。

每条记忆必须输出:
- relation: 六个类别的概率,键必须恰好是
  SUPPORT / REFUTE / SUPERSEDED / CURRENT / MISBIND / INSUFFICIENT,
  六个值均为 0.0-1.0 且总和为 1.0
- condition_present: 该记忆是否只是一条"仅在某条件成立时才适用"的规则
  (注意:"when she arrived"这类事件时间修饰不算条件;
   "even if / what if"属于问题句式,不属于记忆,不算条件)
- condition_text: 条件内容原文,没有则空串
- condition_satisfied: "TRUE" / "FALSE" / "UNKNOWN"
  —— 问题所述情形能否确认满足该条件;无法判断填 UNKNOWN
- entity_match: "MATCH" / "MISMATCH" / "UNCLEAR"

整体必须输出:
- premise_conflict: true/false,问题是否包含与某条记忆直接矛盾的前提
- sufficiency: 0.0-1.0,当前记忆集合是否足以回答问题
- risk: 0.0-1.0,当前集合是否需要准入干预(无需干预填低值)

只输出 JSON,不要输出任何其他文字。格式:
{"premise_conflict":false,"sufficiency":0.0,"risk":0.0,
 "memories":[{"id":"m1","relation":{"SUPPORT":0.0,"REFUTE":0.0,"SUPERSEDED":0.0,
 "CURRENT":0.0,"MISBIND":0.0,"INSUFFICIENT":1.0},"condition_present":false,
 "condition_text":"","condition_satisfied":"UNKNOWN","entity_match":"UNCLEAR"}]}
```

**`memory_block` 的构造**:每条一行,格式固定
`[<id> | <event_time 或 "?" > | <entity_anchors 拼接 或 "-" >] <text>`
—— 即 Stage 3 结构化块的同款格式,保证估计器看到的信息与生成器一致。

### 4.5 输出校验与回退(必须实现)

1. 解析 JSON;失败 → 重试 ≤3 次(指数退避);仍失败 → `failed=True`。
2. 逐条校验:
   - `id` 必须与输入集合完全一致(不多不少),缺失的补 `INSUFFICIENT: 1.0`
   - 六个键齐全、均 ∈ [0,1]、和 ∈ [1e-6, 1+1e-6] → 否则重新归一化
   - 归一化后仍非法 → 该条置 `INSUFFICIENT: 1.0`,`entity_match="UNCLEAR"`,
     `condition_present=False`,并记 `validation_warning`
   - `condition_satisfied` 不在枚举内 → `"UNKNOWN"`
   - `entity_match` 不在枚举内 → `"UNCLEAR"`
3. `risk` / `sufficiency` 越界 → clip 到 [0,1]。
4. `failed=True` → **Stage 1 返回安全默认**:`risk=0.0`(→ 门控走 no-op),
   下游等价 baseline。**绝不抛异常中断整批。**

### 4.6 缓存

每个 `case_id` 的估计结果落盘 `estimates/{pool}/{case_id}.json`,
键含 `(question_hash, [record.text hash 列表], model, prompt_hash)`。
断点续跑时命中缓存直接读。

### 4.7 并发

`ThreadPoolExecutor(max_workers=12)`,沿用现有 `retry_call` 的退避策略。

---

## 5. Stage 2 — Decision(真实实现,本任务重点)

### 5.1 动作空间(六个动作,严格用这六个名字)

动作 = **(salience, license)** 二维因子的一个受限组合:

| 动作 | salience | license | 渲染效果(Stage 3 执行) |
|---|---|---|---|
| `VOUCH` | 高(排序置前) | 无 | 前置 + 注入 `[关键证据]` 模板 |
| `KEEP` | 中(保持原位) | 无 | 原样渲染 |
| `DEMOTE` | 低(排序置后) | 无 | 后置 + 注入 `[次要信息]` 前缀 |
| `QUALIFY` | 中 | `QUALIFY` | 原序 + 注入 `[使用范围]` 模板 |
| `REFUTE` | 高(排序置前) | `REFUTATIONAL` | 前置 + 注入 `[证据说明]` 反驳模板 |
| `BLOCK` | 零 | — | **不进入 context** |

> 注意:动作名与关系名有部分重名(`REFUTE`),这是有意的但**极易混淆**。
> 代码里必须用前缀区分命名空间:动作用 `Action.REFUTE`,
> 关系用 `Relation.REFUTE`。不要用裸字符串比较两者。

### 5.2 代价矩阵(核心决策规则)

对每条记忆,给定 Stage 1 的关系后验 `p(r)`,计算每个动作 `a` 的期望代价:

```
cost(a) = Σ_r p(r) · [ λ_H · H(a,r) + λ_O · O(a,r) ]
```

主实验取 **λ_H = 1.0, λ_O = 1.0**(对称,中性立场)。
λ_O 敏感性另跑 `{0.3, 0.6, 1.0, 2.0}` 四档(见 §11)。

**下表已验算过,六个 one-hot 后验的 argmin 结果与 §11.3 的断言完全一致。
逐字使用,不要凭直觉改动数值。**

```python
# 每格格式:(H_cost, O_cost)
COST_MATRIX = {
    #            SUPPORT        REFUTE          SUPERSEDED      CURRENT         MISBIND         INSUFFICIENT
    "VOUCH":   [(0.00, 0.00), (0.20, 0.50),   (0.75, 0.00),   (0.05, 0.02),   (0.70, 0.05),   (0.80, 0.02)],
    "KEEP":    [(0.00, 0.00), (0.05, 0.50),   (0.50, 0.05),   (0.05, 0.05),   (0.40, 0.10),   (0.45, 0.05)],
    "DEMOTE":  [(0.10, 0.25), (0.10, 0.45),   (0.30, 0.10),   (0.10, 0.15),   (0.25, 0.15),   (0.30, 0.10)],
    "QUALIFY": [(0.05, 0.15), (0.10, 0.35),   (0.20, 0.10),   (0.05, 0.10),   (0.15, 0.25),   (0.10, 0.10)],
    "REFUTE":  [(0.25, 0.10), (0.05, 0.05),   (0.15, 0.15),   (0.15, 0.15),   (0.25, 0.20),   (0.20, 0.15)],
    "BLOCK":   [(0.00, 0.95), (0.10, 0.90),   (0.05, 0.05),   (0.02, 0.85),   (0.05, 0.15),   (0.05, 0.05)],
}
```

**验算结果(必须复现,否则接错线了)**:

| 纯后验(one-hot) | 期望代价最小动作 | 理由 |
|---|---|---|
| SUPPORT | `VOUCH` | 0.00,与 KEEP 并列 → tie-break 取 VOUCH |
| REFUTE | `REFUTE` | 0.10 vs VOUCH 0.70 → 唯一最小 |
| SUPERSEDED | `BLOCK` | 0.10 vs DEMOTE 0.40 → 唯一最小 |
| CURRENT | `VOUCH` | 0.07 vs KEEP 0.10 → 唯一最小 |
| MISBIND | `BLOCK` | 0.20 vs QUALIFY 0.40 → 唯一最小 |
| INSUFFICIENT | `BLOCK` | 0.10 vs DEMOTE 0.40 → 唯一最小 |
| `{SUPPORT:0.5, INSUFFICIENT:0.5}` | `QUALIFY` | 0.200,次小 KEEP 0.250(证明后验加权真的在起作用) |

**表值语义说明(写进代码注释,便于审稿人理解来源)**:
- `VOUCH` 对 `SUPPORT`/`CURRENT` 最优,但对 `SUPERSEDED`/`MISBIND`/`INSUFFICIENT`
  **是高危动作**(0.70–0.80)——鼓励过度推断、使用过期值、用错绑记忆。
  这是"就地指认"必须谨慎的原因。
- `BLOCK` 对 `SUPERSEDED`/`MISBIND`/`INSUFFICIENT` 最优,但对
  `SUPPORT`/`CURRENT` 是灾难(O_cost 0.95/0.85,制造 omission)。
- `REFUTE` 只在真实关系为 `REFUTE` 时安全;错授权会让模型否定正确前提 → 幻觉升高。
- `KEEP` 是唯一的"无作为"动作,代价普遍中等——它存在是为了让"什么都不做"
  也是一个可选解。

**tie-break 规则(确定性)**:期望代价差值 ≤ 1e-9 时,按以下固定优先级选取:

```
VOUCH > KEEP > QUALIFY > DEMOTE > BLOCK > REFUTE
```

> ⚠️ 因为 `VOUCH` 优先级最高,**任何未验算的平局都会静默落到 VOUCH**
> (最危险的过度自信动作)。所以上表必须逐字使用,
> 且 §11.3/§11.4 的断言必须跑通——它们是防止这个静默失效的唯一屏障。

### 5.3 集合级裁决:互斥状态集合

逐条 argmin **之后**执行一次集合级修正(顺序不能颠倒)。

> **先测再实现(强制前置步骤)**:在写这段逻辑前,先跑一个一次性统计脚本,
> 输出:① `memory_key` 的有值率;② `entity_anchors` 非空的记录占比;
> ③ 在同一 `case_id` 内、按下面的分组键分组后,组大小 ≥2 的组数分布。
> **把这三个实数写进 `RESULTS.md`。**
> 理由:`memory_key` 实测约只有一半对象有值,**如果兜底键设计不当,
> 分组会恒为单元素,本节逻辑等于永不触发**——那 Stage 2 就退化成了逐条 argmax,
> 而这正是 B2 臂要测的东西。你必须先确认分组真的会发生。

1. **分组键(按优先级取第一个可得者)**:
   1. `normalized(entity_anchors[0])` —— 去空格、小写
   2. `normalized(memory_key)` —— 若有值(**实测约 50% 的记录有**)
   3. 若上两者都空:**用记忆正文与问题的共享名词短语**(纯 Python 实现:
      两边各取长度 ≥4 的非停用词 token 集合,取交集最大者作为一个临时键)
      —— 不要用 "m1/m2" 这类位置 id 当分组键,那会让每条各成一组
   4. 若仍为空:该条**不参与**互斥裁决(视为聚合型),记 `group_key="none"`

2. **互斥判定**:组内 ≥2 条且它们互相冲突。MVP 的判定用**任一**下列条件:
   - 至少一条 `p(SUPERSEDED) > 0.4`,或
   - 两条在同一分组键下、`relation` 的 argmax 一为 `CURRENT` 一为 `SUPERSEDED`
   (**不要**尝试做属性值抽取,那是下一篇论文的事)

3. **裁决**:
   - **有时序信号**(组内存在可比较的时间:`event_time` 优先;
     仅 `ingest_time` 可用时**允许使用但必须打标** `time_proxy="ingest"`;
     第 2 层的区间用**上界**参与比较):
     选时间**最新**的唯一一条 → 该条 `VOUCH`;其余条 → `DEMOTE`。
     若最新时间**并列**(≥2 条时间完全相等)→ 走下面的降级分支。
   - **无时间信号**(全部 `time_source == "none"` 或不可解析):
     组内**全部**降级为 `QUALIFY`,不得产生任何 CURRENT 权威。
   - **代理时间警告**:若裁决依赖 `ingest_time`(即 `time_is_proxy=True`),
     该条的 `decision_note` 必须记 `"temporal_from_ingest_proxy"`,
     且统计批级占比。**这是"把写入新当成事实新"的已知风险,必须可审计。**

4. **聚合集合不受约束**:组内 ≥2 条且**不冲突**(都不满足第 2 步条件),
   视为聚合型(如多个支持者),**全部保持各自动作不变**,不得裁决唯一。

**不变量**:任一互斥状态集合中,`VOUCH` 的条数 ≤ 1;
无时序信号的互斥集合中 `VOUCH` 条数 = 0。

### 5.4 条件约束(scope)

- `scope = CONDITIONAL` **当且仅当** `condition_present == True`
  且该判定**只来自记忆正文**(Stage 1 的 `condition_text` 必须能在该记忆
  `text` 中找到子串证据;找不到 → 降为 `condition_present=False`)。
- 当 `scope = CONDITIONAL` 且 `condition_satisfied ∈ {FALSE, UNKNOWN}` 时:
  - **不得**把该记忆当作已发生事实 → 若当前动作为 `VOUCH`/`KEEP`,
    改判为 `QUALIFY`;
  - 同时记 `decision_note = "conditional_rule_not_as_event"`。
- **关系维度优先**:若 `relation` 的 argmax ∈ {`REFUTE`, `SUPERSEDED`},
  条件性**不得**改写该判定,只允许在渲染时附加条件说明。

### 5.5 充分度边界

- 若 Stage 1 的 `sufficiency < 0.35` 且没有任何记忆的动作是 `VOUCH`:
  在渲染时追加一条查询级指令(固定模板,见 §7.3 的 `INSUFFICIENT_NOTE`),
  告知模型证据不足以断言。**不得**凭空回答,也**不得**塞入任何集合外内容。
- 若所有记忆都被判为 `BLOCK`:该样本走 **bypass**,直接复用 baseline context
  (等价 no-op),标记 `no_strict_evidence`。**不得**渲染空 context 让模型自由发挥。

### 5.6 输出

```python
@dataclass
class DecisionRecord:
    id: str
    action: str                  # 六个动作名之一
    relation_argmax: str
    scope: str                   # "UNCONDITIONAL" | "CONDITIONAL"
    temporal: str                # "CURRENT" | "HISTORICAL" | "UNKNOWN"
    use: str                     # "ASSERT" | "QUALIFY" | "REFUTATIONAL"
    decision_note: str           # 空串或诊断标记
```

**不变量**:`use == "ASSERT"` ⟺ 该条不注入任何授权模板文本(防 silent no-op)。
在渲染前断言这条。

---

## 6. Stage 3 — Rendering

### 6.1 结构化块

每条记忆渲染为:

```
[<id> | <time> | <anchor>] <可选标注前缀>\n<text>
```

- `<time>`:`event_time` 的日期部分(`YYYY-MM-DD`);缺失 → `?`
- `<anchor>`:`entity_anchors[0]`;缺失 → `-`
- 字段顺序固定,`|` 分隔,缺字段也保留占位(不得省略分隔符)

### 6.2 排序

按 salience 分层:`VOUCH`/`REFUTE` → 前置区;`KEEP`/`QUALIFY` → 中区;
`DEMOTE` → 后区。区内保持原始位置序(`raw_index` 升序)。
`BLOCK` 不渲染。

### 6.3 固定模板(全部逐字使用,不得改写)

```python
LICENSE_TEMPLATES = {
    "VOUCH":       "[关键证据] 该记忆包含回答当前问题所需的关键信息，请优先依据它作答。",
    "REFUTATIONAL":"[证据说明] 该记忆与问题中的某个前提直接矛盾。你被允许且应当依据该记忆指出前提错误，而不是回答“不知道”。",
    "QUALIFY":     "[使用范围] 该记忆仅在其所述条件成立时适用。若问题所述情形无法确认满足该条件，不要把它当作已经发生的事实，必须在回答中说明该条件。",
    "DEMOTE_PREFIX":"[次要信息] ",
}

INSUFFICIENT_NOTE = (
    "[证据不足] 现有记忆不足以支持对所问事实作出确定断言。"
    "请明确说明缺少什么信息，不要依据常识或推测作答。"
)
```

### 6.4 上下文拼接

**no-op / bypass 分支无例外地复用 `context_str_full` 逐字节原文**
(可用性前提:`00_verify_serializer.py` 已验证 `serializer_ok`)。
这是 do-no-harm 的**构造性保证**,不要重拼。

其它分支统一用:

```python
f"Memories for user {user_name}:\n\n    " + "\n".join(lines)
```

`user_name` 取样本的 `user_name`。若 `pref_note` 非空**且动作集合中存在
非 BLOCK 的记忆**,把它作为最后一行追加(与 baseline 序列化一致);
若所有记忆都被 BLOCK,走 bypass,不追加。

**空白 context 禁令**:若 `lines` 为空但不是 bypass 分支 → 报错,
不允许渲染空记忆块。

### 6.5 泄漏检查

渲染前对**全部**注入模板跑 `check_license_leakage`(扩展到新模板)。
命中 → 该样本该臂标记 `leakage`、不生成、写入 `leakage_failures.jsonl` 并继续其他样本。

---

## 7. 校准:conformal 风险门控(必须实现)

### 7.1 为什么

需要一个**可校准的旋钮**:控制"被判定为无需干预的样本里,实际答错的比例 ≤ α"。
这是从 "调出来的工作点" 变成 "控制器" 的关键,也是论文里那张 α→实测曲线图的数据来源。

> ⚠️ **池定义决定这个机制是否成立(见 §9.1 的修正)**:
> 如果评估池只包含"baseline 已经答错"的样本,那么
> `noop_err = Σ noop·baseline_wrong / Σ noop` **恒等于 1.0**,
> 于是"≤ α"永不满足 → 按下面的规则退化为 `τ = -inf` → **全程干预,
> 门控形同虚设,do-no-harm 也无法测量**。
> 因此评估池**必须包含 baseline 答对的样本**(§9.1)。

### 7.2 数据划分

按 `case_id` 的 `sha256` 取前 8 位十六进制 mod 2 划分:
`0` → calibration split,`1` → test split。(约 50/50,固定、可复现。)

**代价矩阵调整与门控阈值都只能在 calibration split 上做。**

### 7.3 门控算法(单调、可在 cal 上直接求解)

```
输入:cal split 上每条样本的 (risk_score_i, baseline_wrong_i)
      risk_score_i = Stage 1 的 risk(估计失败时取 0.0)

对候选阈值 τ ∈ 该 split 上所有 risk_score 的取值(含 -inf):
    noop_i(τ) = (risk_score_i <= τ)
    coverage(τ)   = mean(noop_i(τ))
    noop_err(τ)   = Σ noop_i·baseline_wrong_i / max(1, Σ noop_i)

选择:在满足 noop_err(τ) <= α 的候选中,取 coverage 最大者。
      若无任何 τ 满足,取 τ = -inf(永不 no-op,即全程干预)。

落盘:calibration/{pool}.json = {alpha, tau, coverage, noop_err, n_cal,
                                n_cal_baseline_wrong, degenerate_flag}
```

**`degenerate_flag`**:当 `τ == -inf`(即没有任何阈值能满足 α)时置 true,
并在 `RESULTS.md` 显著标注"门控退化为全程干预"。**这是必须暴露的失效,
不是可以静默吞掉的边界情况。**

主实验取 **α = 0.10**;另跑 α ∈ {0.05, 0.10, 0.20, 0.30} 的 coverage/realized-error 曲线。
在 test split 上报告**实测** `coverage` 与 `noop_err`,与 cal 值并列,
用于验证该保证的迁移性(不成立就如实报告偏离)。

### 7.4 与 Stage 1 / Stage 2 的接线

- `risk_score <= τ` → **no-op**:整条流水线不介入,直接复用 `context_str_full`。
- `risk_score > τ` → 走 Stage 2 + Stage 3 渲染。
- 估计失败(`failed=True`)→ `risk_score = 0.0` → 必然 no-op(安全默认)。

---

## 8. 实验臂定义(`a2_arms.py`)

| 臂 | 名称 | 构造 | 神谕化阶段 | 作用 |
|---|---|---|---|---|
| `B0` | no-A2 replay | 逐字节 `context_str_full` | — | baseline / 噪声地板 |
| `B1` | prompt-only(强) | `context_str_full` + 一条**静态**规则指令(见 §8.1) | — | **决定性 baseline** |
| `B2` | 无决策层 | Stage 0 + Stage 1 真实,但**跳过 Stage 2**:直接按 `argmax(relation)` 套固定映射(见 §8.2),Stage 3 正常渲染 | — | 隔离"代价矩阵是否必要" |
| `A2` | 完整流水线 | Stage 0→1→2→3 全部真实 + 门控 | — | **主方法** |
| `A2-nogate` | 去门控 | 同 A2,但强制 `τ = -inf`(全程干预) | — | 门控消融 |
| `A2-nosal` | 去 salience | 同 A2,但所有动作的 salience 置中性(只保留 license) | — | 因子消融 |
| `A2-nolic` | 去 license | 同 A2,但所有动作的 use 置 `ASSERT`(只保留 salience) | — | 因子消融 |
| `A2-noblock` | 禁 BLOCK | 同 A2,但 BLOCK → DEMOTE | — | 风险动作消融 |
| `ORACLE_REL` | 关系神谕上界 | Stage 1 用 `gold_memory_ids` + `question_type` 硬映射替换 | Stage 1 | 上界参照(复用已有 UA3 数字,不重跑) |

### 8.1 B1 静态指令(prompt-only,必须写强——这是最重要的一条)

把下面整段作为**单条静态** system/前置指令,与 baseline context 拼接,**一次生成调用**:

```
请严格按以下规则使用上面的记忆:
1. 先逐条核对每条记忆的时间。若同一事项存在新旧不同说法,以时间最新的一条为准。
2. 核对记忆中的实体与问题所问的人/物是否一致;若记忆讲的是别人别的事,
   不要用它回答。
3. 若记忆中某条与问题中的某个前提直接矛盾,请直接指出该前提有误,
   不要回答"不知道"。
4. 若某条记忆只在特定条件下成立,回答时必须显式说明该条件,
   不得直接当作已经发生的事实。
5. 若记忆只是话题相关但不包含所问事实,不要推断,
   明确说明缺少什么信息。
作答前先逐条评估,再给出最终答案。
```

**这个臂必须做到最强**。若 A2 相对 B1 增益 < 3pp,如实报告,
不得通过弱化 B1 来制造差距。

### 8.2 B2 的固定映射(不带代价矩阵)

```
argmax(relation) == SUPPORT      -> VOUCH
argmax(relation) == CURRENT      -> VOUCH
argmax(relation) == REFUTE       -> REFUTE
argmax(relation) == SUPERSEDED   -> BLOCK
argmax(relation) == MISBIND      -> BLOCK
argmax(relation) == INSUFFICIENT -> BLOCK
```
不做后验加权、不做集合级裁决、不做条件降级。

---

## 9. 数据集与执行计划

### 9.0 池定义(最关键的一处修正,先读完再建池)

**旧定义(错误,不要用)**:只取 `baseline_label != "correct"` 的样本。
这个池有两个致命问题:
1. **门控退化**:池内每条 baseline 都错 → `noop_err ≡ 1.0` → τ 永远求解失败 →
   全程干预,门控变摆设(见 §7.1)。
2. **do-no-harm 无法测量**:池里没有 baseline 答对的样本,
   就测不出"干预有没有把对的搅错"。

**新定义(用这个)**:**按检索条件定义,不按 baseline 对错定义。**

```
池 = 所有满足以下条件的样本:
      retrieval_stratum == "strict_supported"     # 检索检回了严格支撑的 gold
      或 retrieval_stratum == "partial_supported"  # 同时也纳入部分支撑(更接近真实部署)
      且 gold_evidence 非空
      且 serializer_ok == true                     # 逐字节重放可用
```

**必须做的等价性校验(建池后立刻跑,写入 RESULTS.md)**:在这个新池上重跑 B0,
断言"B0 判错的样本集合 = 原来的 1987 条"。
- 若**完全一致** → 池等价,已有的 A3=46.13% / UA3=53.29% 可直接对照。
- 若**不一致** → 报告差异条数,并以新池为准;**不要在两者之间混用数字**。
  此时旧数字仅作为参考,和 Codex 说明差异来源。

**池内分层(全部保留,不要在生成前过滤)**:
- `B0 correct` 子池 → 用于 **do-no-harm 测量**(是这次修正的主要目标)
- `B0 wrong` 子池 → 用于 **flip rate**,与旧数字同类可比
- 这样一次运行同时得到"救回多少"和"搅坏多少",而这正是 C/H/O 转移矩阵的核心价值。

### 9.1 分阶段执行(严格按序,未通过不进入下一阶段)

#### 阶段 A — 冒烟(必须先通过)
- 样本:**150 条**(从新池抽样,固定种子 `20260709`)
  —— **必须同时含 `B0 correct` 与 `B0 wrong` 两类**,不要只抽错的
- 臂:`B0`, `B1`, `B2`, `A2`
- 生成器:1 个(优先 `deepseek-chat`,与 baseline 可比)
- **验收**:
  1. 四臂全部产出;`leakage_failures` 为空;无脚本崩溃
  2. A2 的 no-op 率 ∈ (0, 1)(**不要是 0 也不要正好是 1**)
  3. Stage 2 的动作分布**不是单一动作占 ≥95%**(否则代价矩阵接错线了)
  4. §5.3 的分组统计已产出,且"组大小 ≥2 的组数 > 0"
  5. `test_a2_invariants.py` 全绿
- 产出 `RESULTS.md` 的"阶段 A 冒烟"小节,然后**继续**(不必等人确认)

#### 阶段 B — memos 主实验
- 样本:**§9.0 定义的新池全部**
- 臂:`B0`, `B1`, `B2`, `A2`, `A2-nogate`, `A2-nosal`, `A2-nolic`, `A2-noblock`
- 生成器:1 个
- **主指标**:全池端到端 C / H / O(见 §10.2)
- **可比指标**:在 `B0 wrong ∩ strict_supported` 子池上报 flip rate,
  与已有 A3=46.13% / UA3=53.29% 对照
- **do-no-harm 指标**:在 `B0 correct` 子池上的 C→H 与 C→O 计数(**这是新增的重点**)

#### 阶段 C — LongMemEval
- 见 §9.3。若数据集不可得,**跳到阶段 E 并明确报告**。

#### 阶段 D — 跨生成器(固定控制器)
- **前置**:§1.0 预检发现只有一个 LLM 端点时,**本阶段自动跳过**,
  在 RESULTS.md 写明"仅 1 个生成器可用,跨生成器实验未执行",**不要编造**。
- 若确实有 ≥2 个可用端点:在固定 **400 条**子集(种子 `20260709`)上跑 `B1` 与 `A2`,
  换所有可用生成器。控制器(Stage 1/2/3 代码、代价矩阵、τ)**完全不变**。

#### 阶段 E — 跨记忆系统(若 LongMemEval 不可得,本阶段升格为必需)
- 用 `raw_memories` 已保存的其它系统产物(mem0 / memobase / supermemory)
  构建池,跑 `B1` 与 `A2`(控制器不变,只换 Stage 0 的 `system_kind`)
- 报告 capability mask 差异与性能差异
- 注意:这些系统的样本池**只含 baseline 答错的样本**(旧口径),
  因此在本阶段**只报 flip rate,不报 noop_err / do-no-harm**,并注明原因

### 9.2 生成器与 judge

- **生成器**:必须先执行 §1.0 的预检,**按实际发现的端点构造注册表**。
  **绝不虚构 key,绝不使用未在 .env 中出现的端点。**
  目标 3 个(1 个 DeepSeek 系 + 1 个其它家族 + 1 个开源权重),
  **实际有几个就用几个**;当前预期是**只有 1 个**。
  在 `RESULTS.md` 明确写出"实际使用了 N 个生成器,原因是..."。
- **judge**:沿用现有 gold-only judge(`call_judge`,输出 C/H/O),
  与 baseline 数字保持同源可比。若存在**非 DeepSeek 家族**的可用 key,
  额外用它复判 200 条并报告一致性(非必需项,时间不够可跳过并说明)。

### 9.3 LongMemEval 接入

> **现状(已核实)**:本地**没有** LongMemEval 数据。只有一份
> `r3a-exec-log/runs/round_0070/research-sessions/2026-10-08-longmemeval-fit/SUMMARY.md`
> 的适用性审查报告。环境里有 `datasets` 包(4.7.0),可尝试 HF 下载,但需网络。
> **先读那份 SUMMARY.md**——它包含重要的方法论警告(见下)。

1. **先读** `r3a-exec-log/runs/round_0070/research-sessions/2026-10-08-longmemeval-fit/SUMMARY.md`,
   按其"推荐的最小接入方案"执行,并遵守其中列出的边界。
2. **三条必须遵守的警告**(来自该报告,直接引用于此):
   - **不是首次发现**:LongMemEval 原论文 §5.5 已在 oracle retrieval 下研究过
     reading failure。**不得**把"检索到 ≠ 正确使用"这个现象写成 A2 的首次发现。
   - **评估规则不同**:官方 QA 评估按题型用不同规则。**知识更新题允许回答同时
     包含旧信息**,只要正确给出更新信息;**拒答题有专门的不可回答判定**。
     → **C/H/O 不能原样照搬**。不可回答题的正确拒答算 `correct`,**不算 omission**。
   - **标签隔离**:必须屏蔽 `gold`、`has_answer`、`answer_session_ids`、
     `question_type`、以及带 `_abs` 提示的 `question_id`。
     ID 只由外层运行器保管用于结果对齐。
3. **本地无数据则尝试下载**:`datasets` 可用时从 HF 取
   `xiaowu0162/longmemeval-cleaned`(cleaned S 版本,报告推荐)。
   **网络不可用或下载失败 → 立即转阶段 E**,不要反复重试。
4. **最小检索器**(LongMemEval 没有"检索器已返回结果"这一步):
   - 优先纯 Python **TF-IDF + 余弦**(不装新包,约 40 行)
   - `top_k = 20`(固定),**检索一次后冻结**,所有臂共用同一批 `raw_memories`
   - 记录 `recall@k`(对有 `answer_session_ids` 的样本)
5. **评估池 = 全部样本**,**不做** baseline-wrong 过滤(这正是 §9.0 的原则)
6. **锁定数据修订与文件哈希**,写入 `run_config.json`;
   不要与旧版分数混比(cleaned 版移除了影响答案正确性的噪声会话)
7. LongMemEval 的 session 带日期 → 用于验证 §3.3 第 1 层时间路径

### 9.4 预算

每个脚本运行前打印**总调用次数估算**并要求 `--yes`。
在 `RESULTS.md` 报告实际 token 用量。若某阶段估算调用 > 30,000,
**先跑 400 条子集并报告**,不要静默跑全量。

---

## 10. 评估

### 10.1 判定

C / H / O 三分类,沿用 `call_judge`(gold-only judge)。
judge 只读 `(question, gold_answer, model_answer)`,不读 context。缓存。

### 10.2 指标(每个臂 × 每个数据集)

1. **端到端 C / H / O 率**(全池),含绝对数量
2. **相对 B0 的 ΔC / ΔH / ΔO**(百分点),含 Wilson 95% CI
3. **flip rate**(在 `stable_wrong` 子池上 = 由错转对的比例)
4. **转移矩阵** B0 → 各臂,3×3(H/C/O 计数与行内比例)
   —— **必须单列 `O→H` 计数**(把沉默干预成幻觉是最坏的失败)
5. **配对显著性**:各臂 vs B0、B1、B2 的 McNemar 精确检验 p 值
6. **干预率**:A2 的 no-op 比例;以及被 BLOCK 的记忆占比分布
7. **动作分布**:六个动作各被使用了多少次(证明动作空间是被真正使用的,
   而不是退化成单一动作)
8. **校准曲线**:α ∈ {0.05,0.10,0.20,0.30} → cal 阈值 / cal coverage /
   cal noop_err / **test coverage / test noop_err**
9. **λ_O 敏感性**:λ_O ∈ {0.3,0.6,1.0,2.0} 下的 ΔH 与 ΔO(在 400 条子集上跑)

### 10.3 错误分解协议(必做,这是论文的实验节开篇)

在 memos 全池上输出四段分解(逐条归因,可加总回 100%):

| 分段 | 判定条件 |
|---|---|
| **检索失败** | `gold_memory_ids` 不在 `raw_memories` 里 |
| **序列化丢失** | gold 在 `raw_memories` 但在 `context_str_full` 里不出现(用 `visibility.jsonl`) |
| **准入/使用失败** | gold 对 LLM 可见,但 B0 答错 |
| **生成失败** | gold 可见且 `A2`/`ORACLE_REL` 介入后仍答错 |

输出一张表:各段条数与占全池比例。**这是"问题存在且量级够大"的直接证据。**

### 10.4 oracle / learned 归因分解

对同一批样本(全池,或 `stable_wrong ∩ strict_supported`),并列:

| 配置 | Stage 0 | Stage 1 | Stage 2 | Stage 3 | flip rate |
|---|---|---|---|---|---|
| B0 | — | — | — | — | 0(定义) |
| A3(已有) | baseline 抽取 | 神谕(可见 gold) | 神谕(hard map) | 真实 | 46.13% |
| UA3(已有) | 真实 canonical | 神谕(gold_ids) | 神谕(hard map) | 真实 | 53.29% |
| B2(本次) | 真实 | **真实** | 无决策层 | 真实 | ? |
| A2(本次) | 真实 | **真实** | **真实** | 真实 | ? |
| ORACLE_REL | 真实 | 神谕 | 真实 | 真实 | ? |

逐段计算"神谕 → 真实"的**损耗**(每换掉一个神谕阶段掉多少 pp)。
这张表就是"方法不是标签拟合"的证明结构。

### 10.5 估计器内在评估(`24_intrinsic_eval.py`,事后分析)

**只在分析脚本里做,不得进入主流水线。**

- 用 `gold_memory_ids` 构造 oracle 关系(SUPPORT:gold;其余按主关系后验的 argmax 归入
  `SUPERSEDED`/`MISBIND`/`INSUFFICIENT` 中由 `question_type` 提示的那一类;无法判定则跳过)
- 报告 Stage 1 的 `argmax(relation)` 与 oracle 关系的 **accuracy / macro-F1 / 混淆矩阵**
- 报告 `sufficiency` 与"该样本是否真的可被 oracle 修复"的相关性(点二列相关)
- 报告 `risk` 分数在 `B0 答对` vs `B0 答错` 两组上的分布差异(AUC)

---

## 11. 测试与不变量(`test_a2_invariants.py`,必须写并跑通)

用纯 Python 断言,无需 pytest 也可 `python test_a2_invariants.py` 直接执行。
覆盖:

1. **Stage 0 字段完整**:构造一条 `{"memory_value":"v","memory_key":"k","create_time":"2023-01-01"}`,
   断言 `text` 同时含 `v` 与 `k`(**且含字段名前缀**),`ingest_time == "2023-01-01"`,
   `time_is_proxy == True`。
2. **时间三层互斥穷尽**:随机 200 条合成对象,断言 `time_source` 恒为四值之一。
3. **代价矩阵行为**:给定纯后验(六类各一个 one-hot),断言 argmin 结果分别是
   `VOUCH / REFUTE / BLOCK / VOUCH / BLOCK / BLOCK`(**必须与 §5.2 的验算表逐项一致**。
   这是防止平局静默落到 VOUCH 的唯一屏障)。
4. **对冲行为**:后验 `{SUPPORT:0.5, INSUFFICIENT:0.5}` → 断言结果为 `QUALIFY`
   (证明后验加权真的在起作用,而非取 argmax)。
5. **互斥集合裁决**:构造同锚、无时间信号的两条冲突记忆 → 断言两条均为 `QUALIFY`;
   构造有时间信号的新旧两条 → 断言新者为 `VOUCH`、旧者为 `DEMOTE`;
   **构造仅有 `ingest_time` 的两条 → 断言裁决成功且 `decision_note` 含
   `temporal_from_ingest_proxy`**。
6. **聚合集合不被裁决**:构造同锚、不冲突的三条 → 断言三条动作与逐条 argmin 一致。
7. **use/文本锁死**:遍历所有动作,断言 `use=="ASSERT"` ⟺ 渲染时无授权模板注入。
8. **无泄漏**:对全池跑一次泄漏检查,断言 0 命中。
9. **冻结集合**:断言渲染出的每条记忆都能在输入 `raw_memories` 中找到对应条目
   (按 `raw_index` 反查文本 hash)。
10. **门控单调性**:在 cal split 上断言 `noop_err(τ)` 随 τ 单调不减。
11. **池等价性**:断言新池上 B0 判错的样本集合 = 原有 1987 条
    (若不等,报告差异条数,**不要跳过这条检查**)。
12. **分组非退化**:断言 §5.3 的分组在真实数据上产生"组大小 ≥2 的组数 > 0"
    (若为 0,说明分组键设计失效,本节逻辑等于没实现)。

任一条失败 → 修代码,不要修测试。

---

## 12. 交付物:`RESULTS.md`

必须包含以下小节(**数字如实填写,不得美化、不得省略负结果**):

```
# A2 MVP 结果报告

## 0. 环境与配置
   - §1.0 预检结果:可用 LLM 端点清单(仅名称/base_url)、依赖 import 结果
   - 实际使用的生成器 / judge(及为什么是这些;**若只有 1 个,明确说明**)
   - 脚本版本、git commit(若有)、run_config.json 路径

## 0.5 池定义与等价性校验(必填)
   - 新池的构造条件与总条数
   - 池内分层:strict_supported / partial_supported 各多少;
     B0 correct / B0 wrong 各多少
   - **等价性校验结论**:新池上 B0 wrong 是否 == 原有 1987 条?
     若否,列出差异条数并解释可能来源
   - §5.3 的分组统计三数:memory_key 有值率 / entity_anchors 非空率 /
     组大小 ≥2 的组数
   - time_source 分布 + **time_is_proxy=True 占比**

## 1. 阶段 A 冒烟结果(150 条)
   四臂的 C/H/O + 五项验收是否全部通过

## 2. memos 主实验(新池全部)
   - 表:各臂 端到端 C/H/O + ΔC/ΔH/ΔO + Wilson CI
   - 表:各臂 vs B0/B1/B2 的 McNemar p
   - 表:转移矩阵(B0 → 各臂),**单列 O→H**
   - **do-no-harm 小节:在 B0 correct 子池上的 C→H 与 C→O 计数**
     (这是本次修正新增的重点,务必单独报告)
   - 表:动作使用分布(六个动作的计数)
   - 行:A2 的 no-op 率、BLOCK 记忆占比、`degenerate_flag` 是否为 true
   - 小池对照:B0 wrong ∩ strict_supported 上 A3=46.13% / UA3=53.29% vs A2=?

## 3. 错误分解协议
   四段分解表(检索失败 / 序列化丢失 / 准入使用失败 / 生成失败)

## 4. oracle–learned 归因分解
   §10.4 的表 + 每换掉一个神谕阶段的损耗(pp)

## 5. 校准
   α → τ / coverage / noop_err(cal 与 test 并列)

## 6. 消融
   A2-nogate / nosal / nolic / noblock 的 ΔC/ΔH/ΔO

## 7. λ_O 敏感性
   四档 λ_O 下的 ΔH / ΔO

## 8. 估计器内在评估
   accuracy / macro-F1 / 混淆矩阵 / risk 的 AUC

## 9. 跨生成器(或跨记忆系统)
   各生成器下 B1 vs A2 的 ΔC/ΔH/ΔO(控制器固定不变)

## 10. LongMemEval(或阻断说明 + 阶段 E 替代结果)

## 11. 意外发现与失败案例
   - 至少 5 条具体样本:样本 id、问题、A2 做对了什么/做错了什么
   - 被 license 打坏的样本(如有)
   - 任何"结果与预期不符"的现象,如实写,不要隐藏

## 12. 结论与下一步
   - 一句话:Stage 1/2 真实实现后,A2 相对 B1 是多少?
   - 哪些数字支撑"方法不是标签拟合"?
   - 哪些环节是明显短板?
```

---

## 13. 阻断处理(遇到下列情况就停下并报告,不要硬编)

| 情况 | 处置 |
|---|---|
| 缺 `openai` 包 | 停止,报告预检结果 |
| 只有一个 LLM 端点 | **不是阻断**:阶段 D 自动跳过,如实记录,继续其余阶段 |
| 找不到 memos 样本池 / visibility.jsonl | 停止,报告缺失文件路径 |
| 新池 B0 wrong ≠ 原有 1987 条 | **不阻断**:报告差异条数,以新池为准,继续 |
| `00_verify_serializer.py` 未通过 | 停止,不要绕过 |
| 阶段 A 中某臂全为同一动作 | 停止,检查 §5.2 代价矩阵是否逐字抄对了 |
| 门控 `degenerate_flag = true` | **不阻断**:照常跑完,但必须在 RESULTS.md 显著标注 |
| §5.3 分组统计显示"组大小 ≥2 的组数 = 0" | **不阻断**:如实报告"集合级裁决未触发",继续 |
| LongMemEval 不可得且无网络 | 转阶段 E,在 RESULTS.md 明确写阻断原因 |
| 泄漏检查命中 | 修模板后重跑;不得放宽检查 |
| 预算估算 > 30,000 调用且非分阶段 | 改跑 400 条子集并报告 |

**任何时候都不要为了让数字好看而修改:泄漏检查、冻结原则校验、
门控校准的划分、B1 的强度、以及 §5.2 的代价矩阵数值。**

---

## 14. 执行顺序速查

```bash
# 0) 环境预检(§1.0,必做;结果写进 RESULTS.md 第 0 节)
python -c "import openai, dotenv; print('ok')"     # 逐个包试 import
# 打印可用端点清单(只打印变量名与 base_url)

# 1) 前置校验(已有脚本,只需确认通过)
python 00_verify_serializer.py

# 2) 构建池(§9.0 新定义:按检索条件,不按 baseline 对错)
python 20_build_pool.py --dataset memos            # 内含 B0 等价性校验
python 20_build_pool.py --dataset longmemeval      # 失败则记录并继续

# 3) 分组统计 + 单元测试(必须先全绿)
python a2_stage2_decision.py --probe-groups        # §5.3 的分组统计
python test_a2_invariants.py

# 4) 阶段 A 冒烟(样本需同时含 B0 correct 与 B0 wrong)
python 21_run_generation.py --pool memos --arm B0,B1,B2,A2 --limit 150 --generator deepseek-chat --yes
python 22_judge.py          --pool memos --arm B0,B1,B2,A2 --limit 150
python 23_analyze.py        --pool memos --smoke

# 5) 校准(用全池,split 在脚本内部完成)
python a2_calibrate.py --pool memos --alpha 0.10

# 6) 阶段 B 主实验
python 21_run_generation.py --pool memos --arm B0,B1,B2,A2,A2-nogate,A2-nosal,A2-nolic,A2-noblock --generator deepseek-chat --yes
python 22_judge.py          --pool memos --arm B0,B1,B2,A2,A2-nogate,A2-nosal,A2-nolic,A2-noblock
python 23_analyze.py        --pool memos
python 24_intrinsic_eval.py --pool memos

# 7) 阶段 C / E
python 21_run_generation.py --pool longmemeval --arm B1,A2 --generator deepseek-chat --yes
python 22_judge.py          --pool longmemeval --arm B1,A2
python 23_analyze.py        --pool longmemeval

# 8) 阶段 D 跨生成器(仅当 §1.0 预检发现 ≥2 个端点;否则跳过并记录)
python 21_run_generation.py --pool memos --arm B1,A2 --subset 400 --generator <all-available> --yes
python 22_judge.py          --pool memos --arm B1,A2 --subset 400

# 9) 汇总
python 23_analyze.py --report
```

**最后:把 `outputs/a2_mvp_v1/RESULTS.md` 完整内容返回给我。
如果任何阶段被阻断,仍然要返回已完成部分的 `RESULTS.md`,
并在第 10 / 11 / 13 节写清阻断原因。**
