# E1 Memos Full Oracle Results

- samples: 1987
- A0 judged: 1987
- stable_wrong: 1573
- retrieved_strict stable_wrong: 598
- A0 replay non-correct rate: 79.16%
- replay unstable: True

## Flip Rates

| pool | condition | n | correct | flip_rate | Wilson 95% CI |
|---|---|---:|---:|---:|---|
| full_pool | A1 | 1573 | 72 | 4.58% | [3.65%, 5.73%] |
| full_pool | A2 | 1573 | 246 | 15.64% | [13.93%, 17.52%] |
| full_pool | A3 | 1573 | 272 | 17.29% | [15.50%, 19.24%] |
| full_pool | A4 | 1573 | 60 | 3.81% | [2.97%, 4.88%] |
| retrieved_strict | A1 | 598 | 65 | 10.87% | [8.62%, 13.62%] |
| retrieved_strict | A2 | 598 | 242 | 40.47% | [36.61%, 44.45%] |
| retrieved_strict | A3 | 598 | 268 | 44.82% | [40.88%, 48.82%] |
| retrieved_strict | A4 | 598 | 55 | 9.20% | [7.13%, 11.78%] |

## McNemar

| pool | comparison | n | b | c | p_value |
|---|---|---:|---:|---:|---:|
| full_pool | A3_vs_A1 | 1573 | 226 | 26 | 5.5562e-41 |
| full_pool | A3_vs_A2 | 1573 | 38 | 12 | 0.000305864 |
| full_pool | A4_vs_A0 | 1573 | 60 | 0 | 1.73472e-18 |
| retrieved_strict | A3_vs_A1 | 598 | 222 | 19 | 4.44775e-45 |
| retrieved_strict | A3_vs_A2 | 598 | 38 | 12 | 0.000305864 |
| retrieved_strict | A4_vs_A0 | 598 | 55 | 0 | 5.55112e-17 |
