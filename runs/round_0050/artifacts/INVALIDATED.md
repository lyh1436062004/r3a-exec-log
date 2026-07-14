# Invalidated default-thinking run

This archived run is not a valid result of the intended gold-evidence generation-failure experiment.

## Reason

`deepseek-v4-flash` defaults to thinking mode unless the request explicitly sends `thinking.type=disabled`. The first formal run omitted that switch while retaining `max_tokens=128`.

- 655/1,143 generations had empty visible `content`.
- 649 of those empty responses consumed exactly 128 completion tokens.
- Their completion-token details reported all 128 as reasoning tokens.

The resulting automatic count of 205 robust generation failures was therefore inflated by exhausted reasoning budgets and must not be reported as the experiment result.

## Correction

The rerun explicitly sends `extra_body={"thinking":{"type":"disabled"}}`, keeps `deepseek-v4-flash`, `temperature=0`, `max_tokens=128`, the original 5–6 word answer constraint, the same 381 candidates, and the same `qwen3.7-max` independent judge.
