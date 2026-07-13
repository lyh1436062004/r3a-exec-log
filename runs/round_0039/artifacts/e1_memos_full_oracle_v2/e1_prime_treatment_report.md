# E1-prime A1-A5 Treatment Report

## Analysis population

- Source population: 1,987 MemOS baseline-error samples (989 medium + 998 long).
- A0 replay non-correct: 1,951/1,987 (98.19%).
- Gold evidence visible in the exact serialized LLM context: 763.
- Primary E1-prime population: `visible_supported AND A0 non-correct`, 737 samples.
- A1-A5 generation and judging coverage: 737/737 valid paired cases per arm.
- The treatment arms were intentionally not run on samples outside this 737-case population. Consequently, legacy `full_pool` and `retrieved_strict` rows in the generic analyzer are observed-case rows, not estimates for all 1,951 or 867 cases. The primary result is the `visible_supported` row.

## Primary flip rates

| Arm | Correct flips | Denominator | Flip rate | Wilson 95% CI |
|---|---:|---:|---:|---:|
| A1 | 86 | 737 | 11.67% | [9.55%, 14.19%] |
| A2 | 301 | 737 | 40.84% | [37.35%, 44.43%] |
| A3 | 340 | 737 | 46.13% | [42.56%, 49.74%] |
| A4 | 69 | 737 | 9.36% | [7.46%, 11.68%] |
| A5 | 176 | 737 | 23.88% | [20.94%, 27.09%] |

The new E1-prime headline is therefore **340/737 = 46.13%**, replacing the replay-confounded pilot value of 268/598 = 44.82%. Under the preregistered interpretation rule, 46.13% lies in the 40-60% "viable" range, not the greater-than-60% "strong" range.

## Paired effects

- A3 versus A2 (license increment after filtering): 47 cases improved and 8 regressed; net +39 cases, +5.29 percentage points; exact McNemar p = 8.07e-8.
- A3 versus A1 (filtering plus license versus position only): 283 cases improved and 29 regressed; net +254 cases, +34.46 percentage points; exact McNemar p = 1.69e-53.
- A4 versus A0 (license only in the unfiltered context): 69 improved and 0 regressed; +9.36 percentage points; exact McNemar p = 3.39e-21.
- A5 versus A4 (unified vouch increment): 107 improved and 0 regressed; +14.52 percentage points; exact McNemar p = 1.23e-32.

## License stratification

Among the 737 eligible cases, 170 received a REFUTE, SELECT, or CONDITION license and 567 were ASSERT-only under A3/A4.

- Licensed subset: A2 66/170 (38.82%) versus A3 106/170 (62.35%). The paired comparison has 45 A3-only successes and 5 A2-only successes (McNemar p = 4.21e-9).
- ASSERT-only subset: A2 235/567 (41.45%) versus A3 234/567 (41.27%), showing no positive license increment because ASSERT adds no authorization text.
- Judge stability rerun: 198/200 agreement (99.00%).

## Integrity checks

- Generation: every arm has 737 successful rows, zero failed rows, and the same 737 unique case IDs.
- Judging: eight transient failures were retained as audit history and successfully retried; every arm has 737 unique successful verdicts over the same case set.
- Analysis completed with the strict coverage check enabled.
