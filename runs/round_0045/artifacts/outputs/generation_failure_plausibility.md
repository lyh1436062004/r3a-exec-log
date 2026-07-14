# Is A 19.17% DeepSeek Generation-Failure Rate Plausible?

## Short answer

The observed count is plausible, but it should not yet be interpreted as a pure model-generation
failure rate. `381/1987 = 19.17%` uses all baseline-error cases as the denominator. The model actually
had baseline-visible strict evidence in 763 cases, so the conditional non-rescue rate is
`381/763 = 49.93%`. A near-50% failure rate would be unexpectedly high if every UA3 context contained
complete, unambiguous, answer-sufficient oracle evidence.

## Why the current label likely overestimates pure generation failure

1. `strict_supported` only requires at least one retrieved memory to fully support at least one gold
   evidence item. It does not establish that the admitted memories jointly contain everything needed
   to derive the complete gold answer.
2. UA3 admits semantic matches to gold evidence, not the benchmark's original gold-evidence text.
   Deep paraphrases can preserve a relation while dropping timestamps, entities, conditions, or
   multi-hop links needed by the question.
3. The answer prompt enforces an answer under 5-6 words. This can turn partially correct explanatory
   answers into omissions or semantic judge failures, especially for conditional and temporal cases.
4. The generator and gold-only judge are both `deepseek-chat`, so shared model biases are not an
   independent correctness check. The 97% judge self-agreement measures repeatability, not validity.
5. The result is based on one answer generation per condition. Temperature zero does not prove that
   the hosted service is bitwise deterministic.
6. The experiment records the requested alias (`deepseek-chat`) but not `response.model`, so the exact
   server-side snapshot is not recoverable from saved rows.

## Failure distribution in the 763 baseline-visible strict cases

| Question type | UA3 failures / n | Failure rate |
|---|---:|---:|
| Basic Fact Recall | 75 / 148 | 50.68% |
| Generalization & Application | 183 / 348 | 52.59% |
| Multi-hop Inference | 54 / 89 | 60.67% |
| Memory Conflict | 40 / 128 | 31.25% |
| Dynamic Update | 29 / 50 | 58.00% |

The high Basic Fact Recall failure rate is especially inconsistent with a clean interpretation of all
381 cases as intrinsic model incapability.

## Model-version caveat

The experiment was run on 2026-07-14 with the alias `deepseek-chat`. DeepSeek's official documentation
states that, during this period, `deepseek-chat` maps to the non-thinking mode of
`deepseek-v4-flash`; the alias is scheduled for deprecation on 2026-07-24. Because the code did not
save the server-returned model identifier, this mapping is inferred from the official service
documentation rather than proven by the experiment artifact.

## Recommended isolation experiment

Add a direct-gold-evidence oracle condition:

- Context contains the benchmark gold-evidence text verbatim, preserving timestamps and speaker IDs.
- Do not include the gold answer.
- Keep the QA prompt fixed, but separately test the 5-6-word restriction.
- Pin `deepseek-v4-flash` rather than the rolling `deepseek-chat` alias.
- Save `response.model` from every API response.
- Generate three responses per case.
- Use an independent judge model plus a stratified human audit.
- Call a case robust generation failure only when an evidence-sufficiency audit passes and all three
  generations remain non-correct.

If a case succeeds with verbatim gold evidence, the prior UA3 failure belongs to representation,
evidence sufficiency, or admission rather than pure generation. Only the residual failures support a
strong generation-failure claim.

## Official sources

- DeepSeek models and alias mapping: https://api-docs.deepseek.com/quick_start/pricing/
- DeepSeek API change log: https://api-docs.deepseek.com/updates/
