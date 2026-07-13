# E1-prime A0-exact Checkpoint

## Decision

**PASS.** The exact-replay checkpoint is valid for proceeding to treatment design. A0 non-correct replay rate is 98.19%, above the 90% stop threshold.

## Offline Gate

- Samples: 1,987
- Serializer byte-exact: 1,987/1,987
- Visible-supported: 763
- Serialization-loss: 133
- Partial-supported: 233
- No gold retrieved: 858

## A0 Generation And Judge

- Successful A0 generations: 1,987/1,987
- Unique successful A0 verdicts: 1,987/1,987
- Historical failed judge rows retained in append log: 4; every case was eventually completed successfully
- Judge stability rerun: 200/200 agreement (100%)

## Replay Results

- A0 non-correct: 1,951/1,987 (98.19%)
- A0 correct: 36/1,987 (1.81% replay flip/noise)
- Memos Medium non-correct: 973/989 (98.38%)
- Memos Long non-correct: 978/998 (98.00%)

By visibility stratum:

| Stratum | N | A0 non-correct | Rate |
|---|---:|---:|---:|
| visible_supported | 763 | 737 | 96.59% |
| serialization_loss | 133 | 130 | 97.74% |
| partial_supported | 233 | 231 | 99.14% |
| no_gold_retrieved | 858 | 853 | 99.42% |

The treatment-eligible usage-gap pool is therefore `visible_supported AND A0 non-correct`, containing 737 samples.

## Usage

- A0 generation tokens: 1,548,001
- Main judge tokens: 410,476
- Stability rerun tokens: 41,349
- Total: 1,999,826 tokens

## Known Judge Anomaly

For `memos_long:3466`, the successful judge row has `judge_label=hallucination` while its rationale concludes that the answer `No.` matches the gold answer and should be correct. The raw row is preserved and not manually overwritten. This one-case inconsistency changes the aggregate replay rate by approximately 0.05 percentage points and does not affect the checkpoint decision.

## Scope

Only the requested offline gate, A0-exact generation, A0 judge, stability rerun, and A0 analysis were executed. A1-A5 were not launched.
