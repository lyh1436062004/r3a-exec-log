# Alibaba Cloud Model Studio workspace smoke test

- Date: 2026-07-15
- Base URL: `https://ws-jwstivtbj2cmr65l.cn-beijing.maas.aliyuncs.com/compatible-mode/v1`
- Credential handling: process environment only; no key persisted
- Model-list result: HTTP 200, 227 model IDs
- GPT-family models listed: 0

## Inference verification

### Chat Completions

| Requested model | Result | Server response.model | Output |
|---|---|---|---|
| `qwen3.7-max` | success | `qwen3.7-max` | `OK` |
| `glm-5.2` | success | `glm-5.2` | `OK` |
| `deepseek-v4-flash` | success | `deepseek-v4-flash` | `OK` |

### Responses API

| Requested model | Result |
|---|---|
| `qwen3.7-max` | success; exact server model returned |
| `glm-5.2` | unsupported by this protocol |
| `deepseek-v4-flash` | unsupported by this protocol |

### Judge protocol

`qwen3.7-max` successfully returned parseable JSON with `temperature=0` and `response_format={"type":"json_object"}`. It is therefore technically compatible with the experiment's independent-judge request format.

## Relevant text-model families

- Qwen: `qwen3.7-max`, `qwen3.7-plus`, `qwen3.6-plus`, `qwen3.5-plus`, `qwen3-max`, `qwen-plus`, and dated snapshots.
- DeepSeek: `deepseek-v4-flash`, `deepseek-v4-pro`, `deepseek-v3.2`, `deepseek-v3.1`, `deepseek-r1`, and provider variants.
- GLM: `glm-5.2`, `glm-5.1`, `glm-5`, `glm-4.7`, and ZHIPU variants.
- Kimi: `kimi-k2.7-code`, `kimi-k2.6`, `kimi-k2.5`, `kimi-k2-thinking`, and provider variants.
- MiniMax: `MiniMax-M3`, `MiniMax-M2.7`, `MiniMax-M2.5`, and `MiniMax-M2.1` variants.

The full server-returned ID list is saved separately. Model-list presence does not guarantee support by every wire protocol; the three Chat Completions smoke calls above are directly verified.

## Experiment recommendation

Use `qwen3.7-max` as the independent judge only if the protocol is explicitly amended from `gpt-5.5` to `qwen3.7-max`. It is a different model family from the fixed DeepSeek generator and has passed the required JSON-output smoke test.
