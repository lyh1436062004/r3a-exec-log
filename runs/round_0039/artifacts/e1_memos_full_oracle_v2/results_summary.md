# E1 Memos Full Oracle Results

- samples: 1987
- A0 judged: 1987
- stable_wrong: 1951
- retrieved_strict stable_wrong: 867
- visible_supported stable_wrong: 737
- serialization_loss stable_wrong: 130
- A0 replay non-correct rate: 98.19%
- replay unstable: False

## Flip Rates

| pool | condition | n | correct | flip_rate | Wilson 95% CI |
|---|---|---:|---:|---:|---|
| full_pool | A1 | 737 | 86 | 11.67% | [9.55%, 14.19%] |
| full_pool | A2 | 737 | 301 | 40.84% | [37.35%, 44.43%] |
| full_pool | A3 | 737 | 340 | 46.13% | [42.56%, 49.74%] |
| full_pool | A4 | 737 | 69 | 9.36% | [7.46%, 11.68%] |
| full_pool | A5 | 737 | 176 | 23.88% | [20.94%, 27.09%] |
| retrieved_strict | A1 | 737 | 86 | 11.67% | [9.55%, 14.19%] |
| retrieved_strict | A2 | 737 | 301 | 40.84% | [37.35%, 44.43%] |
| retrieved_strict | A3 | 737 | 340 | 46.13% | [42.56%, 49.74%] |
| retrieved_strict | A4 | 737 | 69 | 9.36% | [7.46%, 11.68%] |
| retrieved_strict | A5 | 737 | 176 | 23.88% | [20.94%, 27.09%] |
| visible_supported | A1 | 737 | 86 | 11.67% | [9.55%, 14.19%] |
| visible_supported | A2 | 737 | 301 | 40.84% | [37.35%, 44.43%] |
| visible_supported | A3 | 737 | 340 | 46.13% | [42.56%, 49.74%] |
| visible_supported | A4 | 737 | 69 | 9.36% | [7.46%, 11.68%] |
| visible_supported | A5 | 737 | 176 | 23.88% | [20.94%, 27.09%] |
| serialization_loss | A1 | 0 | 0 | 0.00% | [0.00%, 0.00%] |
| serialization_loss | A2 | 0 | 0 | 0.00% | [0.00%, 0.00%] |
| serialization_loss | A3 | 0 | 0 | 0.00% | [0.00%, 0.00%] |
| serialization_loss | A4 | 0 | 0 | 0.00% | [0.00%, 0.00%] |
| serialization_loss | A5 | 0 | 0 | 0.00% | [0.00%, 0.00%] |

## McNemar

| pool | comparison | n | b | c | p_value |
|---|---|---:|---:|---:|---:|
| full_pool | A3_vs_A1 | 737 | 283 | 29 | 1.68657e-53 |
| full_pool | A3_vs_A2 | 737 | 47 | 8 | 8.06761e-08 |
| full_pool | A4_vs_A0 | 737 | 69 | 0 | 3.38813e-21 |
| full_pool | A5_vs_A0 | 737 | 176 | 0 | 2.0881e-53 |
| full_pool | A5_vs_A4 | 737 | 107 | 0 | 1.2326e-32 |
| full_pool | A5_vs_A2 | 737 | 65 | 190 | 2.18624e-15 |
| retrieved_strict | A3_vs_A1 | 737 | 283 | 29 | 1.68657e-53 |
| retrieved_strict | A3_vs_A2 | 737 | 47 | 8 | 8.06761e-08 |
| retrieved_strict | A4_vs_A0 | 737 | 69 | 0 | 3.38813e-21 |
| retrieved_strict | A5_vs_A0 | 737 | 176 | 0 | 2.0881e-53 |
| retrieved_strict | A5_vs_A4 | 737 | 107 | 0 | 1.2326e-32 |
| retrieved_strict | A5_vs_A2 | 737 | 65 | 190 | 2.18624e-15 |
| visible_supported | A3_vs_A1 | 737 | 283 | 29 | 1.68657e-53 |
| visible_supported | A3_vs_A2 | 737 | 47 | 8 | 8.06761e-08 |
| visible_supported | A4_vs_A0 | 737 | 69 | 0 | 3.38813e-21 |
| visible_supported | A5_vs_A0 | 737 | 176 | 0 | 2.0881e-53 |
| visible_supported | A5_vs_A4 | 737 | 107 | 0 | 1.2326e-32 |
| visible_supported | A5_vs_A2 | 737 | 65 | 190 | 2.18624e-15 |
