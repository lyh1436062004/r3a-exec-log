# R3a-v2.2 Triggered Utility Evaluation

## Scope

- Triggered samples evaluated: 78
- All samples are Memory Conflict: True
- All samples reselected by R3a-v2.2: True
- R0 uses cached baseline response/label from the QA file.
- A_triggered uses the AB5 generic conflict-warning prompt without selected evidence.
- B_triggered admits only R3a-v2.2 selected evidence.
- B_memory_only was skipped by design.

## Route Label Counts

| route | correct | hallucination | omission |
|---|---:|---:|---:|
| R0 | 34 | 9 | 35 |
| A_triggered | 44 | 24 | 10 |
| B_triggered | 36 | 8 | 34 |

## Deltas

| comparison | delta correct | delta hallucination | delta omission | repairs | harm | net repairs |
|---|---:|---:|---:|---:|---:|---:|
| B_vs_R0 | +0.026 | -0.013 | -0.013 | 12 | 10 | 2 |
| B_vs_A | -0.103 | -0.205 | +0.308 | 5 | 13 | -8 |

## Paired Tests

| comparison | label | b | c | p_two_sided |
|---|---|---:|---:|---:|
| R0_vs_B | correct | 10 | 12 | 0.831812 |
| R0_vs_B | hallucination | 6 | 5 | 1.000000 |
| R0_vs_B | omission | 13 | 12 | 1.000000 |
| A_vs_B | correct | 13 | 5 | 0.096252 |
| A_vs_B | hallucination | 17 | 1 | 0.000145 |
| A_vs_B | omission | 0 | 24 | 0.000000 |

## Cache And Generation

```json
{
  "generated": {
    "a_answer": 0,
    "a_judge": 0,
    "b_answer": 76,
    "b_judge": 76
  },
  "reused": {
    "a_old_ab5": 78,
    "b_v2_cache": 2,
    "existing_output": 0
  }
}
```
