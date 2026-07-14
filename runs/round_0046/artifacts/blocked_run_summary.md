# Gold-Evidence Generation-Failure Experiment: Blocked Run

## Status

The experiment implementation is ready, but the required independent judge endpoint failed its
mandatory smoke test. No batch generation or judging calls were started, and no final human-audit
workbook was created from fabricated or partial results.

## Completed offline work

- Candidate invariant passed: 381 cases (Medium 190, Long 191).
- Gold-evidence invariant passed: 793 items, all parsed without loss.
- Generation prompt contains only structured gold evidence and the question; code does not insert the
  `gold_answer` field.
- DeepSeek smoke passed and returned `deepseek-v4-flash` as the server model.
- Generation, sufficiency judging, answer judging, caching, model-identity checking, analysis, Wilson
  intervals, grouped reports, and failure recording are implemented.
- The five-sheet audit workbook was built with synthetic 381-case / 1,143-call data. Formula-error
  scanning returned zero matches and all five representative sheet views rendered successfully.

## Blocking API result

- `GET /v1/models` authenticates successfully and lists exactly `gpt-5.5`.
- Minimal `gpt-5.5` inference requests return HTTP 403 with `bad_response_status_code`.
- The same 403 occurs for Chat Completions and Responses APIs, with and without streaming, and without
  optional temperature/token/JSON parameters.
- The failure is therefore upstream authorization or channel routing, not a prompt or request-parameter
  incompatibility that the experiment can safely work around.

## Required external change

The relay channel must allow an actual inference request for `gpt-5.5` using the supplied connection.
Once fixed, rerun the smoke test. The existing cache-safe command will then proceed through all 2,667
planned calls and build the final workbook at:

`D:\幻觉\临时\人工审查\审查生成错误率\generation_failure_381人工审核.xlsx`

No API key is stored in this report or any experiment artifact.
