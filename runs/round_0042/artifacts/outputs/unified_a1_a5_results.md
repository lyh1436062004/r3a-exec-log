# Unified Parsing A1-A5 Results

All UA arms use the complete raw-memory payload and the same canonical serializer as A6.
The denominator is the 867 strict-supported cases that remained non-correct under exact A0 replay.
Judge self-agreement is reported separately; exact McNemar p-values below are unadjusted for multiple comparisons.

## Conditions

- A6: canonicalize and admit all raw memories in retrieval order; no labels.
- UA1: A6 plus oracle gold-first ordering.
- UA2: canonicalize and retain oracle gold memories only.
- UA3: UA2 plus relation-specific evidence licenses.
- UA4: A6 plus relation-specific licenses on oracle gold memories.
- UA5: UA4 plus VOUCH on oracle gold memories otherwise labeled ASSERT.

## Main Recovery Rates

| condition | correct / n | recovery rate |
|---|---:|---:|
| A6 | 271 / 867 | 31.26% |
| UA1 | 278 / 867 | 32.06% |
| UA2 | 425 / 867 | 49.02% |
| UA3 | 462 / 867 | 53.29% |
| UA4 | 300 / 867 | 34.60% |
| UA5 | 339 / 867 | 39.10% |

## Primary Paired Comparisons

| comparison | b | c | delta | exact p |
|---|---:|---:|---:|---:|
| UA1_vs_A6 | 86 | 79 | +0.81% | 0.640562 |
| UA2_vs_UA1 | 221 | 74 | +16.96% | 3.66033e-18 |
| UA3_vs_UA2 | 51 | 14 | +4.27% | 4.47522e-06 |
| UA4_vs_A6 | 72 | 43 | +3.34% | 0.00873511 |
| UA5_vs_A6 | 120 | 52 | +7.84% | 2.28496e-07 |
| UA5_vs_UA4 | 78 | 39 | +4.50% | 0.000396178 |

## Full Strict Pool Accuracy (Supplementary)

This includes the 29 strict cases that A0 replay judged correct, so regressions are observable.

| condition | correct / n | accuracy | vs A0 b | vs A0 c | net delta | exact p |
|---|---:|---:|---:|---:|---:|---:|
| A0 | 29 / 896 | 3.24% | - | - | - | - |
| A6 | 293 / 896 | 32.70% | 271 | 7 | +29.46% | 9.97214e-71 |
| UA1 | 298 / 896 | 33.26% | 278 | 9 | +30.02% | 2.66538e-70 |
| UA2 | 443 / 896 | 49.44% | 425 | 11 | +46.21% | 2.76217e-110 |
| UA3 | 480 / 896 | 53.57% | 462 | 11 | +50.33% | 4.9625e-121 |
| UA4 | 325 / 896 | 36.27% | 300 | 4 | +33.04% | 2.1696e-83 |
| UA5 | 364 / 896 | 40.62% | 339 | 4 | +37.39% | 6.40041e-95 |

## By Visibility Stratum

| pool | condition | correct / n | recovery rate |
|---|---|---:|---:|
| visible_supported | A6 | 202 / 737 | 27.41% |
| visible_supported | UA1 | 210 / 737 | 28.49% |
| visible_supported | UA2 | 330 / 737 | 44.78% |
| visible_supported | UA3 | 367 / 737 | 49.80% |
| visible_supported | UA4 | 230 / 737 | 31.21% |
| visible_supported | UA5 | 266 / 737 | 36.09% |
| serialization_loss | A6 | 69 / 130 | 53.08% |
| serialization_loss | UA1 | 68 / 130 | 52.31% |
| serialization_loss | UA2 | 95 / 130 | 73.08% |
| serialization_loss | UA3 | 95 / 130 | 73.08% |
| serialization_loss | UA4 | 70 / 130 | 53.85% |
| serialization_loss | UA5 | 73 / 130 | 56.15% |

## By Dataset

| dataset | condition | correct / n | recovery rate |
|---|---|---:|---:|
| long | A6 | 139 / 437 | 31.81% |
| long | UA1 | 138 / 437 | 31.58% |
| long | UA2 | 220 / 437 | 50.34% |
| long | UA3 | 234 / 437 | 53.55% |
| long | UA4 | 154 / 437 | 35.24% |
| long | UA5 | 160 / 437 | 36.61% |
| medium | A6 | 132 / 430 | 30.70% |
| medium | UA1 | 140 / 430 | 32.56% |
| medium | UA2 | 205 / 430 | 47.67% |
| medium | UA3 | 228 / 430 | 53.02% |
| medium | UA4 | 146 / 430 | 33.95% |
| medium | UA5 | 179 / 430 | 41.63% |

## Unified vs Original A1-A5 (Same 737 Cases)

| comparison | old | unified | delta | b | c | exact p |
|---|---:|---:|---:|---:|---:|---:|
| UA1_vs_A1 | 86/737 (11.67%) | 210/737 (28.49%) | +16.82% | 150 | 26 | 2.16241e-22 |
| UA2_vs_A2 | 301/737 (40.84%) | 330/737 (44.78%) | +3.93% | 75 | 46 | 0.0106115 |
| UA3_vs_A3 | 340/737 (46.13%) | 367/737 (49.80%) | +3.66% | 66 | 39 | 0.0108179 |
| UA4_vs_A4 | 69/737 (9.36%) | 230/737 (31.21%) | +21.85% | 173 | 12 | 1.02042e-37 |
| UA5_vs_A5 | 176/737 (23.88%) | 266/737 (36.09%) | +12.21% | 138 | 48 | 2.76078e-11 |
