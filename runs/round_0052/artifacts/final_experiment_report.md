# Gold Evidence Direct Generation-Failure Review Experiment

## Final protocol

- Candidate pool: 381 original UA3 failures with `strict_supported` retrieval and `visible_supported` context.
- Dataset split: Medium 190, Long 191.
- Gold evidence: 793 items, parsed structurally with zero failures and used verbatim as the only evidence context.
- Generator: `deepseek-v4-flash`, `thinking=disabled`, `temperature=0`, `max_tokens=128`, three independent calls per case.
- Answer format: the original MEMOS prompt and 5–6 word constraint were preserved.
- Independent judge: `LongCat-2.0`, `thinking=disabled`, `temperature=0`, JSON Object output.
- Uniform judge coverage: 381 evidence-sufficiency judgments and 1,143 answer judgments.

## Coverage verification

| Record type | Expected | Valid unique records | Failed or unresolved |
|---|---:|---:|---:|
| Candidates | 381 | 381 | 0 |
| Generations | 1,143 | 1,143 | 0 |
| Evidence sufficiency | 381 | 381 | 0 |
| Answer judgments | 1,143 | 1,143 | 0 |

All valid generation records returned `deepseek-v4-flash`; all valid judge records returned `LongCat-2.0`. Both models were run with thinking disabled. Corrected generations contained zero empty visible answers and zero records with positive reasoning tokens.

One LongCat JSON grammar request failed with HTTP 400 and was successfully rerun. The historical failure remains in the failure log, but the case/replicate has a valid final judgment and is not unresolved.

## Machine classification

| Final class | Count | Share of 381 |
|---|---:|---:|
| `robust_generation_failure` | 151 | 39.63% |
| `generation_instability` | 4 | 1.05% |
| `ua3_representation_or_admission_failure` | 144 | 37.80% |
| `evidence_definition_failure` | 82 | 21.52% |
| `unresolved` | 0 | 0.00% |

Among the 299 cases that LongCat judged to have sufficient gold evidence, 151 (50.50%) remained incorrect in all three DeepSeek generations, 4 were unstable, and 144 were correct in all three generations.

## Robust generation-failure rates

| Denominator | Count | Rate | Wilson 95% CI |
|---|---:|---:|---:|
| 381 candidate cases | 151/381 | 39.63% | [34.85%, 44.62%] |
| 763 visible-strict cases | 151/763 | 19.79% | [17.12%, 22.77%] |
| 1,987 baseline errors | 151/1,987 | 7.60% | [6.51%, 8.85%] |

## Dataset split

| Dataset | Cases | Robust failure | Instability | UA3 representation/admission | Evidence definition |
|---|---:|---:|---:|---:|---:|
| Medium | 190 | 75 | 2 | 74 | 39 |
| Long | 191 | 76 | 2 | 70 | 43 |

## Important provenance

The first DeepSeek run was invalidated because `deepseek-v4-flash` defaults to thinking mode. With a 128-token budget, 655/1,143 visible answers were empty and 649 had consumed the entire budget as reasoning tokens. Its apparent count of 205 robust failures must not be reported.

The partial Qwen run was also excluded from the primary result after its free quota expired. All primary sufficiency and answer judgments were rerun uniformly with LongCat-2.0; no judge models were mixed.

## Human review status

The classifications above are machine-judge estimates. The accompanying workbook contains all 381 cases in deterministic random order for blinded human review. Machine judgments are isolated on a separate sheet and should not be opened until the human labels are complete.
