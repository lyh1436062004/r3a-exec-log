# LongCat-2.0 judge compatibility smoke test

- Date: 2026-07-15
- Official OpenAI-compatible base URL: `https://api.longcat.chat/openai/v1`
- Requested model: `LongCat-2.0`
- Credential handling: process environment only; no key persisted

## Endpoint and model

- Model listing succeeded and returned one model: `LongCat-2.0`.
- A basic Chat Completions request succeeded.
- The server-returned model was exactly `LongCat-2.0`.

## Thinking and JSON behavior

- The default request produced `reasoning_content` and reported reasoning tokens.
- Sending `thinking.type=disabled` removed `reasoning_content`.
- With thinking disabled, `response_format={"type":"json_object"}` returned parseable JSON.

## Real experiment-prompt smoke tests

| Request | Result | Valid enum | response.model | reasoning_content |
|---|---|---|---|---|
| Evidence sufficiency | success | `sufficient` | `LongCat-2.0` | absent |
| Generated-answer judgment | success | `omission` | `LongCat-2.0` | absent |

Both tests used the experiment's actual prompt builders and real case records.

## Experimental implication

LongCat-2.0 is technically compatible with the independent-judge protocol. It should not be used only for the 642 judgments missing from the partial Qwen run, because mixing judge models would confound the classification. A protocol switch to LongCat-2.0 requires rerunning all 381 evidence-sufficiency judgments and all 1,143 answer judgments under LongCat while reusing the already valid 1,143 DeepSeek non-thinking generations.
