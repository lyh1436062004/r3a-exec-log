# Unified Parsing Discussion Task

- Correct task ID: `019f5a17-07a2-7c51-81d0-e33a5736f272`
- Exact discussion turn ID: `019f5ad5-1477-7121-9625-092cbfd5ba87`
- Incorrect execution-fork task ID: `019f6b34-9dc0-7081-9bdb-8791d8ecb625`
- App navigation: completed

The matching user question asks why post-retrieval admission omitted memories and whether adding authorization to raw memory would still allow omission.

The matching answer identifies the schema mismatch between fact-memory fields and preference-memory fields, then gives the unified path:

`retriever -> raw_memories -> schema normalizer -> admission/authorization -> canonical serializer -> context -> LLM`

This is the discussion task about how unified raw-memory parsing is achieved. It is distinct from the later worktree task that executes unified UA1-UA5 experiments.
